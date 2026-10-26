// Original procedural GPU ambient effect. No image textures, external assets,
// measurement inputs or game state enter this shader.
const fragment=`#version 300 es
precision highp float;
uniform vec2 resolution;
uniform float time;
out vec4 colour;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1)),f.x),f.y);}
float fbm(vec2 p){float n=0.,a=.5;mat2 m=mat2(1.62,1.17,-1.17,1.62);for(int i=0;i<4;i++){n+=a*noise(p);p=m*p+13.7;a*=.5;}return n;}
mat2 turn(float a){return mat2(cos(a),-sin(a),sin(a),cos(a));}
vec3 stars(vec2 p,float grid,float seed){vec2 cell=floor(p*grid),f=fract(p*grid)-.5;float id=hash(cell+seed);vec2 offset=vec2(hash(cell+1.7),hash(cell+8.2))-.5;vec2 d=(f-offset*.7)*grid/80.;float radius=length(d),pulse=.72+.28*sin(time*(.2+id)+id*90.);float core=exp(-radius*radius*1700.);float halo=exp(-radius*radius*100.);float rays=exp(-abs(d.x)*450.)*exp(-abs(d.y)*28.)+exp(-abs(d.y)*450.)*exp(-abs(d.x)*28.);float bright=step(.985,id);vec3 ink=mix(vec3(.16,.65,1.),vec3(1.,.22,.65),hash(cell+40.));ink=mix(ink,vec3(1.,.85,.6),step(.92,hash(cell+70.)));return ink*(core*.65+halo*.035+bright*(rays*.32+halo*.7))*pulse;}
void main(){vec2 uv=gl_FragCoord.xy/resolution;vec2 p=(gl_FragCoord.xy-resolution*.5)/min(resolution.x,resolution.y);vec2 travel=vec2(sin(time*.035)*.035,time*.006);vec2 q=turn(-.35+sin(time*.018)*.025)*(p+travel)*(1.+.035*sin(time*.024));float radius=length(q);float a=atan(q.y,q.x);float drift=time*.012;
 vec2 warp=vec2(fbm(q*2.4+drift),fbm(q*2.4+vec2(7.3,-drift)))-.5;
 float cloud=fbm(q*5.+warp*2.+vec2(drift,-drift*.6));float detail=fbm(q*22.+warp*4.-drift);
 float band=exp(-pow((q.y-sin(q.x*4.+drift)*.12+warp.x*.2)*4.,2.));
 float spiral=pow(.5+.5*sin(a*2.+radius*10.+warp.y*3.-drift),5.)*exp(-radius*1.8);
 float filaments=pow(max(0.,cloud-.22)*1.4,2.5)*(.3+detail);
 vec3 blue=vec3(.025,.22,.95),pink=vec3(.95,.025,.5),cyan=vec3(.025,.8,.95);
 vec3 ink=mix(blue,pink,smoothstep(-.65,.65,q.x+warp.y));ink=mix(ink,cyan,smoothstep(.25,.8,cloud+q.y*.4));
 vec3 c=vec3(.001,.002,.008)+ink*(band*.4+spiral*.35)*filaments*2.5;
 c+=mix(cyan,pink,.5+.5*sin(q.x*3.+q.y*2.))*pow(cloud,3.)*.16;
 float dust=pow(noise(q*420.+warp*3.),18.);c+=mix(vec3(.22,.7,1.),vec3(1.,.36,.7),cloud)*dust*(band+spiral)*.7;
 for(int layer=0;layer<3;layer++){float depth=fract(float(layer)/3.+time*.014);float fade=pow(sin(depth*3.14159265),2.);float perspective=mix(1.55,.48,depth);vec2 s=(p+travel*(.3+float(layer)*.25))*perspective;c+=stars(s,65.+float(layer)*28.,3.+float(layer)*10.)*fade*(.5+depth*.6);}
 float vignette=1.-smoothstep(.3,1.35,length(p*vec2(.7,1.)));c*=.45+.55*vignette;
 c=1.-exp(-c*1.4);colour=vec4(c,1.);}`;
export function createGalaxy(){
 const canvas=document.createElement('canvas'),gl=canvas.getContext('webgl2',{alpha:false,antialias:false,depth:false,stencil:false});if(!gl)return null;
 const compile=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){gl.deleteShader(s);throw Error('OG ambient shader: '+gl.getShaderInfoLog(s));}return s;};
 let program;try{program=gl.createProgram();const shaders=[compile(gl.VERTEX_SHADER,'#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.-1.,0,1);}'),compile(gl.FRAGMENT_SHADER,fragment)];for(const s of shaders)gl.attachShader(program,s);gl.linkProgram(program);for(const s of shaders)gl.deleteShader(s);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('OG ambient shader link failed');}catch{gl.getExtension('WEBGL_lose_context')?.loseContext();return null;}
 let pixelBudget=450000,last=0,slow=0;
 const size=gl.getUniformLocation(program,'resolution'),clock=gl.getUniformLocation(program,'time');
 return {draw(context,width,height,now,reduced){if(gl.isContextLost())return false;const gap=last?now-last:0;last=now;if(gap>65&&gap<1000){if(++slow>=4){pixelBudget=Math.max(75000,Math.round(pixelBudget*.75));slow=0;}}else slow=Math.max(0,slow-1);const scale=Math.min(.7,Math.sqrt(pixelBudget/(width*height))),w=Math.max(1,Math.round(width*scale)),h=Math.max(1,Math.round(height*scale));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}gl.viewport(0,0,w,h);gl.useProgram(program);gl.uniform2f(size,w,h);gl.uniform1f(clock,reduced?0:now*.001);gl.drawArrays(gl.TRIANGLES,0,3);context.drawImage(canvas,0,0,width,height);return true;},dispose(){gl.deleteProgram(program);gl.getExtension('WEBGL_lose_context')?.loseContext();}};
}
