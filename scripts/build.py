#!/usr/bin/env python3
"""Build shopfloormatters.com into ./dist

    python scripts/build.py                    # production (served from the domain root)
    python scripts/build.py --base /shopfloormatters # preview on <user>.github.io/shopfloormatters

Content:
  content/posts/*.md         new articles (front matter + Markdown)
  content/legacy/posts/*.md  imported Wix articles
  content/seo.yaml           per-article title/description/category overrides
  content/blocks/*.html      reusable on-brand blocks, used in Markdown as `::block name`
"""
import argparse
import os
import datetime as dt
import html
import json
import math
import re
import shutil
from pathlib import Path
from urllib.parse import quote

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SITE = "https://www.shopfloormatters.com"
SHOW_SPEAKING = False  # speaking page held back for launch; review on the speaking-page branch
# Tools are brought back one at a time as they're reviewed. Full set is on the tools branch.
ENABLED_TOOLS = ["systems-landscape", "oee-one-percent"]
SHOW_TOOLS = bool(ENABLED_TOOLS)
LINKEDIN = "https://www.linkedin.com/in/mattjbarber/"
# Social profiles shown in the newsletter box. Leave a url empty to hide that network.
SOCIALS = [
    {"id": "linkedin", "name": "LinkedIn", "url": LINKEDIN},
    {"id": "x", "name": "X", "url": "https://x.com/moojbarber"},
    {"id": "instagram", "name": "Instagram", "url": "https://www.instagram.com/matt.barber.me/"},
]
# Kit (kit.com) form ID for the newsletter sign-up. Set the KIT_FORM_ID repo variable; empty = sign-ups not open yet.
KIT_FORM_ID = os.environ.get("KIT_FORM_ID", "").strip()
# ...and sign-ups only go live once `signups_open: true` is set in content/schedule.yaml
# (after the form is linked to the Kit sequence and its emails are published).
if not (yaml.safe_load((Path(__file__).resolve().parent.parent / "content" / "schedule.yaml").read_text(encoding="utf-8")) or {}).get("signups_open"):
    KIT_FORM_ID = ""
# Where "Ask Matt" questions are POSTed (e.g. a Formspree or Tally endpoint). Empty = copy the question and open LinkedIn.
ASK_FORM_ENDPOINT = os.environ.get("ASK_FORM_ENDPOINT", "").strip()

CATEGORIES = [
    {"key": "thought-leadership", "slug": "thought-leadership", "name": "Smart Factory & AI", "eyebrow": "Think", "art": "thought-leadership",
     "blurb": "Shopfloor AI, the connected worker and where manufacturing goes next.",
     "kicker": "Where AI really adds value on the shopfloor, how connected worker changes the frontline, and what both need underneath."},
    {"key": "education", "slug": "mes-education", "name": "Foundations", "eyebrow": "Learn", "art": "education",
     "blurb": "MES, MOM, ISA-95 and OEE: the systems and standards every smart factory runs on.",
     "kicker": "The systems and standards underneath every smart factory: what MES and MOM actually do, how ISA-95 fits together, how OEE is measured, and a function-by-function tour of MES."},
    {"key": "advice", "slug": "mes-advice", "name": "Implementation", "eyebrow": "Make it work", "art": "advice",
     "blurb": "Business cases, teams and getting shopfloor projects over the line.",
     "kicker": "Practical guidance for getting shopfloor projects over the line: building an honest business case, getting the team right, and avoiding the mistakes that sink implementations."},
]
CAT_BY_KEY = {c["key"]: c for c in CATEGORIES}

NAV = [
    {"key": "roles", "label": "Your role", "desc": "What it means for your job, CEO to operator", "href": "/roles/"},
    {"key": "paths", "label": "Learning paths", "desc": "Guided routes through the articles", "href": "/paths/"},
    {"key": "tools", "label": "Tools", "desc": "Calculators, checks and templates", "href": "/tools/"},
    {"key": "articles", "label": "Articles", "desc": "Everything, by topic or newest first", "href": "/articles"},
    {"key": "featured", "label": "Featured", "desc": "Podcasts, interviews and press", "href": "/featured"},
    {"key": "faq", "label": "FAQ", "desc": "Straight answers to common questions", "href": "/faq/"},
    {"key": "glossary", "label": "Glossary", "desc": "Shopfloor jargon in plain English", "href": "/glossary/"},
    {"key": "about", "label": "About", "desc": "Who I am and why I write this", "href": "/about"},
]
NAV = [n for n in NAV if SHOW_TOOLS or n["key"] != "tools"]

# Old Wix URLs that should point somewhere new
REDIRECTS = {
    "home/categories/interfacing": "/mes-education",
    "home/categories/mes": "/thought-leadership",
    "home/categories/mes-advice": "/mes-advice",
    "copy-of-education": "/mes-advice",
    "blog": "/articles",
    "challenges": "/articles",
    "post/introduction-to-mes-and-smart-manufacturing": "/post/what-is-a-smart-factory",
    "post/mes-is-a-digital-twin": "/post/mes-and-digital-twins",
    "post/smart-manufacturing-maturity-model": "/post/time-to-truth",
    "post/what-is-mes-and-why-is-it-important-in-manufacturing": "/post/what-is-mes",
    "post/what-is-the-isa-95-model-and-where-does-mes-fit": "/post/isa-95-explained",
    "post/who-are-mesa-and-how-do-they-define-mes": "/post/mesa-and-the-definition-of-mes",
    "post/what-is-oee-overall-equipment-effectiveness": "/post/what-is-oee",
    "post/the-history-of-mes-and-digitalisation-in-manufacturing": "/post/history-of-mes",
    "post/mes-functionality-production-monitoring": "/post/mes-functionality-production",
    "post/mes-basics-production-scheduling": "/post/mes-functionality-scheduling",
    "post/mes-functionality-quality-operations": "/post/mes-functionality-quality",
    "post/mes-functionality-inventory-management": "/post/mes-functionality-inventory",
    "post/mes-functionality-logistics-warehousing": "/post/mes-functionality-logistics",
    "post/mes-functionality-inventory-logistics-overview": "/post/mes-functionality-guide",
    "post/implementing-kaizen-principles-with-mes-for-lean-manufacturing-success": "/post/kaizen-and-mes",
    "post/who-benefits-from-an-mes": "/post/who-benefits-from-mes",
    "post/can-mes-improve-your-bottom-line": "/post/mes-roi-bottom-line",
    "post/implementing-mes-can-simplify-your-erp": "/post/mes-simplifies-erp",
    "post/building-a-winning-team-for-mes-implementation-navigating-challenges-and-ensuring-success": "/post/mes-implementation-team",
    "post/an-overview-of-the-mes-market": "/post/mes-market-overview",
    "post/the-future-of-smart-manufacturing-harnessing-the-power-of-mes-intelligence": "/post/ai-needs-shopfloor-data",
    "post/food-beverage-industry-challenges": "/post/food-and-beverage-manufacturing-challenges",
}


PLATFORMS = {"youtube": ("Watch on", "YouTube"), "spotify": ("Listen on", "Spotify"), "apple": ("Listen on", "Apple Podcasts"),
             "transcript": ("Read the", "Transcript"), "read": ("Read the", "Article"), "episode": ("Go to", "Episode page"),
             "event": ("See the", "Event page")}
TYPE_LABEL = {"podcast": "Podcast", "article": "Press", "webinar": "Webinar"}


def load_featured():
    data = yaml.safe_load((ROOT / "content" / "featured.yaml").read_text(encoding="utf-8"))
    items = []
    for it in data["items"]:
        d = it["date"] if isinstance(it["date"], dt.date) else dt.date.fromisoformat(str(it["date"]))
        it = dict(it, date_iso=d.isoformat(), date_text=it.get("date_label") or d.strftime("%B %Y"),
                  date_short=it.get("date_label") or d.strftime("%b %Y"), type_label=TYPE_LABEL[it["type"]],
                  outlet_line=it.get("card_outlet") or it["outlet"])
        links = []
        for l in it["links"]:
            verb, name = PLATFORMS[l["kind"]]
            if l.get("label"):
                verb, name = "Read the", l["label"]
            if l.get("show") and l["kind"] in ("spotify", "apple", "youtube"):
                verb = verb + " (show)"
            short = {"youtube": "YouTube", "spotify": "Spotify", "apple": "Apple Podcasts", "transcript": "Transcript",
                     "read": "Read", "episode": "Episode page", "event": "Event page"}[l["kind"]]
            if l.get("label"):
                short = l["label"]
            links.append(dict(l, verb=verb, name=name, short=short))
        it["links"] = links
        items.append(it)
    items.sort(key=lambda i: i["date_iso"], reverse=True)
    by_img = {i["image"]: i for i in items}
    return {"carousel": [by_img[k] for k in data["carousel"]], "items": items}


