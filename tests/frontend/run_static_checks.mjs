/**
 * 零依赖静态契约检查（无需 npm install）。
 * 用法：在项目根或本目录执行: node tests/frontend/run_static_checks.mjs
 */
import { readFileSync, existsSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import assert from "assert";

const __dirname = dirname(fileURLToPath(import.meta.url));
const staticDir = join(__dirname, "../../backend/static");

const html = readFileSync(join(staticDir, "index.html"), "utf-8");
assert.match(html, /app\.js/, "index.html 应引用 app.js");
for (const id of [
  "taskList",
  "btnCreateTask",
  "btnStart",
  "overallProgress",
  "novelToc",
  "runModeBadge",
]) {
  assert.ok(html.includes(`id="${id}"`), `缺少 #${id}`);
}

const appJs = readFileSync(join(staticDir, "app.js"), "utf-8");
assert.match(appJs, /const API = ["']\/api["']/, "app.js 应使用 API = /api");

const novelApp = join(staticDir, "novel", "app.js");
if (existsSync(novelApp)) {
  const s = readFileSync(novelApp, "utf-8");
  assert.ok(s.includes("/novel-api"), "novel/app.js 应含 /novel-api");
}

console.log("static checks: OK");
