#pragma once
#include <cstdint>
#include <algorithm>
#include <zlib.h>
#include <cstring>
#include <vector>
#include <string>
#include <stdexcept>
namespace tap {
inline void copyRGBA(void* to,const void* from){if(from)std::memcpy(to,from,16);else std::memset(to,0,16);}
inline uint32_t crc32(const uint8_t* bytes,size_t n){if(n>UINT32_MAX)throw std::runtime_error("CRC length overflow");return ::crc32(0,bytes,(uInt)n);}

inline void put32(std::vector<uint8_t>&v,size_t p,uint32_t n){for(int i=0;i<4;i++)v[p+i]=uint8_t(n>>(8*i));}
// Signed rowBytes and nonzero pixel origins are handled by the caller's row pointer.
inline std::vector<float> rgbFrame(const void* origin,int width,int height,int rowBytes,int channels){if(!origin||width<1||height<1||uint64_t(width)*height>16777216||channels!=4||std::abs(int64_t(rowBytes))<int64_t(width)*16)throw std::runtime_error("Invalid float RGBA image layout");std::vector<float> out(size_t(width)*height*3);for(int row=0;row<height;row++){const auto* pixels=reinterpret_cast<const uint8_t*>(origin)+int64_t(height-1-row)*rowBytes;for(int x=0;x<width;x++)std::memcpy(out.data()+(size_t(row)*width+x)*3,pixels+size_t(x)*16,12);}return out;}
// Scatter/gather wire prefix: CRC is identical to a contiguous RIF1 packet.
inline std::vector<uint8_t> packetPrefix(const float*rgb,size_t count,int width,int height,uint32_t sequence,const std::string&meta){
 if(!rgb||width<1||height<1||uint64_t(width)*height>16777216||meta.size()>16384||count!=size_t(width)*height*3)throw std::runtime_error("Invalid packet");
 const size_t ml=(meta.size()+3)&~size_t(3);std::vector<uint8_t> out(32+ml,32);std::fill_n(out.data(),32,0);
 out[0]='R';out[1]='I';out[2]='F';out[3]='1';put32(out,4,sequence);put32(out,8,width);put32(out,12,height);put32(out,16,uint32_t(ml));put32(out,20,uint32_t(count*4));std::memcpy(out.data()+32,meta.data(),meta.size());
 auto crc=::crc32(0,out.data()+32,(uInt)ml);crc=::crc32(crc,reinterpret_cast<const uint8_t*>(rgb),(uInt)(count*4));put32(out,24,crc);return out;
}
inline std::vector<uint8_t> analysisPrefix(const std::vector<uint8_t>&body,int width,int height,uint32_t sequence,const std::string&meta){
 if(width<1||height<1||uint64_t(width)*height>16777216||meta.size()>16384||body.size()>160000000)throw std::runtime_error("Invalid analysis packet");
 size_t ml=(meta.size()+3)&~size_t(3);std::vector<uint8_t> out(32+ml,32);std::fill_n(out.data(),32,0);std::memcpy(out.data(),"GAF2",4);put32(out,4,sequence);put32(out,8,width);put32(out,12,height);put32(out,16,uint32_t(ml));put32(out,20,uint32_t(body.size()));std::memcpy(out.data()+32,meta.data(),meta.size());auto crc=::crc32(0,out.data()+32,(uInt)ml);crc=::crc32(crc,body.data(),(uInt)body.size());put32(out,24,crc);return out;
}
inline std::vector<uint8_t> packet(const std::vector<float>&rgb,int width,int height,uint32_t sequence,const std::string&meta){if(meta.size()>16384||rgb.size()!=size_t(width)*height*3)throw std::runtime_error("Invalid packet");const size_t ml=(meta.size()+3)&~size_t(3);std::vector<uint8_t> out(32+ml+rgb.size()*4);std::memset(out.data()+32,32,ml);out[0]='R';out[1]='I';out[2]='F';out[3]='1';put32(out,4,sequence);put32(out,8,width);put32(out,12,height);put32(out,16,uint32_t(ml));put32(out,20,uint32_t(rgb.size()*4));std::memcpy(out.data()+32,meta.data(),meta.size());std::memcpy(out.data()+32+ml,rgb.data(),rgb.size()*4);put32(out,24,crc32(out.data()+32,out.size()-32));return out;}
}
