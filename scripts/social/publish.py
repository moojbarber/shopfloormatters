#!/usr/bin/env python3
"""Publish approved, due posts from social/queue to LinkedIn, X and Instagram.

Runs every 15 minutes from GitHub Actions (.github/workflows/social.yml).
A post goes out only when ALL of these are true:
  - its queue file says `approved: true`
  - that platform's scheduled time (UK time) has passed, within the last 36 hours
  - that platform hasn't already been posted (social/state/posted.json)
  - the platform doesn't still need your own words (`needs_text: true`)
Failures never stop the other platforms. Each failure is recorded and raised as
a GitHub issue, so you get an email.

Secrets (GitHub Actions secrets):
  LINKEDIN_TOKEN                     LinkedIn member access token (renew every 60 days)
  X_API_KEY, X_API_SECRET            X app consumer keys
  X_ACCESS_TOKEN, X_ACCESS_SECRET    X user access token and secret (don't expire)
  IG_TOKEN                           Instagram long-lived user token (first one only)
  SOCIAL_KEY                         any long passphrase; encrypts refreshed tokens in the repo

Usage:
  python scripts/social/publish.py [--dry-run] [--now 2026-10-27T09:00]
  python scripts/social/publish.py refresh-ig
"""
import base64
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse

import requests
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE = os.path.join(ROOT, "social", "queue")
STATE = os.path.join(ROOT, "social", "state", "posted.json")
IG_TOKEN_FILE = os.path.join(ROOT, "social", "state", "ig_token.enc")
REPO = os.environ.get("GITHUB_REPOSITORY", "moojbarber/shopfloormatters")
MEDIA_BASE = os.environ.get("MEDIA_BASE") or f"https://raw.githubusercontent.com/{REPO}/main/"
LI_VERSION = os.environ.get("LINKEDIN_VERSION", "202609")
IG_API = "https://graph.instagram.com/" + os.environ.get("IG_VERSION", "v23.0")
try:
    from zoneinfo import ZoneInfo
    UK = ZoneInfo("Europe/London")
except Exception:  # pragma: no cover
    UK = dt.timezone.utc


class Skip(Exception):
    """Credentials missing: skip this platform quietly."""


# ------------------------------------------------------------------ helpers
def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(s, open(STATE, "w"), indent=1, sort_keys=True)


def when(item, platform):
    d = dt.date.fromisoformat(str(item["date"]))
    hh, mm = str(item[platform].get("at", "09:00")).split(":")
    return dt.datetime(d.year, d.month, d.day, int(hh), int(mm), tzinfo=UK)


def public_url(path):
    return MEDIA_BASE + urllib.parse.quote(path)


def fernet():
    key = os.environ.get("SOCIAL_KEY")
    if not key:
        return None
    from cryptography.fernet import Fernet
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()))


def check(r, what):
    if r.status_code >= 300:
        raise RuntimeError(f"{what}: HTTP {r.status_code} {r.text[:500]}")
    return r


# ------------------------------------------------------------------ LinkedIn
LI_RESERVED = re.compile(r"([\\|{}@\[\]()<>*_~])")


def li_text(text):
    """LinkedIn 'little text' format: escape reserved characters, keep #hashtags as real hashtags."""
    out = []
    for token in re.split(r"(#\w+)", text):
        if re.fullmatch(r"#\w+", token):
            out.append("{hashtag|\\#|" + token[1:] + "}")
        else:
            out.append(LI_RESERVED.sub(r"\\\1", token).replace("#", "\\#"))
    return "".join(out)


