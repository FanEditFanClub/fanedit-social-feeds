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

  var main = document.getElementById("main");
  var tabs = document.getElementById("tabs");
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
    (blocks || []).forEach(function (block) {
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

  function renderTabs(current) {
    var nav = (bundle && bundle.nav) || [];
    tabs.innerHTML = "";
    nav.forEach(function (item) {
      var link = document.createElement("a");
      link.href = "#" + item.id;
      link.textContent = item.title;
      if (item.id === current) link.setAttribute("aria-current", "page");
      tabs.appendChild(link);
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