def load_paths(posts):
    """Learning paths: lines of articles. Adds hub-map geometry and per-post path context."""
    data = yaml.safe_load((ROOT / "content" / "paths.yaml").read_text(encoding="utf-8"))
    by_slug = {p["slug"]: p for p in posts}
    HX, END, T, K = 190, 800, 10, 0.55  # K: horizontal run per unit of vertical drop on the branch
    N = len(data["paths"])
    STEP = 80 if N <= 8 else 62
    TOP = 180 if N <= 8 else 215   # room above the first line for its angled station labels
    BOTTOM = 180 if N <= 8 else 70
    HY = TOP + (N - 1) * STEP / 2
    map_h = int(TOP + (N - 1) * STEP + BOTTOM)
    paths = []
    for i, d in enumerate(data["paths"]):
        missing = [s for s in d["stations"] if s not in by_slug]
        assert not missing, f"path {d['id']} has unknown slugs {missing}"
        st = [by_slug[s] for s in d["stations"]]
        y = TOP + i * STEP
        dy = y - HY
        dx = abs(dy) * K
        x0 = HX + dx
        n = len(st)
        gap = (END - x0 - 80) / (n - 1)
        segs = []
        if dy:
            ang = math.degrees(math.atan2(dy, dx))
            segs.append(f"left:{HX}px;top:{HY - T / 2}px;width:{math.hypot(dx, dy):.1f}px;transform-origin:0 50%;transform:rotate({ang:.2f}deg)")
        segs.append(f"left:{x0 - T / 2}px;top:{y - T / 2}px;width:{END - x0 + T}px")
        stations = [{"post": q, "n": k + 1, "x": round(x0 + 80 + k * gap, 1), "y": y} for k, q in enumerate(st)]
        paths.append(dict(d, stations=stations, n=n, minutes=sum(q["read_time"] for q in st), y=y, x0=x0, end=END,
                          segs=segs, flow=f"left:{x0}px;top:{y - 2}px;width:{END - x0}px", slugs=[q["slug"] for q in st]))
    for path in paths:
        for k, stn in enumerate(path["stations"]):
            q = stn["post"]
            q.setdefault("paths", []).append({"id": path["id"], "title": path["title"], "color": path["color"], "rgb": path["rgb"],
                                              "n": path["n"], "index": k + 1, "slugs": path["slugs"],
                                              "prev": path["stations"][k - 1]["post"] if k else None,
                                              "next": path["stations"][k + 1]["post"] if k + 1 < path["n"] else None})
    # at the end of a path, suggest the others in the suggested sequence, starting from the one after it
    for i, path in enumerate(paths):
        after = paths[i + 1:] + paths[:i]
        path["stations"][-1]["post"]["paths"][[e["id"] for e in path["stations"][-1]["post"]["paths"]].index(path["id"])]["after"] = [
            {"id": o["id"], "title": o["title"], "color": o["color"], "rgb": o["rgb"], "blurb": o["blurb"], "who": o.get("who", ""),
             "n": o["n"], "minutes": o["minutes"], "image": o.get("image") or o["slugs"][0], "first": o["slugs"][0]} for o in after]
    for path in paths:
        path["hub"] = {"x": HX, "y": HY, "h": map_h}
    order = {k: i for i, k in enumerate(data["home_order"])}
    return paths, sorted(paths, key=lambda p: order.get(p["id"], 99))


ICONS = {
    "ladder": '<svg viewBox="0 0 24 24"><path d="M5 20h4v-4h4v-4h4V8h3"/><path d="M5 20V4"/></svg>',
    "gauge": '<svg viewBox="0 0 24 24"><path d="M4 16a8 8 0 1 1 16 0"/><path d="M12 16l4-5"/><circle cx="12" cy="16" r="1.5"/></svg>',
    "nodes": '<svg viewBox="0 0 24 24"><rect x="8" y="9" width="8" height="6" rx="1.5"/><rect x="9" y="2" width="6" height="3.5" rx="1"/><rect x="2" y="17" width="6" height="4" rx="1"/><rect x="16" y="17" width="6" height="4" rx="1"/><path d="M12 5.5V9M9 15l-4 2M15 15l4 2"/></svg>',
    "stack": '<svg viewBox="0 0 24 24"><path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/><path d="M3 17.5l9 5 9-5" opacity=".5"/></svg>',
    "scales": '<svg viewBox="0 0 24 24"><path d="M12 4v16M6 20h12M5 8h14"/><path d="M5 8l-3 6h6zM19 8l-3 6h6z"/></svg>',
    "chart": '<svg viewBox="0 0 24 24"><path d="M4 20V4M4 20h16"/><path d="M8 16v-4M12 16V8M16 16v-6"/></svg>',
    "lanes": '<svg viewBox="0 0 24 24"><path d="M3 5h18M3 12h18M3 19h18"/><rect x="6" y="3" width="4" height="4" rx="1"/><rect x="12" y="10" width="4" height="4" rx="1"/><path d="M10 5h2v7"/></svg>',
    "target": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/></svg>',
    "check": '<svg viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 9l2 2 4-4M8 15h8"/></svg>',
}


def post_ref(p):
    return {"slug": p["slug"], "title": p["title"], "short": p["short"], "cat": p["category_label"]}


def load_tools(posts):
    """Tools and templates (/tools/). Resolves article references and attaches 'Put it into practice' boxes to posts."""
    data = yaml.safe_load((ROOT / "content" / "tools.yaml").read_text(encoding="utf-8"))
    by_slug = {p["slug"]: p for p in posts}
    tools = []
    for t in data["tools"]:
        if t["id"] not in ENABLED_TOOLS and t["id"] != "which-systems":
            continue
        t = dict(t)
        f = ROOT / "content" / "tools" / f"{t['id']}.yaml"
        t["data"] = yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else None
        t["reading"] = [by_slug[s] for s in t.get("posts", []) if s in by_slug][:3]
        missing = [s for s in t.get("posts", []) if s not in by_slug]
        if missing:
            print("  tools: unknown posts", t["id"], missing)
        d = t["data"]
        js = None
        if t["id"] == "readiness-check":
            for lv in d["levels"]:
                lv["posts"] = [post_ref(by_slug[s]) for s in lv.pop("read") if s in by_slug]
            for ar in d["areas"]:
                ar["post"] = post_ref(by_slug[ar["read"]])
            js = d
        elif t["id"] == "which-systems":
            for k, c in d["capabilities"].items():
                c["post"] = post_ref(by_slug[c["read"]]) if c.get("read") in by_slug else None
            js = {"caps": d["capabilities"], "order": list(d["capabilities"].keys())}
        elif t["id"] == "vendor-scorecard":
            js = {"n": sum(len(g["questions"]) for g in d["groups"])}
        t["json"] = json.dumps(js, separators=(",", ":")).replace("</", "<\\/") if js is not None else "null"
        tools.append(t)
    caps_src = next((t for t in tools if t["id"] == "which-systems"), None)
    tools = [t for t in tools if t["id"] in ENABLED_TOOLS]
    for t in tools:
        for s in t.get("posts", []):
            if s in by_slug and not by_slug[s].get("tool"):
                by_slug[s]["tool"] = t
    return tools, caps_src


def load_audiences(posts, glossary, tools, caps, base):
    data = yaml.safe_load((ROOT / "content" / "audiences.yaml").read_text(encoding="utf-8"))
    by_slug = {p["slug"]: p for p in posts}
    gl = {g["slug"]: g for g in glossary}
    tl = {t["id"]: t for t in tools}
    def md(s):
        return re.sub(r'href="/(?!/)', f'href="{base}/', markdown.markdown(s))
    out = []
    for a in data["pages"]:
        a = dict(a)
        a["intro_html"] = md(a["intro"])
        a["sections_html"] = [{"h": s["h"], "id": slugify(s["h"]), "html": md(s["body"])} for s in a["sections"]]
        a["post_list"] = [by_slug[s] for s in a.get("posts", []) if s in by_slug]
        a["tool_list"] = [tl[x] for x in a.get("tools", []) if x in tl]
        a["term_list"] = [gl[x] for x in a.get("terms", []) if x in gl]
        a["caps"] = [caps[c] for c in a.get("capabilities", []) if c in caps]
        for kind, have, want in (("posts", a["post_list"], a.get("posts", [])), ("terms", a["term_list"], a.get("terms", []))):
            if len(have) != len(want):
                print("  audiences: missing", kind, a["id"], set(want) - {x["slug"] for x in have})
        out.append(a)
    return out


# ------------------------------------------------------------------ helpers
def parse_md(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    fm = yaml.safe_load(m.group(1)) if m else {}
    return fm or {}, text[m.end():] if m else text


def parse_date(s):
    if not s:
        return None
    if isinstance(s, (dt.date, dt.datetime)):
        return s if isinstance(s, dt.datetime) else dt.datetime(s.year, s.month, s.day)
    return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).replace(tzinfo=None)


