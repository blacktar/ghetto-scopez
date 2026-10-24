#pragma once
#include <cstdint>
#include <functional>
#include <vector>
#include <memory>
namespace tap {
struct MetalRect {int32_t x1,y1,x2,y2;};
struct MetalLayout {MetalRect source,destination,window;int32_t sourceRowBytes,destinationRowBytes;};
struct SharedRGB {const float*data=nullptr;size_t size=0;std::shared_ptr<void> owner;void* metalBuffer=nullptr;};
using MetalSharedCapture=std::function<void(SharedRGB)>;
bool metalCopyAndCaptureShared(void*queue,void*source,void*destination,const MetalLayout&,MetalSharedCapture capture={});
using MetalCapture=std::function<void(std::vector<float>&&)>;
// Encodes onto the supplied host queue, commits, and returns without waiting.
// The completion callback owns its RGB copy; it never retains an OFX Image.
void metalDrain(); // Factory-unload barrier, never called from a render action.
bool metalCopyAndCapture(void*queue,void*source,void*destination,const MetalLayout&,MetalCapture capture={});
}
