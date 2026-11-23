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
