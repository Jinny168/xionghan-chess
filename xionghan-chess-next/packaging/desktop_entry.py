from xionghan_chess.desktop import crashlog

# 先装崩溃通道再 import `app`：`app` 顶层 `import PySide6`，缺 DLL / Qt 插件损坏
# 都可能在 **import 期** 就崩 —— 那时还没进 `run()`，日志一句都没有。
# `install()` 本身是幂等的（保留 previous hook + `faulthandler.is_enabled()` 守卫），
# `run()` 里那次调用保留作兜底。
crashlog.install()

from xionghan_chess.desktop.app import run  # noqa: E402  （故意在 install() 之后）

if __name__ == "__main__":
    run()
