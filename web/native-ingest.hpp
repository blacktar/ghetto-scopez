#pragma once
#include <node_api.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cerrno>
#include <poll.h>
#include <atomic>
#include <thread>
#include <string>
#include <memory>
#include <cstring>
#include <stdexcept>
#include <chrono>
#include <cstdlib>
#include <time.h>
#include <unordered_map>
#include <mutex>
namespace ingest {
static bool diagnostics(){static const bool enabled=[] {const char*v=std::getenv("SCOPE_DIAGNOSTICS");return v&&std::strcmp(v,"1")==0;}();return enabled;}
static uint64_t nowNs(){if(!diagnostics())return 0;return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
struct Metrics{std::atomic<uint64_t> count{0},allocate{0},read{0},queue{0},dispatch{0},callback{0},wrap{0};};static Metrics metrics;
struct Packet{uint8_t*data;size_t size;uint64_t readDone=0;~Packet(){delete[]data;}};
struct Receiver{int listener=-1;std::atomic<int> peer{-1};std::atomic<bool> running{true};napi_threadsafe_function callback=nullptr;std::thread thread;std::string path;};
static std::unique_ptr<Receiver> receiver;static napi_env ownerEnv=nullptr;
static uint32_t word(const uint8_t*p){return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
static bool readAll(int fd,uint8_t*p,size_t n){while(n){auto k=recv(fd,p,n,0);if(k<0&&errno==EINTR)continue;if(k<=0)return false;p+=k;n-=size_t(k);}return true;}
// Packets remain native until the analysis isolate claims their ownership.
// A small descriptor crosses JS; the pixel ArrayBuffer never crosses isolates.
static std::mutex packetsMutex;static std::unordered_map<uint64_t,std::unique_ptr<Packet>> packets;static uint64_t nextToken=1;
static napi_value wrap(napi_env env,std::unique_ptr<Packet> p){napi_value buffer;auto status=napi_create_external_arraybuffer(env,p->data,p->size,[](napi_env env,void*bytes,void*hint){delete[]static_cast<uint8_t*>(bytes);if(env){int64_t total;napi_adjust_external_memory(env,-int64_t(reinterpret_cast<uintptr_t>(hint)),&total);}},reinterpret_cast<void*>(p->size),&buffer);if(status!=napi_ok){napi_throw_error(env,nullptr,"Cannot wrap local packet");return nullptr;}p->data=nullptr;int64_t total;napi_adjust_external_memory(env,int64_t(p->size),&total);return buffer;}
static uint64_t tokenArg(napi_env env,napi_callback_info info){size_t argc=1;napi_value arg;double n=0;napi_get_cb_info(env,info,&argc,&arg,nullptr,nullptr);if(argc)napi_get_value_double(env,arg,&n);return uint64_t(n);}
static napi_value take(napi_env env,napi_callback_info info){auto token=tokenArg(env,info);std::unique_ptr<Packet> p;{std::lock_guard<std::mutex>lock(packetsMutex);auto it=packets.find(token);if(it!=packets.end()){p=std::move(it->second);packets.erase(it);}}if(!p){napi_throw_error(env,nullptr,"Local packet ownership unavailable");return nullptr;}return wrap(env,std::move(p));}
static napi_value discard(napi_env env,napi_callback_info info){auto token=tokenArg(env,info);{std::lock_guard<std::mutex>lock(packetsMutex);packets.erase(token);}napi_value v;napi_get_undefined(env,&v);return v;}
static void deliver(napi_env env,napi_value cb,void*,void*data){auto p=std::unique_ptr<Packet>(static_cast<Packet*>(data));if(!env)return;auto called=nowNs();if(diagnostics())metrics.dispatch=called-p->readDone;
 napi_value descriptor,header,tokenValue,sizeValue,global,result;void*dest;size_t headerBytes=32+word(p->data+16);if(napi_create_arraybuffer(env,headerBytes,&dest,&header)!=napi_ok)return;std::memcpy(dest,p->data,headerBytes);napi_create_object(env,&descriptor);uint64_t token;{std::lock_guard<std::mutex>lock(packetsMutex);if(packets.size()>=3)return;token=nextToken++;napi_create_double(env,double(token),&tokenValue);napi_create_double(env,double(p->size),&sizeValue);packets.emplace(token,std::move(p));}
 napi_set_named_property(env,descriptor,"token",tokenValue);napi_set_named_property(env,descriptor,"size",sizeValue);napi_set_named_property(env,descriptor,"header",header);if(diagnostics())metrics.wrap=nowNs()-called;napi_get_global(env,&global);auto started=nowNs();if(napi_call_function(env,global,cb,1,&descriptor,&result)!=napi_ok){std::lock_guard<std::mutex>lock(packetsMutex);packets.erase(token);}if(diagnostics())metrics.callback=nowNs()-started;}
static void stop(){if(!receiver)return;auto r=std::move(receiver);r->running=false;shutdown(r->listener,SHUT_RDWR);int fd=r->peer.load();if(fd>=0)shutdown(fd,SHUT_RDWR);napi_release_threadsafe_function(r->callback,napi_tsfn_abort);if(r->thread.joinable())r->thread.join();close(r->listener);unlink(r->path.c_str());{std::lock_guard<std::mutex>lock(packetsMutex);packets.clear();}}
static napi_value closeReceiver(napi_env env,napi_callback_info){stop();napi_value v;napi_get_undefined(env,&v);return v;}
static napi_value start(napi_env env,napi_callback_info info){try{
 if(receiver)throw std::runtime_error("Local receiver already running");size_t argc=2;napi_value args[2];napi_get_cb_info(env,info,&argc,args,nullptr,nullptr);if(argc!=2)throw std::runtime_error("Local receiver requires path and callback");size_t n;napi_get_value_string_utf8(env,args[0],nullptr,0,&n);std::string path(n+1,0);napi_get_value_string_utf8(env,args[0],path.data(),path.size(),&n);path.resize(n);
 sockaddr_un address{};address.sun_family=AF_UNIX;if(path.size()>=sizeof(address.sun_path))throw std::runtime_error("Local socket path too long");std::memcpy(address.sun_path,path.c_str(),path.size()+1);
 const auto parent=path.substr(0,path.find_last_of('/'));struct stat directory{};if(lstat(parent.c_str(),&directory)||!S_ISDIR(directory.st_mode)||directory.st_uid!=getuid()||(directory.st_mode&077)!=0)throw std::runtime_error("Local socket directory must be private and owned by this user");
 struct stat old{};if(lstat(path.c_str(),&old)==0){if(!S_ISSOCK(old.st_mode)||old.st_uid!=getuid())throw std::runtime_error("Refusing to replace unrelated socket path");int probe=socket(AF_UNIX,SOCK_STREAM,0);bool active=connect(probe,(sockaddr*)&address,sizeof(address))==0;close(probe);if(active)throw std::runtime_error("Local socket is already in use");unlink(path.c_str());}
 auto r=std::make_unique<Receiver>();r->path=path;r->listener=socket(AF_UNIX,SOCK_STREAM,0);if(r->listener<0||bind(r->listener,(sockaddr*)&address,sizeof(address))||chmod(path.c_str(),0600)||listen(r->listener,1)){if(r->listener>=0)close(r->listener);throw std::runtime_error("Cannot bind local ingest socket");}
 napi_value label;napi_create_string_utf8(env,"GTap bounded local ingest",NAPI_AUTO_LENGTH,&label);if(napi_create_threadsafe_function(env,args[1],nullptr,label,1,1,nullptr,nullptr,nullptr,deliver,&r->callback)!=napi_ok)throw std::runtime_error("Cannot create ingest callback");
 auto raw=r.get();r->thread=std::thread([raw]{while(raw->running){pollfd ready{raw->listener,POLLIN,0};if(poll(&ready,1,100)<=0)continue;if(!raw->running)break;int fd=accept(raw->listener,nullptr,nullptr);if(fd<0){if(errno==EINTR)continue;break;}raw->peer=fd;int capacity=1024*1024;setsockopt(fd,SOL_SOCKET,SO_RCVBUF,&capacity,sizeof(capacity));timeval timeout{1,0};setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
#ifdef SO_NOSIGPIPE
 int one=1;setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&one,sizeof(one));
#endif
 uint8_t h[32];bool accepted=false;if(readAll(fd,h,32)){uint64_t w=word(h+8),height=word(h+12),ml=word(h+16),bytes=word(h+20);if((word(h)==0x31464952||word(h)==0x32464147)&&word(h+28)==0&&w&&height&&w<=16384&&height<=16384&&w*height<=16777216&&ml<=16384&&((word(h)==0x31464952&&bytes==w*height*12)||(word(h)==0x32464147&&bytes>=88&&bytes<=160000000))){size_t total=32+ml+bytes;auto allocating=nowNs();auto p=std::make_unique<Packet>();p->size=total;p->data=new(std::nothrow) uint8_t[total];if(diagnostics())metrics.allocate=nowNs()-allocating;if(p->data){std::memcpy(p->data,h,32);auto reading=nowNs();if(readAll(fd,p->data+32,total-32)){p->readDone=nowNs();if(diagnostics())metrics.read=p->readDone-reading;auto queuing=nowNs();if(napi_call_threadsafe_function(raw->callback,p.get(),napi_tsfn_blocking)==napi_ok){p.release();if(diagnostics())metrics.queue=nowNs()-queuing;if(diagnostics())metrics.count++;accepted=true;}}}}}
 uint8_t reply=accepted?1:0;send(fd,&reply,1,0);raw->peer=-1;close(fd);
 }});receiver=std::move(r);ownerEnv=env;napi_value fn;napi_create_function(env,"stopIngest",NAPI_AUTO_LENGTH,closeReceiver,nullptr,&fn);return fn;
 }catch(const std::exception&e){napi_throw_error(env,nullptr,e.what());return nullptr;}}
static napi_value stats(napi_env env,napi_callback_info){napi_value o;napi_create_object(env,&o);auto add=[&](const char*key,double n){napi_value v;napi_create_double(env,n,&v);napi_set_named_property(env,o,key,v);};add("packets",metrics.count.load());{std::lock_guard<std::mutex>lock(packetsMutex);add("buffered_packets",packets.size());}add("allocate_ms",metrics.allocate.load()/1e6);add("receive_ms",metrics.read.load()/1e6);add("handoff_queue_ms",metrics.queue.load()/1e6);add("js_dispatch_delay_ms",metrics.dispatch.load()/1e6);add("js_wrap_ms",metrics.wrap.load()/1e6);add("js_callback_ms",metrics.callback.load()/1e6);return o;}
static void cleanup(void*env){if(ownerEnv==env)stop();}
}
