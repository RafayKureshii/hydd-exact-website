#!/usr/bin/env python3
"""HYDD public Squarespace snapshot -> self-hosted static website.

Captures PUBLIC URLs only. This is a best-effort HTML/CSS/asset snapshot, not an
export of Squarespace private features, databases, or its proprietary editor.

Usage:
  python3 build_clone.py --out dist
  python3 build_clone.py --out dist
  # After human translations are filled in HYDD_TRANSLATIONS.json:
  python3 build_clone.py --out dist --translations-file HYDD_TRANSLATIONS.json
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree.ElementTree import Element, SubElement, ElementTree

import requests
from bs4 import BeautifulSoup, Comment, NavigableString

ORIGIN = "https://www.hydd.fr"
HOSTS = {"www.hydd.fr", "hydd.fr"}
ASSET_DOMAINS = {
    "www.hydd.fr", "hydd.fr", "images.squarespace-cdn.com", "static1.squarespace.com",
    "static.squarespace.com", "assets.squarespace.com", "fonts.googleapis.com",
    "fonts.gstatic.com", "use.typekit.net", "p.typekit.net",
}
KNOWN_PUBLIC_PATHS = [
    "/", "/services", "/mise-disposition", "/digital-products-1-1",
    "/vip", "/evnements", "/excursions", "/coner", "/guard",
    "/about", "/team", "/app", "/notre-fl", "/contact", "/cgv",
]
SKIP_PATH_PREFIXES = ("/config", "/api/", "/commerce/", "/universal/", "/scheduling/", "/cart")
MEDIA_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".avif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".mp4", ".webm", ".pdf", ".js", ".css", ".json")
URL_PATTERN = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I)
LANGUAGES = {"fr": "Français", "en": "English", "ar": "العربية"}
SKIP_TRANSLATE_IN = {"script", "style", "noscript", "svg", "code", "pre", "iframe", "template"}


def norm_url(raw: str, source: str = ORIGIN) -> str:
    return urljoin(source, html.unescape(raw.strip()))


def path_for(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.hostname not in HOSTS or parsed.scheme not in ("http", "https"):
        return None
    path = re.sub(r"/+", "/", parsed.path or "/")
    if any(path.startswith(prefix) for prefix in SKIP_PATH_PREFIXES):
        return None
    if path.endswith(MEDIA_EXTENSIONS):
        return None
    if "/." in path or ".." in path:
        return None
    return path.rstrip("/") or "/"


def locale_url(path: str, lang: str) -> str:
    p = path.rstrip("/")
    if lang == "fr": return p + "/" if p else "/"
    return "/" + lang + (p if p else "") + "/"


def page_file(out: Path, path: str, lang: str) -> Path:
    relative = locale_url(path, lang).lstrip("/")
    return out / relative / "index.html"


def is_asset_url(url: str) -> bool:
    p = urlsplit(url)
    if p.scheme not in ("http", "https") or p.hostname not in ASSET_DOMAINS:
        return False
    return True


def could_be_asset(url: str) -> bool:
    p = urlsplit(url)
    return p.path.lower().endswith(MEDIA_EXTENSIONS) or p.hostname != "www.hydd.fr" or "/content/v1/" in p.path


class ManualTranslation:
    """Approved on-disk translations. Never contacts a translation service."""
    def __init__(self, catalog: dict):
        self.entries = catalog["strings"]

    def translate_many(self, texts: list[str], target: str) -> dict[str, str]:
        result = {}
        for text in texts:
            value = self.entries.get(text, {}).get(target, "")
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Missing approved {target} translation for source: {text[:80]!r}")
            result[text] = value
        return result


def source_strings(soup: BeautifulSoup) -> set[str]:
    """The same visible strings/attributes the final build translates."""
    selected: set[str] = set()
    for node in soup.find_all(string=True):
        if isinstance(node, Comment) or not isinstance(node, NavigableString):
            continue
        if not node.parent or node.parent.name in SKIP_TRANSLATE_IN:
            continue
        if node.find_parent(list(SKIP_TRANSLATE_IN)):
            continue
        if node.parent.get("data-hydd-nontranslate") == "1":
            continue
        value = str(node)
        if value.strip() and re.search(r"[A-Za-zÀ-ÿ]", value):
            selected.add(value)
    for tag in soup.find_all(True):
        if tag.name == "meta" and tag.get("name", "").lower() in ("description", "keywords"):
            if tag.get("content"):
                selected.add(str(tag["content"]))
        if tag.name in ("img", "input", "textarea", "button", "a"):
            for key in ("alt", "placeholder", "aria-label", "title"):
                value = tag.get(key)
                if value and re.search(r"[A-Za-zÀ-ÿ]", str(value)):
                    selected.add(str(value))
    return selected


def make_catalog(pages: dict[str, str], catalog_path: Path) -> tuple[dict, int]:
    """Merge newly captured original text into the human-editable catalog."""
    old = json.loads(catalog_path.read_text("utf-8")) if catalog_path.exists() else {}
    prior = old.get("strings", {}) if isinstance(old, dict) else {}
    all_strings: set[str] = set()
    for markup in pages.values():
        all_strings |= source_strings(BeautifulSoup(markup, "html.parser"))
    entries = {}
    for source in sorted(all_strings, key=str.casefold):
        previous = prior.get(source, {}) if isinstance(prior, dict) else {}
        entries[source] = {
            "en": previous.get("en", "") if isinstance(previous.get("en", ""), str) else "",
            "ar": previous.get("ar", "") if isinstance(previous.get("ar", ""), str) else "",
        }
    catalog = {
        "note": "Human-reviewed HYDD translations. Keys are original French text. Keep HTML/brand names intact.",
        "source": ORIGIN, "original_language": "fr", "target_languages": ["en", "ar"],
        "strings": entries,
    }
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), "utf-8")
    return catalog, len(all_strings)


def require_complete_catalog(catalog: dict):
    missing = [(text, lang) for text, languages in catalog["strings"].items()
               for lang in ("en", "ar") if not str(languages.get(lang, "")).strip()]
    if missing:
        examples = "; ".join(f"{lang}: {text[:48]!r}" for text, lang in missing[:5])
        raise ValueError(
            f"Translations incomplete: {len(missing)} entries missing. "
            f"Fill HYDD_TRANSLATIONS.json before publishing English/Arabic. Examples: {examples}"
        )


def translated_dom(soup: BeautifulSoup, lang: str, translator: ManualTranslation):
    """Translate text without replacing markup nodes: preserve existing DOM/CSS."""
    selected = []
    for node in soup.find_all(string=True):
        if isinstance(node, Comment) or not isinstance(node, NavigableString):
            continue
        if not node.parent or node.parent.name in SKIP_TRANSLATE_IN:
            continue
        if node.find_parent(list(SKIP_TRANSLATE_IN)):
            continue
        if node.parent.get("data-hydd-nontranslate") == "1":
            continue
        value = str(node)
        if not value.strip() or not re.search(r"[A-Za-zÀ-ÿ]", value):
            continue
        selected.append((node, value))
    attributes = []
    for tag in soup.find_all(True):
        if tag.name == "meta" and (tag.get("name", "").lower() in ("description", "keywords")):
            if tag.get("content"): attributes.append((tag, "content", tag["content"]))
        if tag.name in ("img", "input", "textarea", "button", "a"):
            for key in ("alt", "placeholder", "aria-label", "title"):
                if tag.get(key) and re.search(r"[A-Za-zÀ-ÿ]", str(tag[key])):
                    attributes.append((tag, key, str(tag[key])))
    all_text = [v for _, v in selected] + [v for _, _, v in attributes]
    translations = translator.translate_many(all_text, lang)
    for node, value in selected:
        if node.parent:
            leading = value[:len(value) - len(value.lstrip())]
            trailing = value[len(value.rstrip()):]
            node.replace_with(leading + translations[value].strip() + trailing)
    for tag, key, value in attributes:
        tag[key] = translations[value]


class Mirror:
    def __init__(self, output: Path, *, limit: int = 100, delay: float = .25):
        self.out = output
        self.limit = limit
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; HYDD approved site migration/1.0)", "Accept-Language": "fr-FR,fr;q=0.9"})
        self.pages: dict[str, str] = {}
        self.assets: dict[str, str] = {}
        self.warnings: list[str] = []
        self.bytes = 0
        self.asset_count_limit = 1800
        self.asset_bytes_limit = 750 * 1024 * 1024

    def get(self, url: str, *, asset=False) -> requests.Response:
        resp = self.session.get(url, timeout=35, stream=asset, allow_redirects=True)
        resp.raise_for_status()
        time.sleep(self.delay)
        return resp

    def download_asset(self, value: str, source: str) -> str:
        url = norm_url(value, source)
        if not is_asset_url(url) or url.startswith("data:"):
            return value
        if url in self.assets:
            return self.assets[url]
        if len(self.assets) >= self.asset_count_limit:
            raise RuntimeError("Asset count limit reached; inspect capture before raising the limit")
        try:
            with self.get(url, asset=True) as resp:
                if (resp.url and not is_asset_url(resp.url)):
                    raise RuntimeError("Unexpected redirect outside approved asset hosts")
                content_type = resp.headers.get("Content-Type", "").lower()
                parts = []
                total = 0
                for part in resp.iter_content(256 * 1024):
                    total += len(part)
                    if total > 30 * 1024 * 1024 or self.bytes + total > self.asset_bytes_limit:
                        raise RuntimeError("Asset exceeds download safety limit")
                    parts.append(part)
                blob = b"".join(parts)
                self.bytes += len(blob)
                ext = Path(urlsplit(url).path).suffix.lower()
                if not (ext and re.fullmatch(r"\.[a-z0-9]{1,7}", ext)):
                    ct_to_ext = {"text/css": ".css", "application/javascript": ".js", "text/javascript": ".js", "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/svg+xml": ".svg", "font/woff2": ".woff2", "font/woff": ".woff"}
                    ext = ct_to_ext.get(content_type.split(";")[0], ".bin")
                filename = hashlib.sha256(url.encode()).hexdigest()[:24] + ext
                local = "/assets/mirror/" + filename
                path = self.out / local.lstrip("/")
                path.parent.mkdir(parents=True, exist_ok=True)
                self.assets[url] = local  # cache before parsing CSS to prevent cycles
                if "text/css" in content_type or ext == ".css":
                    data = blob.decode("utf-8", errors="replace")
                    data = self.rewrite_css_urls(data, url)
                    path.write_text(data, "utf-8")
                else:
                    path.write_bytes(blob)
                return local
        except (requests.RequestException, RuntimeError) as exc:
            self.warnings.append(f"Asset could not be mirrored: {url} ({type(exc).__name__})")
            return value

    def rewrite_css_urls(self, css: str, source: str) -> str:
        def replace(m):
            raw = m.group(2).strip()
            if not raw or raw.startswith(("data:", "#", "blob:")):
                return m.group(0)
            local = self.download_asset(raw, source)
            return 'url("' + local + '")'
        return URL_PATTERN.sub(replace, css)

    def rewrite_srcset(self, value: str, source: str) -> str:
        if value.startswith("data:"):
            return value
        result = []
        for part in value.split(","):
            part = part.strip()
            if not part: continue
            pieces = part.split()
            if not pieces: continue
            pieces[0] = self.download_asset(pieces[0], source)
            result.append(" ".join(pieces))
        return ", ".join(result)

    def collect_and_rewrite(self, soup: BeautifulSoup, source: str, page_path: str):
        for tag in soup.find_all(True):
            # Remove only Weglot's old integration. The new selector is standalone.
            if tag.name == "script" and ("weglot" in tag.get("src", "").lower() or "weglot" in tag.get("id", "").lower()):
                tag.decompose(); continue
            if tag.name == "link" and "weglot" in tag.get("href", "").lower():
                tag.decompose(); continue
            for attr in ("src", "poster", "data-src", "data-image", "data-background-image"):
                value = tag.get(attr)
                if isinstance(value, str) and value and not value.startswith(("data:", "blob:", "#")):
                    tag[attr] = self.download_asset(value, source)
            for attr in ("srcset", "data-srcset"):
                value = tag.get(attr)
                if isinstance(value, str) and value:
                    tag[attr] = self.rewrite_srcset(value, source)
            if tag.has_attr("style"):
                tag["style"] = self.rewrite_css_urls(tag["style"], source)
            if tag.name == "style" and tag.string:
                tag.string.replace_with(self.rewrite_css_urls(str(tag.string), source))
            if tag.name in ("link", "script") and tag.get("href"):
                rel = [r.lower() for r in tag.get("rel", [])]
                if "stylesheet" in rel or "icon" in rel or "preload" in rel or "modulepreload" in rel:
                    tag["href"] = self.download_asset(tag["href"], source)
            if tag.name == "a" and tag.get("href"):
                url = norm_url(tag["href"], source)
                p = path_for(url)
                if p is not None:
                    parsed = urlsplit(url)
                    tag["href"] = locale_url(p, "fr") + ("?" + parsed.query if parsed.query else "") + ("#" + parsed.fragment if parsed.fragment else "")
                elif is_asset_url(url) and could_be_asset(url):
                    tag["href"] = self.download_asset(tag["href"], source)
            # Original Squarespace form markup remains, contact_bridge.js handles submissions on new site.
        return soup

    def mirror_page(self, path: str) -> tuple[str, list[str]]:
        url = ORIGIN + (path if path != "/" else "/")
        resp = self.get(url)
        if "text/html" not in resp.headers.get("Content-Type", "").lower():
            raise RuntimeError(f"Not HTML at {url}")
        final_path = path_for(resp.url)
        if final_path is None:
            raise RuntimeError(f"Unexpected redirect for {url}")
        soup = BeautifulSoup(resp.text, "html.parser")
        # Scan links prior to rewriting so original locale does not affect crawl.
        new_pages = []
        for link in soup.select("a[href]"):
            p = path_for(norm_url(link.get("href", ""), resp.url))
            if p is not None: new_pages.append(p)
        self.collect_and_rewrite(soup, resp.url, path)
        return str(soup), new_pages

    def crawl(self):
        queue = list(dict.fromkeys(KNOWN_PUBLIC_PATHS))
        for path in queue:
            if path in self.pages or len(self.pages) >= self.limit:
                continue
            try:
                rendered, discovered = self.mirror_page(path)
                self.pages[path] = rendered
                print(f"[FR] {path} ({len(rendered):,} chars)", flush=True)
                for p in discovered:
                    if p not in self.pages and p not in queue:
                        queue.append(p)
            except (requests.RequestException, RuntimeError) as exc:
                self.warnings.append(f"Page capture failed: {path} ({type(exc).__name__}: {str(exc)[:130]})")
                print(f"[WARN] Could not capture {path}: {exc}", flush=True)
        if "/" not in self.pages:
            raise RuntimeError("Homepage capture failed; cannot prepare a faithful website copy")


def apply_locale(soup: BeautifulSoup, path: str, lang: str, all_languages: list[str]):
    if soup.html:
        soup.html["lang"] = lang
        if lang == "ar": soup.html["dir"] = "rtl"
        elif soup.html.get("dir") == "rtl": del soup.html["dir"]
    if not soup.head:
        head = soup.new_tag("head")
        soup.html.insert(0, head)
    else: head = soup.head
    if lang != "fr":
        for a in soup.select("a[href]"):
            url = urlsplit(a["href"])
            if url.path.startswith("/") and not url.path.startswith(("/assets/", "/hydd/")):
                candidate = path_for(ORIGIN + url.path)
                if candidate is not None:
                    a["href"] = locale_url(candidate, lang) + ("?" + url.query if url.query else "") + ("#" + url.fragment if url.fragment else "")
    for item in list(soup.select('link[rel="canonical"], link[rel="alternate"][hreflang]')):
        item.decompose()
    canonical = soup.new_tag("link", rel="canonical", href=ORIGIN + locale_url(path, lang))
    head.append(canonical)
    for language in all_languages:
        alternate = soup.new_tag("link", rel="alternate", href=ORIGIN + locale_url(path, language))
        alternate["hreflang"] = language
        head.append(alternate)
    xdefault = soup.new_tag("link", rel="alternate", href=ORIGIN + locale_url(path, "fr"))
    xdefault["hreflang"] = "x-default"; head.append(xdefault)
    enabled = soup.new_tag("meta", attrs={"name": "hydd-built-languages", "content": ",".join(all_languages)})
    head.append(enabled)
    css = soup.new_tag("link", rel="stylesheet", href="/hydd/hydd-additions.css")
    head.append(css)
    if soup.body:
        js = soup.new_tag("script", src="/hydd/hydd-additions.js", defer=True)
        soup.body.append(js)
    return soup


def add_sitemap(out: Path, paths: list[str], languages: list[str]):
    root = Element("urlset", {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"})
    for path in paths:
        for lang in languages:
            u = SubElement(root, "url")
            SubElement(u, "loc").text = ORIGIN + locale_url(path, lang)
    ElementTree(root).write(out / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (out / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: " + ORIGIN + "/sitemap.xml\n", "utf-8")


def write_release_report(out: Path, mirror: Mirror, languages: list[str]):
    report = {
        "source": ORIGIN,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "page_count_original": len(mirror.pages),
        "languages_built": languages,
        "total_generated_pages": len(mirror.pages) * len(languages),
        "assets_captured": len(mirror.assets),
        "asset_bytes": mirror.bytes,
        "original_paths": sorted(mirror.pages),
        "warnings": mirror.warnings,
        "production_approved": False,
        "pending_checks": [
            "Visually compare every page at mobile and desktop sizes with hydd.fr",
            "Review translated English and Arabic text, especially legal pages",
            "Test images/fonts, navigation, popups, mobile menu, links and forms",
            "Configure and test contact API SMTP under HTTPS",
            "Audit any Squarespace-only widgets that cannot work independently",
            "Verify legal permission to self-host all photos and licensed assets",
            "Approve domain cutover and roll-back plan",
        ],
    }
    (out / "BUILD_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="dist", help="output folder; may be overwritten")
    p.add_argument("--translations-file", default="", help="human-reviewed JSON translations: no external API key")
    p.add_argument("--catalog", default="HYDD_TRANSLATIONS.json", help="where to export/update source strings")
    p.add_argument("--max-pages", type=int, default=70)
    args = p.parse_args()
    out = Path(args.out).resolve()
    if out == Path("/") or out == Path.home():
        p.error("Unsafe output folder")
    catalog_path = Path(args.catalog).resolve()
    if args.translations_file and Path(args.translations_file).resolve() != catalog_path:
        p.error("--translations-file must point to the same file as --catalog (to prevent mismatch)")
    if out.exists() and any(out.iterdir()):
        marker = out / "BUILD_REPORT.json"
        if not marker.exists():
            p.error("Output folder is nonempty without a HYDD build report: choose a new --out directory")
        try:
            old = json.loads(marker.read_text("utf-8"))
        except (ValueError, UnicodeDecodeError):
            p.error("Invalid prior HYDD build report; choose a new --out directory")
        if old.get("source") != ORIGIN:
            p.error("Refusing to overwrite a non-HYDD output directory")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    mirror = Mirror(out, limit=max(1, min(args.max_pages, 150)))
    mirror.crawl()
    catalog, count = make_catalog(mirror.pages, catalog_path)
    if args.translations_file:
        try:
            require_complete_catalog(catalog)
        except ValueError as exc:
            p.error(str(exc))
    languages = ["fr", "en", "ar"] if args.translations_file else ["fr"]
    translator = ManualTranslation(catalog) if args.translations_file else None
    for path, markup in mirror.pages.items():
        for lang in languages:
            soup = BeautifulSoup(markup, "html.parser")
            if lang != "fr" and translator is not None:
                translated_dom(soup, lang, translator)
            apply_locale(soup, path, lang, languages)
            dest = page_file(out, path, lang)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("<!doctype html>\n" + str(soup), "utf-8")
    src = Path(__file__).resolve().parent / "hydd_custom"
    shutil.copytree(src, out / "hydd", dirs_exist_ok=True)
    add_sitemap(out, sorted(mirror.pages), languages)
    report = write_release_report(out, mirror, languages)
    print("\nBuilt:", report["total_generated_pages"], "pages,", report["assets_captured"], "assets")
    if mirror.warnings:
        print("WARNING: See dist/BUILD_REPORT.json for", len(mirror.warnings), "capture issues")
    if not args.translations_file:
        print(f"French replica preview created. Translation catalog: {catalog_path} ({count} unique strings)")
        print("No translation API key needed. Populate translations, then run FINALIZE_TRANSLATIONS.command.")
    print("NOT PRODUCTION APPROVED: inspect all pages, contact forms, licensing, translations, and mobile layouts")


if __name__ == "__main__":
    main()
