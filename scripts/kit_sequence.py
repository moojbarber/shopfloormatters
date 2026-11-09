#!/usr/bin/env python3
"""Load the evergreen newsletter into a Kit (kit.com) sequence.

Every subscriber starts at email 1, whenever they join. The order follows the
learning paths in content/paths.yaml. This script creates the sequence named in `sequence.name`
(if it doesn't exist) and adds one email per article, in order. Existing emails
(matched by subject) are updated rather than duplicated, so it's safe to re-run
after reordering, editing notes or changing the cadence.

Emails are drafts unless `sequence.publish` is true. Nothing sends until the
emails are published and a form or automation adds subscribers to the sequence.

Needs KIT_API_KEY (GitHub Actions secret). Kit's Creator plan is needed for sequences.

Usage: python scripts/kit_sequence.py [--dry-run] [--limit N]
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import ROOT, SITE, parse_md  # noqa: E402
from newsletter import API, article, email_html, extras, clip, written_email, intro_emails  # noqa: E402


def kit(method, path, key, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-Kit-Api-Key": key, "Accept": "application/json",
                                          "Content-Type": "application/json", "User-Agent": "shopfloormatters-newsletter"})
    for attempt in range(8):
        try:
            time.sleep(0.6)  # stay under Kit's rate limit
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 7:
                time.sleep(15 * (attempt + 1))
                continue
            detail = e.read().decode("utf-8", "replace")[:500]
            if e.code == 403:
                detail += "\nKit refused this. Sequences need the Creator plan (or its free trial)."
            sys.exit(f"Kit API {method} {path} failed with {e.code}: {detail}")


def every(key, path, field):
    items, after = [], None
    for _ in range(50):
        sep = "&" if "?" in path else "?"
        data = kit("GET", f"{path}{sep}per_page=100" + (f"&after={after}" if after else ""), key)
        items += data.get(field, [])
        page = data.get("pagination") or {}
        if not page.get("has_next_page"):
            break
        after = page.get("end_cursor")
    return items


def order():
    """Every live article once, in learning-path order (paths.yaml file order), with the path it's sent under."""
    paths = (yaml.safe_load((ROOT / "content" / "paths.yaml").read_text(encoding="utf-8")) or {})["paths"]
    seen, out = set(), []
    for p in paths:
        first = True
        for slug in p["stations"]:
            if slug in seen:
                continue
            fm, _ = parse_md(ROOT / "content" / "posts" / f"{slug}.md")
            if fm.get("draft"):
                continue
            seen.add(slug)
            out.append((slug, p, first))
            first = False
    return out


def plan(cfg, limit=None):
    seq = cfg.get("sequence") or {}
    first, gap = int(seq.get("weekly_first", 8)), int(seq.get("then_every_days", 14))
    notes = cfg.get("notes") or {}
    items = order()
    titles = [article(slug)[0] for slug, _, _ in items]
    out = []
    intro_gap = int(seq.get("intro_every_days", 3))
    for j, (subject, preview, content) in enumerate(intro_emails()):
        out.append({"subject": subject, "preview_text": preview, "content": content,
                    "delay_value": 0 if j == 0 else intro_gap, "delay_unit": "days",
                    "published": bool(seq.get("publish", False)), "position": j})
    n_intro = len(out)
    for i, (slug, path, starts) in enumerate(items[:limit]):
        title, description, intro = article(slug)
        extra = notes.get(slug) or {}
        note = extra.get("note", "")
        more = extras(slug)
        more["path"] = {"title": path["title"], "blurb": path["blurb"], "starts": starts and i > 0}
        more["next"] = titles[i + 1] if i + 1 < len(titles) else ""
        written = written_email(slug, path["title"], more["minutes"])
        subject, preview, content = written or (title, clip(description),
                                                email_html(slug, title, description, intro, note, extra.get("ps", ""), more))
        out.append({
            "subject": subject,
            "preview_text": preview,
            "content": content,
            "delay_value": (7 if n_intro else 0) if i == 0 else (7 if i < first else gap),
            "delay_unit": "days",
            "published": bool(seq.get("publish", False)),
            "position": n_intro + i,
        })
    return seq, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, help="only the first N articles")
    a = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "content" / "schedule.yaml").read_text(encoding="utf-8")) or {}
    seq, emails = plan(cfg, a.limit)
    name = seq.get("name") or "Shopfloor Matters: the article series"
    day = 0
    for e in emails:
        day += e["delay_value"]
        print(f"day {day:>3}  {e['subject']}")

    key = os.environ.get("KIT_API_KEY", "").strip()
    if a.dry_run or not key:
        print(("DRY RUN" if a.dry_run else "KIT_API_KEY not set") + f": {len(emails)} emails for '{name}', nothing changed in Kit.")
        return

    found = [s for s in every(key, "/sequences", "sequences") if s.get("name") == name]
    if found:
        sid = found[0]["id"]
        print(f"Using existing sequence {sid}")
    else:
        sid = kit("POST", "/sequences", key, {
            "name": name, "send_hour": int(seq.get("send_hour", 8)), "time_zone": "Europe/London",
            "send_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "hold": True, "repeat": False, "active": True,
        })["sequence"]["id"]
        print(f"Created sequence {sid}")

    existing = every(key, f"/sequences/{sid}/emails", "emails")
    if existing and not any(e.get("published") for e in existing):
        # all drafts: start clean so the order is exactly right
        for e in existing:
            kit("DELETE", f"/sequences/{sid}/emails/{e['id']}", key)
        print(f"Removed {len(existing)} draft emails to rebuild in order")
        existing = []
    have = {e.get("subject"): e for e in existing}
    added = updated = 0
    for e in emails:
        old = have.get(e["subject"])
        if old:
            kit("PUT", f"/sequences/{sid}/emails/{old['id']}", key, e)
            updated += 1
        else:
            kit("POST", f"/sequences/{sid}/emails", key, e)
            added += 1
    state = "published" if seq.get("publish") else "drafts"
    print(f"Sequence {sid}: {added} added, {updated} updated ({state}).")


if __name__ == "__main__":
    main()
