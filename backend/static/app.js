const API = "/api";
let currentTaskId = null;
let refreshTimer = null;
let refreshInterval = 30;
let filesByAgent = {};
let selectedAgentTab = null;
let novelData = null;
let runMode = "prod";

function api(path, options = {}) {
  return fetch(API + path, { ...options, headers: { "Content-Type": "application/json", ...options.headers } })
    .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); });
}

function setRefreshInterval(sec) {
  refreshInterval = sec;
  document.getElementById("refreshVal").textContent = sec;
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refreshAll, sec * 1000);
}

function refreshAll() {
  if (currentTaskId) {
    api("/tasks/" + currentTaskId + "/progress").then(renderProgress).catch(() => {});
    api("/tasks/" + currentTaskId + "/files/by-agent").then(d => {
      filesByAgent = d.by_agent || {};
      renderAgentFileTabs();
      if (selectedAgentTab && filesByAgent[selectedAgentTab]) {
        document.getElementById("agentFileList").innerHTML = renderAgentFiles(filesByAgent[selectedAgentTab]);
        bindFilePreviewButtons();
      }
    }).catch(() => {});
    api("/tasks/" + currentTaskId + "/novel").then(d => {
      novelData = d;
      renderNovelToc(d);
    }).catch(() => { novelData = null; document.getElementById("novelToc").innerHTML = "<p class='hint'>成书未生成或任务未选</p>"; });
    const agent = document.getElementById("agentSelect").value;
    api("/tasks/" + currentTaskId + "/logs/" + agent + "?limit=100").then(d => { renderLogs(d.logs); }).catch(() => {});
  } else {
    document.getElementById("agentFileTabs").innerHTML = "";
    document.getElementById("agentFileList").innerHTML = "<p class='hint'>请先选择任务</p>";
    document.getElementById("novelToc").innerHTML = "";
  }
  api("/tasks/current").then(d => {
    const running = d.running;
    const paused = d.paused;
    const autoRun = !!d.auto_run;
    document.getElementById("currentRun").textContent = running ? (paused ? "已暂停: " + d.task_id : "运行中: " + d.task_id) : "";
    document.getElementById("btnStop").disabled = !running;
    // 连续模式下允许继续点“启动”，后端会新建排队任务，不冲掉当前任务
    document.getElementById("btnStart").disabled = running && !autoRun;
    document.getElementById("btnPause").disabled = !running || paused;
    document.getElementById("btnResume").disabled = !paused;
    const chk = document.getElementById("chkAutoRun");
    if (chk && d.auto_run !== undefined) { chk.checked = !!d.auto_run; }
  }).catch(() => {});
  api("/run-mode").then(d => {
    runMode = d.mode || "prod";
    const badge = document.getElementById("runModeBadge");
    const btn = document.getElementById("btnToggleMode");
    if (badge) {
      if (runMode === "test") {
        const tc = d.test_chapters || 6;
        const target = d.normal_target_chapters || tc;
        badge.textContent = "模式：测试" + tc + "章 / 目标" + target + "章";
      } else {
        badge.textContent = "模式：正式模式";
      }
    }
    if (btn) btn.textContent = runMode === "test" ? "切到正式模式" : "切到测试6章";
  }).catch(() => {});
  api("/tasks").then(d => {
    const list = document.getElementById("taskList");
    list.innerHTML = (d.tasks || []).map(t => `
      <li>
        <span class="task-name" data-id="${t.task_id}">${escapeHtml(t.name || t.task_id)}</span>
        <span class="task-status">${renderTaskStatus(t)}</span>
        <button class="task-act task-select" data-id="${t.task_id}" type="button">选择</button>
        <button class="task-act task-start" data-id="${t.task_id}" type="button">启动</button>
        <button class="task-act task-delete" data-id="${t.task_id}" type="button" title="删除任务">删除</button>
      </li>
    `).join("");
    list.querySelectorAll(".task-name, .task-select").forEach(el => {
      el.addEventListener("click", () => { currentTaskId = el.dataset.id; selectedAgentTab = null; refreshAll(); document.getElementById("btnStart").disabled = false; });
    });
    list.querySelectorAll(".task-start").forEach(el => {
      el.addEventListener("click", (e) => { e.stopPropagation(); const id = el.dataset.id; api("/tasks/" + id + "/start", { method: "POST" }).then(() => { currentTaskId = id; refreshAll(); }).catch(err => alert(err.message || "启动失败")); });
    });
    list.querySelectorAll(".task-delete").forEach(el => {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = el.dataset.id;
        if (!confirm("确定删除该任务？删除后不可恢复。")) return;
        fetch(API + "/tasks/" + id, { method: "DELETE" })
          .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
          .then(() => { if (currentTaskId === id) currentTaskId = null; refreshAll(); })
          .catch(err => alert(err.message || "删除失败"));
      });
    });
  }).catch(() => {});
}

