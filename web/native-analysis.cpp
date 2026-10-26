#include <node_api.h>
#include "native-ingest.hpp"
#include <zlib.h>
#include <cmath>
#include <cstdint>
#include <vector>
#include <cstring>
#include <stdexcept>
#include <algorithm>
#include <thread>
#include <memory>
#include <atomic>
#include <type_traits>
#include <limits>
#if defined(__aarch64__)
#include <arm_neon.h>
#endif
#ifdef __APPLE__
#include <dispatch/dispatch.h>
#endif
// IEEE double arithmetic, no fast-math/FMA. Counts stay uint32 throughout.
static void check(napi_status s){if(s!=napi_ok)throw std::runtime_error("Native analysis argument error");}
static napi_value prop(napi_env e,napi_value o,const char*k){napi_value v;check(napi_get_named_property(e,o,k,&v));return v;}
static double number(napi_env e,napi_value o,const char*k){double d;check(napi_get_value_double(e,prop(e,o,k),&d));return d;}
static void set(napi_env e,napi_value o,const char*k,double d){napi_value v;check(napi_create_double(e,d,&v));check(napi_set_named_property(e,o,k,v));}
static double roundBin(double x){double n=std::floor(x);return n+(x-n>=.5?1.:0.);}
static double jmin(double a,double b){return a==0&&b==0?(std::signbit(a)||std::signbit(b)?-0.:0.):std::min(a,b);}
static double jmax(double a,double b){return a==0&&b==0?(std::signbit(a)&&std::signbit(b)?-0.:0.):std::max(a,b);}
struct Stats{double lo=0,hi=0;uint32_t invalid=0,under=0,over=0,vu=0,vo=0;bool any=false;void add(double v,double mn,double mx){if(!std::isfinite(v)){invalid++;return;}if(!any){lo=hi=v;any=true;}else{if(v<lo||(v==0&&lo==0&&std::signbit(v)))lo=v;if(v>hi||(v==0&&hi==0&&!std::signbit(v)))hi=v;}under+=v<0;over+=v>1;vu+=v<mn;vo+=v>mx;}};
struct Pair{uint32_t plotted=0,outside=0,invalid=0,gamut=0;};
struct Plane{uint32_t*p;size_t n;std::vector<uint32_t> active,owned;void add(size_t i){if(i>=n)throw std::runtime_error("Native bin outside plane");if(p[i]==0)active.push_back((uint32_t)i);p[i]++;}};
static void* typed(napi_env e,napi_value v,napi_typedarray_type want,size_t&n){napi_typedarray_type type;void*p;napi_value ab;size_t off;check(napi_get_typedarray_info(e,v,&type,&n,&p,&ab,&off));if(type!=want)throw std::runtime_error("Native array type mismatch");return p;}
static int laneCount(napi_env e,napi_value c,size_t pixels,size_t bytes){bool has=false;check(napi_has_named_property(e,c,"workerLimit",&has));int requested=has?int(number(e,c,"workerLimit")):4;int cores=std::max(1u,std::thread::hardware_concurrency());int memory=int((128ull*1024*1024)/std::max(size_t(1),bytes));return pixels<262144?1:std::max(1,std::min({requested,8,cores,memory}));}
static napi_value run(napi_env e,napi_callback_info info){try{
 size_t argc=5;napi_value a[5];check(napi_get_cb_info(e,info,&argc,a,nullptr,nullptr));if(argc!=5)throw std::runtime_error("Native analysis requires five arguments");
 size_t count;auto data=(float*)typed(e,a[0],napi_float32_array,count);auto c=a[1],m=a[2],planes=a[3],result=a[4];
 int width=number(e,c,"sourceWidth"),height=number(e,c,"sourceHeight"),x0=number(e,c,"x0"),x1=number(e,c,"x1"),y0=number(e,c,"y0"),y1=number(e,c,"y1");
 int mask=number(e,c,"planeMask");int hb=number(e,c,"histBins"),levels=number(e,c,"levels"),ww=number(e,c,"waveWidth"),vs=number(e,c,"vectorSize"),tw=number(e,c,"twinWidth"),th=number(e,c,"twinHeight");
 double mn=number(e,c,"min"),mx=number(e,c,"max"),zoom=number(e,c,"vectorZoom"),txb=number(e,c,"twinX"),tyb=number(e,c,"twinY"),lc=number(e,c,"lowCut"),hc=number(e,c,"highCut"),kr=number(e,m,"kr"),kg=number(e,m,"kg"),kb=number(e,m,"kb");
 if(width<1||height<1||uint64_t(width)*height>16777216||count!=size_t(width)*height*3||x0<0||x1>width||y0<0||y1>height||x0>=x1||y0>=y1||levels<2||levels>4096||(ww<512||ww>2048||ww%512)||(vs!=512&&vs!=1024&&vs!=1536&&vs!=2048)||(tw<512||tw>2048||tw%512)||th!=tw*2||!(mx>mn)||!(zoom>0)||!(txb>0)||!(tyb>0))throw std::runtime_error("Invalid native dimensions/configuration");
 const char*names[]={"wave","parade","hist","vector","low","mid","high","twin"};size_t sizes[]={size_t(ww)*levels,size_t(ww)*levels*3,size_t(hb)*3,size_t(vs)*vs,size_t(vs)*vs,size_t(vs)*vs,size_t(vs)*vs,size_t(tw)*th};Plane p[8];
 for(int j=0;j<8;j++){p[j].p=(uint32_t*)typed(e,prop(e,planes,names[j]),napi_uint32_array,p[j].n);if(p[j].n!=sizes[j])throw std::runtime_error("Invalid native plane dimensions");}
 Stats stats[4],raw[3];Pair pairs[2];uint32_t bp[3]={},bo[3]={},bn[3]={},outside=0;double half=.5/zoom;
 const int numberMask=mask;
 auto scanImpl=[&](auto tag,int begin,int end,Plane* p,Stats* stats,Stats* raw,Pair* pairs,uint32_t* bp,uint32_t* bo,uint32_t* bn,uint32_t&outside){
 const int mask=decltype(tag)::value<0?int(numberMask):decltype(tag)::value;

#if defined(__aarch64__)
 // Two pixels per SIMD register, retaining double operations and their order.
 // Row scratch is private to each lane and bounded by the source width.
 thread_local std::vector<double> derived;thread_local std::vector<uint8_t> ordinary;
 if constexpr(decltype(tag)::value==240){derived.resize(size_t(x1-x0)*9);ordinary.resize(x1-x0);}
#endif
 for(int sy=begin;sy<end;sy++){
#if defined(__aarch64__)
 if constexpr(decltype(tag)::value==240){
 float64x2_t lows[4],highs[4];for(int ch=0;ch<4;ch++){lows[ch]=vdupq_n_f64(INFINITY);highs[ch]=vdupq_n_f64(-INFINITY);}
 const auto kr2=vdupq_n_f64(kr),kg2=vdupq_n_f64(kg),kb2=vdupq_n_f64(kb),ud=vdupq_n_f64(2*(1-kb)),vd=vdupq_n_f64(2*(1-kr));
 const auto hx=vdupq_n_f64(txb),hy=vdupq_n_f64(tyb),dx=vdupq_n_f64(2*txb),dy=vdupq_n_f64(2*tyb),nx=vdupq_n_f64(tw-1),ny=vdupq_n_f64(th-1);
 for(int sx=x0;sx<x1;sx+=2){
  const size_t src=(size_t(sy)*width+sx)*3,at=size_t(sx-x0);
  if(sx+1==x1){ordinary[at]=0;double r=data[src],g=data[src+1],b=data[src+2],l=kr*r+kg*g+kb*b;
   double samples[]={r,g,b,l};for(int ch=0;ch<4;ch++)stats[ch].add(samples[ch],mn,mx);
   double u=(b-l)/(2*(1-kb)),v=(r-l)/(2*(1-kr));double a[]={l,(b-l)/(2*(1-kb)),(r-l)/(2*(1-kr)),((b-g)+txb)/(2*txb)*(tw-1),((b+g)+tyb)/(2*tyb)*(th-1),((r-g)+txb)/(2*txb)*(tw-1),(-(r+g)+tyb)/(2*tyb)*(th-1),(u+half)/(2*half)*(vs-1),(v+half)/(2*half)*(vs-1)};for(int k=0;k<9;k++)derived[size_t(k)*(x1-x0)+at]=a[k];continue;}
  float32x2x3_t packed=vld3_f32(data+src);auto r=vcvt_f64_f32(packed.val[0]),g=vcvt_f64_f32(packed.val[1]),b=vcvt_f64_f32(packed.val[2]);
  auto l=vaddq_f64(vaddq_f64(vmulq_f64(kr2,r),vmulq_f64(kg2,g)),vmulq_f64(kb2,b));
  float64x2_t samples[]={r,g,b,l};auto valid=vdupq_n_u64(UINT64_MAX);
  const auto lower=vdupq_n_f64(std::max(0.,mn)),upper=vdupq_n_f64(std::min(1.,mx));
  for(int ch=0;ch<4;ch++)valid=vandq_u64(valid,vandq_u64(vcgeq_f64(samples[ch],lower),vcleq_f64(samples[ch],upper)));
  ordinary[at]=ordinary[at+1]=vminvq_u32(vreinterpretq_u32_u64(valid))==UINT32_MAX;
  if(ordinary[at]){for(int ch=0;ch<4;ch++){lows[ch]=vminq_f64(lows[ch],samples[ch]);highs[ch]=vmaxq_f64(highs[ch],samples[ch]);}}
  else for(int ch=0;ch<4;ch++){stats[ch].add(vgetq_lane_f64(samples[ch],0),mn,mx);stats[ch].add(vgetq_lane_f64(samples[ch],1),mn,mx);}
  auto u=vdivq_f64(vsubq_f64(b,l),ud),v=vdivq_f64(vsubq_f64(r,l),vd);
  float64x2_t values[]={l,u,v,vmulq_f64(vdivq_f64(vaddq_f64(vsubq_f64(b,g),hx),dx),nx),vmulq_f64(vdivq_f64(vaddq_f64(vaddq_f64(b,g),hy),dy),ny),vmulq_f64(vdivq_f64(vaddq_f64(vsubq_f64(r,g),hx),dx),nx),vmulq_f64(vdivq_f64(vaddq_f64(vnegq_f64(vaddq_f64(r,g)),hy),dy),ny),vmulq_f64(vdivq_f64(vaddq_f64(u,vdupq_n_f64(half)),vdupq_n_f64(2*half)),vdupq_n_f64(vs-1)),vmulq_f64(vdivq_f64(vaddq_f64(v,vdupq_n_f64(half)),vdupq_n_f64(2*half)),vdupq_n_f64(vs-1))};
  for(int k=0;k<9;k++){vst1q_f64(derived.data()+size_t(k)*(x1-x0)+at,values[k]);}
 }
 for(int ch=0;ch<4;ch++){double lo=vminvq_f64(lows[ch]),hi=vmaxvq_f64(highs[ch]);if(std::isfinite(lo)){auto&s=stats[ch];s.lo=s.any?jmin(s.lo,lo):lo;s.hi=s.any?jmax(s.hi,hi):hi;s.any=true;}}
 }
#endif
 for(int sx=x0;sx<x1;sx++){
  size_t i=(size_t(sy)*width+sx)*3;double r=data[i],g=data[i+1],b=data[i+2],l;
#if defined(__aarch64__)
 if constexpr(decltype(tag)::value==240)l=derived[size_t(sx-x0)];else
#endif
 l=kr*r+kg*g+kb*b;
#if defined(__aarch64__)
 if constexpr(decltype(tag)::value==240){if(ordinary[sx-x0]&&txb>=1&&tyb>=2){
  const size_t at=sx-x0,span=x1-x0;double u=derived[span+at],v=derived[2*span+at];int band=l<lc?0:l<hc?1:2;bn[band]++;
  if(u< -half||u>half||v< -half||v>half){outside++;bo[band]++;}else{int x=int(roundBin(derived[7*span+at])),y=int(roundBin(derived[8*span+at]));p[4+band].add(size_t(y)*vs+x);bp[band]++;}
  for(int pair=0;pair<2;pair++){int x=int(roundBin(derived[size_t(3+pair*2)*span+at])),y=int(roundBin(derived[size_t(4+pair*2)*span+at]));p[7].add(size_t(y)*tw+x);pairs[pair].plotted++;}
  continue;
 }}
#endif
 double vv[]={r,g,b,l};int xx=(mask&3)?int(std::floor(double(sx-x0)*ww/(x1-x0))):0;
  
  for(int ch=0;ch<4;ch++){double v=vv[ch];
#if defined(__aarch64__)
 if constexpr(decltype(tag)::value!=240)
#endif
 stats[ch].add(v,mn,mx);if(!std::isfinite(v)||v<mn||v>mx||!(mask&(ch==3?1:6)))continue;int bin=int(roundBin((v-mn)/(mx-mn)*(levels-1)));if(ch==3&&(mask&1))p[0].add(size_t(bin)*ww+xx);else if(ch<3){if(mask&2)p[1].add((size_t(ch)*levels+bin)*ww+xx);if(mask&4)p[2].add(ch*hb+int(roundBin((v-mn)/(mx-mn)*(hb-1))));}}
  if(std::isfinite(r)&&std::isfinite(g)&&std::isfinite(b)){double u,v;
#if defined(__aarch64__)
 if constexpr(decltype(tag)::value==240){u=derived[size_t(x1-x0)+sx-x0];v=derived[size_t(2)*(x1-x0)+sx-x0];}else
#endif
 {u=(b-l)/(2*(1-kb));v=(r-l)/(2*(1-kr));}int band=l<lc?0:l<hc?1:2;bn[band]++;if(u< -half||u>half||v< -half||v>half){outside++;bo[band]++;}else{int x,y;
#if defined(__aarch64__)
 if constexpr(decltype(tag)::value==240){x=int(roundBin(derived[size_t(7)*(x1-x0)+sx-x0]));y=int(roundBin(derived[size_t(8)*(x1-x0)+sx-x0]));}else
#endif
 {x=int(roundBin((u+half)/(2*half)*(vs-1)));y=int(roundBin((v+half)/(2*half)*(vs-1)));}size_t ix=size_t(y)*vs+x;if(mask&8)p[3].add(ix);if(mask&(1<<(4+band)))p[4+band].add(ix);bp[band]++;}}
  for(int pair=0;pair<2;pair++){double v=pair?r:b;auto&st=pairs[pair];if(!std::isfinite(v)||!std::isfinite(g)){st.invalid++;continue;}st.gamut+=v<0||v>1||g<0||g>1;double x=v-g,y=(pair?-1.:1.)*(v+g);if(std::abs(x)>txb||std::abs(y)>tyb){st.outside++;continue;}if(mask&128){int ix,iy;
#if defined(__aarch64__)
 if constexpr(decltype(tag)::value==240){ix=int(roundBin(derived[size_t(3+pair*2)*(x1-x0)+sx-x0]));iy=int(roundBin(derived[size_t(4+pair*2)*(x1-x0)+sx-x0]));}else
#endif
 {ix=int(roundBin((x+txb)/(2*txb)*(tw-1)));iy=int(roundBin((y+tyb)/(2*tyb)*(th-1)));}p[7].add(size_t(iy)*tw+ix);}st.plotted++;}
 }}
};
 auto scan=[&](int begin,int end,Plane* planes,Stats* stats,Stats* raw,Pair* pairs,uint32_t* bp,uint32_t* bo,uint32_t* bn,uint32_t&outside){
 if(mask==240)scanImpl(std::integral_constant<int,240>{},begin,end,planes,stats,raw,pairs,bp,bo,bn,outside);
 else scanImpl(std::integral_constant<int,-1>{},begin,end,planes,stats,raw,pairs,bp,bo,bn,outside);
 };
 size_t laneBytes=0;for(int j=0;j<8;j++)if(mask&(1<<j))laneBytes+=sizes[j]*4;
 int workers=laneCount(e,c,size_t(x1-x0)*(y1-y0),laneBytes);set(e,result,"workerCount",workers);
 if(workers==1)scan(y0,y1,p,stats,raw,pairs,bp,bo,bn,outside);
 else{
  struct Work{Plane p[8];Stats stats[4],raw[3];Pair pairs[2];uint32_t bp[3]={},bo[3]={},bn[3]={},outside=0;};
  thread_local std::vector<std::unique_ptr<Work>> pool;while(pool.size()<size_t(workers))pool.push_back(std::make_unique<Work>());
  for(size_t i=workers;i<pool.size();i++)for(auto&p:pool[i]->p){std::vector<uint32_t>().swap(p.owned);std::vector<uint32_t>().swap(p.active);}
  std::atomic<int> nextRow{y0};
  std::vector<std::thread> threads;
  for(int worker=0;worker<workers;worker++){
   auto&w=*pool[worker];for(int j=0;j<8;j++){auto&a=w.p[j];if(mask&(1<<j)){if(a.owned.size()!=sizes[j])a.owned.assign(sizes[j],0);else for(auto ix:a.active)a.owned[ix]=0;}else a.owned.clear();a.active.clear();a.p=a.owned.data();a.n=sizes[j];}
   for(auto&s:w.stats)s=Stats{};for(auto&s:w.pairs)s=Pair{};std::fill_n(w.bp,3,0);std::fill_n(w.bo,3,0);std::fill_n(w.bn,3,0);w.outside=0;
  }
  // Small row batches let faster cores take more work without changing any
  // pixel arithmetic. Each lane owns its integer planes and statistics.
  std::vector<Work*> lanes;for(int worker=0;worker<workers;worker++)lanes.push_back(pool[worker].get());
  auto lane=[&](size_t worker){auto&w=*lanes[worker];for(;;){int begin=nextRow.fetch_add(32,std::memory_order_relaxed);if(begin>=y1)break;scan(begin,std::min(begin+32,y1),w.p,w.stats,w.raw,w.pairs,w.bp,w.bo,w.bn,w.outside);}};
#ifdef __APPLE__
  dispatch_apply_f(workers,dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),&lane,[](void*context,size_t i){(*static_cast<decltype(lane)*>(context))(i);});
#else
  for(int worker=0;worker<workers;worker++)threads.emplace_back([&,worker]{lane(worker);});
  for(auto&t:threads)t.join();
#endif
  auto mergeStats=[](Stats&a,const Stats&b){if(b.any){a.lo=a.any?jmin(a.lo,b.lo):b.lo;a.hi=a.any?jmax(a.hi,b.hi):b.hi;a.any=true;}a.invalid+=b.invalid;a.under+=b.under;a.over+=b.over;a.vu+=b.vu;a.vo+=b.vo;};
  for(int worker=0;worker<workers;worker++){auto&w=*pool[worker];for(int j=0;j<8;j++)for(auto ix:w.p[j].active){if(!p[j].p[ix])p[j].active.push_back(ix);p[j].p[ix]+=w.p[j].p[ix];}for(int j=0;j<4;j++)mergeStats(stats[j],w.stats[j]);for(int j=0;j<3;j++){bp[j]+=w.bp[j];bo[j]+=w.bo[j];bn[j]+=w.bn[j];}for(int j=0;j<2;j++){pairs[j].plotted+=w.pairs[j].plotted;pairs[j].outside+=w.pairs[j].outside;pairs[j].invalid+=w.pairs[j].invalid;pairs[j].gamut+=w.pairs[j].gamut;}outside+=w.outside;}
 }

 for(int group=0;group<2;group++){auto array=prop(e,result,group?"rawStats":"stats");for(int ch=0;ch<(group?3:4);ch++){napi_value o;check(napi_get_element(e,array,ch,&o));auto&s=stats[ch];if(s.any){set(e,o,"min",s.lo);set(e,o,"max",s.hi);}set(e,o,"invalid",s.invalid);if(!group){set(e,o,"under",s.under);set(e,o,"over",s.over);set(e,o,"viewportUnder",s.vu);set(e,o,"viewportOver",s.vo);}}}
 auto split=prop(e,result,"splitStats");for(int j=0;j<3;j++){napi_value o;check(napi_get_element(e,split,j,&o));set(e,o,"pixels",bn[j]);set(e,o,"plotted",bp[j]);set(e,o,"outside",bo[j]);}
 auto twin=prop(e,result,"twinStats");for(int j=0;j<2;j++){auto o=prop(e,twin,j?"lower":"upper");auto&s=pairs[j];set(e,o,"plotted",s.plotted);set(e,o,"outside",s.outside);set(e,o,"invalid",s.invalid);set(e,o,"gamut",s.gamut);}set(e,result,"vectorOutside",outside);
 napi_value indices;check(napi_create_object(e,&indices));for(int j=0;j<8;j++){void*dest;napi_value ab,v;size_t bytes=p[j].active.size()*4;check(napi_create_arraybuffer(e,bytes,&dest,&ab));if(bytes)std::memcpy(dest,p[j].active.data(),bytes);check(napi_create_typedarray(e,napi_uint32_array,p[j].active.size(),ab,0,&v));check(napi_set_named_property(e,indices,names[j],v));}return indices;
 }catch(const std::exception&x){napi_throw_error(e,nullptr,x.what());return nullptr;}}
