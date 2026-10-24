# Source builds and validation

The supported user workflow is in the HTML guide. The current browser host is
`web/server.mjs`; the viewer is under `web/public`; the Resolve effect is in `ofx`.
`host` and `ipad` contain earlier transport prototypes, not required by the current
browser product. Internal benchmark recordings, local session notes, Resolve media,
credentials, installed dependencies and build caches are not release source.

## Host

Install Node.js and Apple's command line tools, then:

```sh
npm --prefix web ci
bash scripts/build-analysis.sh
bash start.sh
```

If Node headers are installed elsewhere, set `NODE_HEADERS` to the directory
containing `node_api.h` before running `build-analysis.sh`.

## GTap

Building the effect requires Apple's command line tools and the OpenFX SDK/support
library supplied with Resolve. `OFX_SDK` can override its location.

```sh
bash scripts/build-ofx.sh
```

The build increments the plugin build version and creates signed universal bundles
in `build`. Inspect their minimum macOS deployment version before redistributing.
Do not replace an installed plugin while Resolve is running. The release installer
expects the versioned plugin archive and SHA256SUMS under `release`.

## Checks

```sh
npm --prefix web test
bash scripts/test-ofx.sh
bash scripts/test-metal.sh
bash scripts/test-metal-analysis.sh
```

The guide/asset host change passed the full 121-test Node suite. GTap 1.2.23
previously passed 96 GPU analysis cases, native/core/panel checks and scope image
comparisons. Physical-device performance depends on the machine and browser;
these correctness results are not a frame-rate promise.

The plugin is ad-hoc signed. Apple notarization is pending Apple’s reactivation
of the dormant Apple Developer ID. An installer preflight and isolated
host smoke check are not a fresh-machine installation test. No automatic Resolve
quit/relaunch or public-network hosting is performed by the installer.

The current release installer uses the signed universal Node-API host binary in
release/scope-analysis.node. It installs the pinned official Node.js package only
when needed. Published Mac ZIPs also include the three pinned host dependencies.
The source build commands above remain available for contributors.
