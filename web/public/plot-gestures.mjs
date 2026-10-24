// Claim gestures only inside an interactive plot. Header controls and Settings
// retain normal touch/scroll behavior. Safari also needs non-passive Touch events.
export function bindPlotGestureGuard(plot){
 const cancel=event=>{if(event.cancelable)event.preventDefault();};
 for(const type of ['touchstart','touchmove','touchend','gesturestart','gesturechange','gestureend'])plot.addEventListener(type,cancel,{passive:false,capture:true});
 plot.style.touchAction='none';plot.style.overscrollBehavior='contain';plot.style.webkitUserSelect='none';plot.style.webkitTouchCallout='none';
 return ()=>{for(const type of ['touchstart','touchmove','touchend','gesturestart','gesturechange','gestureend'])plot.removeEventListener(type,cancel,{capture:true});};
}
