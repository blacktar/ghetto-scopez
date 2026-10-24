# Ghetto Scopez + GTap

Colour scopes from DaVinci Resolve in a browser on your local network.
Made by **Vidar Andersen**. [Project website](https://vidarandersen.com/dmz/ghettoscopez).

**[Read the user guide](web/public/guide/index.html)** ·
[Download the Mac release](https://github.com/blacktar/ghetto-scopez/releases/latest)

## Install and start

This release includes **GTap 1.2.23** and **viewer 0.2.48**.
The supplied universal GTap binary requires **macOS 27 or later** (Apple silicon
or Intel). Earlier macOS versions have not been verified for this release.
DaVinci Resolve, Node.js 20+ (a current LTS is recommended), and Apple's command
line tools are required. Node.js and Resolve are not bundled.

1. Download and unzip the complete release ZIP. Keep its folder together.
2. Install [Node.js](https://nodejs.org/en/download) and, if needed, run
   `xcode-select --install` and finish Apple's installation.
3. Quit Resolve. In Terminal, change into the unzipped folder.
4. Run `bash install.sh`. It installs dependencies, builds the local host component,
   verifies GTap's checksum and signature, then asks for administrator access to
   install the effect. It does not launch Resolve.
5. Run `bash start.sh` and keep the Terminal window open.
6. Open Resolve, add GTap after the output/display transform you want to measure,
   and declare the matching BT.709 or BT.2020 RGB input primaries.
7. Open the scope address shown in GTap's panel on another device on the same
   network. Select **Start listening**, or **Fullscreen** to start automatically.

The installer only uses administrator access for the system OFX plugin folder.
`bash install.sh --check` checks requirements without installing.
GTap is currently locally signed. Apple notarization is pending Apple’s reactivation
of the dormant Apple Developer ID. The current binary's minimum OS
comes from its actual build metadata, not an inferred compatibility claim.

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
