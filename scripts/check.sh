#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 vendor/ipe_web_kit/vendor.py verify .
python3 -m unittest discover -s tests
node --check assets/stampost-play.mjs
node --test tests/*.test.mjs
python3 scripts/build_site.py --check
echo GREEN
