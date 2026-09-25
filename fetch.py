#!/usr/bin/env python3
"""Build public JSON feeds for the Fan Edit Fan Club website widgets.

- x-posts.json: latest sent X posts, via Buffer's GraphQL API.
- fb-page.json: latest Fan Edit Fan Club Facebook Page posts, via the Graph API.
- reddit-community.json: latest r/FanEditFanClub posts, via Reddit's public RSS.
- reddit-multireddit.json: latest posts from the club's multireddit feed, via RSS.

Runs on GitHub Actions; served to the site via GitHub Pages. 100% free.
Reddit's RSS endpoints serve fine without auth as long as the request
carries a descriptive User-Agent; generic/no UA gets 403'd.
Required env: BUFFER_TOKEN, FACEBOOK_PAGE_TOKEN (Reddit needs no credentials).
The page token is sent via Authorization header, never in the URL, and is
never printed to logs.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Temporary diagnostic: records the last FB Graph error (never the token)
# into fb-debug.json so failures can be read without the Actions log UI.
FB_DEBUG = {}

UA = "fanedit-social-feeds/1.0 (by /u/faneditfanclub)"
BUFFER_TOKEN = os.environ.get("BUFFER_TOKEN", "")
BUFFER_X_CHANNEL_ID = "6a63a3d9e2638b94d7ca2793"
BUFFER_ORG_ID = "6a63a35db088b578e206e7b2"
FB_PAGE_ID = "1240699955783812"
FB_PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN", "")
LIMIT = 10


def http_json(method, url, headers=None, body=None, timeout=30):
    data = body
    if isinstance(body, dict):
        data = urllib.parse.urlencode(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", UA)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        print(f"HTTP {e.code} {method} {url}: {detail}")
        return None


def fetch_x_posts():
    if not BUFFER_TOKEN:
        print("BUFFER_TOKEN missing, skipping X feed.")
        return None
    query = """query($oid: OrganizationId!) {
      posts(first: 25, input: {organizationId: $oid, filter: {channelIds: ["%s"]}}) {
        edges { node { text status sentAt externalLink } }
      }
    }""" % BUFFER_X_CHANNEL_ID
    res = http_json(
        "POST", "https://api.buffer.com",
        {"Content-Type": "application/json", "Authorization": f"Bearer {BUFFER_TOKEN}"},
        body=json.dumps({"query": query, "variables": {"oid": BUFFER_ORG_ID}}).encode(),
    )
    if not res or res.get("errors"):
        print("Buffer error:", json.dumps(res)[:300] if res else "no response")
        return None
    posts = []
    for edge in res["data"]["posts"]["edges"]:
        n = edge["node"]
        if n.get("status") != "sent" or not n.get("sentAt"):
            continue
        posts.append({"text": n["text"], "url": n.get("externalLink") or "", "sent_at": n["sentAt"]})
    posts.sort(key=lambda p: p["sent_at"], reverse=True)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "profile": {"name": "Fan Edit Fan Club", "handle": "@FanEditFanClub"},
        "posts": posts[:LIMIT],
    }


def fb_api(path, params):
    """GET the Facebook Graph API with the page token in the Authorization
    header (never in the URL, never logged)."""
    url = "https://graph.facebook.com/v24.0/" + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", UA)
    req.add_header("Authorization", f"Bearer {FB_PAGE_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        msg = f"FB Graph HTTP {e.code} on {path}: {detail}"
        print(msg)
        FB_DEBUG["last_error"] = msg
        return None


def fetch_fb_page():
    if not FB_PAGE_TOKEN:
        print("FACEBOOK_PAGE_TOKEN missing, skipping FB Page feed.")
        return None
    page = fb_api(FB_PAGE_ID, {"fields": "name,picture{url}"})
    res = fb_api(f"{FB_PAGE_ID}/promotable_posts", {
        "fields": "id,message,story,full_picture,created_time,permalink_url,"
                  "shares,reactions.summary(true).limit(0),comments.summary(true).limit(0)",
        "limit": 20,
    })
    if not res or "data" not in res:
        print("FB posts error:", json.dumps(res)[:300] if res else "no response")
        return None
    posts = []
    for p in res["data"]:
        text = (p.get("message") or "").strip()
        img = p.get("full_picture") or ""
        if not text and not img:
            continue
        posts.append({
            "id": p["id"],
            "text": text,
            "image": img,
            "url": p.get("permalink_url") or "",
            "created_at": p.get("created_time"),
            "likes": ((p.get("reactions") or {}).get("summary") or {}).get("total_count", 0),
            "comments": ((p.get("comments") or {}).get("summary") or {}).get("total_count", 0),
            "shares": (p.get("shares") or {}).get("count", 0),
        })
        if len(posts) >= LIMIT:
            break
    pic = ""
    try:
        pic = page["picture"]["data"]["url"]
    except (TypeError, KeyError):
        pass
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "profile": {
            "name": (page or {}).get("name", "Fan Edit Fan Club"),
            "handle": "FanEditFanClub",
            "picture": pic,
        },
        "posts": posts,
    }


def fetch_reddit_rss(url, attempts=4):
    """Fetch a Reddit RSS/Atom feed. Retries with backoff; None if all fail."""
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                root = ET.fromstring(resp.read().decode())
            posts = []
            for entry in root.findall("a:entry", ns)[:LIMIT]:
                link = entry.find("a:link", ns)
                posts.append({
                    "title": (entry.find("a:title", ns).text or "").strip(),
                    "url": link.get("href") if link is not None else "",
                    "published": entry.find("a:updated", ns).text,
                    "author": (entry.find("a:author/a:name", ns).text or "").strip(),
                })
            return {"updated_at": datetime.now(timezone.utc).isoformat(), "posts": posts}
        except Exception as e:  # noqa: BLE001 - any failure -> retry/skip
            print(f"RSS attempt {i + 1}/{attempts} failed for {url}: {e}")
            time.sleep(2 * (i + 1))
    return None


def write(name, payload):
    if payload is None:
        print(f"{name}: no data, leaving existing file.")
        return
    with open(name, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"{name}: wrote {len(payload['posts'])} posts.")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    write("x-posts.json", fetch_x_posts())
    fb = fetch_fb_page()
    write("fb-page.json", fb)
    if fb is None:
        with open("fb-debug.json", "w") as f:
            json.dump({
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "error": FB_DEBUG.get("last_error", "no Graph call was made"),
                "token_present": bool(FB_PAGE_TOKEN),
                "token_len": len(FB_PAGE_TOKEN),
            }, f, indent=1)
        print("wrote fb-debug.json")
    write("reddit-community.json",
          fetch_reddit_rss("https://www.reddit.com/r/FanEditFanClub/new/.rss"))
    write("reddit-multireddit.json",
          fetch_reddit_rss("https://www.reddit.com/user/faneditfanclub/m/fan_edit_fan_club_reddit_feed/new/.rss"))


if __name__ == "__main__":
    sys.exit(main())
