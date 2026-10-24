#pragma once
#include "MetalTap.hpp"
#include <string>
namespace tap {
struct AnalysisResult {std::vector<uint8_t> body;std::string config,summary;double gpuMs=0,totalMs=0;size_t scratchBytes=0;};
std::vector<std::string> analysisRequests(const std::string&);
// Sender thread only. Reuses one bounded workspace; never runs on render thread.
AnalysisResult metalAnalyze(const SharedRGB&,int width,int height,const std::string& request,bool bt709,bool profile=false,double pixelAspect=1);
}
