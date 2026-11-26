"""Load the dated journal ledger and the reviewed queue."""

import json
import re
from datetime import date
from pathlib import Path

from ipe_web_kit import journal

DIRECTORY = Path(__file__).resolve().parents[1] / "content" / "journal"
LEDGER = "published.json"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def load(directory, page_url):
    posts = {}
    for path in sorted(directory.glob("[0-9]*-*.json")):
        post = json.loads(path.read_text(encoding="utf-8"))
        slug = post["slug"]
        if not SLUG.fullmatch(slug) or slug in posts:
            raise ValueError(f"{path.name}: invalid or duplicate journal slug")
        posts[slug] = {
            lang: {**edition, "url": page_url(lang, f"journal/{slug}/")}
            for lang, edition in post["editions"].items()
        }
    ledger = json.loads((directory / LEDGER).read_text(encoding="utf-8"))
    dates = [date.fromisoformat(published) for published in ledger.values()]
    if any(day.isoformat() != published for day, published in zip(dates, ledger.values())):
        raise ValueError("Journal publication dates must use YYYY-MM-DD")
    if len(dates) != len(set(dates)):
        raise ValueError("The journal can publish only one entry per calendar day")
    for slug, published in ledger.items():
        if slug not in posts:
            raise ValueError(f"{slug}: published entry has no source")
        problems = review_problems(posts[slug], published)
        if problems:
            raise ValueError(f"{slug}: " + "; ".join(problems))
    return posts, ledger


def review_problems(editions, published):
    problems = journal.check_post(editions)
    for lang, edition in editions.items():
        for field in ("title", "summary"):
            if not isinstance(edition.get(field), str) or not edition[field].strip():
                problems.append(f"{lang}: missing {field}")
        paragraphs = edition.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs or any(
            not isinstance(paragraph, str) or not paragraph.strip() for paragraph in paragraphs
        ):
            problems.append(f"{lang}: missing or empty paragraphs")
        try:
            reviewed = date.fromisoformat(edition.get("copy_review_date", ""))
        except (TypeError, ValueError):
            problems.append(f"{lang}: invalid review calendar date")
            continue
        if reviewed > date.fromisoformat(published):
            problems.append(f"{lang}: review date is later than publication")
    return problems


def next_post(posts, ledger, today):
    if ledger and today <= max(ledger.values()):
        return None
    for slug, editions in posts.items():
        if slug not in ledger and not review_problems(editions, today):
            return slug
    return None


def sections(ledger):
    return {
        f"journal/{slug}/": (slug, published)
        for slug, published in sorted(ledger.items(), key=lambda item: item[1], reverse=True)
    }
