#!/usr/bin/env python3
"""Build public JSON feeds for the Fan Edit Fan Club website widgets.

- x-list.json: Fan Editors X list, from X's public syndication timeline.
  Replies and reposts are dropped. Each author appears at most twice so a
  high-volume account (SopranosOrder posts about every 15 minutes) cannot
  fill the card. No X widgets.js, no paid API.
- x-posts.json: @FanEditFanClub posts. Syndication (profile timeline, then
  the club's own posts inside the list) is preferred. Buffer fills gaps for
  posts that were not in the syndication window. The previous file is used
  only when Buffer itself is unavailable, so a failed run cannot wipe posts.
- fb-page.json: latest Fan Edit Fan Club Facebook Page posts, via the Graph API.
- fb-group.json: recent Facebook Group posts. Facebook removed the Groups
  API in April 2024 and the Page Plugin does not show groups, so this reads
  the public JSON behind the club's existing SociableKit "Facebook Group
  Posts" widget (embed 25717067, the one website-widgets.html used). On the
  free SociableKit plan that snapshot only changes when someone presses
  "Request sync" in the SociableKit dashboard; paid plans sync on their own.
- reddit-community.json / reddit-multireddit.json: written by the daily
  5pm ET browser scan (Muse cron), NOT by this script. Reddit killed public
  RSS on 2026-11-13, so the scan replaces the old RSS fetch; this script
  must not touch those files.
- site-pages.json: text, buttons, and embed list for the installable app.
  Google Sites cannot be iframed, so each run downloads the published pages
  and keeps a sanitized copy. A failed download leaves the previous file.

X syndication (syndication.twitter.com) allows about 30 requests per 15
minutes per IP address. GitHub-hosted runners share IPs with other
workflows, so HTTP 429 is common. This script retries only when the rate
limit resets within a minute (or once after a short backoff). If the fetch
still fails, the existing JSON file is left untouched — the site keeps the
last good posts instead of going blank.

Runs on GitHub Actions; served via GitHub Pages. 100% free.
Required env for the optional sources: BUFFER_TOKEN, FACEBOOK_PAGE_TOKEN.
Tokens are sent via Authorization headers, never in the URL, and never printed.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

UA = "Mozilla/5.0 (compatible; fanedit-social-feeds/1.0; +https://www.faneditfanclub.com)"
BUFFER_TOKEN = os.environ.get("BUFFER_TOKEN", "")
BUFFER_X_CHANNEL_ID = "6a63a3d9e2638b94d7ca2793"
BUFFER_ORG_ID = "6a63a35db088b578e206e7b2"
FB_PAGE_ID = "1240699955783812"
FB_PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN", "")
LIMIT = 10

FB_GROUP_URL = "https://www.facebook.com/groups/faneditfanclub"
SOCIABLEKIT_GROUP_FEED = "https://data.accentapi.com/feed/25717067.json"
GROUP_KEEP = 8

LIST_ID = "2072540475530084770"
SCREEN_NAME = "FanEditFanClub"
SYNDICATION_LIST = (
    "https://syndication.twitter.com/srv/timeline-list/list-id/" + LIST_ID
)
SYNDICATION_PROFILE = (
    "https://syndication.twitter.com/srv/timeline-profile/screen-name/" + SCREEN_NAME
)
# At most this many of the stored (and therefore shown) list posts per author.
AUTHOR_CAP = 2
LIST_KEEP = 12
PROFILE_KEEP = 10

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)
STATUS_RE = re.compile(r"/status/(\d+)")


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


def http_get(url, timeout=30):
    """Return (status, headers, body). Network failures are status 0."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "text/html,application/xhtml+xml")
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.headers, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        return e.code, e.headers, detail
    except urllib.error.URLError as e:
        print(f"network error {url}: {e}")
        return 0, {}, ""


def fetch_syndication(url, label):
    """Fetch one syndication HTML document.

    429s are expected from GitHub-hosted runners (shared IP, 30 requests /
    15 minutes). Wait only when the advertised reset is imminent, otherwise
    back off once and then stop so the job does not sit through the window.
    Returns HTML, or None when the caller should keep the last good file.
    """
    for attempt in range(3):
        status, headers, body = http_get(url)
        if status == 200 and body and "__NEXT_DATA__" in body:
            print(f"{label}: HTTP 200 ({len(body)} bytes)")
            return body
        if status == 429:
            reset_raw = ""
            if headers:
                reset_raw = headers.get("x-rate-limit-reset") or ""
            wait = None
            try:
                wait = float(reset_raw) - time.time()
            except (TypeError, ValueError):
                wait = None
            reset_msg = f", resets in {wait:.0f}s" if wait is not None else ""
            print(
                f"{label}: HTTP 429 rate limit{reset_msg}. "
                "syndication.twitter.com allows about 30 requests / 15 min per IP. "
                "GitHub-hosted runners share IPs, so this is expected."
            )
            if wait is not None and 0 < wait <= 45 and attempt < 2:
                print(f"{label}: waiting {wait:.0f}s for the rate-limit window")
                time.sleep(wait + 1)
                continue
            if attempt == 0:
                print(f"{label}: backing off 20s and retrying once")
                time.sleep(20)
                continue
            print(f"{label}: still rate limited; keeping the last good file")
            return None
        print(f"{label}: HTTP {status} {(body or '')[:180]!r}")
        if status in (0, 500, 502, 503, 504) and attempt < 2:
            delay = 5 * (attempt + 1)
            print(f"{label}: retrying in {delay}s")
            time.sleep(delay)
            continue
        return None
    return None