def long_date(d):
    return f"{d.day} {d:%B %Y}" if d else ""


def short_date(d):
    return f"{d.day} {d:%b %Y}" if d else ""


def slugify(value, separator="-"):
    value = re.sub(r"[^\w\s-]", "", html.unescape(value).lower())
    return re.sub(r"[\s_-]+", separator, value).strip(separator)


def render_body(md_text, base, blocks):
    md_text = md_text.replace("\\_", "_")
    # ::block name  ->  raw HTML block
    def blk(m):
        name = m.group(1)
        return "\n" + blocks.get(name, f"<!-- missing block {name} -->") + "\n"
    md_text = re.sub(r"^::block\s+([\w-]+)\s*$", blk, md_text, flags=re.M)
    conv = markdown.Markdown(extensions=["toc", "tables", "sane_lists", "attr_list"],
                             extension_configs={"toc": {"slugify": slugify, "toc_depth": "2"}})
    out = conv.convert(md_text)
    toc = [{"id": t["id"], "name": html.unescape(t["name"])} for t in conv.toc_tokens]
    # internal links -> site-relative, external links open in new tab
    out = re.sub(r'href="https?://(?:www\.)?(?:mesmatters|shopfloormatters)\.com(/[^"]*)?"', lambda m: f'href="{base}{m.group(1) or "/"}"', out)
    out = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', out)
    out = re.sub(r'(src|href)="/(?!/)', lambda m: f'{m.group(1)}="{base}/', out)
    out = re.sub(r"<table>", '<div class="table-wrap"><table>', out).replace("</table>", "</table></div>")
    out = re.sub(r"<img ", '<img loading="lazy" ', out)
    return out, toc


def load_schedule():
    """slug -> release date (UK) from content/schedule.yaml."""
    path = ROOT / "content" / "schedule.yaml"
    if not path.exists():
        return {}
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    start = cfg.get("start")
    if isinstance(start, str):
        start = dt.date.fromisoformat(start)
    return {slug: start + dt.timedelta(weeks=i) for i, slug in enumerate(cfg.get("weekly") or [])}


def publish_all_now():
    path = ROOT / "content" / "schedule.yaml"
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {} if path.exists() else {}
    return bool(cfg.get("publish_all_now"))


def uk_today():
    override = os.environ.get("BUILD_DATE")
    if override:
        return dt.date.fromisoformat(override)
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("Europe/London")).date()
    except Exception:
        return dt.date.today()


ANSWERS = yaml.safe_load((ROOT / "content" / "answers.yaml").read_text(encoding="utf-8")) if (ROOT / "content" / "answers.yaml").exists() else {}
ANSWERS = ANSWERS or {}


def month_year(d):
    return d.strftime("%B %Y") if d else ""


def load_posts(base, blocks, seo, include_scheduled=False):
    posts = []
    schedule = {} if publish_all_now() else load_schedule()
    today = uk_today()
    sources = sorted((ROOT / "content" / "legacy" / "posts").glob("*.md")) + sorted((ROOT / "content" / "posts").glob("*.md"))
    seen = {}
    for path in sources:
        fm, body = parse_md(path)
        if fm.get("draft"):
            continue
        slug = fm.get("slug") or path.stem
        meta = {**fm, **seo.get(slug, {})}
        if slug in schedule:
            if schedule[slug] > today and not include_scheduled:
                continue
            meta["published"] = schedule[slug].isoformat()
            meta.pop("updated", None)
        published = parse_date(meta.get("published"))
        updated = parse_date(meta.get("updated")) or published
        cat = CAT_BY_KEY[meta.get("category", "education")]
        words = len(re.findall(r"[A-Za-z0-9']+", body))
        html_body, toc = render_body(body, base, blocks)
        extra = ANSWERS.get(slug, {})
        p = {
            "slug": slug,
            "title": html.unescape(meta.get("title", slug)),
            "short": meta.get("short") or html.unescape(meta.get("title", slug)),
            "description": meta.get("description", ""),
            "category_key": cat["key"], "category_slug": cat["slug"], "category_label": cat["name"],
            "art": meta.get("art", "hexgrid"),
            "series": meta.get("series"), "guide": bool(meta.get("guide")), "order": meta.get("order", 0), "start": meta.get("start"),
            "published": published, "updated": updated,
            "published_iso": published.date().isoformat() if published else "",
            "updated_iso": updated.date().isoformat() if updated else "",
            "date_long": long_date(published), "updated_long": long_date(updated) if updated and published and updated.date() != published.date() else "",
            "date_short": short_date(published),
            "words": words, "read_time": max(1, math.ceil(words / 230)),
            "body": html_body, "toc": toc,
            "canonical": f"{SITE}/post/{slug}",
            "md": body,
            "summary": extra.get("summary", ""), "summary_label": extra.get("label", "Summary"),
            "faq": extra.get("faq", []),
            "reviewed": parse_date(extra.get("reviewed")) or updated,
        }
        p["reviewed_long"] = month_year(p["reviewed"])
        seen[slug] = p
    posts = sorted(seen.values(), key=lambda p: p["published"] or dt.datetime(2000, 1, 1), reverse=True)
    # links to articles that aren't released yet become plain text until they are
    live = set(seen)
    pat = re.compile(r'<a href="' + re.escape(base) + r'/post/([\w-]+)"[^>]*>(.*?)</a>', re.S)
    for p in posts:
        p["body"] = pat.sub(lambda m: m.group(0) if m.group(1) in live else m.group(2), p["body"])
    return posts


