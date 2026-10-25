# Ghetto Scopez + GTap

Colour scopes from DaVinci Resolve in a browser on your local network.
Made by **Vidar Andersen**. [Read the user guide](https://vidarandersen.com/dmz/ghettoscopez).

[Download the Mac release](https://github.com/blacktar/ghetto-scopez/releases/latest)

## Install and start

This release includes **GTap 1.2.24** and **viewer 0.2.52**.
The supplied universal GTap binary requires **macOS 27 or later** (Apple silicon
or Intel). Earlier macOS versions have not been verified for this release.
DaVinci Resolve is required. The new `.pkg` installer bundles the server,
Node.js runtime, browser dependencies and prebuilt GTap; no developer tools or
separate runtime installation are required.

1. Quit Resolve and stop any older Ghetto Scopez host.
2. Open the Mac `.pkg` installer and enter your administrator password when asked.
3. Double-click the desktop **Ghetto Scopez** alias to start the app or open its
   server controls. Use **GS** in the menu bar to open the viewer or guide, start/stop the server,
   show its log or quit. The server starts after installation and at login.
4. Open Resolve, add GTap at the measurement point and choose the matching input.
   Open its panel’s network address on the other display.

Open **Ghetto Scopez** from Applications to reopen the menu-bar app after quitting.
The installer is Developer ID signed and Apple-notarised. Full fresh/upgrade
installation and login-startup testing remain pending. The earlier
ZIP/Install.command package is retained as a legacy download.

## What is included

Waveform, RGB parade/histogram, vectorscopes and highs/mids/lows views, DoubleD,
a rotatable RGB cube, saturation/luma and hue histogram; image region and colour
selection; three A/B/C snapshots per scope; saved browser settings and settings
files. The guide works offline and on portrait phones. Its full-width header
randomly selects one of 37 supplied images, converted to responsive WebP assets.

Source / working-space tap: choose **Source / working-space RGB — no transform**
in GTap Input to measure raw float32 RGB at that node. RGB is unchanged; negative
and above-one values are retained. Weighted RGB and difference views use an
explicit fixed BT.709 analysis basis, without inferring project primaries or
transfer. Display targets are hidden and axes use raw float values.

The host is intended for a trusted local network. No account is required.
Update speed varies by image and device; source-coloured waveforms remain demanding.

## Licence

**CC BY-NC-SA 4.0**, for original project material. See [LICENSE](LICENSE) and
[LICENSE-NOTICE.txt](LICENSE-NOTICE.txt). Included third-party components retain
their own licences; see [THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt).

## Source and validation

See [DEVELOPING.md](DEVELOPING.md) for source builds and tests. Source archives
without the prebuilt effect cannot run the release installer until GTap is built.