def to_iso(value):
    """Normalize Twitter, ISO, and Buffer timestamps to UTC with a numeric offset.

    Browsers parse `2026-10-08T13:00:00+00:00` as UTC and `Intl` then renders
    it in the viewer's local zone. A bare `Z` is equivalent, but the offset
    form is unambiguous, including for Facebook's `+0000` (no colon).
    """
    if not value:
        return ""
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        text = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", text)
        dt = None
        if "T" in text:
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                dt = None
        if dt is None:
            try:
                dt = parsedate_to_datetime(text)
            except (TypeError, ValueError, IndexError):
                return text
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def parse_syndication(html_text):
    """Pull timeline tweets out of a syndication `__NEXT_DATA__` payload.

    Returns {"header": {...}, "tweets": [raw tweet, ...]} or None.
    """
    match = NEXT_DATA_RE.search(html_text or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        page = data["props"]["pageProps"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    entries = ((page.get("timeline") or {}).get("entries")) or []
    tweets = []
    for entry in entries:
        tweet = ((entry or {}).get("content") or {}).get("tweet")
        if isinstance(tweet, dict) and (tweet.get("full_text") or tweet.get("text")):
            tweets.append(tweet)
    return {"header": page.get("headerProps") or {}, "tweets": tweets}


def is_repost(tweet):
    if tweet.get("retweeted_status") or tweet.get("retweeted_status_result"):
        return True
    text = tweet.get("full_text") or tweet.get("text") or ""
    return text.startswith("RT @")


def is_reply(tweet):
    if (
        tweet.get("in_reply_to_status_id_str")
        or tweet.get("in_reply_to_user_id_str")
        or tweet.get("in_reply_to_screen_name")
    ):
        return True
    span = tweet.get("display_text_range") or [0]
    text = tweet.get("full_text") or tweet.get("text") or ""
    if isinstance(span, list) and span and isinstance(span[0], int) and span[0] > 0:
        if text[: span[0]].strip().startswith("@"):
            return True
    own = str(tweet.get("id_str") or "")
    conv = str(tweet.get("conversation_id_str") or "")
    if own and conv and own != conv and text.startswith("@"):
        return True
    return False


def clean_text(tweet):
    text = tweet.get("full_text") or tweet.get("text") or ""
    entities = tweet.get("entities") or {}
    for link in entities.get("urls") or []:
        short = link.get("url") or ""
        expanded = link.get("expanded_url") or ""
        if short and expanded:
            text = text.replace(short, expanded)
    for media in entities.get("media") or []:
        short = media.get("url") or ""
        if short:
            text = text.replace(short, "")
    text = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def status_id_from_url(url):
    match = STATUS_RE.search(url or "")
    return match.group(1) if match else ""


def tweet_to_post(tweet):
    user = tweet.get("user") or {}
    handle = user.get("screen_name") or ""
    permalink = tweet.get("permalink") or ""
    tweet_id = str(tweet.get("id_str") or "")
    if permalink.startswith("/"):
        url = "https://x.com" + permalink
    elif permalink.startswith("http"):
        url = permalink
    elif tweet_id and handle:
        url = f"https://x.com/{handle}/status/{tweet_id}"
    else:
        url = ""
    created = to_iso(tweet.get("created_at"))
    image = ""
    media = (tweet.get("extended_entities") or {}).get("media") or (
        tweet.get("entities") or {}
    ).get("media") or []
    for item in media:
        image = item.get("media_url_https") or ""
        if image:
            break
    return {
        "id": tweet_id or status_id_from_url(url),
        "text": clean_text(tweet),
        "url": url,
        "created_at": created,
        "sent_at": created,
        "author_name": user.get("name") or "",
        "author_handle": handle,
        "author_avatar": user.get("profile_image_url_https") or "",
        "reply_count": int(tweet.get("reply_count") or 0),
        "repost_count": int(tweet.get("retweet_count") or 0),
        "like_count": int(tweet.get("favorite_count") or 0),
        "image": image,
    }


def select_originals(tweets):
    """Newest first, replies and reposts removed."""
    posts = []
    for tweet in tweets:
        if is_repost(tweet) or is_reply(tweet):
            continue
        post = tweet_to_post(tweet)
        if post["id"] and post["text"]:
            posts.append(post)
    posts.sort(key=lambda post: post["created_at"], reverse=True)
    return posts


def cap_authors(posts, per_author=AUTHOR_CAP, limit=LIST_KEEP):
    """Keep chronological order, but no author may take more than `per_author` slots."""
    counts = {}
    chosen = []
    for post in posts:
        handle = (post.get("author_handle") or "").lower()
        if counts.get(handle, 0) >= per_author:
            continue
        counts[handle] = counts.get(handle, 0) + 1
        chosen.append(post)
        if len(chosen) >= limit:
            break
    return chosen


def build_list_payload(header, posts):
    owner = (header or {}).get("owner") or {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return {
        "updated_at": now,
        "source": "syndication.twitter.com/srv/timeline-list",
        "author_cap": AUTHOR_CAP,
        "list": {
            "id": LIST_ID,
            "name": (header or {}).get("name") or "Fan Editors",
            "member_count": (header or {}).get("memberCount"),
            "url": "https://x.com/i/lists/" + LIST_ID,
            "owner_name": owner.get("name") or "Fan Edit Fan Club",
            "owner_handle": owner.get("screenName") or SCREEN_NAME,
            "owner_avatar": owner.get("profileImageUrl") or "",
        },
        "posts": posts,
    }


def merge_profile(syndication_posts, buffer_posts, existing_posts):
    """Prefer syndication copies, then Buffer, then whatever was already on disk.

    Dedupe by status id. `existing_posts` should be empty when Buffer succeeded,
    so a stale file cannot outrank a fresh Buffer response.
    """
    merged = {}
    order = []

    def add(post, source):
        sid = str(post.get("id") or "") or status_id_from_url(post.get("url") or "")
        key = sid or ("text:" + (post.get("text") or "")[:120])
        if key in merged:
            return
        text = (post.get("text") or "").strip()
        if not text:
            return
        sent = to_iso(post.get("sent_at") or post.get("created_at"))
        merged[key] = {
            "id": sid,
            "text": text,
            "url": post.get("url") or "",
            "sent_at": sent,
            "created_at": sent,
            "author_name": post.get("author_name") or "Fan Edit Fan Club",
            "author_handle": (post.get("author_handle") or SCREEN_NAME).lstrip("@"),
            "author_avatar": post.get("author_avatar") or "",
            "reply_count": int(post.get("reply_count") or 0),
            "repost_count": int(post.get("repost_count") or 0),
            "like_count": int(post.get("like_count") or 0),
            "image": post.get("image") or "",
            "source": source,
        }
        order.append(key)

    for post in syndication_posts or []:
        handle = (post.get("author_handle") or SCREEN_NAME).lstrip("@")
        if handle != SCREEN_NAME:
            continue
        add(post, "syndication")
    for post in buffer_posts or []:
        add(post, "buffer")
    for post in existing_posts or []:
        # Posts already on disk came from an earlier Buffer or syndication run.
        source = post.get("source") or "buffer"
        if source == "previous":
            source = "buffer"
        add(post, source)
    posts = [merged[key] for key in order]
    posts.sort(key=lambda post: post["sent_at"], reverse=True)
    return posts[:PROFILE_KEEP]


def fetch_buffer_posts():
    """Return Buffer-sent X posts, or None if Buffer could not be read."""
    if not BUFFER_TOKEN:
        print("BUFFER_TOKEN missing, Buffer will not fill profile gaps.")
        return None
    query = """query($oid: OrganizationId!) {
      posts(first: 25, input: {organizationId: $oid, filter: {channelIds: ["%s"]}}) {
        edges { node { text status sentAt externalLink } }
      }
    }""" % BUFFER_X_CHANNEL_ID
    res = http_json(
        "POST",
        "https://api.buffer.com",
        {"Content-Type": "application/json", "Authorization": f"Bearer {BUFFER_TOKEN}"},
        body=json.dumps({"query": query, "variables": {"oid": BUFFER_ORG_ID}}).encode(),
    )
    if not res or res.get("errors"):
        print("Buffer error:", json.dumps(res)[:300] if res else "no response")
        return None
    posts = []
    try:
        edges = res["data"]["posts"]["edges"]
    except (KeyError, TypeError):
        print("Buffer response missing posts.")
        return None
    for edge in edges:
        node = edge.get("node") or {}
        if node.get("status") != "sent" or not node.get("sentAt"):
            continue
        sent = to_iso(node["sentAt"])
        url = node.get("externalLink") or ""
        posts.append({
            "id": status_id_from_url(url),
            "text": node.get("text") or "",
            "url": url,
            "sent_at": sent,
            "created_at": sent,
            "author_name": "Fan Edit Fan Club",
            "author_handle": SCREEN_NAME,
        })
    posts.sort(key=lambda post: post["sent_at"], reverse=True)
    return posts


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
        print(f"FB Graph HTTP {e.code} on {path}: {detail}")
        return None


def fetch_fb_page():
    if not FB_PAGE_TOKEN:
        print("FACEBOOK_PAGE_TOKEN missing, skipping FB Page feed.")
        return None
    page = fb_api(FB_PAGE_ID, {"fields": "name,picture{url}"})
    res = fb_api(f"{FB_PAGE_ID}/posts", {
        "fields": "id,message,story,full_picture,created_time,permalink_url,"
                  "shares,reactions.summary(true).limit(0),comments.summary(true).limit(0)",
        "limit": 20,
    })
    if not res or "data" not in res:
        print("FB posts error:", json.dumps(res)[:300] if res else "no response")
        return None
    posts = []
    for post in res["data"]:
        text = (post.get("message") or "").strip()
        image = post.get("full_picture") or ""
        if not text and not image:
            continue
        posts.append({
            "id": post["id"],
            "text": text,
            "image": image,
            "url": post.get("permalink_url") or "",
            "created_at": to_iso(post.get("created_time")),
            "likes": ((post.get("reactions") or {}).get("summary") or {}).get("total_count", 0),
            "comments": ((post.get("comments") or {}).get("summary") or {}).get("total_count", 0),
            "shares": (post.get("shares") or {}).get("count", 0),
        })
        if len(posts) >= LIMIT:
            break
    picture = ""
    try:
        picture = page["picture"]["data"]["url"]
    except (TypeError, KeyError):
        pass
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "profile": {
            "name": (page or {}).get("name", "Fan Edit Fan Club"),
            "handle": "FanEditFanClub",
            "picture": picture,
        },
        "posts": posts,
    }


def group_text(value):
    """SociableKit gives Facebook's markdown-ish text. Keep plain words."""
    text = html.unescape(value or "")
    text = re.sub(r"\[([^\]]*)\]\((https?://[^)]+)\)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = text.replace("**", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


SK_TZ = timezone(timedelta(hours=8))


def sk_time(value):
    """SociableKit stamps ('YYYY-MM-DD HH:MM:SS') are in its server time,
    UTC+8: last_sync_info 2026-09-28 01:37:41 matched the feed's HTTP
    Last-Modified of Sun, 27 Sep 2026 17:37:41 GMT. Return ISO UTC."""
    try:
        stamp = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return ""
    stamp = stamp.replace(tzinfo=SK_TZ).astimezone(timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def fetch_fb_group():
    data = http_json("GET", SOCIABLEKIT_GROUP_FEED, {"Accept": "application/json"})
    if not isinstance(data, dict) or not isinstance(data.get("posts"), list):
        print("fb-group: SociableKit feed unavailable")
        return None
    posts = []
    for post in data["posts"]:
        url = post.get("post_link") or ""
        if not url.startswith(FB_GROUP_URL):
            continue
        text = group_text(post.get("description") or post.get("story"))
        images = post.get("image_urls") or post.get("images") or []
        image = images[0] if images and isinstance(images[0], str) else ""
        if not text and not image:
            continue
        posts.append({
            "id": str(post.get("post_id") or post.get("id") or ""),
            "text": text,
            "image": image,
            "url": url,
            "created_at": sk_time(post.get("publish_date")),
            "author_name": post.get("profile_name") or "",
        })
    posts.sort(key=lambda item: item["created_at"], reverse=True)
    synced = sk_time(data.get("last_sync_info"))
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "source": "sociablekit embed 25717067 (manual sync on the free plan)",
        "source_synced_at": synced,
        "group": {
            "name": "Fan Edit Fan Club",
            "url": FB_GROUP_URL,
        },
        "posts": posts[:GROUP_KEEP],
    }


def load_json(name):
    try:
        with open(name) as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def write(name, payload):
    if payload is None:
        print(f"{name}: no data, leaving existing file.")
        return
    posts = payload.get("posts") or []
    if not posts:
        print(f"{name}: empty post list, leaving existing file.")
        return
    with open(name, "w") as handle:
        json.dump(payload, handle, indent=1)
        handle.write("\n")
    print(f"{name}: wrote {len(posts)} posts.")


def refresh_x(existing_profile):
    """Refresh x-list.json and return fresh @FanEditFanClub posts (may be empty)."""
    club_posts = []
    list_html = fetch_syndication(SYNDICATION_LIST, "x-list")
    if not list_html:
        print("x-list: fetch failed; keeping the last x-list.json")
    else:
        parsed = parse_syndication(list_html)
        if not parsed or not parsed["tweets"]:
            print("x-list: response had no tweets; keeping the last x-list.json")
        else:
            originals = select_originals(parsed["tweets"])
            shown = cap_authors(originals)
            if not shown:
                print("x-list: nothing left after filters; keeping the last x-list.json")
            else:
                write("x-list.json", build_list_payload(parsed["header"], shown))
            club_posts = [
                post for post in originals
                if post.get("author_handle") == SCREEN_NAME
            ]

    profile_posts = []
    profile_html = fetch_syndication(SYNDICATION_PROFILE, "x-profile")
    if not profile_html:
        print("x-profile: fetch failed; profile feed will use the list and Buffer")
    else:
        parsed = parse_syndication(profile_html)
        if parsed and parsed["tweets"]:
            profile_posts = [
                post for post in select_originals(parsed["tweets"])
                if post.get("author_handle") in (SCREEN_NAME, "")
            ]
            print(f"x-profile: {len(profile_posts)} original posts")
        else:
            print("x-profile: response had no tweets")

    buffer_posts = fetch_buffer_posts()
    if buffer_posts is None and not profile_posts and not club_posts:
        print("x-posts: no fresh source, leaving existing file.")
        return
    # When Buffer is down, keep posts already on disk so the card does not shrink.
    previous = []
    if buffer_posts is None:
        previous = (existing_profile or {}).get("posts") or []
    merged = merge_profile(profile_posts + club_posts, buffer_posts or [], previous)
    if not merged:
        print("x-posts: merge produced nothing, leaving existing file.")
        return
    avatar = ""
    for post in merged:
        if post.get("author_avatar"):
            avatar = post["author_avatar"]
            break
    if not avatar:
        avatar = ((existing_profile or {}).get("profile") or {}).get("picture") or ""
    write("x-posts.json", {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "source": "syndication, buffer fallback",
        "profile": {
            "name": "Fan Edit Fan Club",
            "handle": "@FanEditFanClub",
            "picture": avatar,
        },
        "posts": merged,
    })


# --- Google Sites pages for the installable app ----------------------------
# The published site cannot be iframed. Each feeds run downloads the nav
# pages, drops scripts and Google chrome, and writes site-pages.json. The
# app renders that file, plus the same JSON the embed cards already use.

SITE_ORIGIN = "https://www.faneditfanclub.com"
SITE_PAGES_FILE = "site-pages.json"
ICON_CATALOG_FILE = "embed-icons.html"

EMBED_KINDS = {
    "embed-discord.html": "discord",
    "embed-x-profile.html": "x-profile",
    "embed-x-list.html": "x-list",
    "embed-facebook.html": "facebook",
    "embed-reddit-community.html": "reddit-community",
    "embed-reddit-feed.html": "reddit-feed",
    "embed-fb-group.html": "fb-group",
    "embed-paypal.html": "paypal",
    "embed-icons.html": "icons",
}

BOILERPLATE = {
    "google sites",
    "report abuse",
    "page details",
    "page updated",
    "skip to main content",
    "skip to navigation",
    "search this site",
    "embedded files",
}


def attr(attrs, name):
    match = re.search(
        r'\b' + re.escape(name) + r'\s*=\s*(?:"([^"]*)"|\'([^\']*)\')',
        attrs or "",
        re.I,
    )
    if not match:
        return ""
    return html.unescape(match.group(1) if match.group(1) is not None else match.group(2))


def unwrap_google_url(url):
    """Google Sites wraps outbound links. Keep the real target."""
    if not url:
        return ""
    text = html.unescape(url).strip()
    parsed = urllib.parse.urlparse(text)
    host = parsed.netloc.lower()
    if host.endswith("google.com") and parsed.path.rstrip("/").endswith("/url"):
        target = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
        if target:
            return html.unescape(target).strip()
    return text


def href_is_usable(url):
    """Drop truncated Google Sites embed hrefs such as `url?id=9`."""
    if not url:
        return False
    if url.startswith("mailto:"):
        return "@" in url and " " not in url
    if url.startswith("#") and not url.startswith("#h."):
        return True
    if not (url.startswith("https://") or url.startswith("http://")):
        return False
    if re.search(r"paypal\.biz/faneditfanclub\d+\b", url):
        return False
    return True


def esc_text(value):
    return html.escape(value or "", quote=True)


def tidy_inline(value):
    text = (value or "").replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class InlineHTML(HTMLParser):
    """Keep text and real links. Drop scripts, styles, and heading-link icons."""

    def __init__(self, page_ids):
        super().__init__(convert_charrefs=True)
        self.page_ids = page_ids
        self.skip = 0
        self.anchor = None
        self.anchor_parts = []
        self.tokens = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg"):
            self.skip += 1
            return
        if self.skip:
            return
        data = dict(attrs)
        if tag == "br":
            self._text(" ")
        elif tag == "a":
            self.anchor = data.get("href") or ""
            self.anchor_parts = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg") and self.skip:
            self.skip -= 1
            return
        if self.skip:
            return
        if tag == "a" and self.anchor is not None:
            label = tidy_inline("".join(self.anchor_parts))
            href = self._app_href(self.anchor)
            if label and href and href_is_usable(href) and not href.startswith("#h."):
                external = href.startswith("http://") or href.startswith("https://") or href.startswith("mailto:")
                extra = ' target="_blank" rel="noopener noreferrer"' if external else ""
                self.tokens.append(
                    '<a href="%s"%s>%s</a>' % (esc_text(href), extra, esc_text(label))
                )
            elif label:
                self._text(label)
            self.anchor = None
            self.anchor_parts = []

    def handle_data(self, data):
        if self.skip or not data:
            return
        if self.anchor is not None:
            self.anchor_parts.append(data)
        else:
            self._text(data)

    def _text(self, data):
        self.tokens.append(esc_text(data))

    def _app_href(self, href):
        target = unwrap_google_url(href)
        if target.startswith("/") and not target.startswith("//"):
            slug = target.strip("/").split("/")[0]
            if slug in self.page_ids:
                return "#" + slug
        return target

    def html(self):
        joined = "".join(self.tokens)
        joined = re.sub(r"\s+", " ", joined).strip()
        return joined


def inline_html(fragment, page_ids):
    parser = InlineHTML(page_ids)
    try:
        parser.feed(fragment or "")
        parser.close()
    except Exception:
        return ""
    return parser.html()


def plain_text(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment or "")
    return tidy_inline(html.unescape(text))


def is_boilerplate(text):
    lowered = tidy_inline(text).lower()
    if not lowered:
        return True
    if lowered in BOILERPLATE:
        return True
    return False


class SectionParser(HTMLParser):
    """Walk one Google Sites section in document order."""

    def __init__(self, page_ids, catalog, repairs, where):
        super().__init__(convert_charrefs=True)
        self.page_ids = page_ids
        self.catalog = catalog
        self.repairs = repairs
        self.where = where
        self.skip = 0
        self.blocks = []
        self.capture = None
        self.buf = []
        self.in_button = 0

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag in ("script", "style", "svg"):
            self.skip += 1
            return
        if self.skip:
            return
        classes = data.get("class") or ""
        label = (data.get("aria-label") or "").strip().lower()
        is_button = tag == "a" and ("FKF6mc" in classes or "QmpIrf" in classes)
        if is_button and self.capture not in ("h1", "h2", "h3") and label != "copy heading link":
            self.in_button += 1
            self.capture = "button"
            self.buf = []
            self._button = data
        elif self.capture is None and tag in ("h1", "h2", "h3"):
            self.capture = tag
            self.buf = []
        elif self.capture is None and tag in ("p", "small") and not self.in_button:
            self.capture = tag
            self.buf = []
        elif self.capture in ("p", "small") and tag == "a":
            href = html.escape(data.get("href") or "", quote=True)
            self.buf.append('<a href="%s">' % href)
        elif self.capture in ("p", "small") and tag == "br":
            self.buf.append("<br>")
        if data.get("data-code"):
            self.blocks.extend(classify_embed(
                data["data-code"], self.page_ids, self.catalog, self.repairs, self.where
            ))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg") and self.skip:
            self.skip -= 1
            return
        if self.skip:
            return
        if self.capture in ("p", "small") and tag == "a":
            self.buf.append("</a>")
            return
        if self.capture == "button" and tag == "a":
            self._finish_button()
            self.in_button = max(0, self.in_button - 1)
            return
        if self.capture in ("h1", "h2", "h3") and tag == self.capture:
            text = plain_text("".join(self.buf))
            if text and not is_boilerplate(text) and text.lower() != "copy heading link":
                self.blocks.append({
                    "type": "text",
                    "tag": self.capture,
                    "html": esc_text(text),
                    "align": "center",
                    "font": "display",
                })
            self.capture = None
            self.buf = []
            return
        if self.capture in ("p", "small") and tag == self.capture:
            rendered = inline_html("".join(self.buf), self.page_ids)
            visible = plain_text(rendered)
            if visible and not is_boilerplate(visible):
                self.blocks.append({
                    "type": "text",
                    "tag": "p",
                    "html": rendered,
                    "align": "center",
                    "font": "display",
                })
            self.capture = None
            self.buf = []

    def handle_data(self, data):
        if self.skip or self.capture is None:
            return
        self.buf.append(data)

    def _finish_button(self):
        data = getattr(self, "_button", {})
        label = (data.get("aria-label") or plain_text("".join(self.buf))).strip()
        label = re.sub(r"\s+", " ", label)
        href = unwrap_google_url(data.get("href") or "")
        self.capture = None
        self.buf = []
        if not label or label.lower() == "copy heading link":
            return
        if href.startswith("#"):
            return
        if href.startswith("/") and not href.startswith("//"):
            slug = href.strip("/").split("/")[0]
            if slug in self.page_ids:
                href = "#" + slug
        if not href_is_usable(href):
            return
        self.blocks.append({
            "type": "links",
            "items": [{"label": label, "href": href}],
        })


def parse_icon_catalog(html_text):
    items = []
    for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html_text or "", re.S | re.I):
        attrs, inner = match.group(1), match.group(2)
        href = unwrap_google_url(attr(attrs, "href"))
        label = attr(attrs, "data-label") or attr(attrs, "title")
        icon = ""
        image = re.search(r"<img\b([^>]*)>", inner, re.I)
        if image:
            icon = attr(image.group(1), "src")
            if not label:
                label = attr(image.group(1), "alt")
        label = tidy_inline(label)
        if label and href_is_usable(href):
            items.append({"label": label, "href": href, "icon": icon})
    return items


def label_key(value):
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def catalog_match(label, catalog):
    key = label_key(label)
    exact = [item for item in catalog if label_key(item["label"]) == key]
    if exact:
        return exact[0]
    # "Rockstar" in the Sites embed is "Rockstar Games" on the homepage grid.
    if len(key) < 6:
        return None
    hits = [
        item for item in catalog
        if label_key(item["label"]).startswith(key) or key.startswith(label_key(item["label"]))
    ]
    if len(hits) == 1:
        return hits[0]
    return None


def repair_links(items, catalog, repairs, where):
    fixed = []
    for item in items:
        href = item.get("href") or ""
        icon = item.get("icon") or ""
        label = tidy_inline(item.get("label") or "")
        if not label:
            continue
        if not href_is_usable(href):
            replacement = catalog_match(label, catalog)
            if not replacement:
                repairs.append("%s: dropped broken link %s" % (where, label))
                continue
            href = replacement["href"]
            if not icon:
                icon = replacement.get("icon") or ""
            repairs.append("%s: repaired %s from the homepage icon grid" % (where, label))
        entry = {"label": label, "href": href}
        if icon:
            entry["icon"] = icon
        fixed.append(entry)
    return fixed


def social_cards(body, page_ids, catalog, repairs, where):
    items = []
    for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", body or "", re.S | re.I):
        attrs, inner = match.group(1), match.group(2)
        if "social-card" not in (attr(attrs, "class") or ""):
            continue
        href = unwrap_google_url(attr(attrs, "href"))
        label = ""
        label_match = re.search(r'class="social-label"[^>]*>([^<]*)', inner)
        if label_match:
            label = tidy_inline(html.unescape(label_match.group(1)))
        icon = ""
        image = re.search(r"<img\b([^>]*)>", inner, re.I)
        if image:
            icon = attr(image.group(1), "src")
            if not label:
                label = tidy_inline(attr(image.group(1), "alt"))
        if label:
            items.append({"label": label, "href": href, "icon": icon})
    if not items:
        return []
    return [{
        "type": "links",
        "style": "channels",
        "items": repair_links(items, catalog, repairs, where),
    }]


def classify_embed(code, page_ids, catalog=None, repairs=None, where="page"):
    catalog = catalog or []
    repairs = repairs if repairs is not None else []
    blocks = []
    for match in re.finditer(r"<iframe\b([^>]*)>", code or "", re.I):
        attrs = match.group(1)
        src = unwrap_google_url(attr(attrs, "src") or attr(attrs, "data-src"))
        name = src.split("?")[0].rstrip("/").split("/")[-1]
        if name in EMBED_KINDS:
            block = {
                "type": "card",
                "kind": EMBED_KINDS[name],
                "title": attr(attrs, "title") or "",
                "src": name,
            }
            if block["kind"] == "icons" and catalog:
                block["items"] = list(catalog)
            blocks.append(block)
    if blocks:
        return blocks

    body_match = re.search(r"<body\b[^>]*>([\s\S]*)</body>", code or "", re.I)
    body = body_match.group(1) if body_match else (code or "")
    static = re.sub(r"<script\b[\s\S]*?</script>", "", body, flags=re.I)
    markers = []

    def add(token, block):
        index = static.find(token)
        if index >= 0:
            markers.append((index, block))

    add('id="fb-page-feed"', {
        "type": "card",
        "kind": "facebook",
        "title": "Fan Edit Fan Club on Facebook",
        "src": "embed-facebook.html",
    })
    group_at = static.find("25717067")
    if group_at < 0:
        group_at = static.find("facebook-group-posts")
    if group_at >= 0:
        markers.append((group_at, {
            "type": "card",
            "kind": "fb-group",
            "title": "Fan Edit Fan Club Facebook Group",
            "src": "embed-fb-group.html",
        }))
    add('id="community-rss-feed"', {
        "type": "card",
        "kind": "reddit-community",
        "title": "r/FanEditFanClub",
        "src": "embed-reddit-community.html",
    })
    add('id="custom-rss-feed"', {
        "type": "card",
        "kind": "reddit-feed",
        "title": "Fan Edit Fan Club Reddit Feed",
        "src": "embed-reddit-feed.html",
    })
    if "paypal-container-6N34NNU436TT4" in static:
        at = static.find("paypal-container")
        markers.append((at if at >= 0 else 0, {
            "type": "card",
            "kind": "paypal",
            "title": "Support Fan Edit Fan Club",
            "src": "embed-paypal.html",
        }))
    markers.sort(key=lambda item: item[0])
    blocks.extend(block for _, block in markers)
    blocks.extend(social_cards(static, page_ids, catalog, repairs, where))
    return blocks


def parse_sections(raw, page_ids, catalog, repairs, where):
    blocks = []
    for match in re.finditer(r"<section\b[^>]*>([\s\S]*?)</section>", raw or "", re.I):
        parser = SectionParser(page_ids, catalog, repairs, where)
        try:
            parser.feed(match.group(1))
            parser.close()
        except Exception as exc:
            print(f"site-pages: section parse skipped ({exc})")
            continue
        blocks.extend(parser.blocks)
    return merge_link_runs(blocks)


def merge_link_runs(blocks):
    merged = []
    for block in blocks:
        if (
            block.get("type") == "links"
            and not block.get("style")
            and merged
            and merged[-1].get("type") == "links"
            and not merged[-1].get("style")
        ):
            merged[-1]["items"].extend(block.get("items") or [])
            continue
        merged.append(block)
    return merged


def doc_blocks(doc_html, page_ids):
    cleaned = re.sub(r"<style\b[\s\S]*?</style>", "", doc_html or "", flags=re.I)
    cleaned = re.sub(r"<script\b[\s\S]*?</script>", "", cleaned, flags=re.I)
    body_match = re.search(r"<body\b[^>]*>([\s\S]*)</body>", cleaned, re.I)
    body = body_match.group(1) if body_match else cleaned

    class DocParser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.blocks = []
            self.capture = None
            self.buf = []
            self.skip = 0

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self.skip += 1
                return
            if self.skip:
                return
            data = dict(attrs)
            if tag in ("h1", "h2", "h3", "p", "li") and self.capture is None:
                self.capture = tag
                self.buf = []
            elif self.capture and tag == "a":
                href = html.escape(data.get("href") or "", quote=True)
                self.buf.append('<a href="%s">' % href)
            elif self.capture and tag == "br":
                self.buf.append("<br>")

        def handle_endtag(self, tag):
            if tag in ("script", "style") and self.skip:
                self.skip -= 1
                return
            if self.capture and tag == "a":
                self.buf.append("</a>")
                return
            if self.capture == tag:
                rendered = inline_html("".join(self.buf), page_ids)
                visible = plain_text(rendered)
                if visible:
                    font = "display" if tag in ("h1", "h2", "h3") else "body"
                    align = "center" if tag in ("h1", "h2") else "left"
                    self.blocks.append({
                        "type": "text",
                        "tag": "h2" if tag == "h1" else tag,
                        "html": rendered,
                        "align": align,
                        "font": font,
                    })
                self.capture = None
                self.buf = []

        def handle_data(self, data):
            if self.capture is not None and not self.skip:
                self.buf.append(data)

    parser = DocParser()
    parser.feed(body)
    parser.close()
    return parser.blocks[:400]


def find_doc_url(raw):
    """Document id from an embed iframe only. The Sites shell mentions docs.google.com."""
    for match in re.finditer(r"<iframe\b([^>]*)>", raw or "", re.I):
        src = attr(match.group(1), "src") or attr(match.group(1), "data-src")
        found = re.search(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)", src or "")
        if found:
            return "https://docs.google.com/document/d/%s/export?format=html" % found.group(1)
    return ""


def parse_nav(raw):
    items = []
    seen = set()
    pattern = re.compile(
        r"<a\b([^>]*\bdata-level=\"(\d)\"[^>]*)>([\s\S]*?)</a>",
        re.I,
    )
    for match in pattern.finditer(raw or ""):
        attrs, level, inner = match.group(1), match.group(2), match.group(3)
        href = unwrap_google_url(attr(attrs, "href"))
        label = tidy_inline(re.sub(r"<[^>]+>", " ", inner))
        if not label or not href:
            continue
        if level == "1":
            key = href.split("?")[0]
            if key in seen:
                break
            seen.add(key)
            external = href.startswith("http://") or href.startswith("https://")
            slug = ""
            if href.startswith("/") and not href.startswith("//"):
                slug = href.strip("/").split("/")[0] or "home"
            elif external and "discord.gg" in href:
                slug = "discord"
            elif external:
                slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "link"
            items.append({
                "id": slug or "home",
                "title": label,
                "href": href,
                "path": href if href.startswith("/") else "",
                "external": external and slug != "discord",
                "children": [],
            })
        elif level == "2" and items:
            items[-1]["children"].append({"label": label, "href": href})
    return items


def dedupe_links(items):
    kept = []
    seen = set()
    for item in items:
        href = item.get("href") or ""
        label = item.get("label") or ""
        key = (label_key(label), href)
        if not label or not href or key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return kept


def parse_page(raw, item, page_ids, catalog, repairs):
    blocks = parse_sections(raw, page_ids, catalog, repairs, item["title"])
    # The Master Links page is a Google Doc embed, which Sites will not let
    # the app iframe. Export the doc and keep its text and links instead.
    doc_url = find_doc_url(raw)
    if doc_url:
        status, _, body = http_get(doc_url)
        if status == 200 and body:
            doc = doc_blocks(body, page_ids)
            if doc:
                kept = [block for block in blocks if block.get("type") == "links"]
                blocks = kept + doc
                print(f"site-pages: {item['id']} synced {len(doc)} blocks from the Google Doc")
            else:
                repairs.append("%s: Google Doc exported empty" % item["title"])
        else:
            repairs.append("%s: Google Doc export failed (HTTP %s)" % (item["title"], status))
            blocks.append({
                "type": "links",
                "items": [{
                    "label": "Open Master Links",
                    "href": doc_url.replace("/export?format=html", "/preview"),
                }],
            })
    child_items = []
    for child in item.get("children") or []:
        href = unwrap_google_url(child.get("href") or "")
        if href.startswith("/") and not href.startswith("//"):
            slug = href.strip("/").split("/")[0]
            if slug in page_ids:
                href = "#" + slug
        if href_is_usable(href):
            child_items.append({"label": child["label"], "href": href})
    # A Sites button can store a cut-off copy of a menu URL. Prefer the menu copy.
    donors = {label_key(link["label"]): link["href"] for link in child_items}
    for block in blocks:
        if block.get("type") != "links" or block.get("style") == "channels":
            continue
        for link in block.get("items") or []:
            longer = donors.get(label_key(link.get("label")))
            href = link.get("href") or ""
            if longer and longer.startswith(href) and len(longer) > len(href) + 2:
                repairs.append("%s: restored %s from the site menu" % (item["title"], link["label"]))
                link["href"] = longer
    if child_items:
        existing_hrefs = set()
        existing_labels = set()
        for block in blocks:
            for link in block.get("items") or []:
                existing_hrefs.add(link.get("href"))
                existing_labels.add(label_key(link.get("label")))
        extra = [
            link for link in child_items
            if link["href"] not in existing_hrefs and label_key(link["label"]) not in existing_labels
        ]
        if extra:
            blocks.insert(0, {"type": "links", "items": dedupe_links(extra)})
    # Collapse duplicate link rows created above.
    blocks = merge_link_runs(blocks)
    for block in blocks:
        if block.get("type") == "links":
            block["items"] = dedupe_links(block.get("items") or [])
    blocks = [block for block in blocks if block.get("type") != "links" or block.get("items")]
    return {
        "id": item["id"],
        "title": item["title"],
        "url": SITE_ORIGIN + item["path"] if item.get("path") else item.get("href") or "",
        "blocks": blocks,
    }


def discord_page(item):
    return {
        "id": "discord",
        "title": item.get("title") or "Discord Server",
        "url": item.get("href") or "https://discord.gg/d8A9xHTey7",
        "blocks": [
            {
                "type": "text",
                "tag": "p",
                "html": "The club's Discord server. Open the chat when you want it. Until then, this page keeps scrolling.",
                "align": "center",
                "font": "display",
            },
            {
                "type": "card",
                "kind": "discord",
                "title": "Fan Edit Fan Club Discord",
                "src": "embed-discord.html",
            },
            {
                "type": "links",
                "items": [{
                    "label": "Open Discord",
                    "href": item.get("href") or "https://discord.gg/d8A9xHTey7",
                }],
            },
        ],
    }


def external_page(item):
    return {
        "id": item["id"],
        "title": item["title"],
        "url": item.get("href") or "",
        "blocks": [{
            "type": "links",
            "items": [{"label": item["title"], "href": item.get("href") or ""}],
        }],
    }


def previous_site_page(page_id):
    existing = load_json(SITE_PAGES_FILE) or {}
    for page in existing.get("pages") or []:
        if page.get("id") == page_id:
            return page
    return None


def refresh_site_pages():
    status, _, body = http_get(SITE_ORIGIN + "/home")
    if status != 200 or not body:
        print(f"site-pages: home HTTP {status}; keeping the last file")
        return
    nav = parse_nav(body)
    if len(nav) < 4:
        print("site-pages: navigation was too short; keeping the last file")
        return
    try:
        with open(ICON_CATALOG_FILE, encoding="utf-8") as handle:
            catalog = parse_icon_catalog(handle.read())
    except OSError:
        catalog = []
    page_ids = {item["id"] for item in nav}
    repairs = []
    pages = []
    for item in nav:
        if item["id"] == "discord":
            pages.append(discord_page(item))
            continue
        if item.get("external"):
            pages.append(external_page(item))
            continue
        page_status, _, page_body = http_get(SITE_ORIGIN + item["path"])
        if page_status != 200 or not page_body:
            print(f"site-pages: {item['path']} HTTP {page_status}; keeping the previous copy")
            previous = previous_site_page(item["id"])
            if previous:
                pages.append(previous)
            continue
        pages.append(parse_page(page_body, item, page_ids, catalog, repairs))
        print(f"site-pages: {item['id']} -> {len(pages[-1]['blocks'])} blocks")
    if len(pages) < 4:
        print("site-pages: not enough pages; keeping the last file")
        return
    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "source": SITE_ORIGIN,
        "nav": [{"id": item["id"], "title": item["title"]} for item in nav],
        "pages": pages,
        "limitations": [
            "Google Sites cannot be embedded, so page text is copied into this file on each feeds run.",
            "Per-letter coloring on the home page is flattened. The words, links, and headings are kept.",
            "Some All Channels hrefs are truncated inside the Google Sites HTML embed. Those labels are filled from embed-icons.html, the grid the homepage actually shows.",
            "Discord chat and the PayPal button stay live. They need a connection and are not copied into this file.",
            "The Facebook Group card still follows the free SociableKit snapshot, which updates when someone presses Request sync.",
        ],
        "repairs": repairs,
    }
    with open(SITE_PAGES_FILE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1)
        handle.write("\n")
    print(f"site-pages.json: wrote {len(pages)} pages, {len(repairs)} link repairs.")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    existing_profile = load_json("x-posts.json")
    refresh_x(existing_profile)
    write("fb-page.json", fetch_fb_page())
    write("fb-group.json", fetch_fb_group())
    # reddit-*.json are owned by the daily 5pm ET browser scan; never
    # write them here (Reddit RSS is dead as of 2026-11-13).
    try:
        refresh_site_pages()
    except Exception as exc:
        print(f"site-pages: {exc}; keeping the last file")


if __name__ == "__main__":
    sys.exit(main() or 0)
