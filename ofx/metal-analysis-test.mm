#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include "MetalAnalysis.hpp"
#include "FrameCore.hpp"
#include <fstream>
#include <iostream>
int main(int argc,char**argv){@autoreleasepool{try{
 if(argc!=2)throw std::runtime_error("Pass manifest path");NSData*md=[NSData dataWithContentsOfFile:@(argv[1])];NSArray*cases=[NSJSONSerialization JSONObjectWithData:md options:0 error:nil];auto device=MTLCreateSystemDefaultDevice();if(!device)throw std::runtime_error("No Metal device");std::cout<<"Device: "<<device.name.UTF8String<<"\n";
 for(NSDictionary*item in cases){NSData*data=[NSData dataWithContentsOfFile:item[@"input"]];const auto*p=(const uint8_t*)data.bytes;if(data.length<32)throw std::runtime_error("Missing fixture");auto word=[&](int at){uint32_t u;std::memcpy(&u,p+at,4);return u;};int width=word(8),height=word(12),ml=word(16);auto input=[device newBufferWithBytes:p+32+ml length:word(20) options:MTLResourceStorageModeShared];tap::SharedRGB rgb{(const float*)input.contents,size_t(width)*height*3,{},(__bridge void*)input};NSData*request=[NSJSONSerialization dataWithJSONObject:item[@"config"] options:NSJSONWritingSortedKeys error:nil];std::string config((const char*)request.bytes,request.length);
 NSDictionary*sourceMeta=[NSJSONSerialization JSONObjectWithData:[NSData dataWithBytes:p+32 length:ml] options:0 error:nil];double pixelAspect=sourceMeta[@"pixelAspect"]?[sourceMeta[@"pixelAspect"] doubleValue]:1;
 tap::AnalysisResult result;for(int i=0;i<[item[@"runs"] intValue];i++){result=tap::metalAnalyze(rgb,width,height,config,[item[@"matrix"] isEqualToString:@"bt709"],true,pixelAspect);std::cout<<[item[@"name"] UTF8String]<<" run="<<i<<" gpu_ms="<<result.gpuMs<<" total_ms="<<result.totalMs<<" payload_bytes="<<result.body.size()<<" workspace_bytes="<<result.scratchBytes<<"\n";}
 auto normal=tap::metalAnalyze(rgb,width,height,config,[item[@"matrix"] isEqualToString:@"bt709"],false,pixelAspect);if(normal.gpuMs!=0||normal.totalMs!=0||normal.body!=result.body||normal.summary!=result.summary)throw std::runtime_error("Normal unprofiled analysis differs from profiled reference");
 std::string meta((const char*)p+32,ml);auto end=meta.find_last_of('}');meta.resize(end);meta+=",\"analysis\":{\"schema\":2,\"backend\":\"Metal full-pixel float32 / uint32 counts\",\"config\":"+result.config+",\"summary\":"+result.summary+"}}";auto header=tap::analysisPrefix(result.body,width,height,word(4),meta);std::ofstream out([item[@"output"] UTF8String],std::ios::binary);out.write((const char*)header.data(),header.size());out.write((const char*)result.body.data(),result.body.size());if(!out)throw std::runtime_error("Cannot write analysis fixture");
 }return 0;}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}}
