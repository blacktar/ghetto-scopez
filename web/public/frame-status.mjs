// Frame age distinguishes active arrivals from a retained still, not connection health.
export function resolveFrameStatus(ageMs){return ageMs<=2000?'Receiving data from Resolve':'Still frame · scopes retained';}