static napi_value crc(napi_env e,napi_callback_info info){try{size_t argc=1;napi_value a;check(napi_get_cb_info(e,info,&argc,&a,nullptr,nullptr));if(argc!=1)throw std::runtime_error("CRC requires bytes");size_t n;auto p=(uint8_t*)typed(e,a,napi_uint8_array,n);if(n>UINT32_MAX)throw std::runtime_error("CRC length overflow");napi_value v;check(napi_create_uint32(e,::crc32(0,p,(uInt)n),&v));return v;}catch(const std::exception&x){napi_throw_error(e,nullptr,x.what());return nullptr;}}
static napi_value cube(napi_env e,napi_callback_info info){try{
 size_t argc=4;napi_value a[4];check(napi_get_cb_info(e,info,&argc,a,nullptr,nullptr));if(argc!=4)throw std::runtime_error("Native cube requires four arguments");
 size_t count,bins;auto data=(float*)typed(e,a[0],napi_float32_array,count);auto c=a[1];auto output=(uint32_t*)typed(e,a[2],napi_uint32_array,bins);auto stats=a[3];
 int width=number(e,c,"sourceWidth"),height=number(e,c,"sourceHeight"),x0=number(e,c,"x0"),x1=number(e,c,"x1"),y0=number(e,c,"y0"),y1=number(e,c,"y1"),n=number(e,c,"cubeResolution");double mn=number(e,c,"min"),mx=number(e,c,"max");
 if(width<1||height<1||uint64_t(width)*height>16777216||count!=size_t(width)*height*3||x0<0||x1>width||y0<0||y1>height||x0>=x1||y0>=y1||(n!=16&&n!=32&&n!=64&&n!=128)||bins!=size_t(n)*n*n||!std::isfinite(mn)||!std::isfinite(mx)||!(mx>mn))throw std::runtime_error("Invalid native cube dimensions");
 struct CubeLane{std::vector<uint32_t> bins,active;uint32_t plotted=0,outside=0,invalid=0;};thread_local std::vector<CubeLane> lanes(8);int workers=laneCount(e,c,size_t(x1-x0)*(y1-y0),bins*4);for(size_t i=workers;i<lanes.size();i++){std::vector<uint32_t>().swap(lanes[i].bins);std::vector<uint32_t>().swap(lanes[i].active);}
 for(int i=0;i<workers;i++){auto&l=lanes[i];if(l.bins.size()!=bins)l.bins.assign(bins,0);else for(auto ix:l.active)l.bins[ix]=0;l.active.clear();l.plotted=l.outside=l.invalid=0;}
 std::vector<CubeLane*> selected;for(int i=0;i<workers;i++)selected.push_back(&lanes[i]);
 std::atomic<int> next{y0};double scale=(n-1)/(mx-mn);auto scan=[&](size_t k){auto&l=*selected[k];for(;;){int begin=next.fetch_add(32,std::memory_order_relaxed);if(begin>=y1)break;for(int y=begin;y<std::min(begin+32,y1);y++)for(int x=x0;x<x1;x++){size_t i=(size_t(y)*width+x)*3;double r=data[i],g=data[i+1],b=data[i+2];if(!std::isfinite(r)||!std::isfinite(g)||!std::isfinite(b)){l.invalid++;continue;}if(r<mn||r>mx||g<mn||g>mx||b<mn||b>mx){l.outside++;continue;}size_t ix=size_t(roundBin((r-mn)*scale))+n*(size_t(roundBin((g-mn)*scale))+n*size_t(roundBin((b-mn)*scale)));if(!l.bins[ix])l.active.push_back(uint32_t(ix));l.bins[ix]++;l.plotted++;}}};
#ifdef __APPLE__
 dispatch_apply_f(workers,dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),&scan,[](void*context,size_t i){(*static_cast<decltype(scan)*>(context))(i);});
#else
 std::vector<std::thread> threads;for(int i=0;i<workers;i++)threads.emplace_back([&,i]{scan(i);});for(auto&t:threads)t.join();
#endif
 std::vector<uint32_t> active;uint32_t plotted=0,outside=0,invalid=0;for(int i=0;i<workers;i++){auto&l=lanes[i];for(auto ix:l.active){if(!output[ix])active.push_back(ix);output[ix]+=l.bins[ix];}plotted+=l.plotted;outside+=l.outside;invalid+=l.invalid;}
 set(e,stats,"plotted",plotted);set(e,stats,"outside",outside);set(e,stats,"invalid",invalid);set(e,stats,"occupied",active.size());
 void*dest;napi_value ab,result;check(napi_create_arraybuffer(e,active.size()*4,&dest,&ab));if(!active.empty())std::memcpy(dest,active.data(),active.size()*4);check(napi_create_typedarray(e,napi_uint32_array,active.size(),ab,0,&result));return result;
 }catch(const std::exception&x){napi_throw_error(e,nullptr,x.what());return nullptr;}}

