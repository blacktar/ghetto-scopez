#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include "MetalTap.hpp"
#include "FrameCore.hpp"
#include "BoundedCapture.hpp"
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <vector>
#include <stdexcept>
#include <thread>
static void wait(std::condition_variable&cv,std::mutex&mutex,bool&done){std::unique_lock<std::mutex> lock(mutex);if(!cv.wait_for(lock,std::chrono::seconds(30),[&]{return done;}))throw std::runtime_error("Metal completion timeout");}
int main(){@autoreleasepool{
 auto device=MTLCreateSystemDefaultDevice();if(!device){std::cerr<<"No Metal device available\n";return 2;}auto queue=[device newCommandQueue];std::cout<<"Metal device: "<<device.name.UTF8String<<"\n";
 for(int mode=0;mode<4;mode++){
  const int width=13,height=7,stride=(width*4+8)*4;std::vector<uint32_t> input(size_t(stride/4)*height),original(size_t(stride/4)*height,0xfeedbeef);for(size_t i=0;i<input.size();i++)input[i]=uint32_t(i*77813+123);uint32_t edge[]={0,0x80000000,0x7fc01234,0x7f800000,0xff800000,0x00000001,0x3f800000,0xbf800000};std::memcpy(input.data(),edge,sizeof(edge));
  tap::MetalRect src{11,23,11+width,23+height},dst=src,window=src;if(mode==1)window={14,24,21,28};if(mode==2)src={13,25,11+width,23+height};
  tap::MetalLayout layout{src,dst,window,stride,stride};auto in=[device newBufferWithBytes:input.data() length:input.size()*4 options:MTLResourceStorageModeShared],out=[device newBufferWithBytes:original.data() length:original.size()*4 options:MTLResourceStorageModeShared];
  if(mode==3){layout.sourceRowBytes=-stride;assert(!tap::metalCopyAndCapture((__bridge void*)queue,(__bridge void*)in,(__bridge void*)out,layout));continue;}
  auto expected=original;for(int y=window.y1;y<window.y2;y++)for(int x=window.x1;x<window.x2;x++){size_t di=size_t(y-dst.y1)*(stride/4)+(x-dst.x1)*4;if(x>=src.x1&&x<src.x2&&y>=src.y1&&y<src.y2){size_t si=size_t(y-src.y1)*(stride/4)+(x-src.x1)*4;std::memcpy(expected.data()+di,input.data()+si,16);}else std::memset(expected.data()+di,0,16);}
  std::mutex mutex;std::condition_variable cv;bool done=false;std::vector<float> captured;
  assert(tap::metalCopyAndCapture((__bridge void*)queue,(__bridge void*)in,(__bridge void*)out,layout,[&](std::vector<float>&&rgb){{std::lock_guard<std::mutex> lock(mutex);captured=std::move(rgb);done=true;}cv.notify_one();}));wait(cv,mutex,done);
  assert(std::memcmp(out.contents,expected.data(),expected.size()*4)==0);auto rgb=tap::rgbFrame(input.data(),src.x2-src.x1,src.y2-src.y1,stride,4);assert(captured.size()==rgb.size());assert(std::memcmp(captured.data(),rgb.data(),rgb.size()*4)==0);
 }
 // Queue ordering, output-only rendering and shared capture ownership are exercised
 // with the real 4224x1980 workload; no float arithmetic is used by the GPU kernels.
 const int width=4224,height=1980;size_t bytes=size_t(width)*height*16;auto src=[device newBufferWithLength:bytes options:MTLResourceStorageModeShared],dst=[device newBufferWithLength:bytes options:MTLResourceStorageModeShared];auto words=(uint32_t*)src.contents;for(size_t i=0;i<bytes/4;i++)words[i]=uint32_t(i*912371+11);tap::MetalLayout layout{{0,0,width,height},{0,0,width,height},{0,0,width,height},width*16,width*16};
 for(int capture=0;capture<2;capture++)for(int run=0;run<5;run++){
  std::mutex mutex;std::condition_variable cv;bool done=false;std::vector<float> rgb;auto start=std::chrono::steady_clock::now();tap::MetalCapture callback;if(capture)callback=[&](std::vector<float>&&v){{std::lock_guard<std::mutex> lock(mutex);rgb=std::move(v);done=true;}cv.notify_one();};
  assert(tap::metalCopyAndCapture((__bridge void*)queue,(__bridge void*)src,(__bridge void*)dst,layout,callback));auto submitted=std::chrono::steady_clock::now();if(capture)wait(cv,mutex,done);else{auto fence=[queue commandBuffer];[fence commit];[fence waitUntilCompleted];}auto end=std::chrono::steady_clock::now();assert(std::memcmp(src.contents,dst.contents,bytes)==0);if(capture){auto expected=tap::rgbFrame(src.contents,width,height,width*16,4);assert(rgb.size()==expected.size());assert(std::memcmp(rgb.data(),expected.data(),rgb.size()*4)==0);}std::cout<<"BENCH capture="<<capture<<" submit_ms="<<std::chrono::duration<double,std::milli>(submitted-start).count()<<" complete_ms="<<std::chrono::duration<double,std::milli>(end-start).count()<<"\n";
 }
 // Production path: retain shared RGB beyond GPU completion and worker drain.
 tap::SharedRGB shared;
 assert(tap::metalCopyAndCaptureShared((__bridge void*)queue,(__bridge void*)src,(__bridge void*)dst,layout,[&](tap::SharedRGB view){shared=std::move(view);}));
 tap::metalDrain();
 assert(shared.data&&shared.owner&&shared.size==size_t(width)*height*3);
 auto reference=tap::rgbFrame(src.contents,width,height,width*16,4);
 assert(std::memcmp(shared.data,reference.data(),shared.size*4)==0);
 auto begin=std::chrono::steady_clock::now();auto contiguous=tap::packet(reference,width,height,99,"{}");auto mid=std::chrono::steady_clock::now();
 auto prefix=tap::packetPrefix(shared.data,shared.size,width,height,99,"{}");auto endPrefix=std::chrono::steady_clock::now();
 assert(prefix.size()+shared.size*4==contiguous.size());assert(std::memcmp(prefix.data(),contiguous.data(),prefix.size())==0);assert(std::memcmp(shared.data,contiguous.data()+prefix.size(),shared.size*4)==0);
 std::cout<<"BENCH packet_contiguous_ms="<<std::chrono::duration<double,std::milli>(mid-begin).count()<<" packet_shared_prefix_ms="<<std::chrono::duration<double,std::milli>(endPrefix-mid).count()<<" payload_copy_bytes_avoided="<<shared.size*8<<"\n";
 shared={};
 // Hold delivery deliberately: capture storage must stay bounded while every
 // requested Resolve output still passes through. No GPU wait in submission.
 tap::CaptureBudget budget(3);std::mutex heldMutex;
 struct Held {std::shared_ptr<tap::CaptureBudget::Permit> permit;tap::SharedRGB rgb;};
 std::vector<Held> held;unsigned accepted=0,skipped=0;
 for(int i=0;i<64;i++){
  auto permit=budget.tryAcquire();tap::MetalSharedCapture callback;
  if(permit){accepted++;callback=[&,permit](tap::SharedRGB rgb){std::lock_guard<std::mutex>lock(heldMutex);held.push_back({permit,std::move(rgb)});};}else skipped++;
  assert(tap::metalCopyAndCaptureShared((__bridge void*)queue,(__bridge void*)src,(__bridge void*)dst,layout,callback));
 }
 tap::metalDrain();assert(accepted==3&&skipped==61&&budget.used()==3&&held.size()==3);
 for(const auto& item:held){assert(item.rgb.data&&item.rgb.size==reference.size());assert(std::memcmp(item.rgb.data,reference.data(),reference.size()*4)==0);}
 // Exhaust the physical pool independently of the producer's permit budget.
 bool overflowCallback=false;tap::SharedRGB overflow;
 assert(tap::metalCopyAndCaptureShared((__bridge void*)queue,(__bridge void*)src,(__bridge void*)dst,layout,[&](tap::SharedRGB view){overflowCallback=true;overflow=std::move(view);}));
 tap::metalDrain();assert(overflowCallback&&!overflow.data);
 assert(std::memcmp(src.contents,dst.contents,bytes)==0);held.clear();assert(budget.used()==0);assert(budget.tryAcquire());
 std::cout<<"PASS bounded Metal delivery: 64 full-resolution outputs, 3 retained exact RGB captures, 61 nonwaiting capture skips, all permits reclaimed\n";
 // Drain must include queued CPU delivery, even after GPU completion.
 std::mutex drainMutex;bool drainDone=false;
 assert(tap::metalCopyAndCapture((__bridge void*)queue,(__bridge void*)src,(__bridge void*)dst,layout,[&](std::vector<float>&&v){
  std::this_thread::sleep_for(std::chrono::milliseconds(30));
  std::lock_guard<std::mutex> lock(drainMutex);drainDone=!v.empty();
 }));
 tap::metalDrain();
 {std::lock_guard<std::mutex> lock(drainMutex);assert(drainDone);}
 std::cout<<"PASS Metal bitwise RGBA/alpha/NaN/signed-zero, padded strides, nonzero origins, partial windows, zero-fill, RGB orientation, queue order and full-resolution capture\n";
}}
