# Browser viewer

Current viewer: **0.2.52**; release effect: **GTap 1.2.24**.

Use [README.md](README.md) for installation or
[the HTML guide](web/public/guide/index.html) for everyday use.
Run `bash start.sh`; open the address from GTap's panel on a device on the same LAN.
The guide is also at `/guide/index.html` on the host, linked from Settings.

The host uses Node.js and a Node-API native analysis component, with the Resolve
OFX/Metal effect providing image data. Runtime browser dependencies are served
locally, not from a CDN. See [DEVELOPING.md](DEVELOPING.md) for tests/source builds.

Source / working-space tap: choose **Source / working-space RGB — no transform**
in GTap Input to measure raw float32 RGB at that node. RGB is unchanged; negative
and above-one values are retained. Weighted RGB and difference views use an
explicit fixed BT.709 analysis basis, without inferring project primaries or
transfer. Display targets are hidden and axes use raw float values.

The user guide includes a Lens Debaser teaser and optional tawk.to support chat,
loaded after the guide finishes loading. The guide remains readable offline.
