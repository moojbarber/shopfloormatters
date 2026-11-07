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


def clip(text, n=150):
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def extras(slug):
    """Extra value for the email, all taken from reviewed site content: reading time,
    the article's summary, its section headings, up to three FAQs and two related articles."""
    fm, body = parse_md(ROOT / "content" / "posts" / f"{slug}.md")
    answers = (yaml.safe_load((ROOT / "content" / "answers.yaml").read_text(encoding="utf-8")) or {}).get(slug) or {}
    words = len(re.findall(r"\w+", re.sub(r"\(https?://[^)]*\)", "", body)))
    heads = [re.sub(r"[*_`]", "", h).strip() for h in re.findall(r"^##\s+(.+)$", body, flags=re.M)]
    heads = [h for h in heads if not re.match(r"(faq|frequently asked)", h, re.I)][:8]
    tags = (yaml.safe_load((ROOT / "content" / "tags.yaml").read_text(encoding="utf-8")) or {}).get("articles") or {}
    mine = set(tags.get(slug) or [])
    others = [s for s in tags if s != slug and (ROOT / "content" / "posts" / f"{s}.md").exists()]
    # rarer shared tags count for more, so a broad tag like MES/MOM doesn't decide it
    count = {}
    for ids in tags.values():
        for t in ids or []:
            count[t] = count.get(t, 0) + 1
    score = lambda s: sum(1 / count[t] for t in mine & set(tags.get(s) or []))
    others.sort(key=lambda s: -score(s))
    related = []
    for s in others[:2]:
        rfm, _ = parse_md(ROOT / "content" / "posts" / f"{s}.md")
        related.append({"slug": s, "title": html.unescape(rfm["title"]), "description": rfm.get("description", "")})
    return {"minutes": max(3, round(words / 230)), "summary": answers.get("summary", ""),
            "faq": [q for q in (answers.get("faq") or []) if not same(q["a"], answers.get("summary", ""))][:3],
            "heads": heads, "related": related}


def same(a, b):
    """True when an FAQ answer mostly repeats the summary."""
    wa, wb = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) > 0.6


def email_html(slug, title, description, intro, note="", ps="", more=None):
    utm = "utm_source=newsletter&utm_medium=email"
    url = f"{SITE}/post/{slug}?{utm}"
    img = f"{SITE}/images/og/{slug}.png"
    fix = lambda t: re.sub(r'href="/', f'href="{SITE}/', markdown.markdown(t))
    inline = lambda t: fix(t)[3:-4] if fix(t).startswith("<p>") else fix(t)
    h2 = 'style="font-size:19px;margin:32px 0 10px"'
    lead = fix(note) + '<hr style="border:none;border-top:1px solid #ddd;margin:24px 0">' if note else ""
    tail = f'<p style="margin-top:24px">{inline(ps)}</p>' if ps else ""
    button = f'<p style="margin:28px 0"><a href="{url}" style="display:inline-block;padding:14px 24px;border-radius:12px;background:#8b6cff;color:#ffffff;font-weight:700;text-decoration:none">Read the full article →</a></p>'
    m = more or {}
    mins = f'<p style="margin:0 0 16px;color:#888;font-size:14px">{m["minutes"]}-minute read</p>' if m.get("minutes") else ""
    short = (f'<div style="margin:24px 0;padding:16px 20px;border-left:4px solid #8b6cff;background:#f5f3ff;border-radius:8px">'
             f'<p style="margin:0 0 6px;font-weight:700">In short</p><p style="margin:0">{inline(m["summary"])}</p></div>') if m.get("summary") else ""
    heads = (f'<h2 {h2}>In the full article</h2><ul style="padding-left:20px">'
             + "".join(f"<li>{html.escape(h)}</li>" for h in m["heads"]) + "</ul>") if m.get("heads") else ""
    faq = (f'<h2 {h2}>Quick answers</h2>' + "".join(
        f'<p style="margin:16px 0 4px;font-weight:700">{html.escape(q["q"])}</p><p style="margin:0">{inline(q["a"])}</p>' for q in m["faq"])) if m.get("faq") else ""
    rel = (f'<h2 {h2}>Related reading</h2>' + "".join(
        f'<p style="margin:12px 0"><a href="{SITE}/post/{r["slug"]}?{utm}" style="font-weight:700">{html.escape(r["title"])}</a><br>'
        f'<span style="color:#555">{html.escape(r["description"])}</span></p>' for r in m["related"])) if m.get("related") else ""
    pth = m.get("path") or {}
    ptag = (f'<p style="margin:0 0 16px;font-size:14px;color:#555">'
            + (f'<b>New learning path: {html.escape(pth["title"])}.</b> {html.escape(pth["blurb"])}' if pth.get("starts")
               else f'From the learning path <b>{html.escape(pth["title"])}</b>') + '</p>') if pth else ""
    nxt = (f'<p style="margin-top:24px;font-size:14px;color:#555">Next time: <b>{html.escape(m["next"])}</b></p>') if m.get("next") else ""
    return f"""{lead}{ptag}<p><a href="{url}"><img src="{img}" alt="{html.escape(title)}" width="600" style="width:100%;max-width:600px;height:auto;border-radius:12px"></a></p>
<h1 style="margin:24px 0 8px">{html.escape(title)}</h1>
{mins}{intro}
{short}{heads}{button}{faq}{rel}
<p style="margin-top:28px">If you have a question about your own project, just hit reply.</p>
<p>Matt</p>{tail}{nxt}
<p style="margin-top:32px;font-size:13px;color:#888">Forwarded this email? You can <a href="{SITE}/subscribe?{utm}">subscribe here</a> to get the series from the first article.</p>"""


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
    content = email_html(slug, title, description, intro, extra.get("note", ""), extra.get("ps", ""), extras(slug))
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
        "preview_text": clip(description),
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
