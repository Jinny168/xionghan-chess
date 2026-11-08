"""训练链路冒烟（**独立进程**执行，供 `test_training_pipeline` 用 subprocess 调用）。

## 为什么单独成一个脚本

整跑 `pytest tests/` 时，这条冒烟排在**最后**，会在原生层直接崩掉进程（无 traceback）。
证据：`git stash` 回到 `512cb56` 干净树同样崩；逐文件跑、分段跑都通过；
把本文件排到最前跑也通过 —— 说明不是这条用例本身的断言逻辑有问题，而是
"长期累积的进程状态（Qt 对象 / 位图缓存）遇到一次大块 numpy 分配"时炸掉，根因未定。

处置是**隔离执行、保留覆盖**（不是跳过、不是标 slow 摘出门禁）：
`test_numpy_policy_value_training_smoke` 用 `sys.executable` 起一个干净解释器跑本脚本，
断言退出码与完成标记。覆盖没少，只是换了个执行环境。

用法：`python tests/_smoke_training_impl.py`（退出码 0 且打印 `TRAINING_SMOKE_OK` 即通过）。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from xionghan_chess.training.selfplay import append_jsonl, collect_game  # noqa: E402


def main() -> int:
    from xionghan_chess.training.network import NumpyPolicyValueNet

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        samples = collect_game(simulations=1, max_plies=1, seed=8)
        dataset = root / "samples.jsonl"
        append_jsonl(dataset, samples)

        network = NumpyPolicyValueNet(hidden=4, seed=2)
        metrics = network.train_jsonl(dataset, epochs=1)
        model = root / "model.npz"
        network.save(model)

        assert metrics["samples"] == 1, metrics
        assert metrics["loss"] > 0, metrics
        assert model.exists(), "模型没有落盘"

    print(f"TRAINING_SMOKE_OK samples={metrics['samples']} loss={metrics['loss']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
