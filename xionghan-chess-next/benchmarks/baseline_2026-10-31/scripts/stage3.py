"""第 3 段：8 局面深参照（AI_TIME_SCALE=4 → 48s）+ 12s 选点 ×3。

用法: python stage3.py <code_root> <out_ref.json> <out_sel.json>
额外：把 corpus16 里 p12 的 9d4dda34 也补一遍（它不在前 8，但需要它的深度差）。
"""
import sys, os, json, hashlib, time

code_root, out_ref, out_sel = sys.argv[1], sys.argv[2], sys.argv[3]
MODE = sys.argv[4] if len(sys.argv) > 4 else "both"
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

EIGHT = [(s, 4) for s in (700, 701, 702, 703)] + [(s, 8) for s in (700, 701, 702, 703)]
EXTRA = [(702, 12)]          # 9d4dda34：不在前 8，但需要它的深度差


def kid_fp(gen):
    st = gen.state
    return (hashlib.sha1(gen.rules.position_key(st).encode()).hexdigest()[:16],
            f"{len(st.pieces)}/{len(gen.rules.legal_moves(st))}")


# ---------- 深参照 48s ----------
os.environ["AI_TIME_SCALE"] = "4.0"
ref = {}
for seed, plies in (EIGHT + EXTRA) if MODE in ("both", "ref") else []:
    gen, _ = BR.build_position("desktop_complete", seed, plies)
    kid, fp = kid_fp(gen)
    a = ChessAI("hard")
    t = time.perf_counter()
    mv = a.choose_move(Game.from_state(gen.state.clone(), gen.options))
    ref[kid] = {"profile": "desktop_complete", "seed": seed, "plies": plies, "fp": fp,
                "ref_move": mv.key() if mv else None, "ref_depth": a.completed_depth,
                "wall": round(time.perf_counter() - t, 1),
                "in_eight": (seed, plies) in EIGHT}
    print(f"[ref ] s{seed} p{plies:2d} {kid} {fp:8s} -> {ref[kid]['ref_move']} "
          f"d{a.completed_depth} {ref[kid]['wall']}s", flush=True)
os.environ.pop("AI_TIME_SCALE", None)
if MODE in ("both", "ref"):
    json.dump(ref, open(out_ref, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[ref] 落盘", out_ref, flush=True)

# ---------- 12s 选点 ×3 ----------
sel = {}
for seed, plies in (EIGHT + EXTRA) if MODE in ("both", "sel") else []:
    gen, _ = BR.build_position("desktop_complete", seed, plies)
    kid, fp = kid_fp(gen)
    reps = []
    for _ in range(3):
        a = ChessAI("hard")
        mv = a.choose_move(Game.from_state(gen.state.clone(), gen.options))
        reps.append({"move": mv.key() if mv else None, "depth": a.completed_depth})
    sel[kid] = {"profile": "desktop_complete", "seed": seed, "plies": plies, "fp": fp,
                "reps": reps, "in_eight": (seed, plies) in EIGHT}
    print(f"[sel ] s{seed} p{plies:2d} {kid} {fp:8s} "
          f"{[(r['move'], r['depth']) for r in reps]}", flush=True)
if MODE in ("both", "sel"):
    json.dump(sel, open(out_sel, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[sel] 落盘", out_sel, flush=True)

print("\n=== 汇总 ===")
for k in ref:
    r, s = ref[k], sel[k]
    tag = "" if r["in_eight"] else "  [附加:p12]"
    print(f"{k} {r['fp']:8s} ref d{r['ref_depth']}={r['ref_move']} | 12s d{s['reps'][0]['depth']}"
          f"={s['reps'][0]['move']} {'命中' if s['reps'][0]['move']==r['ref_move'] else '未命中'}{tag}")
