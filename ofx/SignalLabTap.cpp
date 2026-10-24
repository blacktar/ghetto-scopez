#include "TapVersion.hpp"
#include "ofxsImageEffect.h"
#include "FrameCore.hpp"
#include "LocalDelivery.hpp"
#include "MetalTap.hpp"
#include "MetalAnalysis.hpp"
#include <map>
#include "BoundedCapture.hpp"
#include "TapInfo.hpp"
#include "TapSignal.hpp"
#include "TapPanel.hpp"
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <sstream>
#include <iomanip>
#include <memory>
#include <algorithm>
#include <chrono>
using namespace OFX;
struct Snapshot {std::shared_ptr<tap::CaptureBudget::Permit> permit;std::vector<float> rgb;tap::SharedRGB shared;int width,height;double pixelAspect=1;bool bt709=true;uint32_t seq;std::string meta;};
class Sender {
 tap::LatestMailbox<Snapshot> mailbox;std::atomic<bool> running{true};std::thread thread;
 void run(){std::shared_ptr<Snapshot> last;std::map<std::string,uint32_t> delivered;size_t cursor=0;while(running){auto fresh=mailbox.takeFor(std::chrono::milliseconds(100));if(!running)break;if(fresh){last=std::move(fresh);delivered.clear();}if(!last)continue;try{
  auto requests=tap::analysisRequests(tap::fetchHostInfo(8765,"/api/tap-analysis"));if(requests.empty())continue;
  for(auto it=delivered.begin();it!=delivered.end();)if(std::find(requests.begin(),requests.end(),it->first)==requests.end())it=delivered.erase(it);else ++it;
  std::string request;for(size_t i=0;i<requests.size();i++){auto&candidate=requests[(cursor+i)%requests.size()];if(!delivered.count(candidate)){request=candidate;cursor=(cursor+i+1)%requests.size();break;}}if(request.empty())continue;
  auto frame=last;const float*rgb=frame->shared.data?frame->shared.data:frame->rgb.data();size_t count=frame->shared.data?frame->shared.size:frame->rgb.size();
  tap::AnalysisResult analysis;bool gpu=frame->shared.metalBuffer!=nullptr;if(gpu)try{analysis=tap::metalAnalyze(frame->shared,frame->width,frame->height,request,frame->bt709,false,frame->pixelAspect);}catch(...){gpu=false;}
  auto meta=frame->meta;meta.pop_back();if(gpu)meta+=",\"analysis\":{\"schema\":2,\"backend\":\"Metal full-pixel float32 / uint32 counts\",\"config\":"+analysis.config+",\"summary\":"+analysis.summary+"}";meta+="}";
  auto prefix=gpu?tap::analysisPrefix(analysis.body,frame->width,frame->height,frame->seq,meta):tap::packetPrefix(rgb,count,frame->width,frame->height,frame->seq,meta);bool ok=tap::sendLocalFrame(prefix.data(),prefix.size(),gpu?static_cast<const void*>(analysis.body.data()):static_cast<const void*>(rgb),gpu?analysis.body.size():count*4);if(ok)delivered[request]=frame->seq;
 }catch(...){/* Monitoring failure must not alter or fail the grade. */}}}
public:Sender():thread([this]{run();}){}~Sender(){running=false;mailbox.close();thread.join();}void enqueue(std::shared_ptr<Snapshot> value){mailbox.tryPut(std::move(value));}
};
class SignalLabTap:public ImageEffect {
 Clip *source,*output;ChoiceParam *encoding,*addresses,*devices,*primaryAddress;StringParam *hostStatus,*refreshedAt;int primaryIndex=0;tap::PanelInfo panel;bool updatingPanel=false;std::shared_ptr<Sender> sender=std::make_shared<Sender>();tap::CaptureBudget captureBudget{3};uint32_t seq=0;std::string id;
public:SignalLabTap(OfxImageEffectHandle handle):ImageEffect(handle){source=fetchClip(kOfxImageEffectSimpleSourceClipName);output=fetchClip(kOfxImageEffectOutputClipName);hostStatus=fetchStringParam("hostStatus");refreshedAt=fetchStringParam("refreshedAt");primaryAddress=fetchChoiceParam("primaryAddress");addresses=fetchChoiceParam("addresses");devices=fetchChoiceParam("devices");encoding=fetchChoiceParam("signal");std::ostringstream s;s<<getpid()<<'-'<<std::hex<<reinterpret_cast<uintptr_t>(this);id=s.str();refreshStatus();}
 void refreshStatus(){updatingPanel=true;try{panel=tap::parsePanelInfo(tap::fetchHostInfo());hostStatus->setValue(panel.host);hostStatus->setHint("Last refreshed: "+panel.snapshot);addresses->resetOptions();for(const auto&url:panel.urls)addresses->appendOption(url);if(panel.urls.empty())addresses->appendOption("Host unavailable — start scopes server");int selected=0;for(size_t i=0;i<panel.urls.size();i++)if(panel.urls[i].find("localhost")==std::string::npos&&panel.urls[i].find("127.0.0.1")==std::string::npos){selected=int(i);break;}addresses->setValue(selected);primaryIndex=selected;primaryAddress->resetOptions();primaryAddress->appendOption(panel.urls.empty()?"Host unavailable — start scopes server":panel.urls[selected]);primaryAddress->setValue(0);refreshedAt->setValue(panel.snapshot);devices->resetOptions();for(const auto&device:panel.viewers)devices->appendOption(device);if(panel.viewers.empty())devices->appendOption("No connected viewers");devices->setValue(0);updatingPanel=false;}catch(...){updatingPanel=false;throw;}}
 void changedParam(const InstanceChangedArgs&,const std::string&name)override{if(updatingPanel)return;if(name=="refreshStatus")refreshStatus();else if(name=="about")tap::showPanelAbout();else if(name=="copyURL"||name=="copyAlternative"){int index=primaryIndex;if(name=="copyAlternative")addresses->getValue(index);if(index>=0&&size_t(index)<panel.urls.size())tap::copyPanelText(panel.urls[index]);}}
 void render(const RenderArguments&args)override{
  std::unique_ptr<Image> src(source->fetchImage(args.time)),dst(output->fetchImage(args.time));if(!src||!dst)throwSuiteStatusException(kOfxStatFailed);if(src->getPixelDepth()!=eBitDepthFloat||dst->getPixelDepth()!=eBitDepthFloat||src->getPixelComponents()!=ePixelComponentRGBA||dst->getPixelComponents()!=ePixelComponentRGBA)throwSuiteStatusException(kOfxStatErrFormat);
  const auto db=dst->getBounds(),sb=src->getBounds();const int w=sb.x2-sb.x1,h=sb.y2-sb.y1;const auto rod=src->getRegionOfDefinition();int choice=0;encoding->getValueAtTime(args.time,choice);
  // Thumbnails must not consume capture buffers or replace grading pixels.
  bool full=args.renderScale.x==1.&&args.renderScale.y==1.&&w>0&&h>0&&uint64_t(w)*h<=16777216&&sb.x1==rod.x1&&sb.y1==rod.y1&&sb.x2==rod.x2&&sb.y2==rod.y2;
  std::shared_ptr<Snapshot> frame;
  if(full&&choice!=0){
   try{auto permit=captureBudget.tryAcquire();if(permit){frame=std::make_shared<Snapshot>();frame->permit=std::move(permit);frame->width=w;frame->height=h;frame->pixelAspect=src->getPixelAspectRatio();frame->bt709=tap::uses709Basis(choice);frame->seq=seq++;std::ostringstream meta;meta<<std::setprecision(17)<<"{\"producer\":\"resolve-ofx\",\"instanceId\":\""<<id<<"\",\"time\":"<<args.time<<",\"renderScale\":{\"x\":"<<args.renderScale.x<<",\"y\":"<<args.renderScale.y<<"},\"pixelAspect\":"<<src->getPixelAspectRatio()<<",\"origin\":{\"x\":"<<sb.x1<<",\"y\":"<<sb.y1<<"},\"orientation\":\"top-down\",\"inputPrecision\":\"float32 RGB from OFX (bitwise capture); alpha unchanged in output\",\"signal\":"<<tap::signalMetadata(choice)<<"}";frame->meta=meta.str();frame->meta.pop_back();frame->meta+=",\"tapName\":\"GTap\",\"tapRelease\":\"" GHETTO_TAP_VERSION "\"}";frame->meta.pop_back();frame->meta+=args.isEnabledMetalRender?",\"captureBackend\":\"Metal asynchronous bitwise\"}":",\"captureBackend\":\"CPU row copy\"}"; }}catch(...){frame.reset();}
  }
  if(args.isEnabledMetalRender){
   tap::MetalLayout layout{{sb.x1,sb.y1,sb.x2,sb.y2},{db.x1,db.y1,db.x2,db.y2},{args.renderWindow.x1,args.renderWindow.y1,args.renderWindow.x2,args.renderWindow.y2},src->getRowBytes(),dst->getRowBytes()};
   tap::MetalSharedCapture capture;if(frame){auto outputSender=sender;capture=[frame,outputSender](tap::SharedRGB rgb){if(!rgb.data)return;frame->shared=std::move(rgb);outputSender->enqueue(frame);};}
   bool ok=false;try{ok=tap::metalCopyAndCaptureShared(args.pMetalCmdQ,src->getPixelData(),dst->getPixelData(),layout,capture);}catch(...){throwSuiteStatusException(kOfxStatFailed);}if(!ok){throwSuiteStatusException(kOfxStatErrFormat);}return;
  }
  // CPU fallback: copy whole valid rows instead of two address lookups per pixel.
  for(int y=args.renderWindow.y1;y<args.renderWindow.y2;y++){if(abort())return;const int x0=std::max(args.renderWindow.x1,db.x1),x1=std::min(args.renderWindow.x2,db.x2);if(x0>=x1||y<db.y1||y>=db.y2)continue;auto*to=dst->getPixelAddress(x0,y);if(!to)continue;if(y>=sb.y1&&y<sb.y2&&x0>=sb.x1&&x1<=sb.x2){auto*from=src->getPixelAddress(x0,y);if(to!=from){if(from)std::memcpy(to,from,size_t(x1-x0)*16);else std::memset(to,0,size_t(x1-x0)*16);}}else for(int x=x0;x<x1;x++)tap::copyRGBA(dst->getPixelAddress(x,y),src->getPixelAddress(x,y));}
  if(frame)try{frame->rgb=tap::rgbFrame(src->getPixelAddress(sb.x1,sb.y1),w,h,src->getRowBytes(),4);sender->enqueue(std::move(frame));}catch(...){/* Monitoring failure does not affect output. */}
 }

