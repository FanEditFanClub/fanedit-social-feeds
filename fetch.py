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


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    existing_profile = load_json("x-posts.json")
    refresh_x(existing_profile)
    write("fb-page.json", fetch_fb_page())
    write("fb-group.json", fetch_fb_group())
    # reddit-*.json are owned by the daily 5pm ET browser scan; never
    # write them here (Reddit RSS is dead as of 2026-11-13).


if __name__ == "__main__":
    sys.exit(main() or 0)
