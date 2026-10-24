// Adapt concurrency to measured work and source cadence, with hysteresis.
// A slow source should not consume all CPU cores just because they are present.
export class AnalysisLanes{
 constructor(max=4){this.max=Math.max(1,Math.min(8,Math.floor(max)));this.lanes=Math.min(2,this.max);this.mean=null;this.samples=0;}
 observe(ms,periodMs){if(!Number.isFinite(ms)||ms<=0)return this.lanes;this.mean=this.mean===null?ms:.7*this.mean+.3*ms;if(++this.samples<4)return this.lanes;this.samples=0;const budget=.7*Math.max(16.67,Math.min(1000,periodMs||100));let next=this.lanes;
 if(this.mean>budget*1.1)next=Math.min(this.max,this.lanes+1);
 else if(this.mean<budget*.6)next=Math.max(1,this.lanes-1);
 if(next!==this.lanes){this.lanes=next;this.mean=null;}return this.lanes;}
}
