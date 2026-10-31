# 5 主题渲染基线（体积说明）

5 张 PNG 共约 **2.0 MB**（classic / green / blue / purple / dark，1260×850），
是 `scripts/theme_pixel_baseline.py` 的 `--check` 基线，服务 A-2/B 阶段的"零视觉变化"判据。

**本仓库未配置 Git LFS**，这些是直接进 Git 的二进制。若将来启用 LFS，应把它们迁过去。

重新生成：
```
python scripts/theme_pixel_baseline.py --write
```
换机器（字体/DPI 不同）前，先跑 `--noise` 重测噪声底，再决定是否需要重写基线。