function renderTaskStatus(task) {
  const status = task.status || "";
  let label = status;
  if (status === "failed" && task.warning) {
    label = "completed（" + task.warning + "）";
  } else if (status === "failed" && task.error) {
    label = "failed（" + task.error + "）";
  }
  const mode = task.run_mode === "test" ? "测试6章" : "正式";
  return escapeHtml(label + " · " + mode);
}

function renderProgress(summary) {
  const overall = document.getElementById("overallProgress");
  const cards = document.getElementById("agentCards");
  const agents = Object.entries(summary || {});
  const completed = agents.filter(([, v]) => v.status === "completed").length;
  const total = agents.length;
  overall.textContent = `整体进度：${completed}/${total} 个 Agent 已完成`;
  cards.innerHTML = agents.map(([name, v]) => {
    let msg = v.message || "—";
    if (v.status === "failed" && msg.length > 20) msg = "失败（点击查看）";
    else if (v.progress_percent) msg += " " + v.progress_percent + "%";
    return `
    <div class="agent-card ${v.status}" data-agent="${name}" data-full-msg="${escapeHtml((v.message || "").replace(/"/g, "&quot;"))}" title="点击查看详情">
      <div class="name">${name}</div>
      <div class="msg">${escapeHtml(msg)}</div>
    </div>
  `;
  }).join("");
  cards.querySelectorAll(".agent-card").forEach(card => {
    card.addEventListener("click", () => {
      document.getElementById("agentSelect").value = card.dataset.agent;
      const agent = card.dataset.agent;
      const p = summary[agent];
      const fullMsg = card.dataset.fullMsg != null ? card.dataset.fullMsg : (p.message || "");
      document.getElementById("agentDetail").innerHTML = `
        <strong>${agent}</strong><br/>
        状态: ${p.status} | 进度: ${p.progress_percent || 0}%<br/>
        ${fullMsg ? escapeHtml(fullMsg) : "—"}
      `;
      api("/tasks/" + currentTaskId + "/logs/" + agent + "?limit=100").then(d => renderLogs(d.logs)).catch(() => {});
    });
  });
}

function renderLogs(logs) {
  const container = document.getElementById("logContainer");
  container.innerHTML = (logs || []).map(l => `
    <div class="log-line ${l.level === "error" ? "log-error" : ""}">
      <span class="log-time">${(l.time || "").replace("T", " ").slice(0, 19)}</span>
      ${escapeHtml(l.message)}
    </div>
  `).join("");
}

const AGENT_LABELS = {
  TrendAgent: "热门趋势",
  StyleAgent: "风格解析",
  PlannerAgent: "策划大纲",
  WriterAgent: "正文生成",
  PolishAgent: "润色",
  AuditorAgent: "质量审计",
  ReviserAgent: "修订定稿"
};

function renderAgentFileTabs() {
  const container = document.getElementById("agentFileTabs");
  const agents = Object.keys(filesByAgent).filter(a => (filesByAgent[a] || []).length > 0);
  if (!agents.length) {
    container.innerHTML = "<p class='hint'>暂无产出文件</p>";
    return;
  }
  container.innerHTML = agents.map(name => `
    <button type="button" class="tab ${selectedAgentTab === name ? "active" : ""}" data-agent="${name}">${AGENT_LABELS[name] || name}</button>
  `).join("");
  container.querySelectorAll(".tab").forEach(btn => {
    btn.addEventListener("click", () => {
      selectedAgentTab = btn.dataset.agent;
      document.getElementById("agentFileList").innerHTML = renderAgentFiles(filesByAgent[selectedAgentTab] || []);
      bindFilePreviewButtons();
      renderAgentFileTabs();
    });
  });
}

function renderAgentFiles(files) {
  if (!files.length) return "<p class='hint'>该 Agent 暂无产出</p>";
  const base = "/api/tasks/" + currentTaskId + "/files/download?path=";
  return files.map(f => `
    <div class="file-row">
      <a href="${base + encodeURIComponent(f.path)}" target="_blank">${escapeHtml(f.path)}</a> (${f.size || 0} B)
      <button class="btn-mini btn-preview" type="button" data-path="${escapeHtml(f.path)}">预览</button>
    </div>
  `).join("");
}

function bindFilePreviewButtons() {
  document.querySelectorAll("#agentFileList .btn-preview").forEach(btn => {
    btn.addEventListener("click", () => viewFileInModal(btn.dataset.path));
  });
}

