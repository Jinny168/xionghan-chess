/**
 * WorkBuddy 1024 大赛投稿自动化。
 *
 * 做三件事：
 *   1. 打开有界面的 Chrome，停在登录页等你扫码（已登录则直接跳过）
 *   2. 登录后打开「发布作品」，按 .contest/params.json 填报并上传截图
 *   3. 提交并等待「提交成功，等待审核」
 *
 * 用法：
 *   node scripts/contest_submit.mjs [--dry-run] [--wait-login=480]
 *
 * 说明：
 *   - UserID 不写死，登录后从 WorkBuddy 账号读取并回填，保证与账号一致。
 *   - 表单会做内容安全校验，文案改动后需重新跑一次。
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'file:///D:/CodeManagement/nodejs/node_global/node_modules/@playwright/cli/node_modules/playwright-core/index.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const STATE_DIR = path.join(ROOT, '.contest');
const PROFILE = path.join(ROOT, '.pw-profile');
const PARAMS = path.join(STATE_DIR, 'params.json');
const STATUS = path.join(STATE_DIR, 'status.json');

const CONTEST = 'https://www.workbuddy.link/p/8QYARuAmZ9RgQty3FSzNUs?source=2';
const args = process.argv.slice(2);
const DRY_RUN = args.includes('--dry-run');
const LOGIN_ONLY = args.includes('--login-only');
const WAIT_LOGIN = Number((args.find((a) => a.startsWith('--wait-login=')) || '').split('=')[1] || 480);

fs.mkdirSync(STATE_DIR, { recursive: true });

function status(patch) {
  const payload = { at: new Date().toISOString(), ...patch };
  fs.writeFileSync(STATUS, JSON.stringify(payload, null, 2), 'utf8');
  console.log('[status]', JSON.stringify(patch));
}

function readParams() {
  if (!fs.existsSync(PARAMS)) throw new Error(`缺少参数文件 ${PARAMS}`);
  return JSON.parse(fs.readFileSync(PARAMS, 'utf8'));
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function findContestFrame(page, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const frame = page.frames().find((f) => f.url().includes('workbuddy-space-static'));
    if (frame) return frame;
    await sleep(500);
  }
  return null;
}

async function waitForLogin(page) {
  const deadline = Date.now() + WAIT_LOGIN * 1000;
  let lastShot = 0;
  while (Date.now() < deadline) {
    if (page.url().includes('workbuddy.link/p/')) {
      const frame = await findContestFrame(page, 5000);
      if (frame) {
        const uid = await frame.evaluate(async () => {
          const sp = window.__SMART_PAGE__;
          if (!sp?.database?.getUserInfo) return '';
          try {
            const res = await sp.database.getUserInfo();
            return res?.userInfo?.id ? String(res.userInfo.id) : '';
          } catch {
            return '';
          }
        }).catch(() => '');
        if (uid) return uid;
      }
    }
    if (Date.now() - lastShot > 5000) {
      lastShot = Date.now();
      await page.screenshot({ path: path.join(STATE_DIR, 'login.png') }).catch(() => {});
    }
    await sleep(1500);
  }
  return '';
}

async function main() {
  const params = readParams();
  status({ step: 'launch' });

  const ctx = await chromium.launchPersistentContext(PROFILE, {
    channel: 'chrome',
    headless: false,
    viewport: { width: 1440, height: 960 },
  });
  const page = ctx.pages()[0] || (await ctx.newPage());

  await page.goto(CONTEST, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(4000);

  let uid = '';
  const frame0 = await findContestFrame(page, 8000);
  if (frame0) {
    uid = await frame0.evaluate(async () => {
      const sp = window.__SMART_PAGE__;
      if (!sp?.database?.getUserInfo) return '';
      try {
        const res = await sp.database.getUserInfo();
        return res?.userInfo?.id ? String(res.userInfo.id) : '';
      } catch {
        return '';
      }
    }).catch(() => '');
  }

  if (!uid) {
    status({ step: 'need-login', hint: '请在弹出的浏览器窗口中扫码登录' });
    if (!page.url().includes('/login')) {
      const loginUrl = 'https://www.workbuddy.cn/login/?platform=buddylink&redirect_uri=' + encodeURIComponent(CONTEST);
      // 活动页自身也可能正在重定向到登录页，这里允许导航被打断
      await page.goto(loginUrl, { waitUntil: 'commit' }).catch(() => {});
    }
    await page.waitForTimeout(3500);
    await page.screenshot({ path: path.join(STATE_DIR, 'login.png') }).catch(() => {});
    uid = await waitForLogin(page);
    if (!uid) {
      status({ step: 'login-timeout' });
      await ctx.close();
      process.exit(2);
    }
  }
  status({ step: 'logged-in', uid });
  if (LOGIN_ONLY) {
    await page.waitForTimeout(1200);
    await ctx.close();
    status({ step: 'login-only-done', uid });
    return;
  }

  await page.goto(CONTEST, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3500);
  const frame = await findContestFrame(page);
  if (!frame) throw new Error('找不到活动页 iframe');

  await frame.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button,a')).find((b) => (b.innerText || '').includes('发布作品'));
    if (btn) btn.click();
  });
  await page.waitForTimeout(2000);
  status({ step: 'form-open' });

  const filled = await frame.evaluate((cfg) => {
    const set = (sel, val) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, val);
      ['input', 'change', 'blur'].forEach((t) => el.dispatchEvent(new Event(t, { bubbles: true })));
      return true;
    };
    set('#fDeclaration', cfg.declaration);
    set('#fName', cfg.name);
    set('#fAuthor', cfg.author);
    set('#fRaw', cfg.raw);
    set('#fUrl', cfg.url);
    set('#fConversation', cfg.conversation || '');
    set('#fShare', cfg.share || '');
    set('#fUid', cfg.uid);
    set('#fPhone', cfg.phone);
    const web = document.querySelector('button.rdo[data-v="网页应用"]');
    if (web) web.click();
    const plat = document.querySelector(`button.rdo[data-p="${cfg.platform || '其他'}"]`);
    if (plat) plat.click();
    const ok = document.querySelector('#fOk');
    if (ok && !ok.checked) ok.click();
    return {
      uid: document.querySelector('#fUid').value,
      phone: document.querySelector('#fPhone').value,
      rawLen: document.querySelector('#fRaw').value.length,
      type: document.querySelector('button.rdo[data-v="网页应用"]').className,
      platform: plat ? plat.className : '',
      ok: ok ? ok.checked : null,
    };
  }, { ...params, uid });

  status({ step: 'filled', filled });
  if (filled.uid !== uid) {
    status({ step: 'uid-mismatch', expect: uid, got: filled.uid });
    await ctx.close();
    process.exit(3);
  }

  await frame.setInputFiles('#fFile', params.shots);
  await page.waitForTimeout(2500);
  const shots = await frame.evaluate(() => {
    const box = document.querySelector('#shotw');
    return box ? Array.from(box.querySelectorAll('img')).map((i) => i.naturalWidth > 0) : [];
  });
  status({ step: 'shots-uploaded', shots });
  if (!shots.length || shots.some((ok) => !ok)) {
    status({ step: 'shots-broken' });
    await ctx.close();
    process.exit(4);
  }

  await page.screenshot({ path: path.join(STATE_DIR, 'before-submit.png') });

  if (DRY_RUN) {
    status({ step: 'dry-run-stop' });
    await sleep(2000);
    await ctx.close();
    return;
  }

  await frame.evaluate(() => document.getElementById('fSub').click());
  status({ step: 'submitting' });

  const deadline = Date.now() + 120000;
  let outcome = '';
  while (Date.now() < deadline) {
    const text = await frame.evaluate(() => (document.querySelector('#ov2')?.innerText || '').slice(0, 400)).catch(() => '');
    if (text.includes('提交成功')) {
      outcome = text.replace(/\s+/g, ' ').slice(0, 200);
      break;
    }
    const toastText = await frame.evaluate(() => (document.querySelector('#toast')?.innerText || '')).catch(() => '');
    if (toastText && /失败|错误|请/.test(toastText)) {
      await page.waitForTimeout(1500);
      const again = await frame.evaluate(() => (document.querySelector('#toast')?.innerText || ''));
      if (again === toastText) {
        outcome = 'ERROR: ' + toastText;
        break;
      }
    }
    await sleep(1000);
  }

  await page.screenshot({ path: path.join(STATE_DIR, 'result.png') });
  status({ step: outcome.startsWith('ERROR') ? 'failed' : 'done', outcome });
  await page.waitForTimeout(3000);
  await ctx.close();
  if (outcome.startsWith('ERROR')) process.exit(5);
}

main().catch((error) => {
  status({ step: 'exception', error: String(error && error.stack || error) });
  process.exit(1);
});
