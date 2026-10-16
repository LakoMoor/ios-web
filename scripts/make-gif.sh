#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node --input-type=module -e "import {readFileSync} from 'node:fs'; const r=JSON.parse(readFileSync('artifacts/browser-result.json')); if(r.arm64Probe!=='passed') throw new Error('Run the real browser test with --capture first');"
ffmpeg -y -framerate 5 -i artifacts/frames/%03d.png \
  -filter_complex 'fps=5,scale=1000:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse' \
  -loop 0 artifacts/ios-web.gif
