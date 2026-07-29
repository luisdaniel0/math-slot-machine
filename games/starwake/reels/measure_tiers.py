"""Per-tier baseline: what does each buy actually pay, and how does it feel?

    ./env/bin/python games/starwake/reels/measure_tiers.py [nsims] [tier ...]

Reports, for buy_corvus / buy_ursa / buy_draco, the numbers every economy decision
in CLAUDE.md turns on:

  ECONOMY   completion rate, price (mean/rtp), natural ceiling, max/cost, >cost
  GAP       carpet max vs cheapest completion (the Draco cliff), widest hole
  FEEL      payout distribution in TICKET MULTIPLES + percentiles

`>cost` and completion rate are the same number whenever the carpet tops out below
cost (you beat the ticket iff you complete) -- watching them diverge is how you see
a cliff close.

Roam length is reported too because it is the tail's real driver: rung index =
roam spins elapsed = how early the constellation completed.

⚠ OVERWRITES THE PRODUCTION POOL for each tier it runs (create_books writes to the
standard library/ paths). Back library/ up first. The forced wincap slice is
stripped -- at a baseline ladder the cap may be out of structural reach, and an
unsatisfiable forced slice loops forever.
"""
import io
import json
import os
import sys

import zstandard as zstd

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(GAME))
sys.path.insert(0, ROOT)
sys.path.insert(0, GAME)

