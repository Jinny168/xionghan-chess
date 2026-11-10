/**
 * 打开一个可见窗口：
 *   标签 1 —— 活动页「我的作品」（该标签依赖提交时的本地缓存，只有这个浏览器能看到）
 *   标签 2 —— 小红书创作服务平台发布页（等你扫码登录）
 * 窗口保持 45 分钟，方便你查看与操作。
 */
import { chromium } from 'file:///D:/CodeManagement/nodejs/node_global/node_modules/@playwright/cli/node_modules/playwright-core/index.mjs';

const PROFILE = 'C:/Users/27415/PycharmProjects/xionghan-chess/xionghan-chess-next/.pw-profile';
const ctx = await chromium.launchPersistentContext(PROFILE, {
  channel: 'chrome',
  headless: false,
  viewport: { width: 1440, height: 950 },
  args: ['--window-size=1460,1000'],
});

const page = ctx.pages()[0] || (await ctx.newPage());
await page.goto('https://www.workbuddy.link/p/8QYARuAmZ9RgQty3FSzNUs?source=2', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(7000);

const fr = page.frames().find((f) => f.url().includes('workbuddy-space-static'));
if (fr) {
  await fr.click('button.tab[data-v="mine"]').catch(() => {});
  await fr.evaluate(() => {
    const el = document.querySelector('.mysub');
    if (el) el.scrollIntoView({ block: 'center' });
  }).catch(() => {});
}

const xhs = await ctx.newPage();
await xhs.goto('https://creator.xiaohongshu.com/publish/publish?source=official', { waitUntil: 'domcontentloaded' }).catch(() => {});

console.log(JSON.stringify({ statusTab: !!fr, xhsUrl: xhs.url() }));
await page.waitForTimeout(45 * 60 * 1000);
await ctx.close();
