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

// Display-only 1D smoothing; each channel is isolated, hue wraps around.
export function smoothHistogram(values,bins,channels=1,wrap=false){const out=new Float64Array(values.length);for(let ch=0;ch<channels;ch++)for(let x=0;x<bins;x++){let sum=0;for(let k=-3;k<=3;k++){const at=wrap?(x+k+bins)%bins:Math.max(0,Math.min(bins-1,x+k));sum+=values[ch*bins+at]*SMOOTH_KERNEL[k+3]/64;}out[ch*bins+x]=.25*values[ch*bins+x]+.75*sum;}return out;}
// Separable Canvas filtering works in Safari without Canvas filter support.
export function createTraceFilter(){const base=document.createElement('canvas'),pass=document.createElement('canvas'),out=document.createElement('canvas');return {draw(source,context,width,height,groups=1){const w=Math.max(1,Math.min(1024,Math.round(width))),h=Math.max(1,Math.min(1024,Math.round(height)));for(const layer of [base,pass,out]){if(layer.width!==w||layer.height!==h){layer.width=w;layer.height=h;}else layer.getContext('2d').clearRect(0,0,w,h);}base.getContext('2d').drawImage(source,0,0,source.width,source.height,0,0,w,h);const a=pass.getContext('2d'),b=out.getContext('2d');a.globalCompositeOperation=b.globalCompositeOperation='lighter';for(let group=0;group<groups;group++){const left=Math.round(group*w/groups),right=Math.round((group+1)*w/groups);a.save();a.beginPath();a.rect(left,0,right-left,h);a.clip();for(let k=-3;k<=3;k++){a.globalAlpha=SMOOTH_KERNEL[k+3]/64;a.drawImage(base,left,0,right-left,h,left+k,0,right-left,h);}a.restore();}b.globalAlpha=.25;b.drawImage(base,0,0);for(let k=-3;k<=3;k++){b.globalAlpha=.75*SMOOTH_KERNEL[k+3]/64;b.drawImage(pass,0,k);}context.drawImage(out,0,0,width,height);}};}