RTP = 0.9665
CAP = 25000.0   # design wincap; "at cap" = reached it, so a forced slice is findable
EDGES = [0, 0.001, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf")]
LABELS = ["zero", "0-0.25x", "0.25-0.5x", "0.5-1x", "1-2x", "2-5x", "5-10x", "10x+"]


def widest_hole(payouts, floor=20.0):
    """Largest multiplicative span above `floor` containing no outcome at all."""
    vals = sorted({p for p in payouts if p >= floor})
    best = (0.0, 0.0, 1.0)
    for lo, hi in zip(vals, vals[1:]):
        if lo > 0 and hi / lo > best[2]:
            best = (lo, hi, hi / lo)
    return best


def read_books(mode):
    """-> (payouts, woke flags, roam-spin counts) for one mode's book tape."""
    pays, woke, roams = [], [], []
    path = f"library/publish_files/books_{mode}.jsonl.zst"
    with open(path, "rb") as f:
        reader = zstd.ZstdDecompressor().stream_reader(f)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            book = json.loads(line)
            pays.append(book["payoutMultiplier"] / 100.0)
            n_roam = sum(1 for e in book["events"] if e["type"] == "beastRoam")
            woke.append(any(e["type"] == "beastWake" for e in book["events"]))
            roams.append(n_roam)
    return pays, woke, roams


def summarise(tier, pays, woke, roams):
    n = len(pays)
    mean = sum(pays) / n
    cost = mean / RTP
    ordered = sorted(pays)
    done = [p for p, w in zip(pays, woke) if w]
    carpet = [p for p, w in zip(pays, woke) if not w]
    lo, hi, ratio = widest_hole(pays)

    buckets = [0] * len(LABELS)
    for p in pays:
        r = p / cost
        for i in range(len(LABELS)):
            if EDGES[i] <= r < EDGES[i + 1]:
                buckets[i] += 1
                break
    pcts = {q: ordered[min(int(q * n), n - 1)] / cost for q in (0.25, 0.5, 0.75, 0.9, 0.99)}
    roamed = [r for r in roams if r]
    return dict(
        tier=tier, n=n, completion=len(done) / n * 100, cost=cost, mean=mean,
        median=ordered[n // 2], mx=max(pays), over=sum(1 for p in pays if p > cost) / n * 100,
        zero=sum(1 for p in pays if p == 0) / n * 100,
        at_cap=sum(1 for p in pays if p >= CAP) / n * 100,
        carpet_max=max(carpet) if carpet else 0.0, beast_min=min(done) if done else 0.0,
        hole=(lo, hi, ratio), buckets=[b / n * 100 for b in buckets], pcts=pcts,
        roam_mean=sum(roamed) / len(roamed) if roamed else 0.0,
        roam_max=max(roams) if roams else 0,
    )


def report(rows):
    w = f"{'':14s}" + "".join(f"{r['tier']:>12s}" for r in rows)
    print("\n" + "=" * (14 + 12 * len(rows)))
    print(f"BASELINE   n={rows[0]['n']:,}/tier   (forced wincap slice stripped)")
    print("=" * (14 + 12 * len(rows)))
    print(w)
    def line(label, key, fmt, suffix=""):
        print(f"{label:14s}" + "".join(format(r[key], fmt) + suffix for r in rows))
    print("\n-- ECONOMY")
    line("completion", "completion", ">10.2f", "%")
    line("price", "cost", ">10,.0f", "x")
    line("mean win", "mean", ">10,.0f", "x")
    line("median", "median", ">10,.0f", "x")
    line("natural max", "mx", ">10,.0f", "x")
    line("at cap", "at_cap", ">10.3f", "%")
    print(f"{'max/cost':14s}" + "".join(f"{r['mx']/r['cost']:>11,.0f}x" for r in rows))
    line(">cost", "over", ">10.2f", "%")
    line("zero pay", "zero", ">10.2f", "%")
    print("\n-- GAP (the Draco cliff)")
    line("carpet max", "carpet_max", ">10,.0f", "x")
    line("cheapest win", "beast_min", ">10,.0f", "x")
    print(f"{'cliff':14s}" + "".join(
        f"{(r['beast_min']/r['carpet_max'] if r['carpet_max'] else 0):>11.1f}x" for r in rows))
    print(f"{'widest hole':14s}" + "".join(f"{r['hole'][2]:>11.2f}x" for r in rows))
    for r in rows:
        lo, hi, ratio = r["hole"]
        print(f"    {r['tier']:12s} widest hole {lo:>8,.0f}x -> {hi:>8,.0f}x  ({ratio:.2f}x)")
    print("\n-- ROAM (rung index = roam spins elapsed = how early it completed)")
    line("mean roam", "roam_mean", ">11.2f")
    line("max roam", "roam_max", ">11d")
    print("   (mean roam is over COMPLETED features only)")
    print("\n-- FEEL (share of buys, in multiples of that tier's own ticket)")
    print(w)
    for i, lab in enumerate(LABELS):
        print(f"{lab:14s}" + "".join(f"{r['buckets'][i]:>11.2f}%" for r in rows))
    print()
    for q in (0.25, 0.5, 0.75, 0.9, 0.99):
        print(f"{'p'+str(int(q*100)):14s}" + "".join(f"{r['pcts'][q]:>11.2f}x" for r in rows))


if __name__ == "__main__":
    args = sys.argv[1:]
    nsims = int(args[0]) if args and args[0].isdigit() else 40000
    tiers = [a for a in args if not a.isdigit()] or ["corvus", "ursa", "draco"]

    os.chdir(GAME)
    from gamestate import GameState
    from game_config import GameConfig
    from src.state.run_sims import create_books

    config = GameConfig()
    for bm in config.bet_modes:
        kept = [d for d in bm.get_distributions() if d.get_criteria() != "wincap"]
        if len(kept) != len(bm.get_distributions()):
            for d in kept:
                d._quota = 1.0 / len(kept)
            bm._distributions = kept
        # BetMode.max_win is ALSO the engine clamp (run_sims.py -> config.wincap),
        # so the published per-mode ceilings (corvus 1500x, ursa 4750x) would cap the
        # draw and hand back the OLD decision as if it were a natural limit. Measure
        # every tier under the one design cap instead.
        bm._wincap = config.wincap
    gamestate = GameState(config)

    spins = config.num_feature_spins
    print(f"roam floor {config.min_roam_spins} | "
          f"beasts {set(config.constellation_beast_shapes.values())}")
    for t, l in config.constellation_mult_ladders.items():
        print(f"  {t:7s} {spins[t]:2d} spins | ladder ({len(l):2d} rungs) {l}")

    rows = []
    for tier in tiers:
        mode = f"buy_{tier}"
        os.makedirs(gamestate.output_files.temp_path, exist_ok=True)
        create_books(gamestate, config, {mode: nsims}, 1000, 14, True, False)
        rows.append(summarise(tier, *read_books(mode)))
    report(rows)
