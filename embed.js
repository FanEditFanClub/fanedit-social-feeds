/* Renders a fixed number of posts into .posts. No scrolling, no widgets.js. */
(function (global) {
  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmt(value) {
    if (!value) return "";
    var date = new Date(value);
    if (isNaN(date.getTime())) return "";
    try {
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

  function setMessage(message) {
    var el = document.getElementById("posts");
    if (el) el.innerHTML = '<p class="empty">' + esc(message) + "</p>";
  }

  function avatarHtml(url) {
    if (!url) return '<span class="avatar fallback" aria-hidden="true"></span>';
    return '<img class="avatar" alt="" src="' + esc(url) + '">';
  }

  function mountPosts(options) {
    load(options.feed).then(function (data) {
      if (typeof options.onData === "function") options.onData(data || {});
      var posts = (data && data.posts) || [];
      var el = document.getElementById("posts");
      if (!el) return;
      if (!posts.length) {
        setMessage("No posts yet.");
        return;
      }
      var profile = (data && data.profile) || {};
      var fallbackAvatar = options.avatar || profile.picture || "";
      var fallbackName = options.name || profile.name || "";
      var fallbackHandle = (options.handle || profile.handle || "").replace(/^@/, "");
      el.innerHTML = posts.slice(0, options.count || 4).map(function (post) {
        var name = post.author_name || fallbackName;
        var handle = String(post.author_handle || fallbackHandle).replace(/^@/, "");
        var when = fmt(post.created_at || post.sent_at || post.published);
        var meta = (handle ? "@" + handle : "");
        if (when) meta = meta ? meta + " · " + when : when;
        return '<a class="post" href="' + esc(post.url) + '" target="_blank" rel="noopener noreferrer">' +
          '<span class="post-head">' +
            avatarHtml(post.author_avatar || fallbackAvatar) +
            '<span class="who"><span class="name">' + esc(name) + "</span>" +
            '<span class="meta">' + esc(meta) + "</span></span></span>" +
          '<span class="post-text">' + esc(post.text || "").replace(/\n/g, "<br>") + "</span>" +
        "</a>";
      }).join("");
    }).catch(function () {
      setMessage("Unable to load posts.");
    });
  }

  function mountReddit(options) {
    load(options.feed).then(function (data) {
      var posts = (data && data.posts) || [];
      var el = document.getElementById("posts");
      if (!el) return;
      if (!posts.length) {
        setMessage("No posts yet.");
        return;
      }
      el.innerHTML = posts.slice(0, options.count || 5).map(function (post) {
        var when = fmt(post.published);
        var sub = post.subreddit ? "r/" + post.subreddit : "";
        var meta = sub && when ? sub + " · " + when : (sub || when);
        return '<a class="post reddit-post" href="' + esc(post.url) + '" target="_blank" rel="noopener noreferrer">' +
          '<span class="post-text">' + esc(post.title || "") + "</span>" +
          '<span class="meta reddit">' + esc(meta) + "</span>" +
        "</a>";
      }).join("");
    }).catch(function () {
      setMessage("Unable to load posts.");
    });
  }

  global.FanEmbed = {
    esc: esc,
    fmt: fmt,
    load: load,
    mountPosts: mountPosts,
    mountReddit: mountReddit
  };
})(window);
