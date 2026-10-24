#include "FrameCore.hpp"
#include <cassert>
#include <iostream>
#include <fstream>
int main(int argc,char**argv){
 assert(tap::crc32(reinterpret_cast<const uint8_t*>("123456789"),9)==0xcbf43926);
 // Bottom-up host rows, padded stride, alpha and nonfinite payloads untouched.
 uint32_t raw[12]={0x80000000,0x7fc01234,0x3f800000,0x3f000000,0,0,0,0,0,0,0,0};
 uint32_t copied[4];tap::copyRGBA(copied,raw);assert(std::memcmp(copied,raw,16)==0);tap::copyRGBA(copied,nullptr);assert(copied[0]==0&&copied[3]==0);
 auto one=tap::rgbFrame(raw,1,1,48,4);assert(std::memcmp(one.data(),raw,12)==0);
 float rows[16]={1,2,3,.5f,99,99,99,99,4,5,6,.25f,99,99,99,99};
 auto pos=tap::rgbFrame(rows,1,2,32,4);assert((pos==std::vector<float>{4,5,6,1,2,3}));
 auto neg=tap::rgbFrame(rows+8,1,2,-32,4);assert((neg==std::vector<float>{1,2,3,4,5,6}));
 bool rejected=false;try{tap::rgbFrame(rows,2,1,8,4);}catch(...){rejected=true;}assert(rejected);
 const std::string metadata=R"({"producer":"resolve-ofx","instanceId":"native-core-test","time":42,"renderScale":{"x":1,"y":1},"signal":{"model":"RGB","range":"full","matrix":"bt709","codeBits":10}})";auto bytes=tap::packet(one,1,1,42,metadata);assert(bytes.size()==32+((metadata.size()+3)&~size_t(3))+12);assert(bytes[0]=='R'&&bytes[4]==42);assert(std::memcmp(bytes.data()+bytes.size()-12,raw,12)==0);
 auto prefix=tap::packetPrefix(one.data(),one.size(),1,1,42,metadata);
 assert(prefix.size()+one.size()*4==bytes.size());assert(std::memcmp(prefix.data(),bytes.data(),prefix.size())==0);
 if(argc>1){std::ofstream out(argv[1],std::ios::binary);out.write(reinterpret_cast<const char*>(bytes.data()),bytes.size());}
 std::cout<<"PASS CRC, signed-zero/NaN payload bits, RGB extraction, alpha exclusion, padded positive/negative row strides, orientation, malformed stride and RIF1 packet\n";
}