#include "wave-colour-codec.hpp"
// Validate compact Metal planes without expanding/repacking their exact bytes.
static napi_value validateMetal(napi_env e,napi_callback_info info){try{
 size_t argc=5;napi_value a[5];check(napi_get_cb_info(e,info,&argc,a,nullptr,nullptr));if(argc<4||argc>5)throw std::runtime_error("Metal validator requires four or five arguments");bool adaptive=false;if(argc==5)check(napi_get_value_bool(e,a[4],&adaptive));
 size_t bytes,sn,ln;auto*p=(uint8_t*)typed(e,a[0],napi_uint8_array,bytes);auto*sizes=(uint32_t*)typed(e,a[1],napi_uint32_array,sn);auto*limits=(uint32_t*)typed(e,a[2],napi_uint32_array,ln);uint32_t mask;check(napi_get_value_uint32(e,a[3],&mask));if(sn!=13||ln!=13||bytes>160000000)throw std::runtime_error("Invalid Metal plane layout");
 std::vector<uint32_t>wave,colour;size_t colourBegin=0,colourEnd=0;if(adaptive){if(sizes[9]!=sizes[0]*3)throw std::runtime_error("Invalid source-colour grid");wave.resize(sizes[0]);colour.resize(sizes[9]);}
 size_t at=0;auto word=[&](){if(bytes-at<4)throw std::runtime_error("Truncated Metal plane");uint32_t v=uint32_t(p[at])|(uint32_t(p[at+1])<<8)|(uint32_t(p[at+2])<<16)|(uint32_t(p[at+3])<<24);at+=4;return v;};
 auto variable=[&](){uint32_t v=0;for(uint32_t j=0;j<5;j++){if(at>=bytes)throw std::runtime_error("Truncated Metal integer");uint32_t b=p[at++];if(j==4&&(b&240))throw std::runtime_error("Metal integer overflow");v|=(b&127)<<(j*7);if(!(b&128))return v;}throw std::runtime_error("Metal integer overflow");};
 for(uint32_t plane=0;plane<13;plane++){if(plane==9)colourBegin=at;uint32_t n=sizes[plane],mode=word(),count=word();if(!n||n>40000000||mode>2||count>n||(!mode&&count!=n)||uint64_t(count)*(mode==2?2:mode?8:4)>bytes-at)throw std::runtime_error("Invalid Metal plane length");int64_t previous=-1;
  for(uint32_t i=0;i<count;i++){uint64_t ix=mode==2?uint64_t(previous+int64_t(variable())):mode?word():i;uint32_t v=mode==2?variable():word();if(ix>=n||int64_t(ix)<=previous||v>limits[plane]||(mode&&!v)||(!(mask&(1u<<plane))&&v))throw std::runtime_error("Invalid Metal count/index");if(adaptive&&plane==0)wave[ix]=v;if(adaptive&&plane==9)colour[ix]=v;previous=int64_t(ix);}
 if(plane==9)colourEnd=at;}
 if(at!=bytes)throw std::runtime_error("Trailing Metal analysis bytes");if(adaptive){auto encoded=adaptiveWaveColour(wave,colour);size_t total=colourBegin+encoded.size()+bytes-colourEnd;if(total>160000000)throw std::runtime_error("Adaptive colour allocation limit");void*dest;napi_value ab,result;check(napi_create_arraybuffer(e,total,&dest,&ab));auto*out=(uint8_t*)dest;std::memcpy(out,p,colourBegin);std::memcpy(out+colourBegin,encoded.data(),encoded.size());std::memcpy(out+colourBegin+encoded.size(),p+colourEnd,bytes-colourEnd);check(napi_create_typedarray(e,napi_uint8_array,total,ab,0,&result));return result;}napi_value result;check(napi_get_boolean(e,true,&result));return result;
 }catch(const std::exception&x){napi_throw_error(e,nullptr,x.what());return nullptr;}}
