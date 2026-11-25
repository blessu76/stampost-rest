#!/usr/bin/env python3
"""Build the checked-in GitHub Pages artifact or check it for drift."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
sys.path.insert(0, str(ROOT / "vendor"))

from ipe_web_kit import langswitch, languages, redirects, seo, ui
from ipe_web_kit.seo import esc
from ipe_web_kit.version import AppVersion
if __package__:
    from .play_markup import render_game
else:
    from play_markup import render_game

DOMAIN = (ROOT / "CNAME").read_text(encoding="utf-8").strip()
BASE = "https://" + DOMAIN
PRIVACY = "https://ipe.rest/privacy/"
TERMS = "https://ipe.rest/legal/"
CONTACT = "ipe.haven@gmail.com"
APP_STORE = "https://apps.apple.com/app/id6838716235"
APP_VERSION = AppVersion.parse("1.0.0+4")
COPY = json.loads((ROOT / "content/copy.json").read_text(encoding="utf-8"))
PLAY_COPY = json.loads((ROOT / "content/play.json").read_text(encoding="utf-8"))
SECTIONS = ("", "support/", "play/")
LEGACY = ("zh-Hans", "ru", "ar", "hi")
REDIRECT_OVERRIDES = {"zh-Hans": "zh-Hant"}
STAMPS = ("flower", "moon", "star")
BATCH_ROWS = 6
WRONG_TAP = "\u22122"


def batch_points(n):
    return n * (n + 1) // 2


def route(lang, section=""):
    return "/" + ("" if lang == languages.DEFAULT else f"{lang}/") + section


def alternate_urls(section):
    return {lang: BASE + route(lang, section) for lang in languages.SUPPORTED}


def game_data(lang, copy):
    return seo.jsonld_script({
        "@context": "https://schema.org",
        "@graph": [
            seo.ORG,
            {
                "@type": ["VideoGame", "MobileApplication"],
                "@id": BASE + "/#game",
                "name": copy["name"],
                "alternateName": ["도장 우체국", "Stampost : Mail Sort Rush"],
                "description": copy["description"],
                "url": BASE + route(lang),
                "inLanguage": lang,
                "applicationCategory": "GameApplication",
                "operatingSystem": ["iOS", "Android"],
                "genre": ["Puzzle", "Casual"],
                "numberOfPlayers": {"@type": "QuantitativeValue", "value": 1},
                "publisher": seo.org_ref(),
            },
        ],
    })


def render_home(lang, copy, artwork):
    rules = "".join(f"<li>{esc(rule)}</li>" for rule in copy["rules"])
    stamps = "".join(
        f'<li class="stamp"><img src="{artwork[stamp]}" width="24" height="24" alt="">{esc(name)}</li>'
        for stamp, name in zip(STAMPS, copy["stamps"])
    )
    return f"""<section class="hero wrap">
  <div class="hero-copy">
    <p class="tagline">{esc(copy["tagline"])}</p>
    <h1>{esc(copy["name"])}</h1>
    <p class="hero-line">{esc(copy["hero"])}</p>
    <p class="intro">{esc(copy["description"])}</p>
    <div class="actions">
      <a class="action" href="{route(lang, 'play/')}">{esc(PLAY_COPY[lang]["start"])}</a>
      <button type="button" disabled class="action store" data-store-url="{APP_STORE}">App Store <span>{esc(copy["soon"])}</span></button>
    </div>
  </div>
  <div class="scene">
    <img class="postbox-art" src="{artwork['mailbox']}" width="137" height="123" alt="">
    <span class="envelope envelope-first" aria-hidden="true">
      <img src="{artwork['envelope']}" width="52" height="50" alt="">
      <img class="envelope-stamp" src="{artwork['flower']}" width="24" height="24" alt="">
    </span>
    <span class="envelope envelope-second" aria-hidden="true">
      <img src="{artwork['envelope']}" width="52" height="50" alt="">
      <img class="envelope-stamp" src="{artwork['moon']}" width="24" height="24" alt="">
    </span>
    <p class="round">{esc(copy["round"])}</p>
  </div>
</section>
<section class="how wrap">
  <div><h2>{esc(copy["how"])}</h2><ol>{rules}</ol></div>
  <ul class="stamps">{stamps}</ul>
</section>"""


def render_detail(lang, section, copy, artwork):
    back = f'<a class="back" href="{route(lang)}">{esc(copy["home"])}</a>'
    if section == "support/":
        mail = "mailto:" + CONTACT + "?" + urlencode({"subject": "Stampost support"}).replace("+", "%20")
        return f"""<section class="page wrap">
  <h1>{esc(copy["support"])}</h1>
  <section class="page-section">
    <h2>{esc(copy["contact"])}</h2>
    <p>{esc(copy["supportText"])}</p>
    <a href="{esc(mail)}">{CONTACT}</a>
  </section>
  <section class="page-section">
    <h2>{esc(copy["faq"])}</h2>
    <dl>
      <dt>{esc(copy["offlineQ"])}</dt><dd>{esc(copy["offlineA"])}</dd>
      <dt>{esc(copy["queueQ"])}</dt><dd>{esc(copy["queueA"])}</dd>
    </dl>
  </section>
  {back}
