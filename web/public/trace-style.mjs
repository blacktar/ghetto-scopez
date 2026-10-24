export function traceStyle(value={}){return {smooth:value.smooth===true,gain:Number.isFinite(Number(value.gain))?Math.max(1/16,Math.min(16,Number(value.gain))):1,brightness:Number.isFinite(Number(value.brightness))?Math.max(10,Math.min(400,Number(value.brightness))):100};}
// Display-only density filtering, before gain/log compression and brightness.
// A retained sharp component keeps isolated excursions visible.
export const SMOOTH_KERNEL=[1,6,15,20,15,6,1];
export function smoothDensity(values,w,h){
 const temp=new Float64Array(w*h),out=new Float64Array(w*h);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){let n=0;for(let k=-3;k<=3;k++)if(x+k>=0&&x+k<w)n+=values[y*w+x+k]*SMOOTH_KERNEL[k+3]/64;temp[y*w+x]=n;}
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){let n=0;for(let k=-3;k<=3;k++)if(y+k>=0&&y+k<h)n+=temp[(y+k)*w+x]*SMOOTH_KERNEL[k+3]/64;out[y*w+x]=.25*values[y*w+x]+.75*n;}
 return out;
}
export const TRACE_STYLE_SHADER=`
float traceDensityAt(usampler2D tex,ivec2 pixel){
 if(any(lessThan(pixel,ivec2(0)))||any(greaterThanEqual(pixel,viewportSize)))return 0.;
 return densityAtPixel(tex,uv,pixel);
}
float traceIntensity(usampler2D tex){
 ivec2 pixel=ivec2(gl_FragCoord.xy);float d=traceDensityAt(tex,pixel);
 if(smoothTraces){
  const float weights[7]=float[7](1.,6.,15.,20.,15.,6.,1.);float filtered=0.;
  for(int y=-3;y<=3;y++)for(int x=-3;x<=3;x++)filtered+=weights[x+3]*weights[y+3]/4096.*traceDensityAt(tex,pixel+ivec2(x,y));
  d=.25*d+.75*filtered;
 }
 return clamp(log(1.+d*traceGain)*.25*traceBrightness,0.,1.);
}`;
