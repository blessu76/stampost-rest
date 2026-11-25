import hashlib
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from scripts import build_site as site


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def find(self, tag, **selectors):
        return [
            attrs for name, attrs in self.tags
            if name == tag and all(key in attrs and attrs[key] == value for key, value in selectors.items())
        ]


class SiteTests(unittest.TestCase):
    def test_locked_web_kit(self):
        pkg = site.ROOT / "vendor/ipe_web_kit"
        lines = pkg.with_suffix(".lock").read_text(encoding="utf-8").splitlines()
        lock = dict(line.split("=", 1) for line in lines)
        self.assertEqual((pkg / "KIT_VERSION").read_text().split(), [lock["tag"], lock["commit"]])
        self.assertEqual(hashlib.sha256((pkg / "MANIFEST.sha256").read_bytes()).hexdigest(), lock["manifest_sha256"])

    def test_languages_and_game_metadata(self):
        self.assertEqual(set(site.COPY), set(site.languages.SUPPORTED))
        for lang, copy in site.COPY.items():
            with self.subTest(lang=lang):
                self.assertEqual(len(copy["stamps"]), 3)
                self.assertEqual(set(copy), set(site.COPY["en"]))
                page_path = site.PUBLIC / site.route(lang).lstrip("/") / "index.html"
                page = Page(page_path)
                self.assertEqual(len(page.find("html", lang=lang)), 1)
                self.assertCountEqual(
                    [option["lang"] for option in page.find("option")],
                    site.languages.SUPPORTED,
                )
                button, = page.find("button", **{"data-store-url": site.APP_STORE})
                self.assertIn("disabled", button)
                self.assertFalse(page.find("a", href=site.APP_STORE))
                game_json = page_path.read_text(encoding="utf-8").split(
                    '<script type="application/ld+json">', 1
                )[1].split("</script>", 1)[0]
                game = json.loads(game_json)["@graph"][1]
                self.assertEqual(game["@type"], ["VideoGame", "MobileApplication"])
                self.assertEqual(game["inLanguage"], lang)
                self.assertEqual(game["name"], copy["name"])

    def test_play_page_explains_rules_in_every_language(self):
        points = (1, 3, 6, 10, 15, 21)
        self.assertEqual([site.batch_points(n) for n in range(1, 7)], list(points))
        self.assertEqual(site.BATCH_ROWS, 6)
        self.assertEqual(site.COPY["ko"]["how"], "노는 법")
        for lang in site.languages.SUPPORTED:
            copy = site.COPY[lang]
            with self.subTest(lang=lang):
                page_path = site.PUBLIC / site.route(lang, "play/").lstrip("/") / "index.html"
                self.assertTrue(page_path.is_file())
                html = page_path.read_text(encoding="utf-8")
                page = Page(page_path)
                self.assertEqual(len(page.find("html", lang=lang)), 1)
                self.assertIn(f'<h2 id="game-guide-title">{site.esc(copy["how"])}</h2>', html)
                self.assertEqual(len(copy["steps"]), 5)
                for step in copy["steps"]:
                    self.assertIn(f"<li>{site.esc(step)}</li>", html)
                # 규칙 숫자는 단계마다 제자리에 정확히 — round.dart: 45초 · 대기줄 6 · n(n+1)/2 · 오답 −2 · 0점 하한
                self.assertIn("n(n+1)/2", copy["steps"][3])
                numbers = [re.findall(r"\d+", step.replace("n(n+1)/2", "")) for step in copy["steps"]]
                expected = [{"45"}, {"6"}, set(), set(), {"2", "0"}]
                for found, facts in zip(numbers, expected):
                    self.assertLessEqual(facts, set(found))
                    self.assertLessEqual(set(found), facts | {"1"})  # ja: 「1ラウンド」
                self.assertIn(site.esc(copy["appText"]), html)
                for n, base in enumerate(points, start=1):
                    self.assertIn(f"<tr><td>{n}</td><td>+{base}</td></tr>", html)
                self.assertEqual(len(copy["rushRules"]), 3)
                for rule in copy["rushRules"]:
                    self.assertIn(f"<li>{site.esc(rule)}</li>", html)
                fever_name = site.PLAY_COPY[lang]["fever"].removesuffix(" ×2").casefold()
                for line in (copy["rushRules"][1], copy["steps"][1], copy["queueA"]):
                    self.assertIn(fever_name, line.casefold())
                fever_numbers = set(re.findall(r"\d+", copy["rushRules"][1]))
                self.assertLessEqual({"18", "6"}, fever_numbers)
                self.assertLessEqual(fever_numbers, {"18", "6", "2"})
                star_numbers = set(re.findall(r"\d+", copy["rushRules"][2]))
                self.assertLessEqual({"150", "300", "450"}, star_numbers)
                self.assertLessEqual(star_numbers, {"150", "300", "450", "1"})
                self.assertEqual(html.count("<tr><td>"), site.BATCH_ROWS)
                self.assertIn(f"<td>{site.esc(copy['wrongTap'])}</td><td>\u22122</td>", html)
                self.assertFalse(page.find("a", href=site.APP_STORE))
                self.assertNotIn("apps.apple.com", html)
                self.assertNotIn("play.google.com", html)
                home = Page(site.PUBLIC / site.route(lang).lstrip("/") / "index.html")
                self.assertEqual(len(home.find("a", href=site.route(lang, "play/"))), 1)

    def test_play_assets_and_translations(self):
        self.assertEqual(set(site.PLAY_COPY), set(site.languages.SUPPORTED))
        for lang, copy in site.PLAY_COPY.items():
            with self.subTest(lang=lang):
                self.assertEqual(set(copy), set(site.PLAY_COPY["en"]))
                page = Page(site.PUBLIC / site.route(lang, "play/").lstrip("/") / "index.html")
                for stamp in site.STAMPS:
                    self.assertEqual(len(page.find("button", **{"data-stamp": stamp})), 1)
                module, = page.find("script", type="module")
                module_path = urlsplit(module["src"]).path.lstrip("/")
                script = (site.PUBLIC / module_path).read_bytes()
                self.assertEqual(module["src"], site.asset_url(module_path.removeprefix("assets/"), script))
                rules_path = "stampost-round.mjs"
                rules = (site.PUBLIC / "assets" / rules_path).read_bytes()
                self.assertIn(f"from '{site.asset_url(rules_path, rules)}';".encode(), script)

    def test_site_links_alternates_and_cache_busting(self):
        for lang in site.languages.SUPPORTED:
            for section in site.SECTIONS:
                route = site.route(lang, section)
                with self.subTest(route=route):
                    page = Page(site.PUBLIC / route.lstrip("/") / "index.html")
                    self.assertEqual(len(page.find("link", rel="canonical", href=site.BASE + route)), 1)
                    alternates = {tag["hreflang"]: tag["href"] for tag in page.find("link", rel="alternate")}
                    self.assertEqual(alternates, {**site.alternate_urls(section), "x-default": site.BASE + site.route("en", section)})
                    self.assertEqual(len(page.find("a", href=site.PRIVACY)), 1)
                    self.assertEqual(len(page.find("a", href=site.TERMS)), 1)
                    for tag, attribute in (("a", "href"), ("option", "value"), ("link", "href"), ("script", "src"), ("img", "src")):
                        for attrs in page.find(tag):
                            target = urlsplit(attrs.get(attribute, ""))
                            if not target.path.startswith("/") or target.netloc:
                                continue
                            path = site.PUBLIC / target.path.lstrip("/")
                            self.assertTrue((path / "index.html").is_file() if target.path.endswith("/") else path.is_file(), target.path)
                            if target.path.startswith("/assets/"):
                                self.assertTrue(target.query.startswith("v="), target.path)

    def test_layout_css(self):
        css = (site.ROOT / "assets/stampost.css").read_text(encoding="utf-8")
        rules = {
            selector.strip(): " ".join(body.split())
            for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        }
        # footer 하단 고정: body 가 세로 flex, main 이 남는 높이를 채운다
        self.assertIn("display: flex;", rules["body"])
        self.assertIn("flex-direction: column;", rules["body"])
        self.assertIn("min-height: 100dvh;", rules["body"])
        self.assertIn("flex: 1 0 auto;", rules["main"])
        # 한국어는 홈을 포함한 모든 페이지에서 낱말 단위로 줄바꿈
        self.assertIn("word-break: keep-all;", rules[":lang(ko) body"])

    def test_retired_languages_are_redirects_only(self):
        mapping = {"ru": "en", "ar": "en", "hi": "en", "zh-Hans": "zh-Hant"}
        for old, target in mapping.items():
            for section in site.SECTIONS:
                with self.subTest(lang=old, section=section):
                    page = Page(site.PUBLIC / old / section / "index.html")
                    dest = site.BASE + site.route(target, section)
                    self.assertEqual(len(page.find("meta", name="robots", content="noindex,follow")), 1)
                    self.assertEqual(len(page.find("meta", **{"http-equiv": "refresh", "content": "0; url=" + dest})), 1)
                    self.assertEqual(len(page.find("link", rel="canonical", href=dest)), 1)
                    self.assertFalse(page.find("link", rel="alternate"))

    def test_search_discovery(self):
        sitemap_file = site.PUBLIC / "sitemap.xml"
        self.assertFalse(site.redirects.sitemap_leaks(sitemap_file.read_text(), overrides=site.REDIRECT_OVERRIDES))
        tree = ET.parse(sitemap_file)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        expected = [site.BASE + site.route(lang, section) for section in site.SECTIONS for lang in site.languages.SUPPORTED]
        self.assertCountEqual([loc.text for loc in tree.findall("s:url/s:loc", ns)], expected)
        self.assertIn(f"Sitemap: {site.BASE}/sitemap.xml", (site.PUBLIC / "robots.txt").read_text())
        self.assertEqual((site.PUBLIC / "CNAME").read_text().strip(), site.DOMAIN)
        self.assertIn(f"{site.BASE}/support/", (site.PUBLIC / "llms.txt").read_text())
        self.assertEqual(len(Page(site.PUBLIC / "404.html").find("meta", name="robots", content="noindex,follow")), 1)