</section>"""
    if section == "play/":
        steps = "".join(f"<li>{esc(step)}</li>" for step in copy["steps"])
        rush_rules = "".join(f"<li>{esc(rule)}</li>" for rule in copy["rushRules"])
        rows = "".join(
            f"<tr><td>{n}</td><td>+{batch_points(n)}</td></tr>" for n in range(1, BATCH_ROWS + 1)
        )
        labels = {**PLAY_COPY[lang], "help": copy["how"]}
        game = render_game(labels, artwork, STAMPS, BATCH_ROWS, batch_points, copy["name"])
        return f"""{game}
<section class="page game-guide wrap" id="rules" aria-labelledby="game-guide-title">
  <h2 id="game-guide-title">{esc(copy["how"])}</h2>
  <p class="intro">{esc(copy["playIntro"])}</p>
  <section class="page-section">
    <ol class="steps">{steps}</ol>
    <ul class="steps rush-rules">{rush_rules}</ul>
  </section>
  <section class="page-section">
    <h2>{esc(copy["scoring"])}</h2>
    <table class="score-table">
      <thead><tr><th scope="col">{esc(copy["batch"])}</th><th scope="col">{esc(copy["points"])}</th></tr></thead>
      <tbody>{rows}<tr class="penalty"><td>{esc(copy["wrongTap"])}</td><td>{WRONG_TAP}</td></tr></tbody>
    </table>
  </section>
  <section class="page-section">
    <h2>{esc(copy["appTitle"])}</h2>
    <p>{esc(copy["appText"])}</p>
  </section>
  {back}
</section>"""
    return f'<section class="page wrap"><h1>{esc(copy["missing"])}</h1>{back}</section>'


def render_page(lang, section, stylesheets, scripts, artwork):
    copy = COPY[lang]
    is_home = section == ""
    missing = section == "404.html"
    brand = copy["name"]
    title = {
        "": f'{brand} | {copy["tagline"]}',
        "support/": f'{copy["support"]} | {brand}',
        "play/": f'{copy["how"]} | {brand}',
        "404.html": f'404 | {brand}',
    }[section]
    desc = {"": copy["description"], "support/": copy["supportText"], "play/": copy["playIntro"],
            "404.html": copy["missing"]}[section]
    description = esc(seo.meta_desc(desc))
    url = BASE + route(lang, section)
    indexing = (
        '<meta name="robots" content="noindex,follow">'
        if missing else
        f'<link rel="canonical" href="{url}">\n'
        + seo.alternate_links(alternate_urls(section), x_default=BASE + route("en", section))
    )
    metadata = game_data(lang, copy) if is_home else ""
    stylesheet_tags = "\n".join(f'<link rel="stylesheet" href="{esc(path)}">' for path in stylesheets)
    lang_entry = " data-language-entry" if lang == "en" and not missing else ""
    select = langswitch.select_html(lang, lambda code: route(code, "" if missing else section))
    is_play = section == "play/"
    content = render_home(lang, copy, artwork) if is_home else render_detail(lang, section, copy, artwork)
    game_script = f'<script type="module" src="{esc(scripts["play"])}"></script>' if is_play else ""
    body_class = ' class="play-page"' if is_play else ""
    return f"""<!doctype html>
<html lang="{lang}" dir="{langswitch.dir_for(lang)}"{lang_entry}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{description}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(brand)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
{indexing}
{stylesheet_tags}
{metadata}
{langswitch.script(scripts)}
<script defer src="{esc(scripts["local"])}"></script>
{game_script}
</head>
<body{body_class}>
<header class="masthead">
  <div class="wrap">
    <a class="wordmark" href="{route(lang)}"><span class="brand-mark" aria-hidden="true">✉</span>{esc(brand)}</a>
    <div class="header-links"><a href="{route(lang, 'support/')}">{esc(copy["support"])}</a>{select}</div>
  </div>
</header>
<main>
{content}
</main>
<footer class="footer">
  <div class="wrap">
    <div class="footer-links"><a href="{TERMS}">{esc(copy["terms"])}</a><a href="{PRIVACY}">{esc(copy["privacy"])}</a></div>
    {ui.studio_line(label="", year=2026, version=APP_VERSION)}
  </div>
