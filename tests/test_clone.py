import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import build_clone as b
from bs4 import BeautifulSoup

class LocalMirrorTests(unittest.TestCase):
    def test_original_paths_remain_unchanged(self):
        for path in ['/', '/coner', '/evnements', '/digital-products-1-1']:
            self.assertEqual(b.path_for('https://www.hydd.fr'+path),path)

    def test_external_and_admin_routes_not_mirrored(self):
        for value in ['https://evil.example/','https://www.hydd.fr/config','https://www.hydd.fr/api/data','https://www.hydd.fr/s/photo.jpg']:
            self.assertIsNone(b.path_for(value))

    def test_language_paths_keep_original_french_slugs(self):
        self.assertEqual(b.locale_url('/coner','fr'),'/coner/')
        self.assertEqual(b.locale_url('/coner','en'),'/en/coner/')
        self.assertEqual(b.locale_url('/','ar'),'/ar/')

    def test_asset_allowlist(self):
        self.assertTrue(b.is_asset_url('https://images.squarespace-cdn.com/content/file.jpg'))
        self.assertFalse(b.is_asset_url('https://example.evil/img.jpg'))

    def test_french_brand_original_html_survives(self):
        soup=BeautifulSoup('<html><head><title>HYDD</title></head><body><h1>Bonjour HYDD</h1><a href="/coner/">Conciergerie</a></body></html>','html.parser')
        b.apply_locale(soup,'/','fr',['fr','en','ar'])
        self.assertEqual(soup.h1.text,'Bonjour HYDD')
        self.assertEqual(soup.a['href'],'/coner/')
        self.assertEqual(soup.html['lang'],'fr')
        self.assertEqual(len(soup.select('link[hreflang]')),4)

    def test_english_links_rewritten(self):
        soup=BeautifulSoup('<html><head></head><body><a href="/coner/#contact">Conciergerie</a></body></html>','html.parser')
        b.apply_locale(soup,'/','en',['fr','en','ar'])
        self.assertEqual(soup.a['href'],'/en/coner/#contact')
        self.assertEqual(soup.html['lang'],'en')

    def test_arabic_rtl_flag(self):
        soup=BeautifulSoup('<html><head></head><body><h1>Bonjour</h1></body></html>','html.parser')
        b.apply_locale(soup,'/','ar',['fr','en','ar'])
        self.assertEqual(soup.html['dir'],'rtl')
        self.assertEqual(soup.html['lang'],'ar')

    def test_sitemap_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            b.add_sitemap(out,['/','/coner'],['fr','en','ar'])
            contents=(out/'sitemap.xml').read_text()
            self.assertIn('https://www.hydd.fr/ar/coner/',contents)
            self.assertIn('https://www.hydd.fr/en/',contents)

    def test_no_key_ever_appears_in_generated_js(self):
        source=(Path(__file__).resolve().parents[1]/'hydd_custom'/'hydd-additions.js').read_text()
        self.assertIn('33765849546',source)
        self.assertNotIn('HYDD_TRANSLATION_API_KEY',source)
        self.assertNotIn('sk_live_',source)

    def test_translation_preserves_nested_markup(self):
        soup=BeautifulSoup('<html><head><title>Bonjour</title></head><body><p>Bonjour <strong>HYDD</strong> !</p></body></html>','html.parser')
        class Stub:
            def translate_many(self,texts,target):return {t:'مرحبا' for t in texts}
        b.translated_dom(soup,'ar',Stub())
        self.assertEqual(soup.strong.name,'strong')
        self.assertEqual(soup.title.text,'مرحبا')

    def test_srcset_rewrites_cached_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=b.Mirror(Path(tmp))
            m.assets={
              'https://images.squarespace-cdn.com/a.jpg':'/assets/mirror/a.jpg',
              'https://images.squarespace-cdn.com/b.jpg':'/assets/mirror/b.jpg'
            }
            self.assertEqual(m.rewrite_srcset('https://images.squarespace-cdn.com/a.jpg 1x, https://images.squarespace-cdn.com/b.jpg 2x',b.ORIGIN),'/assets/mirror/a.jpg 1x, /assets/mirror/b.jpg 2x')

    def test_assets_dont_get_used_for_external_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=b.Mirror(Path(tmp))
            self.assertEqual(m.download_asset('https://badsite.example/file.js',b.ORIGIN),'https://badsite.example/file.js')


class NoApiKeyTranslationTests(unittest.TestCase):
    def test_catalog_export_keeps_original_strings(self):
        pages = {'/':'<html><head><title>Bonjour HYDD</title><meta name="description" content="Chauffeur privé Paris"></head><body><p>Bonjour HYDD</p><img alt="Voiture de luxe"></body></html>'}
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'HYDD_TRANSLATIONS.json'
            catalog,count=b.make_catalog(pages,path)
            self.assertEqual(count,3)
            self.assertEqual(catalog['strings']['Bonjour HYDD'],{'en':'','ar':''})
            self.assertIn('Voiture de luxe', catalog['strings'])
            self.assertRaises(ValueError,b.require_complete_catalog,catalog)

    def test_manual_translation_preserves_html_structure(self):
        pages={'/':'<html><head><title>Bonjour</title></head><body><p>Bonjour <em>Paris</em></p></body></html>'}
        with tempfile.TemporaryDirectory() as temp:
            catalog,_=b.make_catalog(pages,Path(temp)/'HYDD_TRANSLATIONS.json')
            for fr,values in catalog['strings'].items():
                values.update(en={'Bonjour':'Hello','Paris':'Paris'}[fr.strip()],ar={'Bonjour':'مرحبا','Paris':'باريس'}[fr.strip()])
            b.require_complete_catalog(catalog)
            soup=BeautifulSoup(pages['/'],'html.parser')
            b.translated_dom(soup,'ar',b.ManualTranslation(catalog))
            self.assertEqual(soup.em.text,'باريس')
            self.assertEqual(soup.p.text,'مرحبا باريس')

    def test_catalog_merge_retains_human_work(self):
        pages={'/':'<html><body><h1>Bonjour</h1></body></html>'}
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'HYDD_TRANSLATIONS.json'
            catalog,_=b.make_catalog(pages,path)
            catalog['strings']['Bonjour']={'en':'Hello','ar':'مرحبا'}
            import json
            path.write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf-8')
            result,_=b.make_catalog(pages,path)
            self.assertEqual(result['strings']['Bonjour']['ar'],'مرحبا')

    def test_french_preview_hides_language_selector_until_ready(self):
        source=(Path(__file__).resolve().parents[1]/'hydd_custom'/'hydd-additions.js').read_text()
        self.assertIn('enabled.length>1',source)
        soup=BeautifulSoup('<html><head></head><body></body></html>','html.parser')
        b.apply_locale(soup,'/','fr',['fr'])
        self.assertEqual(soup.select_one('meta[name="hydd-built-languages"]')['content'],'fr')

if __name__=='__main__':unittest.main()
