# HYDD — exact website replica (private repository)

This project is a **captured, independently hosted replica candidate** of the original public HYDD website; it does not alter the live Squarespace site.

- `site/`: most recent completed local website preview snapshot, with the French original and EN/AR pages.
- `hydd_custom/`: the language selector and WhatsApp enhancement source.
- `HYDD_TRANSLATIONS.json`: reviewed/draft translation catalogue.
- `build_clone.py`: source capture/build tool.
- `contact_api.py`: optional independent contact service; must be configured separately.

## Run a local preview

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
```

Then open `http://127.0.0.1:8000/`, `/en/` and `/ar/`.

## Deployment warning

**Not yet production-certified.** Compare pages against the live site, verify all images, forms, sliders, navigation, mobile and Arabic RTL, review translations and legal copy, ensure HTTPS and working contact service, and confirm rights to use the captured assets. Do not change DNS or cancel Squarespace until acceptance checks pass.

No API credentials, environment files, virtual environments or local backups should be committed.