</footer>
</body>
</html>
"""


def sitemap():
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    xhtml = "http://www.w3.org/1999/xhtml"
    root = ET.Element("urlset", {"xmlns": namespace, "xmlns:xhtml": xhtml})
    for section in SECTIONS:
        alternates = alternate_urls(section)
        alternate_entries = {**alternates, "x-default": alternates["en"]}
        for url in alternates.values():
            entry = ET.SubElement(root, "url")
            ET.SubElement(entry, "loc").text = url
            for lang, href in alternate_entries.items():
                ET.SubElement(entry, "xhtml:link", rel="alternate", hreflang=lang, href=href)
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def llms():
    translations = "\n".join(
        f"- [{languages.NAMES[lang]}]({BASE + route(lang)})" for lang in languages.SUPPORTED
    )
    return f"""# Stampost / 도장 우체국

> A one-tap mail sorting puzzle by ipe studio. Match the stamp on the first envelope, dispatch the matching batch, and keep the queue to six letters or fewer in a 45-second round.

## Official pages

- [Game overview]({BASE}/)
- [Support and FAQ]({BASE}/support/)
- [Play in your browser and see the rules]({BASE}/play/)
- [Terms of use]({TERMS})
- [Privacy policy]({PRIVACY})

## Languages

{translations}
"""


def asset_url(name, data):
    return f"/assets/{name}?v={hashlib.sha256(data).hexdigest()[:10]}"


def expected_files():
    css = (ROOT / "assets/stampost.css").read_bytes()
    script = (ROOT / "assets/language.js").read_bytes()
    tokens = (ROOT / "assets/design/tokens.css").read_bytes()
    illustrations = {
        name: (ROOT / f"assets/design/{name}.svg").read_bytes() for name in (*STAMPS, "mailbox", "envelope")
    }
    artwork = {name: asset_url(f"design/{name}.svg", data) for name, data in illustrations.items()}
    css_urls = (
        f"/assets/ipe-kit.css?v={ui.css_version()}",
        asset_url("design/tokens.css", tokens),
        asset_url("stampost.css", css),
    )
    scripts = {"js": f"/assets/ipe-lang.js?v={langswitch.asset_version()}", "local": asset_url("language.js", script)}
    round_script = (ROOT / "assets/stampost-round.mjs").read_bytes()
    round_url = asset_url("stampost-round.mjs", round_script)
    play_script = (ROOT / "assets/stampost-play.mjs").read_bytes().replace(
        b"./stampost-round.mjs", round_url.encode("ascii")
    )
    play_css = (ROOT / "assets/stampost-play.css").read_bytes()
    play_css_url = asset_url("stampost-play.css", play_css)
    scripts["play"] = asset_url("stampost-play.mjs", play_script)
    files = {
        "CNAME": DOMAIN + "\n",
        ".nojekyll": b"",
        "assets/stampost.css": css,
        "assets/language.js": script,
        "assets/stampost-play.css": play_css,
        "assets/stampost-round.mjs": round_script,
        "assets/stampost-play.mjs": play_script,
        "assets/ipe-kit.css": ui.CSS.read_bytes(),
        "assets/ipe-lang.js": langswitch.JS.read_bytes(),
        "assets/design/tokens.css": tokens,
        **{f"assets/design/{name}.svg": data for name, data in illustrations.items()},
        "robots.txt": f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n",
        "sitemap.xml": sitemap(),
        "llms.txt": llms(),
        "404.html": render_page("en", "404.html", css_urls, scripts, artwork),
    }
    for lang in languages.SUPPORTED:
        for section in SECTIONS:
            styles = (*css_urls, play_css_url) if section == "play/" else css_urls
            files[route(lang, section).lstrip("/") + "index.html"] = render_page(lang, section, styles, scripts, artwork)
    files.update(redirects.generate(SECTIONS, BASE, en_root=True, langs=LEGACY, overrides=REDIRECT_OVERRIDES))
    return {path: text.encode("utf-8") if isinstance(text, str) else text for path, text in files.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = expected_files()
    if args.check:
        actual = {file.relative_to(PUBLIC).as_posix() for file in PUBLIC.rglob("*") if file.is_file()}
        stale = sorted(set(files) ^ actual)
        stale.extend(path for path in sorted(set(files) & actual) if (PUBLIC / path).read_bytes() != files[path])
        if stale:
            print("Stale public output. Run python3 scripts/build_site.py:", *stale, sep="\n", file=sys.stderr)
            return 1
        print(f"Static output matches ({len(files)} files)")
        return 0

    for path, data in files.items():
        output = PUBLIC / path
        output.parent.mkdir(parents=True, exist_ok=True)
        if not output.is_file() or output.read_bytes() != data:
            output.write_bytes(data)
    print(f"Built {len(files)} files in public/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
