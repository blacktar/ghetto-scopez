#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include "MetalTap.hpp"
#include <algorithm>
#include <cstring>
#include <map>
#include <mutex>
#include <condition_variable>
#include <stdexcept>
#include <atomic>
#include <array>
namespace tap {
namespace {
// This queue owns retained readback buffers until copying and delivery finish.
// The OFX producer's three-frame budget includes delivery through its callback.
dispatch_queue_t readbackQueue(){static dispatch_queue_t queue=dispatch_queue_create("local.ghettoscopez.tap.readback",DISPATCH_QUEUE_SERIAL);return queue;}
void finishCommand();
std::mutex completionMutex;std::condition_variable completionCV;size_t outstanding=0;
void finishCommand(){{std::lock_guard<std::mutex>lock(completionMutex);outstanding--;}completionCV.notify_all();}
// Reuse at most three readback allocations. A lease follows GPU and sender
// ownership; a busy slot is never overwritten. Contention skips capture only.
struct ReadbackSlot {id<MTLBuffer> buffer;std::atomic<bool> busy{false};};
struct ReadbackLease {std::shared_ptr<ReadbackSlot> slot;~ReadbackLease(){slot->busy.store(false,std::memory_order_release);}};
std::shared_ptr<ReadbackLease> acquireReadback(id<MTLDevice> device,size_t bytes){
 static std::mutex mutex;static std::array<std::shared_ptr<ReadbackSlot>,3> slots;
 std::unique_lock<std::mutex> lock(mutex,std::try_to_lock);if(!lock.owns_lock())return {};
 for(auto&slot:slots){if(!slot)slot=std::make_shared<ReadbackSlot>();if(slot->busy.load(std::memory_order_acquire))continue;
  if(!slot->buffer||slot->buffer.length!=bytes||slot->buffer.device!=device)slot->buffer=[device newBufferWithLength:bytes options:MTLResourceStorageModeShared];
  if(!slot->buffer)return {};auto lease=std::make_shared<ReadbackLease>();lease->slot=slot;slot->busy.store(true,std::memory_order_release);return lease;
 }return {};
}
// Integer loads/stores preserve every float32 bit, including NaNs and signed zero.
const char*code=R"(
#include <metal_stdlib>
using namespace metal;
struct Params {int4 src;int4 dst;int4 win;int srcRow;int dstRow;};
kernel void passThrough(device const uint* src [[buffer(0)]],device uint* dst [[buffer(1)]],constant Params&p [[buffer(2)]],uint2 id [[thread_position_in_grid]]){
 int x=p.win.x+int(id.x),y=p.win.y+int(id.y);if(x>=p.win.z||y>=p.win.w)return;
 if(x<p.dst.x||x>=p.dst.z||y<p.dst.y||y>=p.dst.w)return;
 uint di=uint(y-p.dst.y)*uint(p.dstRow)+uint(x-p.dst.x)*4;
 uint4 v=uint4(0);if(x>=p.src.x&&x<p.src.z&&y>=p.src.y&&y<p.src.w){uint si=uint(y-p.src.y)*uint(p.srcRow)+uint(x-p.src.x)*4;v=uint4(src[si],src[si+1],src[si+2],src[si+3]);}
 dst[di]=v.x;dst[di+1]=v.y;dst[di+2]=v.z;dst[di+3]=v.w;
}
kernel void copyAndCapture(device const uint* src [[buffer(0)]],device uint* dst [[buffer(1)]],constant Params&p [[buffer(2)]],device uint* rgb [[buffer(3)]],uint2 id [[thread_position_in_grid]]){
 uint width=uint(p.src.z-p.src.x),height=uint(p.src.w-p.src.y);if(id.x>=width||id.y>=height)return;
 uint si=id.y*uint(p.srcRow)+id.x*4,di=id.y*uint(p.dstRow)+id.x*4,ri=((height-1-id.y)*width+id.x)*3;
 uint4 v=uint4(src[si],src[si+1],src[si+2],src[si+3]);dst[di]=v.x;dst[di+1]=v.y;dst[di+2]=v.z;dst[di+3]=v.w;
 rgb[ri]=v.x;rgb[ri+1]=v.y;rgb[ri+2]=v.z;
}
kernel void captureRGB(device const uint* src [[buffer(0)]],device uint* rgb [[buffer(1)]],constant Params&p [[buffer(2)]],uint2 id [[thread_position_in_grid]]){
 uint width=uint(p.src.z-p.src.x),height=uint(p.src.w-p.src.y);if(id.x>=width||id.y>=height)return;
 uint si=(height-1-id.y)*uint(p.srcRow)+id.x*4,di=(id.y*width+id.x)*3;
 rgb[di]=src[si];rgb[di+1]=src[si+1];rgb[di+2]=src[si+2];
}
)";
struct alignas(16) Params{int32_t src[4],dst[4],win[4],srcRow,dstRow;};
static_assert(sizeof(Params)==64);
struct Pipelines{id<MTLComputePipelineState> copy;id<MTLComputePipelineState> capture;id<MTLComputePipelineState> combined;};
Pipelines pipelines(id<MTLDevice> device){static std::mutex mutex;static std::map<void*,Pipelines> cache;std::lock_guard<std::mutex> lock(mutex);auto key=(__bridge void*)device;auto found=cache.find(key);if(found!=cache.end())return found->second;
 NSError*error=nil;MTLCompileOptions*options=[MTLCompileOptions new];if(@available(macOS 15.0,*)){options.mathMode=MTLMathModeSafe;}else{options.fastMathEnabled=NO;}id<MTLLibrary> library=[device newLibraryWithSource:@(code) options:options error:&error];if(!library)throw std::runtime_error("Cannot compile Metal tap kernels");
 Pipelines p;p.copy=[device newComputePipelineStateWithFunction:[library newFunctionWithName:@"passThrough"] error:&error];p.capture=[device newComputePipelineStateWithFunction:[library newFunctionWithName:@"captureRGB"] error:&error];p.combined=[device newComputePipelineStateWithFunction:[library newFunctionWithName:@"copyAndCapture"] error:&error];if(!p.copy||!p.capture||!p.combined)throw std::runtime_error("Cannot create Metal tap pipelines");cache.emplace(key,p);return p;
}
bool valid(id<MTLBuffer> buffer,MetalRect r,int32_t stride){int64_t w=int64_t(r.x2)-r.x1,h=int64_t(r.y2)-r.y1;if(!buffer||w<1||h<1||w>16384||h>16384||uint64_t(w)*h>16777216||stride<w*16||stride%4)return false;return uint64_t(h-1)*stride+uint64_t(w)*16<=buffer.length;}
void encode(id<MTLComputeCommandEncoder> encoder,id<MTLComputePipelineState> state,id<MTLBuffer> source,id<MTLBuffer> destination,const Params&p,int width,int height){[encoder setComputePipelineState:state];[encoder setBuffer:source offset:0 atIndex:0];[encoder setBuffer:destination offset:0 atIndex:1];[encoder setBytes:&p length:sizeof(p) atIndex:2];NSUInteger tx=state.threadExecutionWidth,ty=std::max<NSUInteger>(1,std::min<NSUInteger>(8,state.maxTotalThreadsPerThreadgroup/tx));[encoder dispatchThreadgroups:MTLSizeMake((width+tx-1)/tx,(height+ty-1)/ty,1) threadsPerThreadgroup:MTLSizeMake(tx,ty,1)];}
}
void metalDrain(){std::unique_lock<std::mutex>lock(completionMutex);completionCV.wait(lock,[]{return outstanding==0;});}
bool metalCopyAndCaptureShared(void*q,void*s,void*d,const MetalLayout&l,MetalSharedCapture capture){@autoreleasepool{
 id<MTLCommandQueue> queue=(__bridge id<MTLCommandQueue>)q;id<MTLBuffer> source=(__bridge id<MTLBuffer>)s,destination=(__bridge id<MTLBuffer>)d;
 if(!queue||!valid(source,l.source,l.sourceRowBytes)||!valid(destination,l.destination,l.destinationRowBytes))return false;
 int width=l.window.x2-l.window.x1,height=l.window.y2-l.window.y1;if(width<1||height<1)return false;
 auto states=pipelines(queue.device);Params p;std::memcpy(p.src,&l.source,16);std::memcpy(p.dst,&l.destination,16);std::memcpy(p.win,&l.window,16);p.srcRow=l.sourceRowBytes/4;p.dstRow=l.destinationRowBytes/4;
 // Normal command buffers retain referenced host buffers until GPU work completes.
 id<MTLCommandBuffer> command=[queue commandBuffer];command.label=@"Ghetto Scopez exact pass-through";
 id<MTLBuffer> readback=nil;size_t words=0;std::shared_ptr<ReadbackLease> lease;
 if(capture){words=size_t(l.source.x2-l.source.x1)*(l.source.y2-l.source.y1)*3;lease=acquireReadback(queue.device,words*4);if(lease)readback=lease->slot->buffer;}
 const bool combined=readback&&std::memcmp(&l.source,&l.destination,sizeof(MetalRect))==0&&std::memcmp(&l.source,&l.window,sizeof(MetalRect))==0;
 id<MTLComputeCommandEncoder> encoder=[command computeCommandEncoder];if(combined)[encoder setBuffer:readback offset:0 atIndex:3];encode(encoder,combined?states.combined:states.copy,source,destination,p,width,height);[encoder endEncoding];
 if(readback&&!combined){auto pack=[command computeCommandEncoder];encode(pack,states.capture,source,readback,p,l.source.x2-l.source.x1,l.source.y2-l.source.y1);[pack endEncoding];}
 auto callback=std::move(capture);{std::lock_guard<std::mutex>lock(completionMutex);outstanding++;}
 // Initialise the worker before submission; never allocate/copy frame bytes on
 // Metal's driver completion thread. ARC retains readback in the queued block.
 auto worker=readbackQueue();
 [command addCompletedHandler:^(id<MTLCommandBuffer> completed){
  if(!callback){finishCommand();return;}
  bool succeeded=completed.status==MTLCommandBufferStatusCompleted;
  dispatch_async(worker,^{@autoreleasepool{
   SharedRGB rgb;
   // ARC owns the Metal buffer through the shared owner until the sender finishes.
   try{if(succeeded&&readback){rgb={static_cast<const float*>(readback.contents),words,lease,(__bridge void*)readback};}}catch(...){rgb={};}
   try{callback(std::move(rgb));}catch(...){/* Monitoring cannot fail output. */}
   finishCommand();
  }});
 }];
 [command commit];return true;
}}
bool metalCopyAndCapture(void*q,void*s,void*d,const MetalLayout&l,MetalCapture capture){
 MetalSharedCapture callback;
 if(capture)callback=[capture](SharedRGB view){std::vector<float> rgb;try{if(view.data){rgb.resize(view.size);std::memcpy(rgb.data(),view.data,view.size*4);}}catch(...){rgb.clear();}capture(std::move(rgb));};
 return metalCopyAndCaptureShared(q,s,d,l,callback);
}
}
