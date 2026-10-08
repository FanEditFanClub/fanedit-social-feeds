# fanedit-social-feeds

Public JSON feeds and scroll-safe embed pages for the [Fan Edit Fan Club](https://www.faneditfanclub.com) Google Site. Feeds refresh every 30 minutes from GitHub Actions and are served by GitHub Pages.

## Feeds

- `x-list.json` — Fan Editors X list (`2072540475530084770`). Built from X's public syndication timeline. Replies and reposts are removed. No author appears more than twice, so SopranosOrder cannot fill the card. On HTTP 429 or any other failure the previous file is kept.
- `x-posts.json` — @FanEditFanClub posts. Syndication (the profile timeline, plus the club's posts from the list) is preferred. Buffer fills in posts that were not in that window. Buffer-only text is the fallback when syndication is rate limited.
- `fb-page.json` — Facebook Page posts (Graph API).
- `reddit-community.json` / `reddit-multireddit.json` — written by the daily browser scan, not by `fetch.py`.

X's syndication host allows about 30 requests per 15 minutes **per IP**. GitHub-hosted runners share IP addresses, so Actions often receives HTTP 429. `fetch.py` waits only if the limit resets within a minute, otherwise it backs off once and leaves the last good JSON in place. The site never replaces a good feed with a blank one.

## Google Sites embeds

Google Sites sizes each Embed box as width × a fixed ratio, and that box gets shorter when the screen gets narrower. These pages are built to that box: the document is exactly the iframe, type and spacing scale with the width, overflow is hidden, and nothing inside the card scrolls. Set each box to the ratio below (drag the embed until the shape matches). A page that is a little shorter than the box just shows black; it will not grow a scrollbar.

Base URL: `https://faneditfanclub.github.io/fanedit-social-feeds/`

Embed code (swap the file name). The box ratio is set in the Sites editor, not by the iframe height:

```html
<iframe src="https://faneditfanclub.github.io/fanedit-social-feeds/embed-x-list.html" title="Fan Editors on X" style="width:100%;height:100%;border:0;"></iframe>
```

| New page | Box ratio (W:H) | Height ÷ width | Replaces |
| --- | --- | --- | --- |
| `embed-x-list.html` | **5:8** | 1.60 | Fan Editors list card in `website-widgets.html` and the list half of `x-tab.html` (the old `widgets.js` timeline) |
| `embed-x-profile.html` | **5:8** | 1.60 | @FanEditFanClub card in `website-widgets.html` and the profile half of `x-tab.html` |
| `embed-facebook.html` | **5:8** | 1.60 | Facebook Page card in `website-widgets.html` / `facebook-tab.html` |
| `embed-reddit-community.html` | **4:5** | 1.25 | r/FanEditFanClub card in `website-widgets.html` / `reddit-tab.html` |
| `embed-reddit-feed.html` | **4:5** | 1.25 | Multireddit card in `website-widgets.html` / `reddit-tab.html` |
| `embed-discord.html` | **2:3** | 1.50 | `discord-embed.html` on the homepage |

Example box sizes when the embed spans the content width:

| Ratio | 390px wide | 768px wide | 1366px wide |
| --- | --- | --- | --- |
| 5:8 | 390×624 | 768×1229 | 1366×2186 |
| 4:5 | 390×488 | 768×960 | 1366×1708 |
| 2:3 | 390×585 | 768×1152 | 1366×2049 |

On a phone, give each card its own embed. Do not put these pages back inside one tall iframe. A narrower column on desktop (around 420–560px) keeps the type at a normal size; the ratio still fits.

Each card shows 4 posts (5 on the Reddit cards). Tap a post to open it on X, Facebook, or Reddit. Follow / View more links are on the card.

`embed-discord.html` keeps the live Discord widget (server `1529915531736383702`) and the WidgetBot chat (channel `1529915534466875546`) at every width, including phones. On a touch screen a transparent layer lets the page scroll; **Tap to interact** hands touches to the chat, and **Done** gives scrolling back. Desktop has no overlay.

The old URLs stay in place until the Site is switched: `website-widgets.html`, `discord-embed.html`, `facebook-tab.html`, `reddit-tab.html`, `support-tab.html`. `x-tab.html` still loads, but it now reads `x-list.json` / `x-posts.json` and no longer requests Facebook, Reddit, PayPal, or `widgets.js`. PayPal, the social icon grid, and the Facebook Group widget remain on `website-widgets.html` / `support-tab.html` — give them their own sections on the Site when you retire that page. The Facebook Group block is a third-party scroller; it is the one homepage piece these new cards do not replace.
