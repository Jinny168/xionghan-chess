/**
 * 小红书图文笔记：上传封面与截图，填标题与正文，停在「发布」前等人工确认。
 * 不点击发布。
 */
import fs from 'node:fs';
import { chromium } from 'file:///D:/CodeManagement/nodejs/node_global/node_modules/@playwright/cli/node_modules/playwright-core/index.mjs';

const ROOT = 'C:/Users/27415/PycharmProjects/xionghan-chess/xionghan-chess-next';
const STATUS = `${ROOT}/.contest/xhs-status.json`;
const state = (o) => fs.writeFileSync(STATUS, JSON.stringify({ at: new Date().toISOString(), ...o }, null, 2));

const TITLE = '1024 我做了个十三路象棋，规则有点野';
const BODY = `这个 1024，我没写 CRUD。

我用 WorkBuddy 把一款桌面象棋重做成了网页版 —— 匈汉象棋。

· 13×13 棋盘，中间不是「河」，是一道「长城—阴山」分界
· 双方各 14 种棋子，射 / 檑 / 甲 / 刺 / 楯 / 巡 这六种是它独有的
· 打开链接就能下，不装软件、不用登录、没有后端

技术上最花时间的是规则移植：
把 Python 规则内核逐行搬到 JavaScript，再用参考实现导出 372 个局面、848 次走子、23741 条合法着法，逐条比对，全绿才敢发布。
AI 跑在 Web Worker 里，四档棋力，思考时界面不卡。

有个小功能我自己很喜欢：棋子图谱。
点任意一枚棋子，就能看到它在这张棋盘上的全部可达点，规则一眼看懂。

体验链接放在评论区（正文放链接容易被限流）。
#WorkBuddy #1024程序员节 #独立开发 #象棋 #网页游戏 #前端开发`;

const ctx = await chromium.launchPersistentContext(`${ROOT}/.pw-profile`, {
  channel: 'chrome', headless: false, viewport: { width: 1440, height: 980 },
  args: ['--window-size=1460,1020'],
});
const page = ctx.pages()[0] || (await ctx.newPage());
state({ step: 'open' });
await page.goto('https://creator.xiaohongshu.com/publish/publish?source=official', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(6000);

state({ step: 'switch-tab' });
await page.evaluate(() => {
  const el = Array.from(document.querySelectorAll('div.creator-tab'))
    .find((e) => (e.innerText || '').trim() === '上传图文' && !e.hasAttribute('aria-hidden'));
  if (!el) return;
  for (const type of ['mousedown', 'mouseup', 'click']) {
    el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
  }
});
await page.waitForTimeout(3000);

state({ step: 'upload' });
const input = page.locator('input[type=file]').first();
await input.setInputFiles([
  `${ROOT}/xhs/01-cover.png`,
  `${ROOT}/webapp/screenshots/01-game.png`,
  `${ROOT}/webapp/screenshots/02-atlas.png`,
  `${ROOT}/webapp/screenshots/03-mobile.png`,
]);
await page.waitForTimeout(18000);

const fields = await page.evaluate(() => ({
  textInputs: Array.from(document.querySelectorAll('input')).map((i) => ({ ph: i.placeholder || '', type: i.type, cls: (i.className || '').toString().slice(0, 40) })),
  editables: Array.from(document.querySelectorAll('[contenteditable=true],textarea')).map((e) => ({ tag: e.tagName, ph: e.getAttribute('data-placeholder') || e.placeholder || '', cls: (e.className || '').toString().slice(0, 50) })),
  body: document.body.innerText.replace(/\s+/g, ' ').slice(0, 260),
}));
state({ step: 'uploaded', fields });

let filled = { title: false, body: false };
try {
  const titleInput = page.locator('input[placeholder*="标题"]').first();
  if (await titleInput.count()) {
    await titleInput.fill(TITLE);
    filled.title = true;
  }
} catch { /* ignore */ }

try {
  const editor = page.locator('[contenteditable=true]').first();
  if (await editor.count()) {
    await editor.click();
    await page.waitForTimeout(400);
    await page.keyboard.insertText(BODY);
    filled.body = true;
  }
} catch { /* ignore */ }

await page.waitForTimeout(2000);
await page.screenshot({ path: `${ROOT}/xhs-compose.png`, fullPage: false });
state({ step: 'composed', filled, note: '停在发布前，等人工确认' });
await page.waitForTimeout(30 * 60 * 1000);
await ctx.close();