def jsonld(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def load_glossary(posts):
    f = ROOT / "content" / "glossary.yaml"
    if not f.exists():
        return []
    data = yaml.safe_load(f.read_text(encoding="utf-8")) or []
    by_slug = {p["slug"]: p for p in posts}
    for g in data:
        g["slug"] = g.get("slug") or slugify(g["term"])
        g["articles"] = [by_slug[a] for a in g.get("articles", []) if a in by_slug]
    names = {g["slug"]: g for g in data}
    for g in data:
        g["see"] = [names[x] for x in g.get("see_also", []) if x in names]
    return sorted(data, key=lambda g: g["term"].lower())


FAQ_TOPICS = [
    {"id": "basics", "name": "MES, MOM and ERP basics", "blurb": "What the systems are, and how they differ.", "color": "#a594ff", "rgb": "165,148,255",
     "icon": "M4 6h16M4 12h16M4 18h10",
     "slugs": ["what-is-mes", "mes-vs-mom", "what-is-erp", "mes-vs-erp", "mes-simplifies-erp", "mes-mom-erp-compared"]},
    {"id": "strategy", "name": "Smart factory strategy", "blurb": "Where to start, and the order that works.", "color": "#ff8fe0", "rgb": "255,143,224",
     "icon": "M4 20l5-6 4 3 7-9M15 8h5v5",
     "slugs": ["what-is-a-smart-factory", "time-to-truth", "smart-factory-where-to-start", "how-to-modernise-a-factory"]},
    {"id": "buying", "name": "Choosing and delivering", "blurb": "Selection, business cases, deployment and timelines.", "color": "#ffb86b", "rgb": "255,184,107",
     "icon": "M9 12l2 2 4-4M5 4h14v16H5z",
     "slugs": ["how-to-choose-an-mes", "mes-business-case", "build-vs-buy-mes", "cloud-vs-on-premises-mes", "how-long-does-mes-implementation-take"]},
    {"id": "shopfloor", "name": "Running the shopfloor", "blurb": "Operators, traceability and maintenance.", "color": "#3ddc97", "rgb": "61,220,151",
     "icon": "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c1-4 4-6 8-6s7 2 8 6",
     "slugs": ["shopfloor-applications-explained", "connected-worker-one-app-not-five", "lot-vs-serial-traceability", "preventive-vs-predictive-maintenance"]},
    {"id": "performance", "name": "Measuring performance", "blurb": "OEE and the measures around it.", "color": "#ff8a70", "rgb": "255,138,112",
     "icon": "M12 21a9 9 0 1 1 9-9M12 12l5-5",
     "slugs": ["what-is-oee", "oee-vs-teep"]},
    {"id": "architecture", "name": "Architecture and integration", "blurb": "ISA-95, connectivity and the systems around MES/MOM.", "color": "#7fa6ff", "rgb": "127,166,255",
     "icon": "M5 5h5v5H5zM14 14h5v5h-5zM10 7.5h4.5V14",
     "slugs": ["isa-95-explained", "it-vs-ot", "opc-ua-vs-mqtt", "iiot-vs-mes", "scada-vs-mes", "historian-vs-mes"]},
]

GLOSSARY_SKIP = {"ai", "erp", "mes", "mom", "batch", "lot", "routing", "edge", "smart-factory", "bottleneck", "changeover", "cycle-time", "scrap-rate",
                 "shopfloor", "availability", "performance", "yield", "recall", "configuration", "customisation", "rework", "throughput",
                 "production-order", "recipe", "lean", "copilot", "validation", "quality-rate", "cavity", "andon", "gemba", "super-user",
                 "change-management", "process-mapping", "traveller", "time-series-data", "saas", "hypercare",
                 "defect", "deviation", "sensor", "barcode", "picking", "putaway", "batch-size", "simulation", "utilisation",
                 "continuous-improvement", "kpi", "spare-parts", "gateway", "goods-receipt", "shelf-life", "smart-manufacturing",
                 "procurement", "supply-chain", "lead-time", "master-data", "digital-transformation", "demand-planning", "capacity-planning"}


def autolink_glossary(posts, glossary, base, limit=6):
    """Link the first mention of glossary terms in each article's paragraphs and list items."""
    terms = []
    for g in glossary:
        if g["slug"] in GLOSSARY_SKIP:
            continue
        forms = [g["term"]] + ([g["term"].lower()] if not g["term"].isupper() and g["term"].lower() != g["term"] else [])
        rx = re.compile(r"(?<![\w/-])(" + "|".join(re.escape(f) for f in forms) + r")(?![\w/-])")
        terms.append((g, rx))
    block = re.compile(r"<(p|li)>(.*?)</\1>", re.S)
    for p in posts:
        if p["slug"] == "smart-factory-glossary":
            continue
        used, count = set(), [0]

        def fix_block(m):
            inner = m.group(2)
            parts = re.split(r"(<a\b.*?</a>|<[^>]+>)", inner, flags=re.S)
            for i, part in enumerate(parts):
                if not part or part.startswith("<"):
                    continue
                for g, rx in terms:
                    if count[0] >= limit:
                        break
                    if g["slug"] in used or (g["articles"] and g["articles"][0]["slug"] == p["slug"]):
                        continue
                    mm = rx.search(part)
                    if mm:
                        used.add(g["slug"]); count[0] += 1
                        link = f'<a class="gloss" href="{base}/glossary/{g["slug"]}" title="{html.escape(g["short"])}">{mm.group(1)}</a>'
                        part = part[:mm.start()] + link + part[mm.end():]
                        # don't re-scan inside the new link
                        before, after = part.split(link, 1)
                        parts[i] = before + link + after
                        break
                else:
                    continue
            return f"<{m.group(1)}>" + "".join(parts) + f"</{m.group(1)}>"

        p["body"] = block.sub(fix_block, p["body"])


def glossary_mentions(posts, glossary):
    """For each term, the articles that mention it, most mentions first."""
    for g in glossary:
        forms = []
        for f in [g["term"], g.get("stands")]:
            if not f:
                continue
            acronym = f.replace("&", "").replace(" ", "").isupper() or any(ch.isdigit() for ch in f)
            forms.append((f, 0 if acronym else re.I))
        found = []
        for p in posts:
            text = re.sub(r"\]\([^)]*\)", "]", p["md"])
            n = sum(len(re.findall(r"(?<![\w-])" + re.escape(f) + r"(?:s|es)?(?![\w-])", text, flags)) for f, flags in forms)
            if n:
                found.append((n, p))
        found.sort(key=lambda x: (-x[0], x[1]["title"]))
        seen = {p["slug"] for n, p in found}
        found += [(0, a) for a in g["articles"] if a["slug"] not in seen]
        g["mentions"] = [{"post": p, "n": n} for n, p in found]


def md_clean(md):
    md = re.sub(r"^::block\s+[\w-]+\s*$", "", md, flags=re.M)
    md = re.sub(r"\]\((/[^)]*)\)", lambda m: f"]({SITE}{m.group(1)})", md)
    return md.strip()


def write_llms(posts, paths, glossary, tools=(), audiences=()):
    by_cat = {}
    for p in posts:
        by_cat.setdefault(p["category_label"], []).append(p)
    out = ["# Shopfloor Matters", "",
           "> Practical, vendor-neutral writing on the smart factory, shopfloor AI and the MES/MOM systems underneath them, "
           "by Matt Barber (VP & General Manager, MES at Infor; former MES developer, implementation lead and head of product). "
           "Covers MES, MOM, ISA-95, OEE, connected worker, integration with ERP, PLM, WMS, APS, QMS, LIMS and CMMS, implementation and the business case.", "",
           "Cite as: Matt Barber, Shopfloor Matters, " + SITE + ". Quoting with attribution and a link is welcome.", "",
           "## Start here", "",
           *[f"- [{g['title']}]({g['canonical']}): {g['summary'] or g['description']}" for g in posts if g.get("guide")],
           f"- [Learning paths]({SITE}/paths/): guided routes through the articles, in order",
           f"- [FAQ]({SITE}/faq/): short answers to common questions, each linked to the full article",
           f"- [Role explorer]({SITE}/roles/): what MES/MOM means for each role, from CEO to operator: KPIs, challenges and the applications that matter most",
           f"- [MES compared]({SITE}/compare/): straight answers to MES vs ERP, MOM, MRP, SCADA, historian, IIoT, UNS, low-code and other comparisons",
           f"- [Glossary]({SITE}/glossary/): definitions of MES, MOM, OEE, ISA-95, UNS and other shopfloor terms",
           f"- [About Matt Barber]({SITE}/about): background and credentials",
           f"- [Podcasts, interviews and press]({SITE}/featured)",
           f"- [Full text of every article]({SITE}/llms-full.txt)", ""]
    for cat, ps in by_cat.items():
        out += [f"## {cat}", ""]
        for p in ps:
            out.append(f"- [{p['title']}]({p['canonical']}): {p['summary'] or p['description']}")
        out.append("")
    if SHOW_TOOLS: out += ["## Tools and templates", ""]
    for x in (tools if SHOW_TOOLS else []):
        out.append(f"- [{x['title']}]({SITE}/tools/{x['id']}): {x['blurb']}")
    out += ["", "## By industry and role", ""]
    for a in audiences:
        out.append(f"- [{a['title']}]({SITE}/for/{a['id']}): {a['kicker']}")
    out += ["", "## Learning paths", ""]
    for x in paths:
        out.append(f"- [{x['title']}]({SITE}/paths/{x['id']}): {x['blurb']}")
    (DIST / "llms.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    full = ["# Shopfloor Matters: full text", "", f"By Matt Barber. Source: {SITE}. Cite as: Matt Barber, Shopfloor Matters, with a link to the article.", ""]
    for p in posts:
        full += ["---", "", f"# {p['title']}", "", f"URL: {p['canonical']}", f"Author: Matt Barber", f"Published: {p['published_iso']}  Last updated: {p['reviewed'].date().isoformat() if p['reviewed'] else ''}", ""]
        if p["summary"]:
            full += [f"Summary: {p['summary']}", ""]
        full += [md_clean(p["md"]), ""]
        if p["faq"]:
            full += ["## Frequently asked questions", ""]
            for f in p["faq"]:
                full += [f"**{f['q']}**", "", f["a"], ""]
    if glossary:
        full += ["---", "", "# Glossary", "", f"URL: {SITE}/glossary/", ""]
        for g in glossary:
            name = g["term"] + (f" ({g['stands']})" if g.get("stands") else "")
            full += [f"## {name}", "", g["short"], "", g.get("body", ""), "", f"URL: {SITE}/glossary/{g['slug']}", ""]
    for a in audiences:
        full += ["---", "", f"# {a['title']}", "", f"URL: {SITE}/for/{a['id']}", "Author: Matt Barber", "", a["intro"].strip(), ""]
        for s in a["sections"]:
            full += [f"## {s['h']}", "", s["body"].strip(), ""]
        for f in a.get("faq", []):
            full += [f"**{f['q']}**", "", f["a"], ""]
    (DIST / "llms-full.txt").write_text("\n".join(full) + "\n", encoding="utf-8")


def write_feeds(posts, paths):
    from email.utils import format_datetime

    def rss(title, link, desc, items, path):
        x = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">', "<channel>",
             f"<title>{html.escape(title)}</title>", f"<link>{link}</link>", f"<description>{html.escape(desc)}</description>", "<language>en-gb</language>",
             f'<atom:link href="{SITE}/{path}" rel="self" type="application/rss+xml"/>']
        for p in items:
            d = p["published"].replace(tzinfo=dt.timezone.utc) if p["published"] else None
            x += ["<item>", f"<title>{html.escape(p['title'])}</title>", f"<link>{p['canonical']}</link>", f"<guid>{p['canonical']}</guid>",
                  f"<description>{html.escape(p['summary'] or p['description'])}</description>",
                  f"<content:encoded><![CDATA[{p['body'].replace(']]>', ']]&gt;')}]]></content:encoded>",
                  f"<author>noreply@shopfloormatters.com (Matt Barber)</author>", f"<category>{html.escape(p['category_label'])}</category>"]
            if d:
                x.append(f"<pubDate>{format_datetime(d)}</pubDate>")
            x.append("</item>")
        x += ["</channel>", "</rss>"]
        out = DIST / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(x) + "\n", encoding="utf-8")
    rss("Shopfloor Matters", SITE + "/", "Practical writing on the smart factory, shopfloor AI and MES/MOM, by Matt Barber.", posts, "feed.xml")
    for x in paths:
        rss(f"Shopfloor Matters: {x['title']}", f"{SITE}/paths/{x['id']}", x["blurb"], [s["post"] for s in x["stations"]], f"paths/{x['id']}.xml")


