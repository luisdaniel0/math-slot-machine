"""FR0 wild-density probe: set the weights, regenerate ONLY FR0, measure all three buys.

    ./env/bin/python games/starwake/reels/sweep_fr0.py <W_reels012> <W_reel3> <W_reel4> [nsims]
    e.g.  sweep_fr0.py 4 2 0 40000

Why this exists: feature payout and completion rate are driven by the SAME thing
(a cell lights when a winning payline crosses it), so wild density moves the buy
prices and the completion ladder together and neither can be reasoned about on
paper. One command per hypothesis is the only honest way through it.

Two things it does deliberately:
  - rewrites FR0 ONLY, never BR0/FRWCAP, so a probe cannot move the base game
    underneath the measurement (see the crc32 seed note in generate_reels.py);
  - drops each mode's forced-wincap slice, because that slice re-rolls until it
    pays exactly the cap -- once drying puts the cap out of reach it would spin
    forever, and the NATURAL ceiling is the number we actually want to read.

It does NOT write the weights back to generate_reels.py. When a probe wins, copy
the numbers into STRIP_WEIGHTS by hand -- the sweep stays a measurement, and the
committed strips only ever change through a deliberate edit.
"""
import csv
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
sys.path.insert(0, HERE)

import generate_reels as gr  # noqa: E402

MODES = ["buy_corvus", "buy_ursa", "buy_draco"]


def set_fr0_wilds(w012, w3, w4):
    """Patch the FR0 spec in memory and rewrite that one strip."""
    spec = gr.STRIP_WEIGHTS["FR0.csv"]
    spec["base"]["W"] = w012
    spec["per_reel"] = {3: {"W": w3}, 4: {"W": w4}}
    length, tables = gr.write_strip("FR0.csv", spec)
    density = [t["W"] / sum(t.values()) * 100 for t in tables]
    print(f"FR0 rewritten: len={length}/reel  W={w012}/{w012}/{w012}/{w3}/{w4}  "
          f"density={'/'.join(f'{d:.1f}%' for d in density)}\n")


def measure(nsims):
    os.chdir(GAME)
    from gamestate import GameState          # imported AFTER the strip is written
    from game_config import GameConfig
    from src.state.run_sims import create_books

    config = GameConfig()
    for bm in config.bet_modes:
        kept = [d for d in bm.get_distributions() if d.get_criteria() != "wincap"]
        if len(kept) != len(bm.get_distributions()):
            for d in kept:
                d._quota = 1.0 / len(kept)
            bm._distributions = kept

    # One call for ALL modes: create_books deletes its temp directory on return,
    # so calling it per-mode leaves the next mode's threads with nowhere to write.
    gamestate = GameState(config)
    create_books(gamestate, config, {m: nsims for m in MODES}, 1000, 14, True, False)
    return [summarise(m) for m in MODES]


def summarise(mode):
    """Split a mode's books by whether the beast ever woke -- the carpet/lottery split."""
    done, carpet = [], []
    path = f"library/publish_files/books_{mode}.jsonl.zst"
    with open(path, "rb") as f:
        reader = zstd.ZstdDecompressor().stream_reader(f)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            book = json.loads(line)
            pay = book["payoutMultiplier"] / 100.0
            (done if any(e["type"] == "beastWake" for e in book["events"]) else carpet).append(pay)
    n = len(done) + len(carpet)
    allp = done + carpet
    return {
        "mode": mode,
        "completion": len(done) / n * 100,
        "mean": sum(allp) / n,
        "max": max(allp),
        "done_mean": sum(done) / len(done) if done else 0.0,
        "carpet_mean": sum(carpet) / len(carpet) if carpet else 0.0,
        "zero": sum(1 for p in allp if p == 0) / n * 100,
    }


if __name__ == "__main__":
    w012, w3, w4 = (int(a) for a in sys.argv[1:4])
    nsims = int(sys.argv[4]) if len(sys.argv) > 4 else 40000

    set_fr0_wilds(w012, w3, w4)
    rows = measure(nsims)

    print("\n" + "=" * 92)
    print(f"FR0 W={w012}/{w012}/{w012}/{w3}/{w4}   n={nsims:,} per mode   (no forced wincap slice)")
    print("=" * 92)
    print(f"{'mode':12s} {'complete':>9s} {'mean':>10s} {'cost':>9s} {'max':>10s} "
          f"{'max/cost':>9s} {'beast':>10s} {'carpet':>9s} {'zero':>6s}")
    for r in rows:
        cost = r["mean"] / 0.9665
        print(f"{r['mode']:12s} {r['completion']:8.1f}% {r['mean']:10,.0f}x {cost:8,.0f}x "
              f"{r['max']:10,.0f}x {r['max']/cost:8.0f}x {r['done_mean']:9,.0f}x "
              f"{r['carpet_mean']:8,.0f}x {r['zero']:5.2f}%")
    print("\ntargets: cost ~50 / ~100 / ~200x, draco max >=25,000x, zero-pay 0.00%, "
          "completion ~95 / ~44 / ~2%")
