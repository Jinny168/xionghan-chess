"""排序 vs 评估对照实验 —— A（固定深度隔离）+ B（静态评估隔离）。

用法: python ab.py <code_root> <baseline_dir> <out.json>
口径与基线一致：desktop_complete、默认 RuleOptions、randomness=0、root_limit=18。
A: 固定 depth=2/3/4（time_limit=180，确保不被时间截断），记录 completed_depth 作为深度到位的证据。
B: 取 12s 选点与 48s 参照两手，各自落子后用同一 _evaluate 打分（行棋方视角）。
"""
import sys, os, json, hashlib, time

code_root, base_dir, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, os.path.join(code_root, "src"))
sys.path.insert(0, os.path.join(code_root, "scripts"))
import xionghan_chess
assert os.path.join(code_root, "src").replace("\\", "/") in xionghan_chess.__file__.replace("\\", "/")

from dataclasses import replace
import xionghan_chess.core.ai as A
from xionghan_chess.core.game import Game
from xionghan_chess.core.ai import ChessAI
from xionghan_chess.core.model import Move, Position
import bench_roots as BR

A.CONFIGS["hard"] = replace(A.CONFIGS["hard"], randomness=0.0, root_limit=18)

sel = json.load(open(os.path.join(base_dir, "base4_sel8.json"), encoding="utf-8"))
ref = json.load(open(os.path.join(base_dir, "base4_ref8.json"), encoding="utf-8"))

CASES = [(s, p) for p in (4, 8) for s in (700, 701, 702, 703)]
POS = {}
for seed, plies in CASES:
    gen, _ = BR.build_position("desktop_complete", seed, plies)
    kid = hashlib.sha1(gen.rules.position_key(gen.state).encode()).hexdigest()[:16]
    POS[kid] = (gen, seed, plies)


def parse(key):
    a, b = key.split("-")
    return Move(Position(*map(int, a.split(","))), Position(*map(int, b.split(","))))


def run_fixed_depth(gen, depth):
    cfg = replace(A.CONFIGS["hard"], depth=depth, time_limit=180.0)
    A.CONFIGS["hard"] = cfg
    ai = ChessAI("hard")
    t = time.perf_counter()
    mv = ai.choose_move(Game.from_state(gen.state.clone(), gen.options))
    wall = round(time.perf_counter() - t, 2)
    A.CONFIGS["hard"] = replace(A.CONFIGS["hard"], depth=8, time_limit=12.0)
    scores = [item[0] for item in ai.root_scores] or [0.0]
    return {"move": mv.key() if mv else None, "completed_depth": ai.completed_depth,
            "wall": wall, "score": round(max(scores), 3)}


def static_score(gen, move_key, mover_color):
    g = Game.from_state(gen.state.clone(), gen.options)
    g.move(parse(move_key))
    ai = ChessAI("hard")
    for k in ("evaluation_cache", "in_check_memo", "see_cache"):
        getattr(ai, k).clear()
    return round(ai._evaluate(g, mover_color), 3)


out = {"commit_note": "baseline_2026-10-31-50p / 95c2784", "positions": {}}
for kid, (gen, seed, plies) in POS.items():
    if kid not in sel or kid not in ref:
        continue
    mover = gen.state.turn
    rec = {"seed": seed, "plies": plies,
           "sel12": sel[kid]["reps"][0]["move"], "sel12_depth": sel[kid]["reps"][0]["depth"],
           "ref": ref[kid]["ref_move"], "ref_depth": ref[kid]["ref_depth"], "A": {}}
    for d in (2, 3, 4):
        rec["A"][f"d{d}"] = run_fixed_depth(gen, d)
    rec["B"] = {"ref_static": static_score(gen, ref[kid]["ref_move"], mover),
                "sel_static": static_score(gen, sel[kid]["reps"][0]["move"], mover)}
    out["positions"][kid] = rec
    print(f"{kid} 12s={rec['sel12']}(d{rec['sel12_depth']}) ref={rec['ref']}(d{rec['ref_depth']}) "
          f"| A: d2={rec['A']['d2']['move']}({rec['A']['d2']['completed_depth']}) "
          f"d3={rec['A']['d3']['move']}({rec['A']['d3']['completed_depth']}) "
          f"d4={rec['A']['d4']['move']}({rec['A']['d4']['completed_depth']}) "
          f"| B: ref={rec['B']['ref_static']} sel={rec['B']['sel_static']}", flush=True)

json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("DONE")
