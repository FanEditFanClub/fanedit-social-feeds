"""Unit tests for X list filtering. No network."""
import unittest

import fetch


def tweet(**kwargs):
    base = {
        "id_str": "1",
        "full_text": "Hello from the club",
        "created_at": "Thu Oct 08 12:00:00 +0000 2026",
        "conversation_id_str": "1",
        "permalink": "/Someone/status/1",
        "user": {
            "screen_name": "Someone",
            "name": "Someone",
            "profile_image_url_https": "https://example.com/a.jpg",
        },
        "entities": {"urls": [], "media": []},
    }
    base.update(kwargs)
    return base


class FilterTests(unittest.TestCase):
    def test_drops_reposts_and_replies(self):
        tweets = [
            tweet(id_str="10", full_text="Original post", conversation_id_str="10",
                  permalink="/Ada/status/10",
                  user={"screen_name": "Ada", "name": "Ada", "profile_image_url_https": ""}),
            tweet(id_str="11", full_text="RT @Other: nope", retweeted_status={"id_str": "9"},
                  conversation_id_str="11", permalink="/Ada/status/11"),
            tweet(id_str="12", full_text="@Bob this is a reply",
                  in_reply_to_status_id_str="8", in_reply_to_screen_name="Bob",
                  conversation_id_str="8", permalink="/Ada/status/12"),
            tweet(id_str="13", full_text="@Bob hidden reply",
                  display_text_range=[5, 17], conversation_id_str="13",
                  permalink="/Ada/status/13"),
        ]
        posts = fetch.select_originals(tweets)
        self.assertEqual([p["id"] for p in posts], ["10"])

    def test_author_cap_keeps_newer_posts(self):
        posts = []
        for i, handle in enumerate(["SopranosOrder", "SopranosOrder", "SopranosOrder", "Ada", "Ada", "Bea"]):
            posts.append({
                "id": str(i),
                "text": "t",
                "created_at": f"2026-10-08T12:0{5 - i}:00Z",
                "author_handle": handle,
            })
        shown = fetch.cap_authors(posts, per_author=2, limit=12)
        handles = [p["author_handle"] for p in shown]
        self.assertEqual(handles, ["SopranosOrder", "SopranosOrder", "Ada", "Ada", "Bea"])

    def test_expands_urls_and_unescapes(self):
        raw = tweet(
            full_text="Batman &amp; Robin https://t.co/abc",
            entities={"urls": [{
                "url": "https://t.co/abc",
                "expanded_url": "https://www.reddit.com/r/fanedits/comments/1/batman/",
            }], "media": []},
        )
        self.assertEqual(
            fetch.clean_text(raw),
            "Batman & Robin https://www.reddit.com/r/fanedits/comments/1/batman/",
        )

    def test_merge_prefers_syndication_and_keeps_buffer_gaps(self):
        syndication = [{
            "id": "100",
            "text": "From the timeline",
            "url": "https://x.com/FanEditFanClub/status/100",
            "created_at": "2026-10-08T08:01:14Z",
            "sent_at": "2026-10-08T08:01:14Z",
            "author_handle": "FanEditFanClub",
            "author_name": "Fan Edit Fan Club",
            "author_avatar": "https://example.com/p.jpg",
        }]
        buffer = [
            {
                "id": "100",
                "text": "Buffer copy of the same post",
                "url": "https://x.com/999/status/100",
                "sent_at": "2026-10-08T08:01:14.830Z",
            },
            {
                "id": "50",
                "text": "Only Buffer has this one",
                "url": "https://x.com/999/status/50",
                "sent_at": "2026-10-07T16:50:32.563Z",
            },
        ]
        merged = fetch.merge_profile(syndication, buffer, [])
        self.assertEqual([p["id"] for p in merged], ["100", "50"])
        self.assertEqual(merged[0]["text"], "From the timeline")
        self.assertEqual(merged[0]["url"], "https://x.com/FanEditFanClub/status/100")
        self.assertEqual(merged[0]["source"], "syndication")
        self.assertEqual(merged[1]["source"], "buffer")

    def test_parse_next_data_roundtrip(self):
        payload = {
            "props": {"pageProps": {
                "headerProps": {"name": "Fan Editors", "memberCount": 46},
                "timeline": {"entries": [
                    {"content": {"tweet": tweet(id_str="7", full_text="Listed")}},
                    {"content": {"tweet": tweet(
                        id_str="8", full_text="RT @Z: x", retweeted_status={"id_str": "1"},
                    )}},
                ]},
            }},
        }
        import json
        html = '<script id="__NEXT_DATA__" type="application/json">%s</script>' % json.dumps(payload)
        parsed = fetch.parse_syndication(html)
        self.assertEqual(parsed["header"]["name"], "Fan Editors")
        shown = fetch.cap_authors(fetch.select_originals(parsed["tweets"]))
        self.assertEqual(len(shown), 1)
        self.assertEqual(shown[0]["text"], "Listed")


if __name__ == "__main__":
    unittest.main()