class LinkedIn:
    def __init__(self, dry):
        self.dry = dry
        self.token = os.environ.get("LINKEDIN_TOKEN")
        if not self.token and not dry:
            raise Skip("LINKEDIN_TOKEN not set")
        self.h = {"Authorization": f"Bearer {self.token}", "Linkedin-Version": LI_VERSION,
                  "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"}
        self._urn = None

    def urn(self):
        if not self._urn:
            r = check(requests.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {self.token}"}, timeout=30), "LinkedIn userinfo")
            self._urn = "urn:li:person:" + r.json()["sub"]
        return self._urn

    def upload_document(self, path):
        r = check(requests.post("https://api.linkedin.com/rest/documents?action=initializeUpload", headers=self.h,
                                json={"initializeUploadRequest": {"owner": self.urn()}}, timeout=30), "LinkedIn document init")
        v = r.json()["value"]
        with open(os.path.join(ROOT, path), "rb") as f:
            check(requests.put(v["uploadUrl"], data=f, headers={"Authorization": f"Bearer {self.token}"}, timeout=120), "LinkedIn document upload")
        urn = v["document"]
        for _ in range(30):
            s = requests.get("https://api.linkedin.com/rest/documents/" + urllib.parse.quote(urn), headers=self.h, timeout=30)
            if s.ok and s.json().get("status") == "AVAILABLE":
                break
            time.sleep(4)
        return urn

    def upload_image(self, path):
        r = check(requests.post("https://api.linkedin.com/rest/images?action=initializeUpload", headers=self.h,
                                json={"initializeUploadRequest": {"owner": self.urn()}}, timeout=30), "LinkedIn image init")
        v = r.json()["value"]
        with open(os.path.join(ROOT, path), "rb") as f:
            check(requests.put(v["uploadUrl"], data=f, headers={"Authorization": f"Bearer {self.token}"}, timeout=120), "LinkedIn image upload")
        return v["image"]

    def post(self, item):
        li = item["linkedin"]
        body = {"author": None, "commentary": li_text(li["text"]), "visibility": "PUBLIC",
                "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
                "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
        if li.get("poll"):
            body["content"] = {"poll": {"question": li["poll"]["question"],
                                        "options": [{"text": o[:30]} for o in li["poll"]["options"]],
                                        "settings": {"duration": "THREE_DAYS"}}}
        if self.dry:
            body["author"] = "urn:li:person:DRYRUN"
            if li.get("document") and not li.get("poll"):
                body["content"] = {"media": {"title": li.get("document_title", item["title"]), "id": "urn:li:document:DRYRUN"}}
            elif li.get("image"):
                body["content"] = {"media": {"altText": item["title"], "id": "urn:li:image:DRYRUN"}}
            print("  [LinkedIn] POST /rest/posts", json.dumps(body)[:300], "...")
            if li.get("comment"):
                print("  [LinkedIn] first comment:", li["comment"])
            return {"id": "dry-run"}
        body["author"] = self.urn()
        if li.get("document") and not li.get("poll"):
            body["content"] = {"media": {"title": li.get("document_title", item["title"]), "id": self.upload_document(li["document"])}}
        elif li.get("image") and not li.get("poll"):
            body["content"] = {"media": {"altText": item["title"], "id": self.upload_image(li["image"])}}
        r = check(requests.post("https://api.linkedin.com/rest/posts", headers=self.h, json=body, timeout=60), "LinkedIn post")
        post_urn = r.headers.get("x-restli-id")
        result = {"id": post_urn}
        if li.get("comment") and post_urn:
            time.sleep(5)
            c = requests.post(f"https://api.linkedin.com/rest/socialActions/{urllib.parse.quote(post_urn)}/comments", headers=self.h,
                              json={"actor": self.urn(), "object": post_urn, "message": {"text": li["comment"]}}, timeout=30)
            if not c.ok:
                result["warning"] = f"Post is live, but the first comment failed (HTTP {c.status_code}). Paste it manually: {li['comment']}"
        return result


# ------------------------------------------------------------------ X
class X:
    def __init__(self, dry):
        self.dry = dry
        keys = [os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")]
        if not all(keys) and not dry:
            raise Skip("X keys not set")
        if all(keys):
            from requests_oauthlib import OAuth1Session
            self.s = OAuth1Session(*keys)

    def post(self, item):
        x = item["x"]
        prev, ids = None, []
        for i, text in enumerate(x["posts"]):
            body = {"text": text}
            if prev:
                body["reply"] = {"in_reply_to_tweet_id": prev}
            if i == 0 and x.get("poll"):
                body["poll"] = {"options": [o[:25] for o in x["poll"][:4]], "duration_minutes": 1440}
            if self.dry:
                print(f"  [X] POST /2/tweets {json.dumps(body)[:200]}")
                prev = f"dry{i}"
                ids.append(prev)
                continue
            r = check(self.s.post("https://api.x.com/2/tweets", json=body, timeout=30), f"X post {i + 1}")
            prev = r.json()["data"]["id"]
            ids.append(prev)
            time.sleep(2)
        return {"id": ids[0], "thread": ids}


# ------------------------------------------------------------------ Instagram
def ig_token():
    f = fernet()
    if f and os.path.exists(IG_TOKEN_FILE):
        data = json.loads(f.decrypt(open(IG_TOKEN_FILE, "rb").read()))
        return data["token"]
    return os.environ.get("IG_TOKEN")


class Instagram:
    def __init__(self, dry):
        self.dry = dry
        self.token = ig_token()
        if not self.token and not dry:
            raise Skip("IG_TOKEN not set")
        self._uid = None

    def uid(self):
        if not self._uid:
            r = check(requests.get(f"{IG_API}/me", params={"fields": "user_id,username", "access_token": self.token}, timeout=30), "Instagram me")
            self._uid = r.json()["user_id"]
        return self._uid

    def container(self, **params):
        params["access_token"] = self.token
        r = check(requests.post(f"{IG_API}/{self.uid()}/media", data=params, timeout=60), "Instagram container")
        return r.json()["id"]

    def wait(self, cid, minutes=6):
        for _ in range(minutes * 6):
            r = requests.get(f"{IG_API}/{cid}", params={"fields": "status_code", "access_token": self.token}, timeout=30)
            code = r.json().get("status_code") if r.ok else None
            if code == "FINISHED":
                return
            if code in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram container {cid} {code}")
            time.sleep(10)
        raise RuntimeError(f"Instagram container {cid} not ready in time")

    def post(self, item):
        ig = item["instagram"]
        kind, media, cap = ig["kind"], ig.get("media", []), ig.get("caption", "")
        if self.dry:
            print(f"  [Instagram] {kind}: {[public_url(m) for m in media][:2]} ... caption {len(cap)} chars")
            return {"id": "dry-run"}
        if kind == "image":
            cid = self.container(image_url=public_url(media[0]), caption=cap)
        elif kind == "carousel":
            kids = [self.container(image_url=public_url(m), is_carousel_item="true") for m in media[:10]]
            for k in kids:
                self.wait(k, 2)
            cid = self.container(media_type="CAROUSEL", children=",".join(kids), caption=cap)
        elif kind == "reel":
            cid = self.container(media_type="REELS", video_url=public_url(media[0]), caption=cap, share_to_feed="true")
        else:
            raise RuntimeError(f"Unsupported Instagram kind {kind}")
        self.wait(cid)
        r = check(requests.post(f"{IG_API}/{self.uid()}/media_publish", data={"creation_id": cid, "access_token": self.token}, timeout=60), "Instagram publish")
        return {"id": r.json()["id"]}


def refresh_ig():
    tok = ig_token()
    f = fernet()
    if not tok or not f:
        print("Instagram refresh skipped: IG_TOKEN or SOCIAL_KEY missing")
        return
    r = check(requests.get("https://graph.instagram.com/refresh_access_token", params={"grant_type": "ig_refresh_token", "access_token": tok}, timeout=30), "Instagram token refresh")
    data = r.json()
    payload = {"token": data["access_token"], "refreshed": dt.datetime.now(dt.timezone.utc).isoformat(), "expires_in": data.get("expires_in")}
    os.makedirs(os.path.dirname(IG_TOKEN_FILE), exist_ok=True)
    open(IG_TOKEN_FILE, "wb").write(f.encrypt(json.dumps(payload).encode()))
    print("Instagram token refreshed; valid for", round(int(data.get("expires_in", 0)) / 86400), "days")


# ------------------------------------------------------------------ main
def open_issue(title, body):
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok:
        print("ISSUE:", title, "\n", body)
        return
    requests.post(f"https://api.github.com/repos/{REPO}/issues", headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"},
                  json={"title": title, "body": body, "labels": ["social"]}, timeout=30)


def main():
    dry = "--dry-run" in sys.argv
    now = dt.datetime.now(UK)
    if "--now" in sys.argv:
        now = dt.datetime.fromisoformat(sys.argv[sys.argv.index("--now") + 1]).replace(tzinfo=UK)
    state = load_state()
    clients, problems, done = {}, [], []
    makers = {"linkedin": LinkedIn, "x": X, "instagram": Instagram}
    for path in sorted(glob.glob(os.path.join(QUEUE, "*.yaml"))):
        item = yaml.safe_load(open(path))
        if not item.get("approved"):
            continue
        for platform in ("linkedin", "x", "instagram"):
            spec = item.get(platform)
            if not spec or spec.get("needs_text") or spec.get("manual") or spec.get("kind") == "manual_reel" or spec.get("skip"):
                continue
            if state.get(item["id"], {}).get(platform, {}).get("id"):
                continue
            due = when(item, platform)
            if not (due <= now <= due + dt.timedelta(hours=36)):
                continue
            if platform in clients and clients[platform] is None:
                continue
            try:
                if platform not in clients:
                    clients[platform] = makers[platform](dry)
                print(f"{item['id']} → {platform}")
                res = clients[platform].post(item)
                res["at"] = dt.datetime.now(UK).isoformat(timespec="minutes")
                if not dry:
                    state.setdefault(item["id"], {})[platform] = res
                done.append(f"{item['id']} {platform}")
                if res.get("warning"):
                    problems.append(f"**{item['id']} on {platform}:** {res['warning']}")
            except Skip as e:
                clients[platform] = None
                print(f"  skipped {platform}: {e}")
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                print(f"  FAILED {platform}: {msg}")
                prev = state.setdefault(item["id"], {}).get(platform, {})
                if not dry:
                    state[item["id"]][platform] = {"error": msg[:500], "tries": prev.get("tries", 0) + 1}
                if prev.get("tries", 0) == 0:
                    problems.append(f"**{item['id']} on {platform}** didn't post: {msg[:800]}")
    if not dry:
        save_state(state)
    if problems and not dry:
        open_issue(f"Social posting needs attention ({now:%d %b %H:%M})",
                   "The social publisher hit a problem. Everything else carried on.\n\n" + "\n\n".join(problems) +
                   "\n\nIt will retry automatically for up to 36 hours after the scheduled time. Reply in Claude if you want help.")
    print(f"Done: {len(done)} posted, {len(problems)} problems")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "refresh-ig":
        refresh_ig()
    else:
        main()
