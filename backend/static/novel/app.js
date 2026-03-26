const API = "/novel-api";
let token = localStorage.getItem("novel_token") || "";

function api(path, opts = {}) {
  const h = { "Content-Type": "application/json", ...opts.headers };
  if (token) h.Authorization = "Bearer " + token;
  return fetch(API + path, { ...opts, headers: h }).then(async (r) => {
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || r.statusText);
    return data;
  });
}

function show(id) {
  document.querySelectorAll("[data-page]").forEach((el) => el.classList.add("hidden"));
  const p = document.getElementById(id);
  if (p) p.classList.remove("hidden");
}

function renderHome() {
  Promise.all([
    api("/novels?sort=hot&per_page=8"),
    api("/novels?sort=update&per_page=8"),
    api("/categories"),
  ])
    .then(([hot, latest, cats]) => {
      document.getElementById("hotList").innerHTML = (hot.novels || [])
        .map(
          (n) => `
        <div class="card" data-slug="${n.slug}">
          <h3>${escapeHtml(n.title)}</h3>
          <div class="meta">${escapeHtml(n.author || "")} · ${n.word_count || 0} 字 · ${n.status || ""}</div>
        </div>`
        )
        .join("");
      document.getElementById("latestList").innerHTML = (latest.novels || [])
        .map(
          (n) => `
        <div class="card" data-slug="${n.slug}">
          <h3>${escapeHtml(n.title)}</h3>
          <div class="meta">更新 ${(n.chapter_updated_at || "").slice(0, 16)}</div>
        </div>`
        )
        .join("");
      document.getElementById("catNav").innerHTML = (cats.categories || [])
        .map((c) => `<a href="#" data-cat="${c.slug}">${escapeHtml(c.name)}</a>`)
        .join(" · ");
      bindCards("#hotList");
      bindCards("#latestList");
      document.querySelectorAll("#catNav a").forEach((a) => {
        a.addEventListener("click", (e) => {
          e.preventDefault();
          location.hash = "#/category/" + a.dataset.cat;
        });
      });
    })
    .catch((e) => alert(e.message));
}

function bindCards(sel) {
  document.querySelectorAll(sel + " .card").forEach((c) => {
    c.addEventListener("click", () => {
      location.hash = "#/novel/" + c.dataset.slug;
    });
  });
}

