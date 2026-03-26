/**
 * 前端契约测试：不启动浏览器，校验静态资源与主控制台脚本约定，
 * 避免误改 API 前缀、关键 DOM id 导致页面不可用。
 */
import { readFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const staticDir = join(__dirname, "../../backend/static");

import { describe, it, expect } from "vitest";

describe("index.html", () => {
  const html = readFileSync(join(staticDir, "index.html"), "utf-8");

  it("引用主脚本与样式", () => {
    expect(html).toMatch(/app\.js/);
    expect(html).toMatch(/styles\.css/);
  });

  it("包含任务与进度关键节点 id（与 app.js 一致）", () => {
    const ids = [
      "taskList",
      "btnCreateTask",
      "btnStart",
      "btnStop",
      "overallProgress",
      "agentSelect",
      "novelToc",
      "runModeBadge",
    ];
    for (const id of ids) {
      expect(html).toContain(`id="${id}"`);
    }
  });
});

describe("app.js", () => {
  const appJsPath = join(staticDir, "app.js");
  it("存在", () => {
    expect(existsSync(appJsPath)).toBe(true);
  });

  const appJs = readFileSync(appJsPath, "utf-8");

  it("API 前缀为 /api", () => {
    expect(appJs).toMatch(/const API = ["']\/api["']/);
  });

  it("包含核心请求路径片段", () => {
    expect(appJs).toContain("/tasks");
    expect(appJs).toContain("/run-mode");
    expect(appJs).toContain("/tasks/current");
  });
});

describe("novel/app.js（小说阅读站）", () => {
  const p = join(staticDir, "novel", "app.js");
  it("若存在则应对接 /novel-api", () => {
    if (!existsSync(p)) return;
    const s = readFileSync(p, "utf-8");
    expect(s).toMatch(/\/novel-api/);
  });
});
