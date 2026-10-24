import {RELEASE} from './release.mjs';
import {reportClientError} from './diagnostics.mjs';
document.documentElement.dataset.release=RELEASE.version;
window.addEventListener('error',event=>reportClientError(event.error||event.message,'page'));
window.addEventListener('unhandledrejection',event=>reportClientError(event.reason,'page'));
import('./viewer.mjs?v='+RELEASE.version).catch(error=>reportClientError(error,'startup'));
