# 5 主题渲染基线

5 张 PNG（classic / green / blue / purple / dark，1260×850），是 `scripts/theme_pixel_baseline.py`
的 `--check` 基线，服务 A-2/B 阶段的"零视觉变化"判据。

## 存储：走 Git LFS
根 `.gitattributes` 已有 `*.png filter=lfs` 规则（52 条 LFS 规则之一），
所以仓库里存的是**指针**，2 MB 不进主历史：
```
$ git check-attr diff merge text -- benchmarks/theme_pixels/classic.png
diff: lfs / merge: lfs / text: unset
$ git show HEAD:…/classic.png | head -c 40
version https://git-lfs.github.com/spec/
```
⚠️ **`git archive` 导出时这些 PNG 会变成指针**（发布流程必须按 `git ls-files` 从工作区复制，
否则图片全裂 —— 与网页版发布图片裂图是同一个原因）。

## 重新生成
```
python scripts/theme_pixel_baseline.py --write
```
换机器（字体/DPI 不同）前，先跑 `--noise` 重测噪声底，再决定是否重写基线。
