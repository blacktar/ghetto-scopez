static const char* analysisSource=R"METAL(#include <metal_stdlib>
using namespace metal;
#pragma clang fp contract(off)
struct Config {uint width,height,x0,x1,y0,y1,levels,vs,n,mask,shards,stride;float mn,mx,zoom,tx,ty,lo,hi,kr,kg,kb;uint offsets[13];uint iso;float hueCenter,hueWidth,satMin,satMax,lumaMin,lumaMax;};

float3 colourHSV(float3 v){float hi=max(v.r,max(v.g,v.b)),lo=min(v.r,min(v.g,v.b)),d=hi-lo,h=0;if(d>0){h=hi==v.r?(v.g-v.b)/d:hi==v.g?(v.b-v.r)/d+2:(v.r-v.g)/d+4;h=fract(h/6+1);}return float3(h,hi>0?d/hi:0,hi);}
bool colourSelected(float3 v,float l,constant Config&c){if(!c.iso)return true;if(!all(isfinite(v))||!isfinite(l))return false;float3 q=colourHSV(v);float distance=fmod(abs(q.x*360-c.hueCenter),360.f);return q.y>=c.satMin&&q.y<=c.satMax&&l>=c.lumaMin&&l<=c.lumaMax&&min(distance,360-distance)<=c.hueWidth;}

void inc(device atomic_uint*p,uint i,uint n=1){if(n)atomic_fetch_add_explicit(p+i,n,memory_order_relaxed);}
void bin(device atomic_uint*out,uint offset,uint ix){if(offset!=0xffffffff)inc(out,offset+ix);}
uint rnd(float v){return uint(floor(v+.5f));}
// Eight interleaved pixels per thread: neighboring lanes retain coalesced reads.
// Every ROI pixel is visited once; metadata reductions are amortized eightfold.
// Counts remain uint32 and the per-pixel float32 expressions are unchanged.
struct Meta {uint4 lo,hi,invalid,under,over,vu,vo;uint3 splitPixels,splitOutside;uint4 upper,lower;uint3 cube;};
void sumCounter(device atomic_uint*s,uint at,uint v,uint lane){uint n=simd_sum(v);if(lane==0)inc(s,at,n);}
kernel void analyze(device const float*rgb [[buffer(0)]],device atomic_uint*counts [[buffer(1)]],device atomic_uint*summaryInput [[buffer(2)]],constant Config&c [[buffer(3)]],uint threadId [[thread_position_in_grid]],uint lane [[thread_index_in_simdgroup]],uint group [[threadgroup_position_in_grid]],uint gridSize [[threads_per_grid]]){
 Meta m={};m.lo=uint4(0xffffffff);device atomic_uint*out=counts+(group%c.shards)*c.stride;uint rw=c.x1-c.x0,rh=c.y1-c.y0;
 for(uint item=0;item<8;item++){uint id=threadId+item*gridSize;if(id>=rw*rh)continue;uint x=c.x0+id%rw,y=c.y0+id/rw,at=(y*c.width+x)*3;float r=rgb[at],g=rgb[at+1],b=rgb[at+2],l=(c.kr*r+c.kg*g)+c.kb*b;if(!colourSelected(float3(r,g,b),l,c))continue;float4 val=float4(r,g,b,l);bool4 finite=isfinite(val);uint4 bits=as_type<uint4>(val),ordered=select(bits^0x80000000u,~bits,(bits&0x80000000u)!=0);m.lo=min(m.lo,select(uint4(0xffffffff),ordered,finite));m.hi=max(m.hi,select(uint4(0),ordered,finite));m.invalid+=uint4(!finite);m.under+=uint4(finite&&(val<0));m.over+=uint4(finite&&(val>1));m.vu+=uint4(finite&&(val<c.mn));m.vo+=uint4(finite&&(val>c.mx));
 if(c.mask&7){uint wx=min(511u,(x-c.x0)*512/rw);for(uint ch=0;ch<4;ch++){if(ch<3&&!(c.mask&6))continue;float v=val[ch];if(isfinite(v)&&v>=c.mn&&v<=c.mx){uint iy=rnd((v-c.mn)/(c.mx-c.mn)*float(c.levels-1));if(ch==3)bin(out,c.offsets[0],iy*512+wx);else{bin(out,c.offsets[1],(ch*c.levels+iy)*512+wx);bin(out,c.offsets[2],ch*c.levels+iy);}}}}

 bool valid=isfinite(r)&&isfinite(g)&&isfinite(b);float u=(b-l)/(2*(1-c.kb)),v=(r-l)/(2*(1-c.kr)),extent=.5f/c.zoom;uint band=l<c.lo?0:l<c.hi?1:2;bool outside=valid&&(u< -extent||u>extent||v< -extent||v>extent);if(valid){m.splitPixels[band]++;m.splitOutside[band]+=outside;if(!outside){uint ix=rnd((u+extent)/(2*extent)*float(c.vs-1)),iy=rnd((v+extent)/(2*extent)*float(c.vs-1));bin(out,c.offsets[3],iy*c.vs+ix);bin(out,c.offsets[4+band],iy*c.vs+ix);}}
 for(uint pair=0;pair<2;pair++){float a=pair==0?b:r,dx=a-g,dy=pair==0?a+g:-(a+g);bool ok=isfinite(a)&&isfinite(g),off=ok&&(abs(dx)>c.tx||abs(dy)>c.ty);uint4 st=uint4(ok&&!off,off,!ok,ok&&(a<0||a>1||g<0||g>1));if(pair==0)m.upper+=st;else m.lower+=st;if(ok&&!off)bin(out,c.offsets[7],rnd((dy+c.ty)/(2*c.ty)*1023)*512+rnd((dx+c.tx)/(2*c.tx)*511));}
 if(c.mask&6144){float3 q=colourHSV(float3(r,g,b));if(valid&&isfinite(l)){if((c.mask&2048)&&l>=c.mn&&l<=c.mx&&q.y>=0&&q.y<=1)bin(out,c.offsets[11],rnd((l-c.mn)/(c.mx-c.mn)*255)*256+rnd(q.y*255));if((c.mask&4096)&&q.y>=.02f&&q.z>1e-6f&&q.z<=1&&min(r,min(g,b))>=0)bin(out,c.offsets[12],min(359u,uint(floor(q.x*360))));}}
 if(c.mask&256){bool off=valid&&(r<c.mn||r>c.mx||g<c.mn||g>c.mx||b<c.mn||b>c.mx);m.cube+=uint3(valid&&!off,off,!valid);if(valid&&!off){float scale=float(c.n-1)/(c.mx-c.mn);uint ix=rnd((r-c.mn)*scale)+c.n*(rnd((g-c.mn)*scale)+c.n*rnd((b-c.mn)*scale));bin(out,c.offsets[8],ix);}}
 }
 device atomic_uint*s=summaryInput+(group%c.shards)*64;
 for(uint ch=0;ch<4;ch++){uint lo=simd_min(m.lo[ch]),hi=simd_max(m.hi[ch]),at=ch*8;if(lane==0){if(lo<atomic_load_explicit(s+at,memory_order_relaxed))atomic_fetch_min_explicit(s+at,lo,memory_order_relaxed);if(hi>atomic_load_explicit(s+at+1,memory_order_relaxed))atomic_fetch_max_explicit(s+at+1,hi,memory_order_relaxed);}sumCounter(s,at+3,m.invalid[ch],lane);sumCounter(s,at+4,m.under[ch],lane);sumCounter(s,at+5,m.over[ch],lane);sumCounter(s,at+6,m.vu[ch],lane);sumCounter(s,at+7,m.vo[ch],lane);}
 for(uint b=0;b<3;b++){sumCounter(s,32+b*3,m.splitPixels[b],lane);sumCounter(s,33+b*3,m.splitPixels[b]-m.splitOutside[b],lane);sumCounter(s,34+b*3,m.splitOutside[b],lane);}for(uint k=0;k<4;k++){sumCounter(s,41+k,m.upper[k],lane);sumCounter(s,45+k,m.lower[k],lane);}if(c.mask&256)for(uint k=0;k<3;k++)sumCounter(s,49+k,m.cube[k],lane);
}
kernel void merge(device const uint*input [[buffer(0)]],device uint*output [[buffer(1)]],constant Config&c [[buffer(3)]],uint id [[thread_position_in_grid]]){if(id>=c.stride)return;uint n=0;for(uint k=0;k<c.shards;k++)n+=input[k*c.stride+id];output[id]=n;}

// Each group owns one waveform column and a bounded 1024-level tile.
// Keep exact colour sums in threadgroup memory; publish each bin once.
kernel void waveformColour(device const float*rgb [[buffer(0)]],device uint*output [[buffer(1)]],constant Config&c [[buffer(3)]],uint tid [[thread_index_in_threadgroup]],uint3 group [[threadgroup_position_in_grid]],uint3 groupSize [[threads_per_threadgroup]]){
 uint threads=groupSize.x;
 threadgroup atomic_uint local[3072];
 for(uint i=tid;i<3072;i+=threads)atomic_store_explicit(local+i,0,memory_order_relaxed);
 threadgroup_barrier(mem_flags::mem_threadgroup);
 uint rw=c.x1-c.x0,rh=c.y1-c.y0,wx=group.x,base=group.y*1024;
 uint left=(wx*rw+511)/512,right=((wx+1)*rw+511)/512,cols=right-left;
 for(uint i=tid;i<cols*rh;i+=threads){uint x=c.x0+left+i%cols,y=c.y0+i/cols,at=(y*c.width+x)*3;
  float3 v=float3(rgb[at],rgb[at+1],rgb[at+2]);float l=(c.kr*v.r+c.kg*v.g)+c.kb*v.b;
  if(colourSelected(v,l,c)&&all(isfinite(v))&&isfinite(l)&&l>=c.mn&&l<=c.mx){uint iy=rnd((l-c.mn)/(c.mx-c.mn)*float(c.levels-1));
   if(iy>=base&&iy<base+1024)for(uint ch=0;ch<3;ch++){uint q=rnd(clamp(v[ch],0.f,1.f)*255.f);if(q)atomic_fetch_add_explicit(local+ch*1024+iy-base,q,memory_order_relaxed);}
  }
 }
 threadgroup_barrier(mem_flags::mem_threadgroup);
 for(uint i=tid;i<3072;i+=threads){uint ch=i/1024,iy=base+i%1024;output[c.offsets[9]+ch*c.levels*512+iy*512+wx]=atomic_load_explicit(local+i,memory_order_relaxed);}
}
)METAL";