function renderNovelToc(data) {
  const container = document.getElementById("novelToc");
  if (!data || !data.toc || !data.toc.length) {
    container.innerHTML = "<p class='hint'>成书未生成</p>";
    return;
  }
  container.innerHTML = `
    <div class="toc-title">${escapeHtml(data.title)}</div>
    <ul class="toc-list">
      ${data.toc.map((item, idx) => `<li><a href="#" data-chapter-index="${idx}">${escapeHtml(item.label)}</a></li>`).join("")}
    </ul>
  `;
  container.querySelectorAll(".toc-list a").forEach(a => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      openChapterModal(parseInt(a.dataset.chapterIndex, 10));
    });
  });
}

let currentChapterIndex = -1;

function openChapterModal(index) {
  if (!novelData || !novelData.chapters || !novelData.chapters[index]) return;
  currentChapterIndex = index;
  const ch = novelData.chapters[index];
  document.getElementById("modalTitle").textContent = ch.title || ("第" + (index + 1) + "章");
  document.getElementById("modalChapterNav").style.display = "flex";
  document.getElementById("chapterIndicator").textContent = (index + 1) + " / " + novelData.chapters.length;
  const isMarkdown = true;
  document.getElementById("modalBody").innerHTML = "<div class='chapter-content'>" + (window.marked ? marked.parse(ch.content || "") : escapeHtml(ch.content || "")) + "</div>";
  document.getElementById("btnPrevChapter").disabled = index <= 0;
  document.getElementById("btnNextChapter").disabled = index >= novelData.chapters.length - 1;
  document.getElementById("previewModal").setAttribute("aria-hidden", "false");
}

let outlinePage = 1;
const outlinePerPage = 30;

function viewFileInModal(path) {
  if (!currentTaskId) return;
  currentChapterIndex = -1;
  document.getElementById("modalChapterNav").style.display = "none";
  document.getElementById("modalTitle").textContent = path.split("/").pop() || path;
  document.getElementById("modalBody").innerHTML = "<p class='hint'>加载中...</p>";
  document.getElementById("previewModal").setAttribute("aria-hidden", "false");
  if (path === "planner/outline.json" || path === "planner\\outline.json") {
    outlinePage = 1;
    loadOutlinePage(1);
    return;
  }
  fetch("/api/tasks/" + currentTaskId + "/files/view?path=" + encodeURIComponent(path))
    .then(r => { if (!r.ok) throw new Error("预览失败"); return r.text(); })
    .then(text => {
      const isMd = /\.(md|markdown)$/i.test(path);
      document.getElementById("modalBody").innerHTML = isMd && window.marked ? marked.parse(text) : "<pre>" + escapeHtml(text) + "</pre>";
    })
    .catch(() => { document.getElementById("modalBody").innerHTML = "<p class='hint'>预览失败</p>"; });
}

function loadOutlinePage(page) {
  if (!currentTaskId) return;
  outlinePage = page;
  api("/tasks/" + currentTaskId + "/outline?page=" + page + "&per_page=" + outlinePerPage)
    .then(d => {
      const chs = d.chapters || [];
      const total = d.total || 0;
      const totalPages = d.total_pages || 0;
      let html = "<div class='outline-pagination'>";
      if (totalPages > 1) {
        html += "<div class='outline-nav'>";
        if (page > 1) html += "<button type='button' class='btn-mini outline-prev'>上一页</button>";
        html += "<span>第 " + page + " / " + totalPages + " 页（共 " + total + " 章）</span>";
        if (page < totalPages) html += "<button type='button' class='btn-mini outline-next'>下一页</button>";
        html += "</div>";
      }
      html += "<div class='outline-list'>";
      chs.forEach((ch, i) => {
        const idx = (page - 1) * outlinePerPage + i + 1;
        html += "<div class='outline-ch'>";
        html += "<strong>" + escapeHtml(ch.title || ("第" + idx + "章")) + "</strong>";
        html += "<p>主题：" + escapeHtml(ch.theme || "") + "</p>";
        html += "<p>事件：" + escapeHtml(ch.event || "") + "</p>";
        html += "<p>衔接：" + escapeHtml(ch.connection || "") + " | 钩子：" + escapeHtml(ch.hook || "") + "</p>";
        html += "</div>";
      });
      html += "</div></div>";
      document.getElementById("modalBody").innerHTML = html;
      document.getElementById("modalTitle").textContent = "故事大纲（第" + page + "页）";
      document.querySelectorAll(".outline-prev").forEach(btn => btn.addEventListener("click", () => loadOutlinePage(page - 1)));
      document.querySelectorAll(".outline-next").forEach(btn => btn.addEventListener("click", () => loadOutlinePage(page + 1)));
    })
    .catch(() => { document.getElementById("modalBody").innerHTML = "<p class='hint'>大纲加载失败</p>"; });
}

