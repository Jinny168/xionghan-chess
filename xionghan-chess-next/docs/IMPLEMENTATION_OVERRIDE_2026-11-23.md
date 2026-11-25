# 实施落点更正（主理人裁定，2026-11-23）

> 性质：**覆盖** `docs/PRODUCT_DECISIONS_2026-11-23.md` 与 `docs/ARCH_DECISIONS_2026-11-23.md` 中
> 关于「Web 旧树新增 `analysis.capped` 键」的**文件落点**。两句裁决的方向（沿用现有三端同句、
> Web 补键、桌面与 Webapp 不改、不跑 S1–S6）全部维持不变，只纠正**改哪个文件**。
> 两份原文档不修改，保留溯源；实施时以本文为准。

## 问题

两份裁决均写：「`web/js/i18n.js` 目前没有 `analysis.capped` 键，由实现方**新增**该键」。

这是错的。web 旧树的词表**不在** `web/js/i18n.js` 里：

```
web/js/i18n.js:17  async function fetchCatalog(language) {
web/js/i18n.js:18    const response = await fetch(`/locales/${language}.json`, { cache: 'no-cache' });
web/js/i18n.js:25  export function t(key, params = {}) {
web/js/i18n.js:26    const template = lookup(activeCatalog, key) ?? lookup(zhCatalog, key) ?? key;
```

`t()` 查的是从 `/locales/{lang}.json` 加载的 catalog。`web/js/i18n.js` 中 `:145-151` 那批
`setText(选择器, 键名)` 只是**把静态 DOM 节点登记到某个键**，不持有文案值。

若照原裁决在 `web/js/i18n.js` 里加一个 `analysis.capped` 键值，那个值没有任何读取者，
`t('analysis.capped')` 仍会走 `?? key` 兜底，界面显示裸键 `analysis.capped` —— 与 2.2.1 刚修掉的
「裸 key」阻断（`fix-naked-key`）是同一类缺陷。

## 裁定：正确的落点

| 目的 | 改这个文件 | 不改这个文件 |
|---|---|---|
| Web 旧树获得 `analysis.capped` 文案 | `locales/zh-CN.json` 与 `locales/en.json` 的 **`analysis` 段**（两份都在 `:615` 附近），新增 `capped` 键 | ~~`web/js/i18n.js` 词表~~（那里没有词表） |
| Web 截断提示节点接入 | 若提示节点需要随语言切换，在 `web/js/i18n.js:149-151` 附近加一行 `setText(选择器, 'analysis.capped')` —— 这是**登记**，不是加词 | — |

文案值逐字沿用三端现有句：

- 中文：`（仅分析前 {n} 手）`
- English: `(first {n} plies only)`

`{n}` 插值由 `web/js/i18n.js:25-27` 的 `t()` 原生支持，无需额外机制。

## 对产物链的影响（重算）

- `locales/*.json` 是服务端静态目录（`service/app.py:759` 挂成 `/locales`），**不在** S1–S6 链上；
- `web/js/**` 同样不在 `SOURCE_DIGEST_FILES`（`scripts/gen_rule_fixtures.py:87-96` 五个源均为
  `webapp/js/core/*`、`online/core/*`、`online/public/index.html`），也不在 `build_webapp_bundle.py`
  的扫描路径内；
- ⇒ 补 Web 文案**不触发 fixtures 重生成、不触发 bundle 重建**。原裁决在这点的结论成立。

## 派工口径

实施方收到的规格里凡写「在 `web/js/i18n.js` 补 `analysis.capped` 键」，一律理解为：
**在 `locales/zh-CN.json` 与 `locales/en.json` 的 `analysis` 段补 `capped` 键**；
只有需要把某个静态 DOM 节点接到这个键时，才动 `web/js/i18n.js` 的 `setText` 登记处。

验收必须包含一条「真取词」断言，而不是只读源码：像 `fix-naked-key` 那样真 import / 真跑
`setLanguage()`，确认 `t('analysis.capped', {n: 120})` 在中英两侧都返回文案而不是裸键。

## 裁定：分析上限的「单一常量」走测试断言，不走 codegen

针对架构文档 D 节开放异议 3（codegen 下发上限到 Webapp vs 测试断言退路），主理人裁定：

**走测试断言退路。** 本轮不把上限下发到 `profiles.js`，不触发 S1–S6 全链。

理由：
1. 本次修复目标是**覆盖面统一到 120**，不是建立跨端单一常量源。codegen 会改 `profiles.js`，
   连带 8 条读回断言、manifest 与内嵌模块全变 —— 为一个常量引入整条产物链的回归面，
   与「小而美、傻瓜式」相悖。
2. 项目已有可维护的同类范式：`tests/test_default_minutes_single_source.py` 即「漂移即红」而非
   「自动同源」。（该测试本轮正被补上漏掉的第五处，说明范式本身可修、可演进。）
3. 架构文档自评 codegen 步骤成本「可能被低估」。

最终落地口径：
- `core/analysis.py` 定义 `ANALYSIS_PLY_CAP = 120` 并作为 `analyze_game` 默认值；
- 服务端 `service/app.py:710` 显式传该常量（`AnalyzeRequest` 字段不变，禁止让客户端传 `max_plies`）；
- 桌面 `desktop/ui/workers.py:32` 删本地字面量、import 同一常量；
- Webapp `const CAP = 120` **保持不动**，由一条 Python 测试断言 JS 常量与 core 相等；
- 不跑 S1–S6、不重生成 24 MB fixtures、不 bump `RULE_VERSION`、不碰 AI `CONFIGS`。

## 补充：Web 侧光补词表键不会产生可见提示（游有方发现的实现缺口）

`b307c68` 只纠正了「词表在哪」，但 Web 旧树**没有承载提示的 DOM 节点，也没有渲染调用**：

- `web/index.html:173` 的 `#analysisContent` 只有 `#analysisMoveList` 与 `#analysisNote`，无 capped 节点；
- `web/js/app.js:325` `renderAnalysis(result)` 只渲染逐手列表，无汇总行、`analysis.capped` 全树零命中。

只加 locales 键会让 `t('analysis.capped')` 有值却无人调用 —— A-1 的「Web 客户端补『真被截断才出现』的覆盖提示」等于没落地。实施必须同时做到：

1. **截断判据用服务端实际结果**：`result.analyzedPlies < app.state.history.length`
   （`core/analysis.py:89` 已返回 `analyzedPlies`），**不要客户端硬编码 120**，避免第二轮漂移；
2. 截断时显示 `t('analysis.capped', { n: <实际分析手数> })`，未截断时不显示 —— 沿用 Webapp 的
   `> CAP` 口径，**恰好等于上限不误报**；
3. 文案值逐字用现有同句：中文「（仅分析前 {n} 手）」/ 英文 `(first {n} plies only)`；
4. **禁止**把 capped 节点挂到 `web/js/i18n.js` 的 `setText` 登记上 —— `setText` 调 `t(key)` **不带 params**，
   `{n}` 会被原样显示成字面量（`t()` 兜底 `params[name] ?? \`{${name}}\``）。应由 `renderAnalysis`
   每次带参写入；若要求语言切换即时生效，在 `setLanguage` 后对已打开的弹窗重跑渲染。

验收须包含一条真渲染断言：构造「截断 / 恰好等于上限 / 未截断」三种结果，确认提示只在第一种出现，
且 `{n}` 被替换成数字而非字面量。
