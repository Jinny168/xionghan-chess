// 三端连对结束页文案行为探针：直接抽取并执行 webapp / web 两套真实
// showStreakBanner 函数体（不复制逻辑），用桩替掉 t() 与 $()，把每条文案
// 归一成 [键名后缀, count] 交给 Python 端与桌面纯函数逐项对拍。
import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.argv[2];
if (!ROOT) {
  console.error('usage: node streak_banner_probe.mjs <repo-root>');
  process.exit(2);
}

// 每端：源文件相对路径、函数抽取标志、调用方式（位置参数 or 解构对象）
const ENDS = [
  { name: 'webapp', file: 'webapp/js/ui/app.js', destructured: true },
  { name: 'web', file: 'web/js/app.js', destructured: false },
];

const CASES = [
  [3, 2], // 破纪录：prev=2 本轮=3
  [1, 2], // 未破纪录
  [0, 0], // count=0，无历史
  [0, 2], // count=0，有历史
  [3, 0], // 从零破纪录
];

function extractFunction(src, name) {
  const marker = `function ${name}`;
  const start = src.indexOf(marker);
  if (start < 0) throw new Error(`找不到函数 ${name}`);
  // 参数里可能有解构花括号（webapp 版），先跳过括号里的参数表再找函数体的第一个 `{`。
  const paren = src.indexOf('(', start);
  if (paren < 0) throw new Error(`${name} 没有参数表`);
  let pdepth = 0;
  let afterParams = paren;
  for (let i = paren; i < src.length; i += 1) {
    if (src[i] === '(') pdepth += 1;
    else if (src[i] === ')') {
      pdepth -= 1;
      if (pdepth === 0) { afterParams = i + 1; break; }
    }
  }
  const brace = src.indexOf('{', afterParams);
  if (brace < 0) throw new Error(`${name} 没有函数体`);
  let depth = 0;
  for (let i = brace; i < src.length; i += 1) {
    if (src[i] === '{') depth += 1;
    else if (src[i] === '}') {
      depth -= 1;
      if (depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error(`${name} 花括号不配对`);
}

function normalize(raw) {
  // 真实实现里 t() 返回翻译后的字符串；桩让它返回 "键|count"，这里再拆回结构。
  return raw.split('\n').filter(Boolean).map((line) => {
    const [key, count] = line.split('|');
    return [key.split('.').pop(), count === '' ? null : Number(count)];
  });
}

const out = {};
for (const end of ENDS) {
  const src = fs.readFileSync(path.join(ROOT, end.file), 'utf8');
  const fnSrc = extractFunction(src, 'showStreakBanner');
  out[end.name] = CASES.map(([correct, previousBest]) => {
    let captured = '';
    const sink = {
      set textContent(v) { captured = String(v); },
      get textContent() { return captured; },
      hidden: false,
    };
    const $ = () => sink;
    const t = (key, params = {}) =>
      `${key}|${Object.prototype.hasOwnProperty.call(params, 'count') ? params.count : ''}`;
    // eslint-disable-next-line no-new-func
    const factory = new Function('$', 't', `${fnSrc}; return showStreakBanner;`);
    const showStreakBanner = factory($, t);
    const isRecord = correct > previousBest;
    if (end.destructured) showStreakBanner({ correct, previousBest, isRecord });
    else showStreakBanner(correct, previousBest, isRecord);
    return normalize(captured);
  });
}

process.stdout.write(JSON.stringify(out));
