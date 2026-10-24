#pragma once
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <cstdint>
#include <cstring>
#include <string>
#include <cerrno>
namespace tap {
inline bool sendLocalFrame(const void*prefix,size_t prefixBytes,const void*pixels,size_t pixelBytes,int port=8765){
 int fd=socket(AF_UNIX,SOCK_STREAM,0);if(fd<0)return false;
 int capacity=1024*1024;setsockopt(fd,SOL_SOCKET,SO_SNDBUF,&capacity,sizeof(capacity));int one=1;setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&one,sizeof(one));timeval timeout{1,0};setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
 sockaddr_un address{};address.sun_family=AF_UNIX;auto path="/tmp/ghettoscopez-"+std::to_string(getuid())+"/ingest-"+std::to_string(port)+".sock";
 if(path.size()>=sizeof(address.sun_path)){close(fd);return false;}std::memcpy(address.sun_path,path.c_str(),path.size()+1);
 auto write=[&](const void*data,size_t n){auto p=static_cast<const uint8_t*>(data);while(n){auto k=send(fd,p,n,0);if(k<0&&errno==EINTR)continue;if(k<=0)return false;p+=k;n-=size_t(k);}return true;};
 bool ok=false;if(connect(fd,(sockaddr*)&address,sizeof(address))==0&&write(prefix,prefixBytes)&&write(pixels,pixelBytes)){uint8_t ack=0;ok=recv(fd,&ack,1,0)==1&&ack==1;}close(fd);return ok;
}
}