# ------------------------------------------------------------------ build
def relativise(page_html, rel):
    """Rewrite root-relative links for a static preview with no server rewrites."""
    depth = rel.count("/")
    prefix = "." if depth == 0 else "/".join([".."] * depth)
    def fix(m):
        attr, path, tail = m.group(1), m.group(2), m.group(3)
        if not path:
            path = "index.html"
        elif path.endswith("/"):
            path = path + "index.html"
        elif "." not in path.rsplit("/", 1)[-1]:
            path = path.rstrip("/") + ".html"
        return f'{attr}="{prefix}/{path}{tail}"'
    page_html = re.sub(r'(href|src)="@REL@/([^"#?]*)([^"]*)"', fix, page_html)
    page_html = page_html.replace('"@REL@"', f'"{prefix}/index.html"')
    return page_html


def build(base, relative=False, include_scheduled=False):
    base = "@REL@" if relative else base.rstrip("/")
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "public", DIST, ignore=shutil.ignore_patterns("legacy"))
    # only ship legacy images that are actually referenced
    seo = yaml.safe_load((ROOT / "content" / "seo.yaml").read_text(encoding="utf-8")) or {}
    blocks = {p.stem: p.read_text(encoding="utf-8") for p in (ROOT / "content" / "blocks").glob("*.html")}
    if "systems-landscape" not in ENABLED_TOOLS:
        blocks = {k: re.sub(r'\s*<div class="imap-cta">.*?</div>', "", v, flags=re.S) for k, v in blocks.items()}
    posts = load_posts(base, blocks, seo, include_scheduled)
    tagd = yaml.safe_load((ROOT / "content" / "tags.yaml").read_text(encoding="utf-8"))
    for p in posts:
        ids = tagd["articles"].get(p["slug"])
        assert ids, f"article has no tags in content/tags.yaml: {p['slug']}"
        bad = [t for t in ids if t not in tagd["tags"]]
        assert not bad, f"unknown tags {bad} on {p['slug']}"
        p["tags"] = [{"id": t, "name": tagd["tags"][t]} for t in ids]
        p["tag_ids"] = " ".join(ids)
    tag_list = [{"id": k, "name": v, "n": sum(1 for p in posts if k in p["tag_ids"].split())} for k, v in tagd["tags"].items()]
    for p in posts:
        for img in re.findall(r'/images/legacy/([^"\')\s]+)', p["body"]):
            src = ROOT / "public" / "images" / "legacy" / img
            if src.exists():
                (DIST / "images" / "legacy").mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, DIST / "images" / "legacy" / img)

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True, trim_blocks=True, lstrip_blocks=True)
    env.globals["socials"] = [s for s in SOCIALS if s["url"]]
    version = dt.datetime.now().strftime("%Y%m%d%H%M")
    common = {"base": base, "nav": NAV, "linkedin": LINKEDIN, "year": dt.date.today().year, "version": version, "kit_form": KIT_FORM_ID,
              "ask_endpoint": ASK_FORM_ENDPOINT,
              "categories": [], "jsonld": []}
    recd = yaml.safe_load((ROOT / "content" / "recommendations.yaml").read_text(encoding="utf-8"))
    import base64
    for x in recd["items"]:
        x["img"] = "data:image/jpeg;base64," + base64.b64encode((ROOT / "public" / "images" / "recs" / f"{x['id']}.jpg").read_bytes()).decode()
        assert x["quote"].strip("…") in " ".join(x["text"].split()), f"quote not verbatim: {x['id']}"
    common["recommendations"] = recd

    for c in CATEGORIES:
        c["posts"] = [p for p in posts if p["category_key"] == c["key"]]
    common["categories"] = CATEGORIES

    featured = load_featured()
    person = {"@type": "Person", "@id": f"{SITE}/about#matt", "name": "Matt Barber", "url": f"{SITE}/about",
              "sameAs": [LINKEDIN, "https://www.industrysagemedia.com/matt-barber",
                         "https://manufacturingdigital.com/articles/lifetime-of-achievement-matt-barber"],
              "jobTitle": "VP & General Manager, MES", "worksFor": {"@type": "Organization", "name": "Infor"},
              "knowsAbout": ["Manufacturing Execution Systems (MES)", "Manufacturing Operations Management (MOM)",
                             "Smart factory", "Shopfloor AI", "Connected worker", "ISA-95", "OEE",
                             "ERP and MES integration", "Industry 4.0", "Manufacturing digital transformation"],
              "image": f"{SITE}/images/matt-barber.jpg",
              "award": "Infor Circle of Excellence, 2024", "alumniOf": [{"@type": "CollegeOrUniversity", "name": "The University of Sheffield"}, {"@type": "CollegeOrUniversity", "name": "The London School of Economics and Political Science"}], "hasOccupation": {"@type": "Occupation", "name": "MES software executive",
              "description": "Involved in countless MES projects across food and beverage, automotive, packaging, metal and plastics fabrication and industrial manufacturing."}}
    person_full = {**person, "description": "Matt Barber studied computer science at the University of Sheffield, started as an MES software engineer and has been VP & General Manager, MES at Infor since 2024. He writes Shopfloor Matters, about the smart factory, shopfloor AI and MES/MOM.",
                   "subjectOf": [{"@type": {"podcast": "PodcastEpisode", "webinar": "CreativeWork"}.get(it.get("type"), "Article"),
                                  "name": it["title"], "url": next((l["url"] for l in it.get("links", [])), None),
                                  "publisher": {"@type": "Organization", "name": it.get("outlet", "")}}
                                 for it in featured["items"] if it.get("links")]}
    org = {"@type": "Organization", "name": "Shopfloor Matters", "url": SITE, "logo": f"{SITE}/favicon.svg"}

    def write(rel, tpl, **ctx):
        out = DIST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        data = {**common, **ctx}
        data.setdefault("og_image", f"{SITE}/images/og/home.png")
        page = env.get_template(tpl).render(**data)
        if relative:
            page = relativise(page, rel)
        out.write_text(page, encoding="utf-8")

    from markupsafe import Markup

    series = sorted([p for p in posts if p["series"] == "functionality"], key=lambda p: p["order"])
    start = sorted([p for p in posts if p["start"]], key=lambda p: p["start"])
    total_words = sum(p["words"] for p in posts)

    paths, paths_home = load_paths(posts)
    glossary = load_glossary(posts)
    autolink_glossary(posts, glossary, base)
    glossary_mentions(posts, glossary)
    tools, _caps_src = load_tools(posts)
    caps = _caps_src["data"]["capabilities"]
    audiences = load_audiences(posts, glossary, tools, caps, base)
    # which roles each article and tool is recommended for (from the role explorer)
    _ro = yaml.safe_load((ROOT / "content" / "roles.yaml").read_text(encoding="utf-8"))
    _gc = {g["id"]: g["color"] for g in _ro["groups"]}
    _pmap, _tmap = {}, {}
    for r in _ro["roles"]:
        ref = {"id": r["id"], "name": r["name"], "color": _gc[r["group"]]}
        slugs = list(r["reads"]) + [_ro["apps"][k]["read"] for k in r["why"]]
        for s in dict.fromkeys(slugs):
            _pmap.setdefault(s, []).append(ref)
        for tid in ([r["tool"]] if r.get("tool") else []) + r.get("also_tools", []):
            _tmap.setdefault(tid, []).append(ref)
    for p in posts:
        p["for_roles"] = _pmap.get(p["slug"], [])
    for x in tools:
        x["for_roles"] = _tmap.get(x["id"], [])
    common["tools"] = tools
    common["ttt_block"] = Markup(blocks.get("time-to-truth", ""))
    common["audiences"] = audiences
    common["paths_home"] = paths_home
    common["paths_json"] = json.dumps([{"id": p["id"], "title": p["title"], "slugs": p["slugs"],
                                        "titles": [st["post"]["short"] for st in p["stations"]]} for p in paths], separators=(",", ":"))
    common["featured_carousel"] = featured["carousel"]
    common["show_speaking"] = SHOW_SPEAKING
    common["show_tools"] = SHOW_TOOLS
    common["enabled_tools"] = ENABLED_TOOLS

    # home
    write("index.html", "home.html", active="home",
          seo_title="Shopfloor Matters | The smart factory, shopfloor AI and MES",
          description="Practical, vendor-neutral writing on the smart factory and shopfloor AI, and the MES and MOM systems underneath them. By Matt Barber.",
          canonical=f"{SITE}/", posts=posts, series=series, start=start, latest=posts[:5], imap_block=blocks.get("integration-map", ""),
          start_minutes=sum(p["read_time"] for p in start), total_words_k=round(total_words / 1000),
          jsonld=[jsonld({"@context": "https://schema.org", "@type": "WebSite", "name": "Shopfloor Matters", "url": SITE,
                          "description": "Practical guides to MES, MOM and smart manufacturing", "author": person, "publisher": org})])

    # all articles
    write("articles.html", "list.html", active="articles",
          seo_title="All articles | Shopfloor Matters", description="Every article on the smart factory, shopfloor AI, implementation and the MES and MOM foundations underneath them.",
          canonical=f"{SITE}/articles", eyebrow=f"Library / {len(posts)} articles", heading="Every article, in one place",
          kicker="Guides, explainers and opinion on the smart factory, shopfloor AI and MES/MOM. Newest first.",
          all_count=len(posts), featured=posts[0], tag_list=tag_list,
          groups=[g for g in ({"label": "The essential guides", "posts": [q for q in posts[1:] if q.get("guide")]},
                              {"label": "Everything else", "posts": [q for q in posts[1:] if not q.get("guide")]}) if g["posts"]])

    # categories (same URLs as the Wix site)
    for c in CATEGORIES:
        cposts = c["posts"]
        groups = []
        if c["key"] == "education":
            groups.append({"label": "Start here", "posts": start, "numbered": True})
            groups.append({"label": "Learning path: MES functionality in depth", "posts": series, "numbered": True})
            rest = [p for p in cposts if p not in start and p not in series]
            if rest:
                groups.append({"label": "More fundamentals", "posts": rest})
        else:
            groups.append({"label": None, "posts": cposts})
        write(f"{c['slug']}.html", "list.html", active=c["slug"],
              seo_title=f"{c['name']} | Shopfloor Matters", description=c["kicker"][:158],
              canonical=f"{SITE}/{c['slug']}", eyebrow=f"{c['eyebrow']} / {len(cposts)} articles",
              heading=c["name"], kicker=c["kicker"], all_count=len(posts), featured=None, groups=groups,
              og_image=f"{SITE}/images/og/page-{c['art']}.png")

    # posts
    for p in posts:
        same = [q for q in posts if q is not p]
        if p["series"]:
            seq = series
        elif p["start"]:
            seq = start
        else:
            seq = [q for q in reversed(posts) if q["category_key"] == p["category_key"]]
        i = seq.index(p)
        prev = seq[i - 1] if i > 0 else None
        nxt = seq[i + 1] if i + 1 < len(seq) else None
        mine = set(p["tag_ids"].split())
        pool = [q for q in same if q not in (prev, nxt)]
        related = sorted(pool, key=lambda q: -len(mine & set(q["tag_ids"].split())))[:3]
        ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"], "description": p["description"],
              "datePublished": p["published_iso"], "dateModified": p["updated_iso"], "author": person, "publisher": org,
              "mainEntityOfPage": p["canonical"], "url": p["canonical"], "image": f"{SITE}/images/og/{p['slug']}.png",
              "articleSection": p["category_label"], "keywords": ", ".join(t["name"] for t in p["tags"]), "wordCount": p["words"], "inLanguage": "en-GB"}
        if p["summary"]:
            ld["abstract"] = p["summary"]
        extra_ld = []
        if p["faq"]:
            extra_ld.append(jsonld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in p["faq"]]}))
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": p["category_label"], "item": f"{SITE}/{p['category_slug']}"},
            {"@type": "ListItem", "position": 3, "name": p["short"], "item": p["canonical"]}]}
        write(f"post/{p['slug']}.html", "post.html", active=p["category_slug"], progress=True,
              seo_title=(p["title"] if len(p["title"]) > 42 else f"{p['title']} | Shopfloor Matters"), og_title=p["title"], og_type="article",
              description=p["description"], canonical=p["canonical"], og_image=f"{SITE}/images/og/{p['slug']}.png",
              p=p, body=Markup(p["body"]), toc=p["toc"], series_posts=series if p["series"] else None,
              prev=prev, next=nxt, related=related, jsonld=[jsonld(ld), jsonld(crumbs)] + extra_ld)

    # learning paths
    write("paths/index.html", "paths.html", active="paths", seo_title="Learning paths | Shopfloor Matters",
          description="Six guided learning paths through the smart factory, MES/MOM, shopfloor AI and implementation. Articles in the right order, with your progress saved as you read.",
          canonical=f"{SITE}/paths/", paths=paths, og_image=f"{SITE}/images/og/page-education.png")
    for path in paths:
        write(f"paths/{path['id']}.html", "path.html", active="paths", seo_title=f"{path['title']}: learning path | Shopfloor Matters",
              description=f"{path['blurb']} {path['n']} articles, about {path['minutes']} minutes.",
              canonical=f"{SITE}/paths/{path['id']}", path=path, integration_map=blocks.get("integration-map", ""), og_image=f"{SITE}/images/og/{path['image']}.png",
              jsonld=[jsonld({"@context": "https://schema.org", "@type": "ItemList", "name": path["title"],
                              "itemListElement": [{"@type": "ListItem", "position": s["n"], "url": s["post"]["canonical"], "name": s["post"]["title"]} for s in path["stations"]]})])

    # featured
    kinds = [("podcast", "Podcasts", "podcasts"), ("article", "Press", "press features"), ("webinar", "Webinars", "webinar")]
    counts = [{"key": k, "short": sh, "label": lab, "n": sum(1 for i in featured["items"] if i["type"] == k)} for k, sh, lab in kinds]
    write("featured.html", "featured.html", active="featured", seo_title="Podcasts, interviews and press | Shopfloor Matters",
          description="Matt Barber on podcasts, webinars and in the trade press, talking MES, the smart factory and shopfloor AI. Watch, listen or read.",
          canonical=f"{SITE}/featured", items=featured["items"], counts=[c for c in counts if c["n"]], og_image=f"{SITE}/images/og/page-about.png",
          jsonld=[jsonld({"@context": "https://schema.org", "@type": "ItemList", "name": "Matt Barber in the media",
                          "itemListElement": [{"@type": "ListItem", "position": n + 1, "url": i["links"][0]["url"], "name": f"{i['title']} ({i['outlet']})"}
                                              for n, i in enumerate(featured["items"])]})])

    # about / contact / 404
    about = (ROOT / "content" / "pages" / "about.html").read_text(encoding="utf-8").replace("{{base}}", base)
    write("about.html", "page.html", active="about", seo_title="About Matt Barber | Shopfloor Matters",
          description="Matt Barber went from writing MES code to running a global MES business. Why he writes about the smart factory and shopfloor AI.",
          canonical=f"{SITE}/about", eyebrow="About", heading="Hi, I'm Matt.",
          kicker="I've spent my career on the shopfloor side of software. This is where I write down what I've learnt about making factories smarter.",
          content=Markup(about), show_cta=True, show_recs=True, og_image=f"{SITE}/images/og/page-about.png",
          jsonld=[jsonld({"@context": "https://schema.org", "@type": "ProfilePage", "mainEntity": person_full})])
    contact = (ROOT / "content" / "pages" / "contact.html").read_text(encoding="utf-8").replace("{{base}}", base).replace("{{linkedin}}", LINKEDIN)
    write("contact.html", "page.html", active="contact", seo_title="Contact | Shopfloor Matters",
          description="Get in touch with Matt Barber about the smart factory, shopfloor AI, MES and MOM, or something you've read here.",
          canonical=f"{SITE}/contact", eyebrow="Contact", heading="Let's talk shopfloor",
          kicker="The quickest way to reach me is a message on LinkedIn. I read everything, even if replies sometimes take a few days.",
          actions=Markup(f'<a class="btn" href="{LINKEDIN}" target="_blank" rel="me noopener">Message me on LinkedIn →</a>'),
          content=Markup(contact), show_cta=False, ask="contact", tools_js=True)
    write("subscribe.html", "page.html", active="subscribe", seo_title="Subscribe to the newsletter | Shopfloor Matters",
          description="A practical newsletter on the smart factory, shopfloor AI and MES/MOM. New articles and lessons from real implementations, straight to your inbox.",
          canonical=f"{SITE}/subscribe", eyebrow="Newsletter", heading="Smart factory thinking, in your inbox",
          kicker="New articles and practical lessons on the smart factory, shopfloor AI and MES/MOM. Written from real implementations. No hype, no spam.",
          actions=Markup(env.get_template("macros.html").module.signup(base, KIT_FORM_ID, big=True)),
          content=Markup((ROOT / "content" / "pages" / "subscribe.html").read_text(encoding="utf-8")), show_cta=False)
    privacy = (ROOT / "content" / "pages" / "privacy.html").read_text(encoding="utf-8").replace("{{base}}", base)
    write("privacy.html", "page.html", active=None, seo_title="Privacy | Shopfloor Matters",
          description="How Shopfloor Matters handles your data, including newsletter sign-ups.",
          canonical=f"{SITE}/privacy", eyebrow="Privacy", heading="Your data, plainly",
          kicker="What I collect, why, and how to get it removed.", content=Markup(privacy), show_cta=False)
    write("404.html", "page.html", active=None, seo_title="Page not found | Shopfloor Matters", description="This page doesn't exist.",
          canonical=f"{SITE}/404", eyebrow="404", heading="This line has stopped.", noindex=True,
          kicker="The page you were looking for isn't here. It may have moved when the site was rebuilt.",
          actions=Markup(f'<a class="btn" href="{base}/articles">Browse all articles →</a><a class="btn ghost" href="{base}/">Home</a>'),
          content=Markup(""), show_cta=False)

    # redirects for old Wix URLs
    for old, new in REDIRECTS.items():
        out = DIST / f"{old}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        page = env.get_template("redirect.html").render(target=f"{base}{new}", canonical=f"{SITE}{new}")
        if relative:
            page = relativise(page, f"{old}.html").replace('"@REL@/', '"' + ("/".join([".."] * old.count("/")) or ".") + "/").replace(new + '"', new + '.html"')
        out.write_text(page, encoding="utf-8")

    # FAQ hub
    by_slug_all = {p["slug"]: p for p in posts}
    faq_topics, faq_all = [], []
    for t in FAQ_TOPICS:
        items = [{"q": f["q"], "a": f["a"], "post": by_slug_all[sl]} for sl in t["slugs"] if sl in by_slug_all for f in by_slug_all[sl]["faq"]]
        if items:
            faq_topics.append({**t, "items": items})
            faq_all += items
    if faq_all:
        write("faq/index.html", "faq.html", active="faq", seo_title="MES, MOM and smart factory FAQ | Shopfloor Matters",
              description=f"Straight answers to {len(faq_all)} common questions about MES, MOM, ERP, OEE, the smart factory and shopfloor systems, each linked to the full article.",
              canonical=f"{SITE}/faq/", topics=faq_topics, total=len(faq_all),
              jsonld=[jsonld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                  {"@type": "Question", "name": i["q"], "acceptedAnswer": {"@type": "Answer", "text": i["a"], "url": i["post"]["canonical"]}} for i in faq_all]})])

    # glossary
    if glossary:
        gset = {"@type": "DefinedTermSet", "@id": f"{SITE}/glossary/#set", "name": "Shopfloor Matters glossary", "url": f"{SITE}/glossary/"}
        for g in glossary:
            g["letter"] = "0–9" if g["term"][0].isdigit() else g["term"][0].upper()
        letters = sorted({g["letter"] for g in glossary}, key=lambda x: (x != "0–9", x))
        write("glossary/index.html", "glossary.html", active="glossary", seo_title="Smart factory and MES glossary | Shopfloor Matters",
              description="Plain-English definitions of MES, MOM, OEE, ISA-95, UNS and the other terms you'll hear in smart factory and shopfloor projects.",
              canonical=f"{SITE}/glossary/", terms=glossary, letters=letters,
              jsonld=[jsonld({"@context": "https://schema.org", **gset, "hasDefinedTerm": [
                  {"@type": "DefinedTerm", "name": g["term"], "description": g["short"], "url": f"{SITE}/glossary/{g['slug']}",
                   **({"alternateName": g["stands"]} if g.get("stands") else {})} for g in glossary]})])
        for g in glossary:
            name = g["term"] + (f" ({g['stands']})" if g.get("stands") else "")
            write(f"glossary/{g['slug']}.html", "term.html", active="glossary", seo_title=f"{name}: meaning in manufacturing | Shopfloor Matters",
                  description=g["short"], canonical=f"{SITE}/glossary/{g['slug']}", g=g,
                  jsonld=[jsonld({"@context": "https://schema.org", "@type": "DefinedTerm", "name": g["term"], "description": g["short"] + " " + g.get("body", ""),
                                  "url": f"{SITE}/glossary/{g['slug']}", "inDefinedTermSet": gset,
                                  **({"alternateName": g["stands"]} if g.get("stands") else {})}),
                          jsonld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                              {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
                              {"@type": "ListItem", "position": 2, "name": "Glossary", "item": f"{SITE}/glossary/"},
                              {"@type": "ListItem", "position": 3, "name": g["term"]}]})])

    # tools
    tool_list = {"@context": "https://schema.org", "@type": "ItemList", "name": "Shopfloor Matters tools and templates",
                 "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/tools/{x['id']}", "name": x["title"]} for i, x in enumerate(tools)]}
    if SHOW_TOOLS: write("tools/index.html", "tools-hub.html", active="tools", seo_title="Free smart factory and MES tools | Shopfloor Matters",
          description="Free, vendor-neutral smart factory tools: " + "; ".join(x["title"].rstrip("?") for x in tools) + ".",
          canonical=f"{SITE}/tools/", icons=ICONS, tools_js=True, og_image=f"{SITE}/images/og/page-advice.png", jsonld=[jsonld(tool_list)])
    for x in (tools if SHOW_TOOLS else []):
        if x["kind"] == "tool":
            ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": x["title"], "url": f"{SITE}/tools/{x['id']}",
                  "description": x["blurb"], "applicationCategory": "BusinessApplication", "operatingSystem": "Any (runs in the browser)",
                  "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "GBP"}, "author": person, "inLanguage": "en-GB"}
        else:
            ld = {"@context": "https://schema.org", "@type": "DigitalDocument", "name": x["title"], "url": f"{SITE}/tools/{x['id']}",
                  "description": x["blurb"], "encodingFormat": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                  "isAccessibleForFree": True, "author": person, "inLanguage": "en-GB"}
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Tools", "item": f"{SITE}/tools/"},
            {"@type": "ListItem", "position": 3, "name": x["title"]}]}
        write(f"tools/{x['id']}.html", "tool.html", active="tools", seo_title=f"{x['title']} | Shopfloor Matters", og_title=x["title"],
              description=x["blurb"], canonical=f"{SITE}/tools/{x['id']}", t=x, tools_js=True,
              og_image=f"{SITE}/images/og/page-advice.png", jsonld=[jsonld(ld), jsonld(crumbs)])

    # compare hub
    cmp_cfg = yaml.safe_load((ROOT / "content" / "compare.yaml").read_text(encoding="utf-8"))
    by_slug = {q["slug"]: q for q in posts}
    def first_sentence(s):
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", (s or "").strip())
        out = parts[0]
        if len(out) < 110 and len(parts) > 1:
            out += " " + parts[1]
        return out
    compare = {"intro": cmp_cfg["intro"], "groups": []}
    for g in cmp_cfg["groups"]:
        items = [{"slug": s, "short": by_slug[s]["short"], "title": by_slug[s]["title"], "canonical": by_slug[s]["canonical"],
                  "answer": first_sentence(by_slug[s]["summary"]) or by_slug[s]["description"]} for s in g["slugs"] if s in by_slug]
        compare["groups"].append({"name": g["name"], "posts": items})
    cmp_items = [x for g in compare["groups"] for x in g["posts"]]
    write("compare/index.html", "compare.html", active="compare", seo_title="MES compared: MES vs ERP, MOM, SCADA and more | Shopfloor Matters",
          description="Straight answers to the most common MES comparisons: MES vs ERP, MOM, MRP, SCADA, historian, IIoT, QMS and more, each linked to the full article.",
          canonical=f"{SITE}/compare/", og_image=f"{SITE}/images/og/page-education.png", compare=compare,
          jsonld=[jsonld({"@context": "https://schema.org", "@type": "CollectionPage", "name": "MES compared", "url": f"{SITE}/compare/",
                          "author": person, "inLanguage": "en-GB",
                          "mainEntity": {"@type": "ItemList", "itemListElement": [
                              {"@type": "ListItem", "position": i + 1, "url": x["canonical"], "name": x["title"]} for i, x in enumerate(cmp_items)]}})])

    # role explorer
    ro = yaml.safe_load((ROOT / "content" / "roles.yaml").read_text(encoding="utf-8"))
    import math
    keys = list(ro["apps"].keys())
    n = len(keys)
    def pt(i, frac, rad=122):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return 150 + rad * frac * math.cos(a), 150 + rad * frac * math.sin(a)
    axes = []
    for i, k in enumerate(keys):
        x, y = pt(i, 1)
        lx, ly = pt(i, 1, 148)
        anchor = "middle" if abs(lx - 150) < 12 else ("start" if lx > 150 else "end")
        axes.append({"key": k, "label": ro["apps"][k]["short"], "x": f"{x:.1f}", "y": f"{y:.1f}", "lx": f"{lx:.1f}", "ly": f"{ly + 4:.1f}", "anchor": anchor})
    rings = [" ".join("%.1f,%.1f" % pt(i, f) for i in range(n)) for f in (0.2, 0.4, 0.6, 0.8, 1.0)]
    gl_slugs = {g["slug"] for g in glossary}
    tools_by = {x["id"]: x for x in tools}
    paths_by = {x["id"]: x for x in paths}
    aud_by = {a["id"]: a for a in audiences}
    groups = {g["id"]: dict(g, roles=[]) for g in ro["groups"]}
    hz = ["Years", "Quarters", "Weeks", "Shifts", "Minutes"]
    roles_by = {}
    for r in ro["roles"]:
        g = groups[r["group"]]
        r["color"], r["group_name"] = g["color"], g["name"]
        sc = r["scores"]
        pts = [pt(i, sc[k] / 5) for i, k in enumerate(keys)]
        r["radar_points"] = " ".join("%.1f,%.1f" % p for p in pts)
        r["radar_dots"] = [{"x": f"{x:.1f}", "y": f"{y:.1f}"} for x, y in pts]
        r["cares"] = [{"label": c[0], "slug": c[1] if c[1] in gl_slugs else None} for c in r["cares"]]
        r["top_apps"] = [dict(ro["apps"][k], key=k, score=sc[k], why=w, post=by_slug.get(ro["apps"][k]["read"])) for k, w in r["why"].items()]
        r["read_posts"] = [by_slug[s] for s in r["reads"] if s in by_slug]
        r["tool_obj"], r["path_obj"], r["for_obj"] = tools_by.get(r.get("tool")), paths_by.get(r.get("path")), aud_by.get(r.get("for"))
        r["also_tool_objs"] = [tools_by[x] for x in r.get("also_tools", []) if x in tools_by]
        r["horizon_text"] = hz[r["horizon"][0]].lower() + ("" if r["horizon"][0] == r["horizon"][1] else " to " + hz[r["horizon"][1]].lower())
        g["roles"].append(r)
        roles_by[r["id"]] = r
    ev = ro["one_event"]
    ev["views"] = [{"id": v[0], "name": roles_by[v[0]]["name"], "color": roles_by[v[0]]["color"], "text": v[1]} for v in ev["views"]]
    ro.update(groups=list(groups.values()), horizons=hz, radar={"axes": axes, "rings": rings}, default="plant-manager")
    ro["js"] = {"roles": [{"id": r["id"], "name": r["name"], "group": r["group_name"], "points": r["radar_points"]} for r in ro["roles"]]}
    write("roles/index.html", "roles.html", active="roles", seo_title="What MES/MOM means for your role: CEO to operator | Shopfloor Matters",
          description="Pick your role, from CEO and CFO to plant manager, quality manager and operator, to see what you're measured on, what gets in the way, and which shopfloor applications matter most to you.",
          canonical=f"{SITE}/roles/", og_image=f"{SITE}/images/og/page-education.png", ro=ro,
          jsonld=[jsonld({"@context": "https://schema.org", "@type": "WebPage", "name": "Role explorer: what MES/MOM means for your role", "url": f"{SITE}/roles/",
                          "author": person, "inLanguage": "en-GB",
                          "about": [{"@type": "Occupation", "name": r["title"]} for r in ro["roles"]]})])

    # industries and roles
    write("for/index.html", "audiences.html", active="for", seo_title="MES and the smart factory by industry and role | Shopfloor Matters",
          description="The smart factory and MES/MOM for food and beverage, automotive, packaging, metal fabrication and plastics, and for plant, IT and quality leaders.",
          canonical=f"{SITE}/for/", og_image=f"{SITE}/images/og/page-education.png")
    for a in audiences:
        lds = [jsonld({"@context": "https://schema.org", "@type": "WebPage", "name": a["title"], "url": f"{SITE}/for/{a['id']}", "description": a["kicker"],
                       "author": person, "inLanguage": "en-GB",
                       "about": {"@type": "Thing", "name": a["short"]}, "audience": {"@type": "Audience", "audienceType": a["short"]}}),
               jsonld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                   {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
                   {"@type": "ListItem", "position": 2, "name": "Industries and roles", "item": f"{SITE}/for/"},
                   {"@type": "ListItem", "position": 3, "name": a["short"]}]})]
        if a.get("faq"):
            lds.append(jsonld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in a["faq"]]}))
        write(f"for/{a['id']}.html", "audience.html", active="for", seo_title=f"{a['seo']} | Shopfloor Matters", og_title=a["title"],
              description=a["kicker"][:158], canonical=f"{SITE}/for/{a['id']}", a=a, tools_js=True,
              og_image=f"{SITE}/images/og/page-education.png", jsonld=lds)

    # speaking and Ask Matt
    sp = yaml.safe_load((ROOT / "content" / "speaking.yaml").read_text(encoding="utf-8"))
    if SHOW_SPEAKING: write("speaking.html", "speaking.html", active="about", seo_title="Speaking: Matt Barber on MES, the smart factory and shopfloor AI | Shopfloor Matters",
          description="Invite Matt Barber to speak on the smart factory, shopfloor AI and MES/MOM. Talk topics, formats, recent appearances, bio and photo.",
          canonical=f"{SITE}/speaking", sp=sp, appearances=featured["items"][:6], tools_js=True, og_image=f"{SITE}/images/og/page-about.png",
          jsonld=[jsonld({"@context": "https://schema.org", "@type": "ProfilePage", "url": f"{SITE}/speaking", "mainEntity": person_full})])
    write("ask.html", "page.html", active="contact", seo_title="Ask Matt a question | Shopfloor Matters",
          description="Ask Matt Barber a question about MES, MOM, the smart factory or shopfloor AI. Useful questions become articles and FAQ answers, anonymised.",
          canonical=f"{SITE}/ask", eyebrow="Ask Matt", heading="Ask me anything about the shopfloor",
          kicker="A question about your project, or about something you've read here. Peer to peer, no sales call.",
          content=Markup(""), show_cta=False, ask="ask", tools_js=True)

    # sitemap, robots
    urls = [(f"{SITE}/", posts[0]["updated"]), (f"{SITE}/articles", posts[0]["updated"]), (f"{SITE}/about", None), (f"{SITE}/subscribe", None)]
    urls += [(f"{SITE}/{c['slug']}", None) for c in CATEGORIES]
    urls += [(f"{SITE}/featured", None), (f"{SITE}/paths/", None)] + [(f"{SITE}/paths/{x['id']}", None) for x in paths]
    urls += [(f"{SITE}/faq/", None), (f"{SITE}/glossary/", None)] + [(f"{SITE}/glossary/{g['slug']}", None) for g in glossary]
    if SHOW_TOOLS: urls += [(f"{SITE}/tools/", None)] + [(f"{SITE}/tools/{x['id']}", None) for x in tools]
    urls += [(f"{SITE}/for/", None)] + [(f"{SITE}/for/{a['id']}", None) for a in audiences]
    urls += ([(f"{SITE}/speaking", None)] if SHOW_SPEAKING else []) + [(f"{SITE}/ask", None), (f"{SITE}/compare/", None), (f"{SITE}/roles/", None)]
    urls += [(p["canonical"], p["updated"]) for p in posts]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, d in urls:
        sm.append(f"  <url><loc>{u}</loc>" + (f"<lastmod>{d.date().isoformat()}</lastmod>" if d else "") + "</url>")
    sm.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai", "PerplexityBot",
            "Perplexity-User", "Google-Extended", "Applebot-Extended", "CCBot", "Bingbot", "Googlebot", "meta-externalagent", "Amazonbot", "cohere-ai"]
    robots = ["# Shopfloor Matters welcomes search engines and AI assistants.", "# Quote freely with attribution: Matt Barber, Shopfloor Matters (shopfloormatters.com).", ""]
    for b in bots:
        robots += [f"User-agent: {b}", "Allow: /", ""]
    robots += ["User-agent: *", "Allow: /", "", f"Sitemap: {SITE}/sitemap.xml", ""]
    (DIST / "robots.txt").write_text("\n".join(robots), encoding="utf-8")
    write_llms(posts, paths, glossary, tools, audiences)
    write_feeds(posts, paths)

    (DIST / ".nojekyll").write_text("")
    if relative:
        for f in DIST.rglob("*.html"):
            depth = len(f.relative_to(DIST).parts) - 1
            t = f.read_text(encoding="utf-8")
            if "@REL@" in t:
                f.write_text(t.replace("@REL@", "/".join([".."] * depth) or "."), encoding="utf-8")
    print(f"Built {len(posts)} posts into {DIST} (base='{base}')")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--relative", action="store_true", help="relative .html links, for previewing as static files")
    ap.add_argument("--all", action="store_true", help="include articles scheduled for future weeks")
    args = ap.parse_args()
    build(args.base, args.relative, args.all)
