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

    def test_to_iso_uses_numeric_utc_offset(self):
        self.assertEqual(
            fetch.to_iso("Thu Oct 08 13:00:00 +0000 2026"),
            "2026-10-08T13:00:00+00:00",
        )
        self.assertEqual(
            fetch.to_iso("2026-10-08T01:40:36+0000"),
            "2026-10-08T01:40:36+00:00",
        )
        self.assertEqual(
            fetch.to_iso("2026-10-08T08:01:14.830Z"),
            "2026-10-08T08:01:14+00:00",
        )

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


class GroupTests(unittest.TestCase):
    def test_group_text_strips_markdown(self):
        text = fetch.group_text("# Rules** Group:**\n\n1. **No Spam.**\n[Site](https://example.com)")
        self.assertEqual(text, "Rules Group:\n1. No Spam.\nSite")

    def test_sociablekit_time_is_utc_plus_8(self):
        self.assertEqual(fetch.sk_time("2026-09-28 01:37:41"), "2026-09-27T17:37:41+00:00")
        self.assertEqual(fetch.sk_time("0000-00-00 00:00:00"), "")

    def test_fetch_fb_group_keeps_group_posts_only(self):
        sample = {"last_sync_info": "2026-09-28 01:37:41", "posts": [
            {"post_id": "1", "post_link": "https://www.facebook.com/groups/faneditfanclub/posts/1/",
             "description": "Older", "publish_date": "2026-09-25 16:10:00", "profile_name": "A"},
            {"post_id": "2", "post_link": "https://www.facebook.com/groups/faneditfanclub/posts/2/",
             "description": "Newer", "publish_date": "2026-09-27 12:57:53", "profile_name": "B"},
            {"post_id": "3", "post_link": "https://example.com/elsewhere", "description": "Skip"},
        ]}
        original = fetch.http_json
        fetch.http_json = lambda *args, **kwargs: sample
        try:
            payload = fetch.fetch_fb_group()
        finally:
            fetch.http_json = original
        self.assertEqual([p["text"] for p in payload["posts"]], ["Newer", "Older"])
        self.assertEqual(payload["source_synced_at"], "2026-09-27T17:37:41+00:00")

    def test_fetch_fb_group_failure_keeps_file(self):
        original = fetch.http_json
        fetch.http_json = lambda *args, **kwargs: None
        try:
            self.assertIsNone(fetch.fetch_fb_group())
        finally:
            fetch.http_json = original


class SitePageTests(unittest.TestCase):
    def test_spans_join_without_extra_spaces(self):
        fragment = (
            "<span>D</span><span>edicated</span> to "
            "<span>T</span><span>he Art</span>"
        )
        self.assertEqual(fetch.inline_html(fragment, set()), "Dedicated to The Art")

    def test_inline_link_unwraps_google_redirect(self):
        fragment = (
            '<a href="https://www.google.com/url?q=https%3A%2F%2Fdiscord.gg%2Fd8A9xHTey7&amp;sa=D">'
            "Discord Server</a>"
        )
        rendered = fetch.inline_html(fragment, set())
        self.assertIn('href="https://discord.gg/d8A9xHTey7"', rendered)
        self.assertIn(">Discord Server</a>", rendered)
        self.assertIn('target="_blank"', rendered)

    def test_site_path_becomes_app_hash(self):
        rendered = fetch.inline_html('<a href="/master-links">Master Links</a>', {"master-links"})
        self.assertIn('href="#master-links"', rendered)
        self.assertNotIn("target=", rendered)

    def test_repairs_truncated_channel_link(self):
        catalog = [{"label": "Rockstar Games", "href": "https://socialclub.rockstargames.com/member/FanEditFanClub", "icon": ""}]
        repairs = []
        fixed = fetch.repair_links(
            [{"label": "Rockstar", "href": "https://www.paypal.biz/faneditfanclub701"}],
            catalog,
            repairs,
            "All Channels",
        )
        self.assertEqual(fixed[0]["href"], catalog[0]["href"])
        self.assertTrue(repairs)

    def test_section_keeps_embed_and_drops_sites_chrome(self):
        raw = """
        <section>
          <h2><span>About Us</span></h2>
          <p><span>We</span><span>'re a Community</span></p>
          <div data-code="&lt;iframe src=&quot;https://faneditfanclub.github.io/fanedit-social-feeds/embed-discord.html&quot; title=&quot;Discord&quot;&gt;&lt;/iframe&gt;"></div>
          <p>Report abuse</p>
        </section>
        """
        blocks = fetch.parse_sections(raw, set(), [], [], "Home")
        self.assertEqual(blocks[0]["html"], "About Us")
        self.assertEqual(fetch.plain_text(blocks[1]["html"]), "We're a Community")
        self.assertEqual(blocks[2]["kind"], "discord")
        self.assertEqual(len(blocks), 3)

    def test_doc_keeps_links(self):
        raw = (
            "<body><ul><li><span><a href=\"https://www.google.com/url?q="
            "https%3A%2F%2Ffanedit.org&amp;sa=D\">FANEDIT.ORG</a></span></li></ul></body>"
        )
        blocks = fetch.doc_blocks(raw, set())
        self.assertEqual(len(blocks), 1)
        self.assertIn('href="https://fanedit.org"', blocks[0]["html"])
        self.assertIn("FANEDIT.ORG", blocks[0]["html"])

    def test_nav_stops_when_the_bar_repeats(self):
        raw = """
        <a data-level="1" href="/home">Home</a>
        <a data-level="1" href="/x">X</a>
        <a data-level="2" href="https://www.google.com/url?q=https%3A%2F%2Fx.com%2FFanEditFanClub">X Profile</a>
        <a data-level="1" href="/home">Home</a>
        """
        nav = fetch.parse_nav(raw)
        self.assertEqual([item["id"] for item in nav], ["home", "x"])
        self.assertEqual(nav[1]["children"][0]["href"], "https://x.com/FanEditFanClub")


if __name__ == "__main__":
    unittest.main()
