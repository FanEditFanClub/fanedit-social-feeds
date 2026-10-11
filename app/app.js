/* Fan Edit Fan Club installable app.
   Tabs come from site-pages.json. Feed cards read the same JSON as the
   website embeds, so a feeds run updates the app with no extra step. */
(function () {
  var REDDIT_MARK = '<svg class="icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M16.67 10a1.46 1.46 0 0 0-2.47-1 7.12 7.12 0 0 0-3.85-1.23l.65-3.08 2.13.45a1.08 1.08 0 1 0 1.13-1 1.08 1.08 0 0 0-1.07.82l-2.37-.5a.18.18 0 0 0-.21.14l-.74 3.47a7.14 7.14 0 0 0-3.86 1.23 1.46 1.46 0 1 0-1.61 2.39 2.87 2.87 0 0 0 0 .44c0 2.22 2.58 4 5.77 4s5.77-1.8 5.77-4a2.87 2.87 0 0 0 0-.44 1.46 1.46 0 0 0 .74-1.7z"/></svg>';

  var CARDS = {
    "x-list": {
      feed: "x-list.json",
      href: "https://x.com/i/lists/2072540475530084770",
      title: "Fan Editors",
      sub: "X list by @FanEditFanClub",
      pill: "Follow",
      more: "View more on X",
      mount: "posts"
    },
    "x-profile": {
      feed: "x-posts.json",
      href: "https://x.com/FanEditFanClub",
      title: "Fan Edit Fan Club",
      sub: "@FanEditFanClub on X",
      pill: "Follow",
      more: "View more on X",
      mount: "posts"
    },
    facebook: {
      feed: "fb-page.json",
      href: "https://www.facebook.com/FanEditFanClub",
      title: "Fan Edit Fan Club",
      sub: "Facebook Page",
      pill: "Follow",
      pillClass: "blue",
      more: "View more on Facebook",
      mount: "posts"
    },
    "fb-group": {
      feed: "fb-group.json",
      href: "https://www.facebook.com/groups/faneditfanclub",
      title: "Fan Edit Fan Club",
      sub: "Facebook Group",
      pill: "Join",
      pillClass: "blue",
      more: "View posts in the group",
      mount: "posts",
      hero: true
    },
    "reddit-community": {
      feed: "reddit-community.json",
      href: "https://www.reddit.com/r/FanEditFanClub",
      title: "r/FanEditFanClub",
      sub: "Latest discussions",
      subClass: "reddit",
      pill: "Open",
      pillClass: "reddit",
      more: "View more on Reddit",
      mount: "reddit",
      mark: true
    },
    "reddit-feed": {
      feed: "reddit-multireddit.json",
      href: "https://www.reddit.com/user/faneditfanclub/m/fan_edit_fan_club_reddit_feed/new",
      title: "Reddit Feed",
      sub: "Fan Edit Fan Club multireddit",
      subClass: "reddit",
      pill: "Open",
      pillClass: "reddit",
      more: "View more on Reddit",
      mount: "reddit",
      mark: true
    }
  };

  var PHONE_TABS = ["home", "discord", "x", "reddit"];
  var MORE_TABS = ["support-us", "master-links", "facebook", "all-channels"];
  var TAB_LABEL = {
    home: "Home",
    "support-us": "Support",
    "master-links": "Links",
    discord: "Discord",
    x: "X",
    facebook: "Facebook",
    reddit: "Reddit",
    "all-channels": "Channels"
  };
  var TAB_ICON = {
    home: '<path d="M4 10.6 12 4l8 6.6V20a1 1 0 0 1-1 1h-5.2v-6.2H10.2V21H5a1 1 0 0 1-1-1z"/>',
    discord: '<path d="M4.5 6.2A2.2 2.2 0 0 1 6.7 4h10.6a2.2 2.2 0 0 1 2.2 2.2v7.1a2.2 2.2 0 0 1-2.2 2.2H9.4L4.5 20v-4.5a2.2 2.2 0 0 1-2-2.2V6.2z"/>',
    x: '<path d="M5 4.5h3.2l3.1 4.3 3.5-4.3H19l-5.2 6.6 5.6 8.4h-3.2l-3.5-4.8-4.1 4.8H5.2l5.6-6.6z"/>',
    reddit: '<path d="M14.7 4.4a1.25 1.25 0 0 1 .15 1.55l-1.45.7a6.1 6.1 0 0 1 3.15 1.45 1.65 1.65 0 1 1 1.55 2.75c.08.38.1.76.1 1.15 0 3.15-2.95 5.45-6.2 5.45s-6.2-2.3-6.2-5.45c0-.39.02-.77.1-1.15a1.65 1.65 0 1 1 1.65-2.65 6.1 6.1 0 0 1 3.05-1.45l1.05-2.35a1.15 1.15 0 0 1 1.45-.55l.55.2zM9.15 11.3a1.15 1.15 0 1 0 .02 2.3 1.15 1.15 0 0 0-.02-2.3zm5.7 0a1.15 1.15 0 1 0 .02 2.3 1.15 1.15 0 0 0-.02-2.3zM8.7 15.05c.85.7 2.05.95 3.3.95s2.45-.25 3.3-.95"/>',
    more: '<circle cx="6" cy="12" r="1.7"/><circle cx="12" cy="12" r="1.7"/><circle cx="18" cy="12" r="1.7"/>',
    "support-us": '<path d="M12 19.3S5.6 15.2 5.6 10.4A3.6 3.6 0 0 1 12 8.3a3.6 3.6 0 0 1 6.4 2.1c0 4.8-6.4 8.9-6.4 8.9z"/>',
    "master-links": '<path d="M9.2 8H7.4a3.5 3.5 0 0 0 0 7h1.8M14.8 8h1.8a3.5 3.5 0 0 1 0 7h-1.8M8.6 11.5h6.8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
    facebook: '<path d="M13.8 8.2H16.5V5h-2.7A3.5 3.5 0 0 0 10.3 8.5V10H8v3.1h2.3V20h3.2v-6.9h2.6l.5-3.1h-3.1V8.7c0-.3.2-.5.6-.5z"/>',
    "all-channels": '<path d="M4.8 4.8h5.6v5.6H4.8zM13.6 4.8h5.6v5.6h-5.6zM4.8 13.6h5.6v5.6H4.8zM13.6 13.6h5.6v5.6h-5.6z"/>'
  };

  var main = document.getElementById("main");
  var tabs = document.getElementById("tabs");
  var moreSheet = document.getElementById("more-sheet");
  var moreBackdrop = document.getElementById("more-backdrop");
  var phoneTabs = window.matchMedia("(max-width: 719px)");
  var installBtn = document.getElementById("install-btn");
  var installTip = document.getElementById("install-tip");
  var iosHint = document.getElementById("ios-hint");
  var bundle = null;
  var deferredPrompt = null;

  function repoRoot() {
    var path = location.pathname;
    var at = path.indexOf("/app/");
    if (at === -1 && /\/app$/.test(path)) {
      return location.origin + path.replace(/\/app$/, "/");
    }
    if (at === -1) return location.origin + "/";
    return location.origin + path.slice(0, at + 1);
  }

  function asset(path) {
    return new URL(path, repoRoot()).href;
  }

  function pageId() {
    var hash = (location.hash || "#home").replace(/^#\/?/, "");
    return hash || "home";
  }

  function standalone() {
    return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  }

  function ios() {
    var ua = navigator.userAgent || "";
    return /iphone|ipad|ipod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  }

  function glueElement(el) {
    var words = (el.textContent || "").trim().split(/\s+/).filter(Boolean);
    if (words.length < 3) return;
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    var nodes = [];
    while (walker.nextNode()) {
      if (walker.currentNode.nodeValue && walker.currentNode.nodeValue.trim()) {
        nodes.push(walker.currentNode);
      }
    }
    if (!nodes.length) return;
    var last = nodes[nodes.length - 1];
    var match = last.nodeValue.match(/^([\s\S]*\S)\s+(\S+)\s*$/);
    if (match) {
      last.nodeValue = match[1] + "\u00A0" + match[2];
      return;
    }
    if (nodes.length < 2) return;
    var prev = nodes[nodes.length - 2];
    prev.nodeValue = prev.nodeValue.replace(/\s+$/, "");
    last.nodeValue = "\u00A0" + last.nodeValue.replace(/^\s+/, "");
  }

  function glueWidows(root) {
    var nodes = root.querySelectorAll("p.prose, h1.prose, h2.prose, h3.prose, .doc li, .post-text, .link-label, .card h1, .sub, .empty");
    Array.prototype.forEach.call(nodes, glueElement);
  }

  function tuneMail(root) {
    var fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    if (!fine) return;
    var links = root.querySelectorAll('a[href^="mailto:"]');
    Array.prototype.forEach.call(links, function (link) {
      if (!/faneditfanclub@gmail\.com/i.test(link.getAttribute("href") || "")) return;
      link.href = "https://mail.google.com/mail/?view=cm&fs=1&to=FanEditFanClub@gmail.com";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    });
  }

  function externalAttrs(href) {
    if (/^https?:/i.test(href) || /^mailto:/i.test(href)) {
      return ' target="_blank" rel="noopener noreferrer"';
    }
    return "";
  }

  function linkRow(items, style) {
    if (style === "channels") {
      var grid = document.createElement("div");
      grid.className = "channels wide";
      items.forEach(function (item) {
        var link = document.createElement("a");
        link.className = "channel";
        link.href = item.href;
        if (/^https?:/i.test(item.href) || /^mailto:/i.test(item.href)) {
          link.target = "_blank";
          link.rel = "noopener noreferrer";
        }
        if (item.icon) {
          var img = document.createElement("img");
          img.alt = "";
          img.src = item.icon;
          link.appendChild(img);
        }
        var label = document.createElement("span");
        label.className = "link-label";
        label.textContent = item.label;
        link.appendChild(label);
        grid.appendChild(link);
      });
      return grid;
    }
    var row = document.createElement("div");
    row.className = "link-row wide";
    items.forEach(function (item) {
      var link = document.createElement("a");
      link.className = "pill";
      link.href = item.href;
      if (/^https?:/i.test(item.href) || /^mailto:/i.test(item.href)) {
        link.target = "_blank";
        link.rel = "noopener noreferrer";
      }
      link.textContent = item.label;
      row.appendChild(link);
    });
    return row;
  }

  function textBlock(block) {
    var tag = block.tag === "h1" || block.tag === "h2" || block.tag === "h3" ? block.tag : "p";
    var el = document.createElement(tag);
    el.className = "prose wide " + (block.font === "body" ? "body left" : "display");
    el.innerHTML = block.html || "";
    return el;
  }

  function mountPaypal() {
    function render() {
      var box = document.getElementById("paypal-box");
      if (!box || !window.paypal || !window.paypal.HostedButtons) return;
      window.paypal.HostedButtons({
        hostedButtonId: "6N34NNU436TT4",
        style: {
          layout: "vertical",
          color: "gold",
          shape: "rect",
          label: "paypal",
          tagline: false
        }
      }).render("#paypal-box");
    }
    if (window.paypal && window.paypal.HostedButtons) {
      render();
      return;
    }
    var existing = document.getElementById("paypal-sdk");
    if (existing) {
      existing.addEventListener("load", render);
      return;
    }
    var script = document.createElement("script");
    script.id = "paypal-sdk";
    script.src = "https://www.paypal.com/sdk/js?client-id=BAAOf94djAa5CPNEqov7_VKaz7cLdghzLv-FPW4D7z_hdQO3rHzp9pDbwfzzdkO3T7b4Pk1lNIITEstuss&components=hosted-buttons&enable-funding=venmo&currency=USD";
    script.onload = render;
    document.head.appendChild(script);
  }

  function frame(src, title, paypal) {
    var wrap = document.createElement("div");
    wrap.className = "frame-wrap wide" + (paypal ? " paypal" : "");
    var iframe = document.createElement("iframe");
    iframe.src = asset(src);
    iframe.title = title || "Fan Edit Fan Club";
    iframe.loading = "lazy";
    wrap.appendChild(iframe);
    return wrap;
  }

  function renderIcons(block, host) {
    function paint(items) {
      host.appendChild(linkRow(items, "channels"));
      glueWidows(host);
      tuneMail(host);
    }
    if (block.kind === "icons" || block.src === "embed-icons.html") {
      fetch(asset("embed-icons.html"), { cache: "no-cache" }).then(function (response) {
        if (!response.ok) throw new Error(String(response.status));
        return response.text();
      }).then(function (html) {
        var doc = new DOMParser().parseFromString(html, "text/html");
        var items = Array.prototype.map.call(doc.querySelectorAll("a.icon-btn"), function (anchor) {
          var img = anchor.querySelector("img");
          return {
            label: anchor.getAttribute("data-label") || anchor.getAttribute("title") || "",
            href: anchor.getAttribute("href") || "",
            icon: img ? img.getAttribute("src") || "" : ""
          };
        }).filter(function (item) { return item.label && item.href; });
        if (!items.length) throw new Error("empty");
        paint(items);
      }).catch(function () {
        if (block.items && block.items.length) paint(block.items);
      });
      return;
    }
    paint(block.items || []);
  }

  function renderCard(block) {
    if (block.kind === "icons") {
      var holder = document.createElement("div");
      holder.className = "wide";
      renderIcons(block, holder);
      return holder;
    }
    if (block.kind === "discord") {
      var discord = document.createElement("article");
      discord.className = "card wide";
      discord.innerHTML =
        '<header class="bar"><a class="brand" href="https://discord.gg/d8A9xHTey7" target="_blank" rel="noopener noreferrer">' +
        '<img class="avatar" alt="" src="icons/icon-192.png"><span class="brand-text">' +
        '<h1>Discord</h1><p class="sub">Live chat with the club</p></span></a></header>' +
        '<p class="sub">Show the chat when you want to type. The page keeps scrolling until then.</p>' +
        '<div class="chat-actions"><button type="button" class="pill" id="chat-toggle">Show chat</button></div>';
      var slot = document.createElement("div");
      discord.appendChild(slot);
      discord.querySelector("#chat-toggle").addEventListener("click", function () {
        var open = slot.firstChild;
        if (open) {
          slot.textContent = "";
          this.textContent = "Show chat";
          return;
        }
        slot.appendChild(frame("embed-discord.html", "Fan Edit Fan Club Discord", false));
        this.textContent = "Done";
      });
      return discord;
    }
    if (block.kind === "paypal") {
      var pay = document.createElement("article");
      pay.className = "card wide paypal-card";
      pay.innerHTML = "<h1>Support Fan Edit Fan Club</h1>" +
        "<p class=\"sub\">Safe &amp; Secure Payment via PayPal or Venmo</p>" +
        "<div id=\"paypal-box\"></div>";
      return pay;
    }
    var spec = CARDS[block.kind];
    if (!spec || !window.FanEmbed) {
      var fallback = document.createElement("p");
      fallback.className = "prose display wide";
      fallback.textContent = block.title || "This part of the club will show up on the next refresh.";
      return fallback;
    }
    var article = document.createElement("article");
    article.className = "card";
    var header = document.createElement("header");
    header.className = spec.hero ? "bar" : "bar";
    var brand = document.createElement("a");
    brand.className = "brand";
    brand.href = spec.href;
    brand.target = "_blank";
    brand.rel = "noopener noreferrer";
    if (spec.mark) {
      brand.insertAdjacentHTML("afterbegin", REDDIT_MARK);
    } else {
      var avatar = document.createElement("img");
      avatar.className = "avatar";
      avatar.alt = "";
      avatar.src = "https://i.imgur.com/xGyaOEB.jpeg";
      brand.appendChild(avatar);
    }
    var who = document.createElement("span");
    who.className = "brand-text";
    var title = document.createElement("h1");
    title.textContent = block.title || spec.title;
    var sub = document.createElement("p");
    sub.className = "sub" + (spec.subClass ? " " + spec.subClass : "");
    sub.textContent = spec.sub;
    who.appendChild(title);
    who.appendChild(sub);
    brand.appendChild(who);
    var pill = document.createElement("a");
    pill.className = "pill" + (spec.pillClass ? " " + spec.pillClass : "");
    pill.href = spec.href;
    pill.target = "_blank";
    pill.rel = "noopener noreferrer";
    pill.textContent = spec.pill;
    header.appendChild(brand);
    header.appendChild(pill);
    if (spec.hero) {
      var hero = document.createElement("div");
      hero.className = "hero";
      hero.appendChild(header);
      article.appendChild(hero);
    } else {
      article.appendChild(header);
    }
    var posts = document.createElement("div");
    posts.className = "posts";
    posts.innerHTML = '<p class="empty">Loading posts…</p>';
    article.appendChild(posts);
    var more = document.createElement("a");
    more.className = "more" + (spec.pillClass ? " " + spec.pillClass : "");
    more.href = spec.href;
    more.target = "_blank";
    more.rel = "noopener noreferrer";
    more.textContent = spec.more;
    article.appendChild(more);
    var options = {
      feed: asset(spec.feed),
      root: posts,
      fit: false,
      max: 20,
      onRender: function () { glueWidows(article); }
    };
    if (spec.mount === "reddit") {
      FanEmbed.mountReddit(options);
    } else {
      options.onData = function (data) {
        if (block.kind === "x-list" && data.list) {
          if (data.list.name) title.textContent = data.list.name;
          if (data.list.owner_avatar) brand.querySelector("img").src = data.list.owner_avatar;
          if (data.list.member_count) sub.textContent = data.list.member_count + " members · @FanEditFanClub";
        }
        if (block.kind === "facebook" && data.profile) {
          if (data.profile.name) title.textContent = data.profile.name;
          if (data.profile.picture) brand.querySelector("img").src = data.profile.picture;
        }
        if (block.kind === "x-profile" && data.profile && data.profile.picture) {
          brand.querySelector("img").src = data.profile.picture;
        }
      };
      FanEmbed.mountPosts(options);
    }
    return article;
  }

  function renderBlocks(blocks) {
    var page = document.createElement("div");
    page.className = "page";
    var list = null;
    function closeList() {
      if (list && list.childElementCount) page.appendChild(list);
      list = null;
    }
    var skipPair = false;
    (blocks || []).forEach(function (block, index) {
      if (skipPair) {
        skipPair = false;
        return;
      }
      if (block.type === "text" && block.tag === "li") {
        if (!list) {
          list = document.createElement("ul");
          list.className = "doc wide prose body";
        }
        var item = document.createElement("li");
        item.innerHTML = block.html || "";
        list.appendChild(item);
        return;
      }
      closeList();
      if (block.type === "text") {
        page.appendChild(textBlock(block));
      } else if (block.type === "links") {
        if (block.style === "channels") {
          var holder = document.createElement("div");
          holder.className = "wide";
          renderIcons(block, holder);
          page.appendChild(holder);
        } else if (block.items && block.items.length) {
          page.appendChild(linkRow(block.items));
        }
      } else if (block.type === "card") {
        var next = (blocks || [])[index + 1];
        if (block.kind === "facebook" && next && next.type === "card" && next.kind === "fb-group") {
          var pair = document.createElement("div");
          pair.className = "card-pair wide";
          pair.appendChild(renderCard(block));
          pair.appendChild(renderCard(next));
          page.appendChild(pair);
          skipPair = true;
          return;
        }
        var card = renderCard(block);
        if (block.kind === "discord" || block.kind === "paypal" || block.kind === "icons") {
          card.classList.add("wide");
        }
        page.appendChild(card);
        if (block.kind === "paypal") mountPaypal();
      }
    });
    closeList();
    glueWidows(page);
    tuneMail(page);
    return page;
  }

  function findPage(id) {
    var pages = (bundle && bundle.pages) || [];
    for (var i = 0; i < pages.length; i++) {
      if (pages[i].id === id) return pages[i];
    }
    return pages[0] || null;
  }

  function closeMore() {
    moreSheet.hidden = true;
    moreBackdrop.hidden = true;
    var btn = document.getElementById("more-tab");
    if (btn) btn.setAttribute("aria-expanded", "false");
  }

  function tabGlyph(name) {
    var wrap = document.createElement("span");
    wrap.className = "tab-icon";
    wrap.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + (TAB_ICON[name] || TAB_ICON.more) + "</svg>";
    return wrap;
  }

  function makeTab(item, current) {
    var link = document.createElement("a");
    link.href = "#" + item.id;
    link.appendChild(tabGlyph(item.id));
    var label = document.createElement("span");
    label.textContent = TAB_LABEL[item.id] || item.title;
    link.appendChild(label);
    if (item.id === current) link.setAttribute("aria-current", "page");
    return link;
  }

  function renderTabs(current) {
    var nav = (bundle && bundle.nav) || [];
    var byId = {};
    nav.forEach(function (item) { byId[item.id] = item; });
    closeMore();
    tabs.innerHTML = "";
    moreSheet.innerHTML = "";
    if (!phoneTabs.matches) {
      nav.forEach(function (item) { tabs.appendChild(makeTab(item, current)); });
      fitTabs();
      return;
    }
    PHONE_TABS.forEach(function (id) {
      if (byId[id]) tabs.appendChild(makeTab(byId[id], current));
    });
    var extras = [];
    MORE_TABS.forEach(function (id) {
      if (byId[id]) extras.push(byId[id]);
    });
    nav.forEach(function (item) {
      if (PHONE_TABS.indexOf(item.id) === -1 && MORE_TABS.indexOf(item.id) === -1) extras.push(item);
    });
    if (!extras.length) {
      fitTabs();
      return;
    }
    var more = document.createElement("button");
    more.type = "button";
    more.id = "more-tab";
    more.className = "tab";
    more.setAttribute("aria-expanded", "false");
    more.setAttribute("aria-controls", "more-sheet");
    more.appendChild(tabGlyph("more"));
    var moreLabel = document.createElement("span");
    moreLabel.textContent = "More";
    more.appendChild(moreLabel);
    if (extras.some(function (item) { return item.id === current; })) {
      more.setAttribute("aria-current", "page");
    }
    more.addEventListener("click", function () {
      var open = moreSheet.hidden;
      moreSheet.hidden = !open;
      moreBackdrop.hidden = !open;
      more.setAttribute("aria-expanded", open ? "true" : "false");
    });
    tabs.appendChild(more);
    extras.forEach(function (item) {
      var link = document.createElement("a");
      link.href = "#" + item.id;
      link.textContent = item.title;
      if (item.id === current) link.setAttribute("aria-current", "page");
      link.addEventListener("click", closeMore);
      moreSheet.appendChild(link);
    });
    fitTabs();
  }

  function fitTabs() {
    var height = tabs.offsetHeight || 96;
    document.documentElement.style.setProperty("--tabs-h", height + "px");
  }

  function render() {
    var id = pageId();
    var page = findPage(id);
    if (!page && bundle && bundle.pages && bundle.pages.length) {
      page = bundle.pages[0];
      id = page.id;
    }
    renderTabs(page ? page.id : id);
    main.innerHTML = "";
    if (!page) {
      var note = document.createElement("p");
      note.className = "prose display";
      note.textContent = "The club pages didn't load. Check your connection and try again.";
      var wrap = document.createElement("div");
      wrap.className = "page";
      wrap.appendChild(note);
      main.appendChild(wrap);
      return;
    }
    document.title = page.id === "home" ? "Fan Edit Fan Club" : page.title + " · Fan Edit Fan Club";
    main.appendChild(renderBlocks(page.blocks));
    window.scrollTo(0, 0);
    fitTabs();
  }

  function showInstall() {
    if (standalone()) {
      installBtn.hidden = true;
      iosHint.hidden = true;
      return;
    }
    installBtn.hidden = false;
    if (ios() && localStorage.getItem("fefc-ios-hint") !== "1") {
      iosHint.hidden = false;
    }
  }

  installBtn.addEventListener("click", function () {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
        installBtn.hidden = true;
        installTip.hidden = true;
      });
      return;
    }
    installTip.textContent = ios()
      ? "Tap the Share button, then Add to Home Screen."
      : "Open the browser menu and choose Install app.";
    installTip.hidden = !installTip.hidden;
  });

  document.getElementById("ios-dismiss").addEventListener("click", function () {
    iosHint.hidden = true;
    try { localStorage.setItem("fefc-ios-hint", "1"); } catch (err) { /* private mode */ }
  });

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferredPrompt = event;
    if (!standalone()) installBtn.hidden = false;
  });

  window.addEventListener("appinstalled", function () {
    installBtn.hidden = true;
    installTip.hidden = true;
    iosHint.hidden = true;
  });

  moreBackdrop.addEventListener("click", closeMore);
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeMore();
  });
  if (phoneTabs.addEventListener) {
    phoneTabs.addEventListener("change", function () { renderTabs(pageId()); });
  }

  window.addEventListener("hashchange", render);
  window.addEventListener("resize", fitTabs);

  showInstall();

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(function () {});
  }

  fetch(asset("site-pages.json"), { cache: "no-cache" }).then(function (response) {
    if (!response.ok) throw new Error(String(response.status));
    return response.json();
  }).then(function (data) {
    bundle = data;
    render();
  }).catch(function () {
    render();
  });
})();
