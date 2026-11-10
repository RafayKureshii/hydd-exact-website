#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -f HYDD_TRANSLATIONS.json ]]; then
  echo "First run: bash BUILD_ON_MAC.command (creates translation catalog)"; exit 1
fi
if [[ ! -f .venv/bin/activate ]]; then
  echo "First run: bash BUILD_ON_MAC.command (installs Python dependencies)"; exit 1
fi
source .venv/bin/activate
python3 build_clone.py --out dist --translations-file HYDD_TRANSLATIONS.json
python3 -m unittest discover -s tests -v
printf '\nTrilingual preview: bash PREVIEW_ON_MAC.command\n'
