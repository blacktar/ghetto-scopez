export const WAVEFORM_COLOURS=['mono','source','false'];
export function falseColour(level){const h=(1-Math.max(0,Math.min(1,level)))*4,x=1-Math.abs(h%2-1);return h<1?[1,x,0]:h<2?[x,1,0]:h<3?[0,1,x]:[0,x,1];}
export function sourceInk(rgb){const peak=Math.max(...rgb);return peak>0?rgb.map(v=>v/peak):[1,1,1];}
export const WAVEFORM_COLOUR_SHADER=`
// Integrate count and RGB sums over the same footprint in one traversal.
vec4 waveformSourceDensity(){
 ivec2 sz=textureSize(dataTex,0),pixel=ivec2(gl_FragCoord.xy),scale=viewportSize;
 ivec2 begin=clamp(pixel*sz,ivec2(0),sz*scale-1),end=clamp((pixel+1)*sz,begin+1,sz*scale);
 ivec2 lo=begin/scale,hi=(end+scale-1)/scale-1;vec2 extent=vec2(end-begin);vec4 n=vec4(0);
 for(int y=lo.y;y<=hi.y;y++){float wy=float(min(end.y,(y+1)*scale.y)-max(begin.y,y*scale.y))/extent.y;
  for(int x=lo.x;x<=hi.x;x++){float wx=float(min(end.x,(x+1)*scale.x)-max(begin.x,x*scale.x))/extent.x;ivec2 at=ivec2(x,y);
   float count=float(texelFetch(dataTex,at,0).r);uint packed=texelFetch(redTex,at,0).r;vec3 mean=vec3(float(packed&511u),float((packed>>9)&511u),float((packed>>18)&511u))*exp2(float(packed>>27)-24.)/256.;n+=vec4(count,mean*count)*wx*wy;
  }
 }
 return n*max(extent.x/float(scale.x),1.)*max(extent.y/float(scale.y),1.);
}
vec3 falseColour(float level){float h=(1.-clamp(level,0.,1.))*4.,x=1.-abs(mod(h,2.)-1.);return h<1.?vec3(1,x,0):h<2.?vec3(x,1,0):h<3.?vec3(0,1,x):vec3(0,x,1);}
`;
