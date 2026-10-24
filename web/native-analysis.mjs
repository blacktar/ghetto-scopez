import {createRequire} from 'node:module';
let kernel=null,crc=null,cube=null,ingest=null,ingestStats=null,take=null,discard=null,validate=null;
if(process.env.SCOPE_ANALYSIS!=='js')try{{const addon=createRequire(import.meta.url)('../build/scope-analysis.node');validate=addon.validateMetal;kernel=addon.analyzeRGB;crc=addon.crc32;cube=addon.cubeRGB;ingest=addon.startLocalIngest;ingestStats=addon.localIngestStats;take=addon.takeLocalPacket;discard=addon.discardLocalPacket;}}catch{}
export const nativeRGB=kernel,nativeCRC=crc,nativeCube=cube,nativeIngest=ingest,nativeIngestStats=ingestStats,nativeTake=take,nativeDiscard=discard;

export const nativeValidateMetal=validate;
