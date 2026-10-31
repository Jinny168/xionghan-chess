"""第 1 段：新基线重建（语料 16 + eval200 + check20 + 机动性表）。

用法:
  python stage1_baseline.py <code_root> <out_dir> [--smoke]

<code_root> 必须是 `git archive <commit>` 解出的干净副本（例如 /tmp/base2/xionghan-chess-next）。
产出（out_dir 下）:
  corpus16.json   16 个局面 id16 + pieces/legal
  eval200.json    200 条平静局面 red/black(6 位小数) + id16 + fp + sha256
  check20.json    20 条将军局面 red/black/sum + id16 + fp + 来源(profile/seed/起点索引/走法)
  mobility.json   13 棋子机动性表 + 初始局面首着每子着数
  summary.txt     人读摘要
"""
import sys, os, json, hashlib, time

code_root, out_dir = sys.argv[1], sys.argv[2]
SMOKE = "--smoke" in sys.argv

sys.path.insert(0, os.path.join(code_root, "src"))
sys.path.insert(0, os.path.join(code_root, "scripts"))

import xionghan_chess
assert os.path.join(code_root, "src").replace("\\", "/") in xionghan_chess.__file__.replace("\\", "/"), \
    f"隔离失败: {xionghan_chess.__file__}"

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import GameState, Color
from xionghan_chess.core.ai import ChessAI
import bench_roots as BR

os.makedirs(out_dir, exist_ok=True)
AI = ChessAI("hard")
LOG = []


def log(line):
    print(line, flush=True)
    LOG.append(line)


def id16(rules, st):
    return hashlib.sha1(rules.position_key(st).encode()).hexdigest()[:16]


def fp(rules, st):
    return f"{len(st.pieces)}/{len(rules.legal_moves(st))}"


def replay(profile, gen):
    """用 Game.move() 重放（纪律：不能用 apply_unchecked）。"""
    g = Game(profile)
    states = [g.state.clone()]
    for h in gen.state.history:
        g.move(h.move)
        states.append(g.state.clone())
    return states


def ev(st, color):
    g = Game.from_state(st.clone(), None, None)
    for k in ("evaluation_cache", "in_check_memo", "see_cache"):
        getattr(AI, k).clear()
    return AI._evaluate(g, color)


# ---------- 1. 语料 16 ----------
CORPUS = ([(("desktop_complete"), s, p) for p in (4, 8, 12) for s in (700, 701, 702, 703)]
          + [("web", 700, 8), ("web", 701, 8), ("traditional", 700, 8), ("traditional", 701, 8)])
corpus = []
for profile, seed, plies in CORPUS:
    gen, _ = BR.build_position(profile, seed, plies)
    st = gen.state
    corpus.append({"profile": profile, "seed": seed, "plies": plies,
                   "id": id16(gen.rules, st), "fp": fp(gen.rules, st)})
