"""第 2 段：16 局面 t_d2 ×3（新规则绝对基线，无对照组）。

用法: python stage2_td2.py <code_root> <out.json>
口径: hard / root_limit=18 / randomness=0；AI_TIME_SCALE=2.5 → 预算 30s；
      记录 d1、d2 各自完成时刻（秒），**d2 一完成立即 abort**（不白等满 30s）。
"""
import sys, os, json, statistics, time

code_root, out_path = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(code_root, "src"))
sys.path.insert(0, os.path.join(code_root, "scripts"))

import xionghan_chess
assert os.path.join(code_root, "src").replace("\\", "/") in xionghan_chess.__file__.replace("\\", "/"), \
    f"隔离失败: {xionghan_chess.__file__}"

from dataclasses import replace
import xionghan_chess.core.ai as A
from xionghan_chess.core.game import Game
from xionghan_chess.core.ai import ChessAI
import bench_roots as BR

A.CONFIGS["hard"] = replace(A.CONFIGS["hard"], randomness=0.0, root_limit=18)


class _D2Done(Exception):
    pass


_rd = A.ChessAI._root


def _root(self, g, mv, d, dl, c, a=-float("inf"), b=float("inf")):
    r = _rd(self, g, mv, d, dl, c, a, b)
    self.done.append((d, time.perf_counter() - self.t0))
    if d >= 2:
        raise _D2Done
    return r


A.ChessAI._root = _root
_oc = A.ChessAI.choose_move


def cm(self, g, c=None):
    self.done = []
    self.t0 = time.perf_counter()
    try:
        return _oc(self, g, c)
    except _D2Done:
        raise


A.ChessAI.choose_move = cm

CASES = ([("desktop_complete", s, p) for p in (4, 8, 12) for s in (700, 701, 702, 703)]
         + [("web", 700, 8), ("web", 701, 8), ("traditional", 700, 8), ("traditional", 701, 8)])

os.environ["AI_TIME_SCALE"] = "2.5"
out = {}
t_all = time.perf_counter()
for profile, seed, plies in CASES:
    gen, _ = BR.build_position(profile, seed, plies)
    rules = gen.rules
    import hashlib
    kid = hashlib.sha1(rules.position_key(gen.state).encode()).hexdigest()[:16]
    fp = f"{len(gen.state.pieces)}/{len(rules.legal_moves(gen.state))}"
    reps = []
    for _ in range(3):
        ai = ChessAI("hard")
        try:
            ai.choose_move(Game.from_state(gen.state.clone(), gen.options))
        except _D2Done:
            pass
        d = {}
        for depth, elapsed in ai.done:
            d[depth] = elapsed
        reps.append([round(d.get(1, -1), 3) if 1 in d else None,
                     round(d.get(2, -1), 3) if 2 in d else None])
    t2 = [r[1] for r in reps if r[1] is not None]
    out[kid] = {"profile": profile, "seed": seed, "plies": plies, "fp": fp, "reps": reps,
                "t2_median": round(statistics.median(t2), 3) if t2 else None}
    print(f"{profile[:9]:9s} s{seed} p{plies:2d} {kid} {fp:8s} reps={reps} "
          f"med={out[kid]['t2_median']}", flush=True)
os.environ.pop("AI_TIME_SCALE", None)

json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
t2s = [v["t2_median"] for v in out.values() if v["t2_median"] is not None]
print(f"\n=== 16 局面 t_d2 中位-of-中位: {statistics.median(t2s):.3f}s "
      f"范围[{min(t2s):.3f},{max(t2s):.3f}] 达标 {len(t2s)}/16 ===")
print(f"总耗时 {time.perf_counter()-t_all:.0f}s")
