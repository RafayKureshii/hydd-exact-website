#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -f dist/index.html ]]; then
  echo "Run BUILD_ON_MAC.command first."; exit 1
fi
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist
