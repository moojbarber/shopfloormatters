#!/usr/bin/env python3
"""Email this week's article to newsletter subscribers via Kit (kit.com).

Run on release day (the GitHub Actions workflow does this every Tuesday morning,
after the site has been rebuilt). It looks up which article content/schedule.yaml
releases today, builds a short email (title, image, intro, link to the full article)
and schedules a Kit broadcast to all subscribers a few minutes later.

Safe to run more than once: if a broadcast with the same subject already exists
in Kit, it does nothing.

Needs the KIT_API_KEY environment variable (a Kit v4 API key, stored as a GitHub
Actions secret). Without it, it prints what it would have sent and exits.

Usage: python scripts/newsletter.py [--date YYYY-MM-DD] [--slug SLUG] [--dry-run]
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import markdown
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import ROOT, SITE, load_schedule, parse_md, uk_today  # noqa: E402

API = "https://api.kit.com/v4"


def kit(method, path, key, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"X-Kit-Api-Key": key, "Accept": "application/json",
                                          "Content-Type": "application/json", "User-Agent": "shopfloormatters-newsletter"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


def existing_subjects(key):
    subjects, after = set(), None
    for _ in range(20):
        q = "/broadcasts?per_page=100" + (f"&after={after}" if after else "")
        data = kit("GET", q, key)
        subjects |= {b.get("subject") for b in data.get("broadcasts", [])}
        page = data.get("pagination") or {}
        if not page.get("has_next_page"):
            break
        after = page.get("end_cursor")
    return subjects


def article(slug):
    path = ROOT / "content" / "posts" / f"{slug}.md"
    fm, body = parse_md(path)
    seo = (yaml.safe_load((ROOT / "content" / "seo.yaml").read_text(encoding="utf-8")) or {}).get(slug, {})
    fm = {**fm, **seo}
    # the opening of the article, up to the first heading (max 3 paragraphs)
    intro_md = re.split(r"^#{2,}\s", body, maxsplit=1, flags=re.M)[0].strip()
    paras = [p for p in re.split(r"\n\s*\n", intro_md) if p.strip() and not p.lstrip().startswith(("::", "<", "|", "-", "!"))][:3]
    intro = markdown.markdown("\n\n".join(paras))
    intro = re.sub(r'href="/', f'href="{SITE}/', intro)
    return html.unescape(fm["title"]), fm.get("description", ""), intro


def email_html(slug, title, description, intro, note="", ps=""):
    url = f"{SITE}/post/{slug}?utm_source=newsletter&utm_medium=email"
    img = f"{SITE}/images/og/{slug}.png"
    fix = lambda t: re.sub(r'href="/', f'href="{SITE}/', markdown.markdown(t))
    lead = fix(note) + '<hr style="border:none;border-top:1px solid #ddd;margin:24px 0">' if note else ""
    tail = f'<p style="margin-top:24px">{fix(ps)[3:-4]}</p>' if ps else ""
    return f"""{lead}<p><a href="{url}"><img src="{img}" alt="{html.escape(title)}" width="600" style="width:100%;max-width:600px;height:auto;border-radius:12px"></a></p>
<h1 style="margin:24px 0 12px">{html.escape(title)}</h1>
{intro}
<p style="margin:28px 0"><a href="{url}" style="display:inline-block;padding:14px 24px;border-radius:12px;background:#8b6cff;color:#ffffff;font-weight:700;text-decoration:none">Read the full article →</a></p>
<p>If you have a question about your own project, just hit reply.</p>
<p>Matt</p>{tail}
<p style="margin-top:32px;font-size:13px;color:#888">Forwarded this email? You can <a href="{SITE}/subscribe?utm_source=newsletter&utm_medium=email">subscribe here</a> to get the series from the first article.</p>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="release date to send for (default: today, UK)")
    ap.add_argument("--slug", help="send this article instead of looking up the schedule")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.slug:
        slug = a.slug
    else:
        day = dt.date.fromisoformat(a.date) if a.date else uk_today()
        due = [s for s, d in load_schedule().items() if d == day]
        if not due:
            print(f"No article scheduled for {day}. Nothing to send.")
            return
        slug = due[0]

    title, description, intro = article(slug)
    cfg = yaml.safe_load((ROOT / "content" / "schedule.yaml").read_text(encoding="utf-8")) or {}
    extra = (cfg.get("notes") or {}).get(slug) or {}
    content = email_html(slug, title, description, intro, extra.get("note", ""), extra.get("ps", ""))
    hh, mm = (cfg.get("send_time") or "08:00").split(":")
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/London")
    except Exception:
        tz = dt.timezone.utc
    now = dt.datetime.now(tz)
    send_at = max(now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0), now + dt.timedelta(minutes=10))

    payload = {
        "subject": title,
        "preview_text": description[:150],
        "description": f"Weekly article: {slug}",
        "content": content,
        "public": False,
        "published_at": now.astimezone(dt.timezone.utc).isoformat(),
        "send_at": send_at.astimezone(dt.timezone.utc).isoformat(),
        "thumbnail_url": f"{SITE}/images/og/{slug}.png",
        "thumbnail_alt": title,
    }

    key = os.environ.get("KIT_API_KEY", "").strip()
    if a.dry_run or not key:
        print(("DRY RUN" if a.dry_run else "KIT_API_KEY not set, so nothing was sent") + f": would email '{title}' at {send_at:%Y-%m-%d %H:%M %Z}")
        print(content)
        return
    if title in existing_subjects(key):
        print(f"A broadcast called '{title}' already exists in Kit. Not sending again.")
        return
    res = kit("POST", "/broadcasts", key, payload)
    print(f"Scheduled '{title}' for {send_at:%Y-%m-%d %H:%M %Z} (Kit broadcast {res.get('broadcast', {}).get('id')})")


if __name__ == "__main__":
    main()
