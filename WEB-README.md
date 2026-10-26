# Browser viewer

Current viewer: **0.2.54**; release effect: **GTap 1.2.26**.

Use [README.md](README.md) for installation or
[the HTML guide](web/public/guide/index.html) for everyday use.
For the new `.pkg` installation, use **GS** in the menu bar to start/stop the
server and open the viewer. It starts automatically at login. Source checkouts
can still run `bash start.sh`. Open GTap’s address on a device on the same LAN.
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

Zoom (1×–4×) and Detail Level (Q1–Q4) are independent. Q controls underlying detail in all scope types; Smooth now applies to every plot using spatial, value-axis, circular-hue or soft-point filtering as appropriate. DoubleD always retains its aspect ratio. The expanded grids require GTap 1.2.25 and the updated host.