function escapeHtml(s) {
  if (!s) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderCategory(slug) {
  show("page-category");
  const sort = document.getElementById("catSort").value;
  api("/novels?category=" + encodeURIComponent(slug) + "&sort=" + sort + "&per_page=20")
    .then((d) => {
      document.getElementById("catTitle").textContent = "分类：" + slug;
      document.getElementById("catList").innerHTML = (d.novels || [])
        .map(
          (n) => `
        <div class="card" data-slug="${n.slug}">
          <h3>${escapeHtml(n.title)}</h3>
          <div class="meta">${escapeHtml(n.author || "")} · ${n.word_count || 0} 字</div>
        </div>`
        )
        .join("");
      bindCards("#catList");
    })
    .catch((e) => alert(e.message));
}

function renderDetail(slug) {
  show("page-detail");
  api("/novels/by-slug/" + encodeURIComponent(slug))
    .then((n) => {
      document.getElementById("detailTitle").textContent = n.title;
      document.getElementById("detailMeta").textContent = `${n.author || ""} · ${n.category_name || ""} · ${n.word_count || 0} 字 · ${n.status || ""} · 读 ${n.read_count || 0} · 藏 ${n.favorite_count || 0}`;
      document.getElementById("detailIntro").textContent = n.intro || "暂无简介";
      document.getElementById("detailChapters").innerHTML = (n.chapters || [])
        .map(
          (ch) =>
            `<div><a href="#" data-ch="${ch.chapter_no}">第${ch.chapter_no}章 ${escapeHtml(ch.title || "")}</a></div>`
        )
        .join("");
      document.getElementById("btnRead").onclick = () => {
        const first = (n.chapters || [])[0];
        if (first) location.hash = "#/read/" + slug + "/" + first.chapter_no;
      };
      document.getElementById("btnFav").onclick = () => {
        if (!token) {
          alert("请先登录");
          location.hash = "#/login";
          return;
        }
        api("/novels/" + n.id + "/favorite", { method: "POST" })
          .then(() => alert("已加入收藏"))
          .catch((e) => alert(e.message));
      };
      document.querySelectorAll("#detailChapters a").forEach((a) => {
        a.addEventListener("click", (e) => {
          e.preventDefault();
          location.hash = "#/read/" + slug + "/" + a.dataset.ch;
        });
      });
    })
    .catch((e) => alert(e.message));
}

function renderRead(slug, ch) {
  show("page-read");
  api("/novels/by-slug/" + encodeURIComponent(slug) + "/chapter/" + ch)
    .then((data) => {
      document.getElementById("readTitle").textContent = data.title || "";
      document.getElementById("readBody").textContent = data.content || "";
      document.getElementById("readNav").innerHTML = `
        <button class="btn btn-ghost" id="prevCh" ${data.prev_chapter == null ? "disabled" : ""}>上一章</button>
        <button class="btn btn-ghost" id="nextCh" ${data.next_chapter == null ? "disabled" : ""}>下一章</button>
        <a href="#" id="backToc">目录</a>`;
      document.getElementById("prevCh").onclick = () => {
        if (data.prev_chapter != null) location.hash = "#/read/" + slug + "/" + data.prev_chapter;
      };
      document.getElementById("nextCh").onclick = () => {
        if (data.next_chapter != null) location.hash = "#/read/" + slug + "/" + data.next_chapter;
      };
      document.getElementById("backToc").onclick = (e) => {
        e.preventDefault();
        location.hash = "#/novel/" + slug;
      };
      if (token && data.novel_id) {
        api("/me/progress", {
          method: "POST",
          body: JSON.stringify({
            novel_id: data.novel_id,
            chapter_no: parseInt(ch, 10),
            scroll_offset: 0,
          }),
        }).catch(() => {});
      }
    })
    .catch((e) => alert(e.message));
}

function renderSearch(q) {
  show("page-search");
  api("/search?q=" + encodeURIComponent(q))
    .then((d) => {
      document.getElementById("searchHint").textContent = d.message || "共 " + (d.total || 0) + " 本";
      document.getElementById("searchList").innerHTML = (d.novels || [])
        .map(
          (n) => `
        <div class="card" data-slug="${n.slug}">
          <h3>${escapeHtml(n.title)}</h3>
          <div class="meta">${escapeHtml(n.author || "")}</div>
        </div>`
        )
        .join("");
      bindCards("#searchList");
    })
    .catch((e) => alert(e.message));
}

function renderUser() {
  show("page-user");
  if (!token) {
    document.getElementById("userGuest").classList.remove("hidden");
    document.getElementById("userMain").classList.add("hidden");
    return;
  }
  document.getElementById("userGuest").classList.add("hidden");
  document.getElementById("userMain").classList.remove("hidden");
  api("/me")
    .then((u) => {
      document.getElementById("userName").textContent = u.user.username;
    })
    .catch(() => {});
  api("/me/favorites")
    .then((d) => {
      document.getElementById("favList").innerHTML = (d.novels || [])
        .map(
          (n) => `<div class="card" data-slug="${n.slug}"><h3>${escapeHtml(n.title)}</h3></div>`
        )
        .join("");
      bindCards("#favList");
    })
    .catch(() => {});
  api("/me/history")
    .then((d) => {
      document.getElementById("histList").innerHTML = (d.items || [])
        .map(
          (n) =>
            `<div class="card" data-slug="${n.slug}"><h3>${escapeHtml(n.title)}</h3><div class="meta">第${n.chapter_no}章</div></div>`
        )
        .join("");
      bindCards("#histList");
    })
    .catch(() => {});
}

document.getElementById("btnSearch").addEventListener("click", () => {
  const q = document.getElementById("q").value.trim();
  if (q) location.hash = "#/search/" + encodeURIComponent(q);
});

document.getElementById("catSort").addEventListener("change", () => {
  const h = location.hash.match(/#\/category\/(.+)/);
  if (h) renderCategory(decodeURIComponent(h[1]));
});

document.getElementById("btnLogout").addEventListener("click", () => {
  token = "";
  localStorage.removeItem("novel_token");
  renderUser();
});

document.getElementById("formLogin").addEventListener("submit", (e) => {
  e.preventDefault();
  const u = document.getElementById("loginUser").value;
  const p = document.getElementById("loginPass").value;
  api("/auth/login", { method: "POST", body: JSON.stringify({ username: u, password: p }) })
    .then((d) => {
      token = d.token;
      localStorage.setItem("novel_token", token);
      location.hash = "#/user";
    })
    .catch((e) => alert(e.message));
});

document.getElementById("formReg").addEventListener("submit", (e) => {
  e.preventDefault();
  const u = document.getElementById("regUser").value;
  const p = document.getElementById("regPass").value;
  api("/auth/register", { method: "POST", body: JSON.stringify({ username: u, password: p }) })
    .then(() => alert("注册成功，请登录"))
    .catch((e) => alert(e.message));
});

function route() {
  const h = location.hash.slice(1) || "/";
  if (h === "/" || h === "") {
    show("page-home");
    renderHome();
  } else if (h.startsWith("/category/")) {
    renderCategory(decodeURIComponent(h.slice("/category/".length)));
  } else if (h.startsWith("/novel/")) {
    renderDetail(decodeURIComponent(h.slice("/novel/".length)));
  } else if (h.startsWith("/read/")) {
    const parts = h.slice("/read/".length).split("/");
    renderRead(decodeURIComponent(parts[0]), parseInt(parts[1], 10));
  } else if (h.startsWith("/search/")) {
    renderSearch(decodeURIComponent(h.slice("/search/".length)));
  } else if (h.startsWith("/user") || h === "/login") {
    renderUser();
  }
}

window.addEventListener("hashchange", route);
token = localStorage.getItem("novel_token") || "";
route();
