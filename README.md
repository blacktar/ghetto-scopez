# Ghetto Scopez + GTap

Colour scopes from DaVinci Resolve in a browser on your local network.
Made by **Vidar Andersen**. [Read the user guide](https://vidarandersen.com/dmz/ghettoscopez).

[Download the Mac release](https://github.com/blacktar/ghetto-scopez/releases/latest)

## Install and start

This release includes **GTap 1.2.23** and **viewer 0.2.51**.
The supplied universal GTap binary requires **macOS 27 or later** (Apple silicon
or Intel). Earlier macOS versions have not been verified for this release.
DaVinci Resolve is required. The installer automatically installs the official
Apple-signed Node.js package if a compatible Node.js version is not already present.
The release includes the compiled host component and browser dependencies; no
command line tools or manual setup commands are needed.

1. Download and unzip the complete Mac release ZIP.
2. Double-click **Install.command**. Quit Resolve if the installer asks; it waits
   and continues automatically.
3. Enter your Mac administrator password when requested. Setup installs the host
   requirements and GTap, then starts the host and opens the HTML guide.
4. Reopen Resolve, add GTap after the display/output transform you want to measure,
   and choose the matching input declaration. Open the address in its panel on
   another device, then select **Start listening** or **Fullscreen**.

For subsequent sessions, double-click **Start.command**. Keep its Terminal window
open while using the scopes. Control-C stops the host.

Node.js is downloaded from nodejs.org only when needed; the installer verifies its
pinned SHA-256 checksum and Apple Developer ID signature before installing it.
`bash install.sh --check` performs a read-only release preflight.
GTap is currently locally signed. Apple notarization is pending Apple’s reactivation
of the dormant Apple Developer ID. macOS may require permission to open downloaded
commands in Privacy & Security. The installer does not bypass macOS security controls
or launch/quit Resolve for you.

## What is included

Waveform, RGB parade/histogram, vectorscopes and highs/mids/lows views, DoubleD,
a rotatable RGB cube, saturation/luma and hue histogram; image region and colour
selection; three A/B/C snapshots per scope; saved browser settings and settings
files. The guide works offline and on portrait phones. Its full-width header
randomly selects one of 34 supplied images, converted to responsive WebP assets.

The host is intended for a trusted local network. No account is required.
Update speed varies by image and device; source-coloured waveforms remain demanding.

## Licence

**CC BY-NC-SA 4.0**, for original project material. See [LICENSE](LICENSE) and
[LICENSE-NOTICE.txt](LICENSE-NOTICE.txt). Included third-party components retain
their own licences; see [THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt).

## Source and validation

See [DEVELOPING.md](DEVELOPING.md) for source builds and tests. Source archives
without the prebuilt effect cannot run the release installer until GTap is built.
