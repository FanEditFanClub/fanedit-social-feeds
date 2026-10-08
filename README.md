# fanedit-social-feeds

Public JSON feeds and scroll-safe embed pages for the [Fan Edit Fan Club](https://www.faneditfanclub.com) Google Site. Feeds refresh every 30 minutes from GitHub Actions and are served by GitHub Pages.

## Feeds

- `x-list.json` — Fan Editors X list (`2072540475530084770`). Built from X's public syndication timeline. Replies and reposts are removed. No author appears more than twice, so SopranosOrder cannot fill the card. On HTTP 429 or any other failure the previous file is kept.
- `x-posts.json` — @FanEditFanClub posts. Syndication (the profile timeline, plus the club's posts from the list) is preferred. Buffer fills in posts that were not in that window. Buffer-only text is the fallback when syndication is rate limited.
- `fb-page.json` — Facebook Page posts (Graph API).
- `fb-group.json` — Facebook Group posts. Facebook removed the Groups API in April 2024 and the Page Plugin cannot show a group, so there is no direct free feed. `fetch.py` copies the public JSON behind the club's existing SociableKit "Facebook Group Posts" widget (embed `25717067`, the one `website-widgets.html` used). On SociableKit's free plan that snapshot only changes after **Request sync** in the SociableKit dashboard (about once a day at most); paid plans sync automatically. Each post shows its date so an old snapshot is obvious. If the feed fails the previous file is kept, and with no posts the card shows the group description.
- `reddit-community.json` / `reddit-multireddit.json` — written by the daily browser scan, not by `fetch.py`.

X's syndication host allows about 30 requests per 15 minutes **per IP**. GitHub-hosted runners share IP addresses, so Actions often receives HTTP 429. `fetch.py` waits only if the limit resets within a minute, otherwise it backs off once and leaves the last good JSON in place. The site never replaces a good feed with a blank one.

## Google Sites embeds

Google Sites sizes each Embed box as width × a ratio, and that box gets shorter when the screen gets narrower. The ratio is set by dragging, so it will only be close (a 5:8 box might land around 5:7.6 or 5:8.4). These pages fit that: the document is the iframe, overflow is hidden, nothing inside scrolls, and `touch-action: pan-y` lets a vertical swipe move the page.

Type and spacing use one unit, `--u = min(1vw, 1vh / ratio)`. At the documented ratio, and when the box is a bit taller, that unit is the width, so the layout stays the designed size and the extra height is empty space. When the box is a bit shorter, the unit shrinks until the same layout fits the height. Aim for the ratio below. About 10% either way still fits.

Base URL: `https://faneditfanclub.github.io/fanedit-social-feeds/`

Embed code (swap the file name and title). The box ratio is set in the Sites editor, not by the iframe height:

```html
<iframe src="https://faneditfanclub.github.io/fanedit-social-feeds/embed-x-list.html" title="Fan Editors on X" style="width:100%;height:100%;border:0;"></iframe>
```

| Page | Box ratio (W:H) | Height ÷ width | Replaces |
| --- | --- | --- | --- |
| `embed-x-list.html` | **5:8** | 1.60 | Fan Editors list card (the old `widgets.js` timeline) |
| `embed-x-profile.html` | **5:8** | 1.60 | @FanEditFanClub card |
| `embed-facebook.html` | **5:8** | 1.60 | Facebook Page card |
| `embed-reddit-community.html` | **4:5** | 1.25 | r/FanEditFanClub card |
| `embed-reddit-feed.html` | **4:5** | 1.25 | Multireddit card |
| `embed-discord.html` | **2:3** | 1.50 | `discord-embed.html` |
| `embed-fb-group.html` | **5:4** | 0.80 | Facebook Group block: cover (`fb-group-cover.jpg`), name, **Join**, the recent posts from `fb-group.json` that fit, and **View posts in the group** (`https://www.facebook.com/groups/faneditfanclub`) |
| `embed-paypal.html` | **4:5** | 1.25 | PayPal / Venmo card (hosted button `6N34NNU436TT4`). The amount field and buttons stay inside the box; the PayPal window may open as a popup |
| `embed-icons.html` | **11:6** | 0.545 | Social icon grid, 11 columns × 6 rows. The Website icon opens `https://www.faneditfanclub.com`. The Email icon opens a new email to FanEditFanClub@gmail.com (see below) |

Do not drop a 5:8 card into a full-width desktop section. At 1366px that box is 2186px tall. Use columns; Google Sites stacks a multi-column section into full width on phones.

Homepage, top to bottom:

| Row | Cards | How to place it | At ~400px wide | At 390px phone |
| --- | --- | --- | --- | --- |
| 1 | X list, X profile, Facebook Page | 3 columns, about 400px each | 400×640 (5:8) | 390×624, stacked |
| 2 | r/FanEditFanClub, Reddit multireddit | 2 columns | half the section, still 4:5 | 390×488, stacked |
| 3 | Discord | its own row, about 800px wide so the chat stays usable | 800×1200 (2:3) | 390×585 |
| 4 | Facebook Group, PayPal | 2 columns, about 400–480px. PayPal is 4:5 and the group card is 5:4, so the PayPal box is taller | group 480×384, PayPal 480×600 | group 390×312, PayPal 390×488, stacked |
| 5 | Icon grid | full width. 11:6 is short enough to span the section | 1366×745, 1200×655, 768×419 | 390×213 |

Discord is the exception to the leftover-space rule: its two panels fill the box, so a taller box gives the chat more room and a shorter box still does not scroll the page. The tap button shrinks with the short box.

Feed cards stack posts from the top with one fixed gap. `embed.js` renders the whole feed, then hides the posts that would be cut off; a post that only fits without its image (or with two lines of text) is shown that way. A taller box shows more posts, and any leftover space sits under the last post, never between posts. Blank lines inside a post are collapsed. Tap a post to open it on X, Facebook, or Reddit. Follow / View more links are on the card. Timestamps are ISO-8601 UTC with a numeric offset (`2026-10-08T13:00:00+00:00`, which is 9:00 AM US Eastern). The card formats them with `Intl` in the viewer's local time zone.

`embed-discord.html` keeps the live Discord widget (server `1529915531736383702`) and the WidgetBot chat (channel `1529915534466875546`) at every width, including phones. On a touch screen a transparent layer lets the page scroll; **Tap to interact** hands touches to the chat, and **Done** gives scrolling back. Desktop has no overlay.

Email icon: Google Sites puts every embed in an iframe sandboxed with `allow-popups allow-popups-to-escape-sandbox` but no top navigation, and some phone browsers drop a `mailto:` that tries to navigate that iframe. The link uses `target="_blank"`, so the tap opens an unsandboxed window that hands `mailto:` to the phone's mail app. On a mouse/trackpad device (`(hover: hover) and (pointer: fine)`), where `mailto:` often has no mail app behind it, the link opens Gmail compose (`https://mail.google.com/mail/?view=cm&fs=1&to=FanEditFanClub@gmail.com`) in a new tab.

`embed-icons.html` does not reflow. All 66 icons stay on 6 rows, and the icon size follows `--u`, so 390px and 1200px are the same grid at different scales.

Once these nine boxes are on the homepage, `website-widgets.html` is unused. The old URLs stay up until the Site is switched: `website-widgets.html`, `discord-embed.html`, `facebook-tab.html`, `reddit-tab.html`, `support-tab.html`. `x-tab.html` still loads, but it reads `x-list.json` / `x-posts.json` and no longer requests Facebook, Reddit, PayPal, or `widgets.js`.
