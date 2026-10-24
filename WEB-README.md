# Browser viewer

Current viewer: **0.2.50**; release effect: **GTap 1.2.23**.

Use [README.md](README.md) for installation or
[the HTML guide](web/public/guide/index.html) for everyday use.
Run `bash start.sh`; open the address from GTap's panel on a device on the same LAN.
The guide is also at `/guide/index.html` on the host, linked from Settings.

The host uses Node.js and a Node-API native analysis component, with the Resolve
OFX/Metal effect providing image data. Runtime browser dependencies are served
locally, not from a CDN. See [DEVELOPING.md](DEVELOPING.md) for tests/source builds.
