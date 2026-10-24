#pragma once
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <poll.h>
#include <chrono>
#include <string>
namespace tap {
// Panel actions and sender configuration discovery. Bounded deadline/reply; never called by render.
inline std::string fetchHostInfo(unsigned short port=8765,const std::string&path="/api/tap-info"){
 const std::string unavailable="Scopes host: unavailable\nStart the local scopes server, then press Refresh status.\nLocal address: http://localhost:8765/scopes.html";
 int fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0)return unavailable;
 struct Close {int fd;~Close(){close(fd);}} owner{fd};
 if(fcntl(fd,F_SETFL,O_NONBLOCK)<0)return unavailable;
 int one=1;setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&one,sizeof(one));
 auto deadline=std::chrono::steady_clock::now()+std::chrono::milliseconds(300);
 auto ready=[&](short events){auto left=std::chrono::duration_cast<std::chrono::milliseconds>(deadline-std::chrono::steady_clock::now()).count();if(left<=0)return false;pollfd p{fd,events,0};return poll(&p,1,int(left))>0&&(p.revents&events);};
 sockaddr_in addr{};addr.sin_family=AF_INET;addr.sin_port=htons(port);inet_pton(AF_INET,"127.0.0.1",&addr.sin_addr);
 if(connect(fd,(sockaddr*)&addr,sizeof(addr))<0){if(!ready(POLLOUT))return unavailable;int error=0;socklen_t n=sizeof(error);if(getsockopt(fd,SOL_SOCKET,SO_ERROR,&error,&n)||error)return unavailable;}
 const std::string request="GET "+path+" HTTP/1.1\r\nHost: 127.0.0.1:8765\r\nConnection: close\r\n\r\n";
 size_t sent=0;while(sent<request.size()){if(!ready(POLLOUT))return unavailable;auto n=send(fd,request.data()+sent,request.size()-sent,0);if(n<=0)return unavailable;sent+=n;}
 std::string reply;char chunk[2048];while(reply.size()<16384){if(!ready(POLLIN))return unavailable;auto n=recv(fd,chunk,sizeof(chunk),0);if(n==0)break;if(n<0)return unavailable;reply.append(chunk,size_t(n));}
 const auto split=reply.find("\r\n\r\n");if(reply.size()>=16384||reply.rfind("HTTP/1.1 200",0)!=0||split==std::string::npos)return unavailable;
 return reply.substr(split+4);
}
}