static napi_value init(napi_env e,napi_value exports){napi_value fn;napi_add_env_cleanup_hook(e,ingest::cleanup,e);napi_create_function(e,"startLocalIngest",NAPI_AUTO_LENGTH,ingest::start,nullptr,&fn);napi_set_named_property(e,exports,"startLocalIngest",fn);napi_create_function(e,"localIngestStats",NAPI_AUTO_LENGTH,ingest::stats,nullptr,&fn);napi_set_named_property(e,exports,"localIngestStats",fn);napi_create_function(e,"takeLocalPacket",NAPI_AUTO_LENGTH,ingest::take,nullptr,&fn);napi_set_named_property(e,exports,"takeLocalPacket",fn);napi_create_function(e,"discardLocalPacket",NAPI_AUTO_LENGTH,ingest::discard,nullptr,&fn);napi_set_named_property(e,exports,"discardLocalPacket",fn);napi_create_function(e,"cubeRGB",NAPI_AUTO_LENGTH,cube,nullptr,&fn);napi_set_named_property(e,exports,"cubeRGB",fn);napi_create_function(e,"analyzeRGB",NAPI_AUTO_LENGTH,run,nullptr,&fn);napi_set_named_property(e,exports,"analyzeRGB",fn);napi_create_function(e,"validateMetal",NAPI_AUTO_LENGTH,validateMetal,nullptr,&fn);napi_set_named_property(e,exports,"validateMetal",fn);napi_create_function(e,"crc32",NAPI_AUTO_LENGTH,crc,nullptr,&fn);napi_set_named_property(e,exports,"crc32",fn);return exports;}
NAPI_MODULE(NODE_GYP_MODULE_NAME,init)