 bool isIdentity(const IsIdentityArguments&,Clip*&,double&)override{return false;}
};
class SignalLabTapFactory:public PluginFactoryHelper<SignalLabTapFactory>{public:SignalLabTapFactory():PluginFactoryHelper<SignalLabTapFactory>("local.signallab.ResolveTap",GHETTO_TAP_MAJOR,GHETTO_TAP_MINOR){}void load()override{}void unload()override{tap::metalDrain();}void describe(ImageEffectDescriptor&d)override{d.setLabels(GHETTO_TAP_LABEL,GHETTO_TAP_LABEL,GHETTO_TAP_LABEL);d.setVersion(GHETTO_TAP_MAJOR,GHETTO_TAP_MINOR,GHETTO_TAP_BUILD,0,GHETTO_TAP_VERSION);d.setPluginGrouping("Ghetto Scopez");d.setPluginDescription("Pass-through float32 pixel tap to the local iPad scopes server. Choose raw source/working-space RGB, or place after the intended display transform and declare the encoded RGB primaries. No screenshot capture. Asynchronous bitwise Metal capture with CPU fallback; not guaranteed real-time.");d.addSupportedContext(eContextFilter);d.addSupportedContext(eContextGeneral);d.addSupportedBitDepth(eBitDepthFloat);d.setSupportsMetalRender(true);d.setSingleInstance(false);d.setHostFrameThreading(false);d.setRenderThreadSafety(eRenderInstanceSafe);d.setSupportsMultiResolution(false);d.setSupportsTiles(false);d.setTemporalClipAccess(false);d.setRenderTwiceAlways(false);d.setSupportsMultipleClipPARs(false);}
 void describeInContext(ImageEffectDescriptor&d,ContextEnum)override{for(auto name:{kOfxImageEffectSimpleSourceClipName,kOfxImageEffectOutputClipName}){auto c=d.defineClip(name);c->addSupportedComponent(ePixelComponentRGBA);c->setSupportsTiles(false);}auto page=d.definePageParam("Controls");auto signal=d.defineChoiceParam("signal");signal->setLabels("Input","Input","Input");signal->appendOption("Undeclared — no transmission");signal->appendOption("BT.709 primaries / encoded RGB");signal->appendOption("BT.2020 primaries / encoded RGB");signal->appendOption("Source / working-space RGB — no transform");signal->setDefault(0);signal->setAnimates(false);signal->setHint("Choose Source / working-space RGB to measure the raw float32 values at this node, before a display transform. RGB is unchanged. Weighted RGB and difference views use a fixed BT.709 analysis basis, not inferred working-space primaries. For display scopes, place after the output CST and choose matching encoded RGB. Later transforms are excluded.");page->addChild(*signal);
 auto status=d.defineStringParam("hostStatus");status->setLabel("Scopes host");status->setStringType(eStringTypeLabel);status->setDefault("Not refreshed");status->setAnimates(false);status->setEvaluateOnChange(false);status->setCanUndo(false);page->addChild(*status);
 auto primary=d.defineChoiceParam("primaryAddress");primary->setLabel("Scopes address");primary->appendOption("Refresh to discover address");primary->setAnimates(false);primary->setEvaluateOnChange(false);page->addChild(*primary);
 auto copy=d.definePushButtonParam("copyURL");copy->setLabel("Copy URL");page->addChild(*copy);
 auto devices=d.defineChoiceParam("devices");devices->setLabel("Viewers");devices->appendOption("Refresh to discover viewers");devices->setAnimates(false);devices->setEvaluateOnChange(false);devices->setHint("Connected viewer names and listening states. Refresh to update.");page->addChild(*devices);
 auto refresh=d.definePushButtonParam("refreshStatus");refresh->setLabel("Refresh status");page->addChild(*refresh);
 auto about=d.definePushButtonParam("about");about->setLabel("About GTap");page->addChild(*about);
 auto advanced=d.defineGroupParam("advanced");advanced->setLabel("Advanced");advanced->setOpen(false);
 auto addresses=d.defineChoiceParam("addresses");addresses->setLabel("All network addresses");addresses->appendOption("Refresh to discover addresses");addresses->setAnimates(false);addresses->setEvaluateOnChange(false);addresses->setParent(*advanced);addresses->setHint("Alternative interfaces and localhost. The primary LAN address above is normally sufficient.");page->addChild(*addresses);
 auto alternate=d.definePushButtonParam("copyAlternative");alternate->setLabel("Copy selected address");alternate->setParent(*advanced);page->addChild(*alternate);
 auto refreshed=d.defineStringParam("refreshedAt");refreshed->setLabel("Status snapshot time");refreshed->setStringType(eStringTypeSingleLine);refreshed->setDefault("Not refreshed");refreshed->setAnimates(false);refreshed->setEvaluateOnChange(false);refreshed->setCanUndo(false);refreshed->setParent(*advanced);page->addChild(*refreshed);
 }



 ImageEffect*createInstance(OfxImageEffectHandle h,ContextEnum)override{return new SignalLabTap(h);}
};
namespace OFX{namespace Plugin{void getPluginIDs(PluginFactoryArray&ids){static SignalLabTapFactory factory;ids.push_back(&factory);}}}
