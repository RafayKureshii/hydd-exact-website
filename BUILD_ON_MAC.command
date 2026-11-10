#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
echo "HYDD — original French website capture (NO API KEYS required)"
echo "Source: https://www.hydd.fr — public site only; doesn't modify Squarespace"
if ! command -v python3 >/dev/null 2>&1; then echo "Python 3 is required"; exit 1; fi
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --quiet -r requirements.txt
python3 build_clone.py --out dist
python3 -m unittest discover -s tests -v
printf '\nFrench site: dist/index.html\nPreview: bash PREVIEW_ON_MAC.command\n'
printf 'For EN/AR, supply human-approved text in HYDD_TRANSLATIONS.json; then bash FINALIZE_TRANSLATIONS.command\n'