json.dump(corpus, open(os.path.join(out_dir, "base4_corpus16.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
uniq = len({c["id"] for c in corpus})
log(f"[corpus16] n={len(corpus)} 互异 {uniq}/{len(corpus)}")
for c in corpus:
    log(f"  {c['profile']:18s} s{c['seed']} p{c['plies']:2d}  {c['id']}  {c['fp']}")

# ---------- 2. eval200 ----------
PROFILES = ("desktop_complete", "desktop_classic", "web", "traditional")
SEEDS = range(700, 710) if not SMOKE else range(700, 701)
TAKE = (2, 4, 6, 8, 10)
rows = []
t0 = time.perf_counter()
for profile in PROFILES:
    rules = Game(profile).rules
    for seed in SEEDS:
        gen, _ = BR.build_position(profile, seed, 12)
        states = replay(profile, gen)
        for i in TAKE:
            st = states[i]
            rows.append({"id": id16(rules, st), "fp": fp(rules, st),
                         "red": round(ev(st, Color.RED), 6),
                         "black": round(ev(st, Color.BLACK), 6),
                         "src": {"profile": profile, "seed": seed, "stateIndex": i}})
    log(f"[eval] {profile} 累计 {len(rows)} 条 {time.perf_counter()-t0:.0f}s")
json.dump(rows, open(os.path.join(out_dir, "base4_eval200.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
zero = sum(1 for r in rows if abs(r["red"] + r["black"]) < 1e-9)
log(f"[eval200] n={len(rows)} 零和 {zero}/{len(rows)} sha256={digest}")

# ---------- 3. check20（一层后继筛，记录来源） ----------
checks, seen = [], set()
# 扫描线内「全部」状态（1..plies），不只 TAKE —— 自检显示只扫 5 个状态产量太低
SCAN = range(1, 13)


def scan_pass(profiles, seeds, pass_name):
    """对给定 (profile, seed) 集合，逐状态枚举红方一层着法，筛 black 被将且 red 未将。"""
    for profile in profiles:
        rules = Game(profile).rules
        for seed in seeds:
            if len(checks) >= 20:
                return
            gen, _ = BR.build_position(profile, seed, 12)
            states = replay(profile, gen)
            for i in SCAN:
                if len(checks) >= 20:
                    return
                if i >= len(states):
                    continue
                base = states[i]
                moves = sorted(rules.legal_moves(base),
                               key=lambda m: (m.target.row, m.target.col, m.source.row, m.source.col,
                                              m.promotion.value if m.promotion else ""))
                for mv in moves:
                    if len(checks) >= 20:
                        return
                    gg = Game.from_state(base.clone(), None, None)
                    try:
                        gg.move(mv)
                    except Exception:
                        continue
                    ns = gg.state
                    if rules.in_check(ns, Color.BLACK) and not rules.in_check(ns, Color.RED):
                        k = id16(rules, ns)
                        if k in seen:
                            continue
                        seen.add(k)
                        red, black = ev(ns, Color.RED), ev(ns, Color.BLACK)
                        checks.append({"id": k, "fp": fp(rules, ns),
                                       "red": round(red, 6), "black": round(black, 6),
                                       "sum": round(red + black, 6), "pass": pass_name,
                                       "src": {"profile": profile, "seed": seed, "stateIndex": i,
                                               "move": mv.key()}})


scan_pass(PROFILES, SEEDS, "A:seed700-709")
if len(checks) < 20:
    log(f"[check20] 一层筛（种子 700-709）只得到 {len(checks)} 条，扩展种子 710-729")
    scan_pass(PROFILES, range(710, 730) if not SMOKE else range(710, 714), "B:seed710-729")

json.dump(checks, open(os.path.join(out_dir, "base4_check20.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
minus60 = sum(1 for c in checks if abs(c["sum"] + 60) < 1e-9)
log(f"[check20] n={len(checks)} sum=-60 的 {minus60}/{len(checks)} "
    f"来源分布={ {p: sum(1 for c in checks if c['pass']==p) for p in ('A:seed700-709','B:seed710-729')} }")

# ---------- 4. 机动性表 ----------
TYPES = ("king", "advisor", "elephant", "horse", "rook", "cannon", "pawn", "guard",
         "patrol", "archer", "thunder")
ZH = {"king": "漢", "rook": "俥", "horse": "傌", "elephant": "相", "advisor": "仕", "cannon": "炮",
      "pawn": "兵", "guard": "尉", "archer": "射", "thunder": "檑", "armor": "甲",
      "assassin": "刺", "shield": "楯", "patrol": "巡"}
KINGS = [{"id": "kr", "type": "king", "color": "red", "row": 12, "col": 6},
         {"id": "kb", "type": "king", "color": "black", "row": 0, "col": 0}]


def mkstate(pieces, turn="red"):
    return GameState.from_dict({"profileId": "desktop_complete", "turn": turn, "pieces": pieces,
                                "history": [], "captured": {"red": [], "black": []},
                                "winner": None, "resultReason": None, "draw": False})


rules = Game("desktop_complete").rules
mob = []
for t in TYPES:
    if t == "king":
        continue
    for row in ((5, 6) if t == "pawn" else (6,)):
        pieces = [dict(k) for k in KINGS] + [
            {"id": f"x_{t}", "type": t, "color": "red", "row": row, "col": 6}]
        st = mkstate(pieces)
        n = sum(1 for m in rules.legal_moves(st)
                if (m.source.row, m.source.col) == (row, 6))
        mob.append({"type": t, "row": row, "col": 6, "moves": n})
log("[mobility] 空盘中心 " + ", ".join(f"{ZH[m['type']]}({m['type']})@{m['row']},{m['col']}={m['moves']}" for m in mob))

# 初始局面首着每子着数
g0 = Game("desktop_complete")
counts = {}
for m in g0.rules.legal_moves(g0.state):
    key = (m.source.row, m.source.col)
    counts[key] = counts.get(key, 0) + 1
by_type = {}
for p in g0.state.pieces:
    if p.color.value != "red":
        continue
    by_type.setdefault(p.type.value, []).append(counts.get((p.position.row, p.position.col), 0))
opening = {k: {"per": v, "total": sum(v)} for k, v in by_type.items()}
json.dump({"center": mob, "opening_red": opening},
          open(os.path.join(out_dir, "base4_mobility.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("[mobility] 初始局面红方首着: " + ", ".join(
    f"{ZH.get(k,k)}({k})={v['total']}({'+'.join(map(str, v['per']))})" for k, v in opening.items()))

open(os.path.join(out_dir, "summary.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
log("DONE")

# ---------- 5. 开局子力与阵型快照 ----------
g0b = Game("desktop_complete")
snap = {"profile": "desktop_complete",
        "total_pieces": len(g0b.state.pieces),
        "types": sorted({p.type.value for p in g0b.state.pieces}),
        "per_side": {}}
for color in ("red", "black"):
    side = sorted((p.type.value, p.position.row, p.position.col)
                  for p in g0b.state.pieces if p.color.value == color)
    from collections import Counter as _C
    snap["per_side"][color] = {"count": len(side),
                               "counts_by_type": dict(sorted(_C(t for t, _, _ in side).items())),
                               "positions": [{"type": t, "row": r, "col": c} for t, r, c in side]}
json.dump(snap, open(os.path.join(out_dir, "base4_opening_snapshot.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log(f"[opening] 全场 {snap['total_pieces']} 子 / {len(snap['types'])} 型：" + ", ".join(snap["types"]))
for color in ("red", "black"):
    d = snap["per_side"][color]
    log(f"  {color} {d['count']} 子: " + ", ".join(f"{ZH.get(k,k)}{v}" for k, v in d["counts_by_type"].items()))
