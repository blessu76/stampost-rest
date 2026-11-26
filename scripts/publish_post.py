#!/usr/bin/env python3
"""Record at most one Iris-reviewed post for the current KST date."""

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import build_site as site
import journal_content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    today = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    posts, ledger = site.journal_data()
    slug = journal_content.next_post(posts, ledger, today)
    if not slug:
        if ledger and today <= max(ledger.values()):
            print(f"ALREADY_PUBLISHED {today}")
        else:
            print(f"QUEUE_EMPTY {today} — no complete Iris-reviewed entry")
        return
    remaining = sum(
        not journal_content.review_problems(editions, today)
        for candidate, editions in posts.items()
        if candidate not in ledger and candidate != slug
    )
    if remaining < 3:
        print(f"QUEUE_LOW — {remaining} reviewed entries after this publication")
    if not args.dry_run:
        ledger[slug] = today
        stamp = journal_content.DIRECTORY / journal_content.LEDGER
        stamp.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    print(f"{'READY' if args.dry_run else 'PUBLISHED'} {today} {slug}")


if __name__ == "__main__":
    main()
