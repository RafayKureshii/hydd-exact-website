# HYDD — English and Arabic translation catalogue

This package contains a filled `HYDD_TRANSLATIONS.json` for the **HYDD_EXACT_REPLICA_NO_API_KEY** Mac-side migration project.

## What is included

- 528 source French strings preserved exactly as captured.
- 528 nonempty English drafts and 528 nonempty Arabic drafts.
- The `source` URL, languages, and JSON structure remain compatible with the existing `FINALIZE_TRANSLATIONS.command` workflow.
- No Google Cloud Translation API key is required.

## Use on your Mac

1. Unzip this package and extract `HYDD_TRANSLATIONS.json`.
2. In the extracted **HYDD_EXACT_REPLICA_NO_API_KEY** project directory where `FINALIZE_TRANSLATIONS.command` exists, back up the existing `HYDD_TRANSLATIONS.json` (for example, rename it `HYDD_TRANSLATIONS_before_translation.json`).
3. Copy the newly provided `HYDD_TRANSLATIONS.json` into that same project directory.
4. Open **Terminal**, type `bash ` followed by a space, drag `FINALIZE_TRANSLATIONS.command` into the terminal, and press Return.
5. If the build succeeds, run `PREVIEW_ON_MAC.command` the same way and open http://127.0.0.1:8000/. Check `/en/` and `/ar/` and each original service-page route.

If the live French site changed since the first capture, the finalizer may add new source strings and refuse to complete until they are translated. This protects against displaying French-only paragraphs on the English and Arabic copies. Preserve your original `HYDD_TRANSLATIONS.json` when reporting any such errors.

## Important acceptance notes

These are **draft translations**, not human-certified translations. The English, Arabic and legal text must be reviewed by qualified native-language reviewers before publication, including names, prices, safety/medical claims, data protection and terms & conditions. The project uses `dir=rtl` for Arabic, but the page layout, licensed assets, navigation, video, slider, buttons and Squarespace-dependent forms still need real-browser and device tests.

No production domain/DNS or Squarespace changes are performed by this file.
