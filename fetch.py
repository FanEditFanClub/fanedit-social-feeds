#!/usr/bin/env python3
"""Build public JSON feeds for the Fan Edit Fan Club website widgets.

- x-posts.json: latest sent X posts, via Buffer's GraphQL API.
- reddit-community.json: latest r/FanEditFanClub posts, via Reddit app-only OAuth.
- reddit-multireddit.json: latest posts from the club's multireddit feed.

Runs on GitHub Actions; served to the site via GitHub Pages. 100% free.
Required env: BUFFER_TOKEN, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone

UA = "fanedit-social-feeds/1.0 (by /u/faneditfanclub)"
BUFFER_TOKEN = os.environ.get("BUFFER_TOKEN", "")
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
BUFFER_X_CHANNEL_ID = "6a63a3d9e2638b94d7ca2793"
BUFFER_ORG_ID = "6a63a35db088b578e206e7b2"
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


def reddit_token():
    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
        print("Reddit credentials missing, skipping Reddit feeds.")
        return None
    basic = base64.b64encode(f"{REDDIT_CLIENT_ID}:{REDDIT_CLIENT_SECRET}".encode()).decode()
    res = http_json(
        "POST", "https://www.reddit.com/api/v1/access_token",
        {"Authorization": f"Basic {basic}"},
        body={"grant_type": "client_credentials"},
    )
    return (res or {}).get("access_token")


def fetch_reddit_listing(token, path):
    res = http_json(
        "GET", f"https://oauth.reddit.com{path}?limit={LIMIT}&raw_json=1",
        {"Authorization": f"Bearer {token}"},
    )
    if not res:
        return None
    posts = []
    for child in res.get("data", {}).get("children", []):
        d = child["data"]
        posts.append({
            "title": d.get("title", ""),
            "url": "https://www.reddit.com" + d.get("permalink", ""),
            "created_utc": d.get("created_utc"),
            "author": d.get("author", ""),
            "num_comments": d.get("num_comments", 0),
            "score": d.get("score", 0),
        })
    return {"updated_at": datetime.now(timezone.utc).isoformat(), "posts": posts}


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
    token = reddit_token()
    if token:
        write("reddit-community.json",
              fetch_reddit_listing(token, "/r/FanEditFanClub/new"))
        write("reddit-multireddit.json",
              fetch_reddit_listing(token, "/user/faneditfanclub/m/fan_edit_fan_club_reddit_feed/new"))
    else:
        print("reddit-*.json: no token, leaving existing files.")


if __name__ == "__main__":
    sys.exit(main())
