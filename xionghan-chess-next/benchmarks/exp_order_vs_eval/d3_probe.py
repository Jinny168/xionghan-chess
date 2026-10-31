"""hard 固定 d3 评估：16 局面 d2/d3 选点 + 参照对照。

用法:
  python d3_probe.py <code_root> <baseline_dir> <out_dir> depth   # 跑 d2/d3（快）
  python d3_probe.py <code_root> <baseline_dir> <out_dir> ref     # 补齐缺失的 48s 参照（慢）
口径：desktop_complete/web/traditional 按 corpus16；randomness=0、root_limit=18、默认 RuleOptions。
"""
import sys, os, json, hashlib, time, statistics

code_root, base_dir, out_dir, phase = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, os.path.join(code_root, "src"))
sys.path.insert(0, os.path.join(code_root, "scripts"))
import xionghan_chess
assert os.path.join(code_root, "src").replace("\\", "/") in xionghan_chess.__file__.replace("\\", "/")

from dataclasses import replace
import xionghan_chess.core.ai as A
from xionghan_chess.core.game import Game
from xionghan_chess.core.ai import ChessAI
import bench_roots as BR

CORPUS = json.load(open(os.path.join(base_dir, "base4_corpus16.json"), encoding="utf-8"))
REF8 = json.load(open(os.path.join(base_dir, "base4_ref8.json"), encoding="utf-8"))
BASE_CFG = replace(A.CONFIGS["hard"], randomness=0.0, root_limit=18)


def fixed(depth):
    return replace(BASE_CFG, depth=depth, time_limit=180.0)


def run(gen, cfg):
    A.CONFIGS["hard"] = cfg
    ai = ChessAI("hard")
    t = time.perf_counter()
    mv = ai.choose_move(Game.from_state(gen.state.clone(), gen.options))
    wall = round(time.perf_counter() - t, 2)
    return {"move": mv.key() if mv else None, "completed_depth": ai.completed_depth, "wall": wall}


if phase == "depth":
    out = {}
    for item in CORPUS:
        gen, _ = BR.build_position(item["profile"], item["seed"], item["plies"])
        kid = hashlib.sha1(gen.rules.position_key(gen.state).encode()).hexdigest()[:16]
        d2 = run(gen, fixed(2))
        d3 = run(gen, fixed(3))
        out[kid] = {"profile": item["profile"], "seed": item["seed"], "plies": item["plies"],
                    "fp": item["fp"], "d2": d2, "d3": d3}
        print(f"{kid} {item['fp']:8s} d2={d2['move']}({d2['completed_depth']}) "
              f"d3={d3['move']}({d3['completed_depth']}) {d3['wall']}s", flush=True)
    A.CONFIGS["hard"] = BASE_CFG
    json.dump(out, open(os.path.join(out_dir, "d3_depth.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("DONE depth")

elif phase == "ref":
    os.environ["AI_TIME_SCALE"] = "4.0"
    out = dict(REF8)
    for item in CORPUS:
        gen, _ = BR.build_position(item["profile"], item["seed"], item["plies"])
        kid = hashlib.sha1(gen.rules.position_key(gen.state).encode()).hexdigest()[:16]
        if kid in out:
            continue
        r = run(gen, BASE_CFG)
        out[kid] = {"profile": item["profile"], "seed": item["seed"], "plies": item["plies"],
                    "fp": item["fp"], "ref_move": r["move"], "ref_depth": r["completed_depth"],
                    "wall": r["wall"], "in_eight": False, "added_by": "d3_probe"}
        print(f"[ref+] {kid} {item['fp']:8s} -> {r['move']} d{r['completed_depth']} {r['wall']}s", flush=True)
    os.environ.pop("AI_TIME_SCALE", None)
    json.dump(out, open(os.path.join(out_dir, "refs_all.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("DONE ref", len(out))