function closeModal() {
  document.getElementById("previewModal").setAttribute("aria-hidden", "true");
}

document.getElementById("modalClose").addEventListener("click", closeModal);
document.querySelector(".modal-backdrop").addEventListener("click", closeModal);
document.getElementById("btnPrevChapter").addEventListener("click", () => { if (currentChapterIndex > 0) openChapterModal(currentChapterIndex - 1); });
document.getElementById("btnNextChapter").addEventListener("click", () => {
  if (novelData && novelData.chapters && currentChapterIndex < novelData.chapters.length - 1) openChapterModal(currentChapterIndex + 1);
});

document.getElementById("btnRefresh").addEventListener("click", () => { refreshAll(); });
document.getElementById("btnCreateTask").addEventListener("click", () => {
  const name = document.getElementById("taskName").value.trim() || "新小说任务";
  api("/tasks", { method: "POST", body: JSON.stringify({ name }) })
    .then(d => { currentTaskId = d.task_id; refreshAll(); });
});
document.getElementById("btnStart").addEventListener("click", () => {
  const chk = document.getElementById("chkAutoRun");
  if (chk && chk.checked) api("/tasks/auto-run", { method: "POST", body: JSON.stringify({ auto_run: true }) }).catch(() => {});
  const doStart = (tid) =>
    api("/tasks/" + tid + "/start", { method: "POST" })
      .then((resp) => {
        if (resp && resp.queued && resp.queued_task_id) currentTaskId = resp.queued_task_id;
        else currentTaskId = tid;
        refreshAll();
      })
      .catch(err => alert(err.message || "启动失败"));
  if (currentTaskId) {
    doStart(currentTaskId);
  } else {
    const name = document.getElementById("taskName").value.trim() || "自动生成小说";
    api("/tasks", { method: "POST", body: JSON.stringify({ name }) })
      .then(d => { currentTaskId = d.task_id; return doStart(d.task_id); })
      .catch(err => alert(err.message || "创建或启动失败"));
  }
});
document.getElementById("chkAutoRun").addEventListener("change", function() {
  api("/tasks/auto-run", { method: "POST", body: JSON.stringify({ auto_run: this.checked }) }).catch(() => {});
});
document.getElementById("btnStop").addEventListener("click", () => {
  api("/tasks/stop", { method: "POST" }).then(() => refreshAll()).catch(alert);
});
document.getElementById("btnPause").addEventListener("click", () => {
  api("/tasks/pause", { method: "POST" }).then(() => refreshAll()).catch(alert);
});
document.getElementById("btnResume").addEventListener("click", () => {
  api("/tasks/resume", { method: "POST" }).then(() => refreshAll()).catch(alert);
});
document.getElementById("btnCreateAndStart").addEventListener("click", () => {
  const name = document.getElementById("taskName").value.trim() || "新小说任务";
  api("/tasks", { method: "POST", body: JSON.stringify({ name }) })
    .then(d => {
      currentTaskId = d.task_id;
      return api("/tasks/" + d.task_id + "/start", { method: "POST" });
    })
    .then(() => refreshAll())
    .catch(err => alert(err.message || "创建或启动失败"));
});
document.getElementById("btnToggleMode").addEventListener("click", () => {
  const next = runMode === "test" ? "prod" : "test";
  api("/run-mode", { method: "POST", body: JSON.stringify({ mode: next }) })
    .then(() => refreshAll())
    .catch(err => alert(err.message || "切换模式失败"));
});

document.getElementById("agentSelect").addEventListener("change", () => {
  if (!currentTaskId) return;
  const agent = document.getElementById("agentSelect").value;
  api("/tasks/" + currentTaskId + "/progress").then(s => {
    const p = s[agent] || {};
    document.getElementById("agentDetail").innerHTML = `<strong>${agent}</strong><br/>状态: ${p.status} | ${escapeHtml(p.message || "")}`;
  });
  api("/tasks/" + currentTaskId + "/logs/" + agent + "?limit=100").then(d => renderLogs(d.logs));
});

function escapeHtml(s) {
  if (s == null) return "";
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");
}

api("/config").then(c => {
  if (c.refresh_interval_seconds) setRefreshInterval(c.refresh_interval_seconds);
}).catch(() => setRefreshInterval(30));

refreshAll();
