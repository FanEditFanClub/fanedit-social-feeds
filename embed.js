/* Renders posts into .posts, then keeps only the ones that fit the box.
   Posts stack from the top with a fixed gap; a taller box shows more posts.
   No scrolling, no widgets.js. */
(function (global) {
  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function parseTime(value) {
    if (value == null || value === "") return null;
    if (typeof value === "number") return new Date(value * 1000);
    var text = String(value).trim().replace(/Z$/, "+00:00");
    text = text.replace(/([+-]\d{2})(\d{2})$/, "$1:$2");
    var date = new Date(text);
    return isNaN(date.getTime()) ? null : date;
  }

  function fmt(value) {
    var date = parseTime(value);
    if (!date) return "";
    try {
      /* No timeZone option: Intl uses the viewer's local zone. */
      return new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit"
      }).format(date);
    } catch (err) {
      return "";
    }
  }

  function load(path) {
    return fetch(path, { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    });
  }

  function setMessage(message, el) {
    el = el || document.getElementById("posts");
    if (el) el.innerHTML = '<p class="empty">' + esc(message) + "</p>";
  }

  /* Collapse blank lines so a clamped post does not spend a line on nothing. */
  function tidy(text) {
    return String(text == null ? "" : text)
      .replace(/\r/g, "")
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n{2,}/g, "\n")
      .trim();
  }

  /* Keep the posts that fit inside .posts and hide the rest. A post that
     is just too tall gets one more chance as a compact post (two lines, no
     image) so leftover space is filled with a post instead of a gap. The
     first post always stays so a very short box is never empty. */
  function fit(el) {
    var items = el.querySelectorAll(".post");
    if (!items.length) return;
    for (var i = 0; i < items.length; i++) {
      items[i].hidden = false;
      items[i].classList.remove("compact");
    }
    var limit = el.getBoundingClientRect().bottom + 0.5;
    var cut = false;
    for (var j = 1; j < items.length; j++) {
      var item = items[j];
      if (cut) { item.hidden = true; continue; }
      if (item.getBoundingClientRect().bottom <= limit) continue;
      item.classList.add("compact");
      if (item.getBoundingClientRect().bottom <= limit) continue;
      item.classList.remove("compact");
      item.hidden = true;
      cut = true;
    }
  }

  function keepFitted(el) {
    var run = function () { fit(el); };
    run();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(run);
    var timer = null;
    window.addEventListener("resize", function () {
      clearTimeout(timer);
      timer = setTimeout(run, 60);
    });
    if (typeof ResizeObserver === "function") new ResizeObserver(run).observe(el);
  }

  function avatarHtml(url) {
    if (!url) return '<span class="avatar fallback" aria-hidden="true"></span>';
    return '<img class="avatar" alt="" src="' + esc(url) + '" onerror="this.onerror=null;this.className=\'avatar fallback\';this.removeAttribute(\'src\')">';
  }

  function mountPosts(options) {
    var el = options.root || document.getElementById("posts");
    load(options.feed).then(function (data) {
      if (typeof options.onData === "function") options.onData(data || {});
      var posts = (data && data.posts) || [];
      if (!el) return;
      if (!posts.length) {
        setMessage("No posts yet.", el);
        return;
      }
      var profile = (data && data.profile) || {};
      var fallbackAvatar = options.avatar || profile.picture || "";
      var fallbackName = options.name || profile.name || "";
      var fallbackHandle = (options.handle || profile.handle || "").replace(/^@/, "");
      el.innerHTML = posts.slice(0, options.max || 10).map(function (post) {
        var name = post.author_name || fallbackName;
        var handle = String(post.author_handle || fallbackHandle).replace(/^@/, "");
        var when = fmt(post.created_at || post.sent_at || post.published);
        var meta = (handle ? "@" + handle : "");
        if (when) meta = meta ? meta + " · " + when : when;
        var image = post.image || "";
        var media = image
          ? '<span class="media-frame"><img alt="" src="' + esc(image) + '" onerror="this.parentNode.remove()"></span>'
          : "";
        return '<a class="post' + (image ? " has-media" : "") + '" href="' + esc(post.url) + '" target="_blank" rel="noopener noreferrer">' +
          '<span class="post-head">' +
            avatarHtml(post.author_avatar || fallbackAvatar) +
            '<span class="who"><span class="name">' + esc(name) + "</span>" +
            '<span class="meta">' + esc(meta) + "</span></span></span>" +
          '<span class="post-text">' + esc(tidy(post.text)).replace(/\n/g, "<br>") + "</span>" +
          media +
        "</a>";
      }).join("");
      if (options.fit !== false) keepFitted(el);
      if (typeof options.onRender === "function") options.onRender(el);
    }).catch(function () {
      setMessage("Unable to load posts.", el);
    });
  }

  function mountReddit(options) {
    var el = options.root || document.getElementById("posts");
    load(options.feed).then(function (data) {
      var posts = (data && data.posts) || [];
      if (!el) return;
      if (!posts.length) {
        setMessage("No posts yet.", el);
        return;
      }
      el.innerHTML = posts.slice(0, options.max || 10).map(function (post) {
        var when = fmt(post.published);
        var sub = post.subreddit ? "r/" + post.subreddit : "";
        var meta = sub && when ? sub + " · " + when : (sub || when);
        return '<a class="post reddit-post" href="' + esc(post.url) + '" target="_blank" rel="noopener noreferrer">' +
          '<span class="post-text">' + esc(tidy(post.title).replace(/\n/g, " ")) + "</span>" +
          '<span class="meta reddit">' + esc(meta) + "</span>" +
        "</a>";
      }).join("");
      if (options.fit !== false) keepFitted(el);
      if (typeof options.onRender === "function") options.onRender(el);
    }).catch(function () {
      setMessage("Unable to load posts.", el);
    });
  }

  global.FanEmbed = {
    esc: esc,
    fmt: fmt,
    load: load,
    tidy: tidy,
    keepFitted: keepFitted,
    avatarHtml: avatarHtml,
    mountPosts: mountPosts,
    mountReddit: mountReddit
  };
})(window);
