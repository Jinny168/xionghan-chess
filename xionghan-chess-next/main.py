"""部署入口：平台默认用 `python main.py` 启动，这里只做两件事。

1. 把 `src/` 放进 `sys.path` —— 本仓库是 src-layout，未安装成包时直接
   `import xionghan_chess` 会失败；
2. 交给 `service.app.run()` —— 它已经读 `PORT` 并绑定 `0.0.0.0`，
   保证"部署平台怎么启动"和"本地怎么启动"只有一处实现。

为什么不改 platform 的启动命令：多一个薄入口文件比在部署面板里维护
一条 `python -c "from ... import run; run()"` 更可靠 —— 后者换环境就丢。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from xionghan_chess.service.app import run  # noqa: E402  （必须在 sys.path 调整之后）

if __name__ == "__main__":
    run()
