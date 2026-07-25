"""Draco cell-shape probe: measure the carpet-vs-completion trade-off directly.

    ./env/bin/python games/starwake/reels/sweep_draco_cells.py [nsims]

Draco has 11 cells on a 5x4 grid and only ONE genuinely hard column. A cell lights
when a winning payline crosses it, so difficulty is really "how long a win does
this cell need": reels 0-2 light off a 3-of-a-kind, reel 3 needs a 4-kind, reel 4
needs a full 5-kind (and FR0 reel 4 carries no wilds of its own).

That makes the shape a ZERO-SUM allocation, which is the thing worth measuring:
  more easy cells  -> thicker wild carpet (draco's price, and per doc L92 its main
                      event) but FEWER hard gates, so it completes MORE often;
  more hard cells  -> genuinely rare dragon, but a thinner carpet.
Both raise the price by different routes, so the shape cannot be reasoned out on
paper -- run the candidates and read the curve.

Only buy_draco is simulated; corvus and ursa have their own cell maps.
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

# Candidate shapes. Every one is 11 cells, on-grid, no duplicates -- asserted below.
# "easy" = reels 0-2, "gate" = reel 3 (medium) or reel 4 (hard).
SHAPES = {
    # committed shape: 6 easy body + a reel-3 neck + the whole reel-4 column
    "current": [(0, 2), (0, 3), (1, 1), (1, 2), (2, 0), (2, 1),
                (3, 2), (4, 0), (4, 1), (4, 2), (4, 3)],
    # thicker carpet, weaker gate: 8 easy body, head loses the neck and one reel-4 cell
    "carpet8": [(0, 1), (0, 2), (0, 3), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2),
                (4, 1), (4, 2), (4, 3)],
    # rarer dragon, thinner carpet: 5 easy body + a two-cell reel-3 neck + reel-4 column
    "gate6": [(0, 2), (0, 3), (1, 1), (1, 2), (2, 1),
              (3, 1), (3, 2), (4, 0), (4, 1), (4, 2), (4, 3)],
    # thick carpet AND a full hard column: 7 easy, no reel-3 neck at all
    "carpet7": [(0, 1), (0, 2), (0, 3), (1, 1), (1, 2), (2, 0), (2, 1),
                (4, 0), (4, 1), (4, 2), (4, 3)],
}


def check(name, cells):
    assert len(cells) == 11, f"{name}: draco is an 11-star constellation, got {len(cells)}"
    assert len(set(cells)) == 11, f"{name}: duplicate cells"
    assert all(0 <= r < 5 and 0 <= row < 4 for r, row in cells), f"{name}: off-grid cell"


def summarise(name, cells):
    done, carpet, lit_counts = [], [], []
    with open("library/publish_files/books_buy_draco.jsonl.zst", "rb") as f:
        reader = zstd.ZstdDecompressor().stream_reader(f)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            book = json.loads(line)
            pay = book["payoutMultiplier"] / 100.0
            # litCount is cumulative, so the last starLit is how far the set got
            lit = max((e["litCount"] for e in book["events"] if e["type"] == "starLit"), default=0)
            lit_counts.append(lit)
            (done if any(e["type"] == "beastWake" for e in book["events"]) else carpet).append(pay)
    n = len(done) + len(carpet)
    allp = done + carpet
    mean = sum(allp) / n
    easy = sum(1 for r, _ in cells if r <= 2)
    return {
        "name": name, "easy": easy, "gate": 11 - easy,
        "completion": len(done) / n * 100,
        "lit": sum(lit_counts) / n,
        "mean": mean, "cost": mean / 0.9665, "max": max(allp),
        "carpet": sum(carpet) / len(carpet) if carpet else 0.0,
        "beast": sum(done) / len(done) if done else 0.0,
    }


if __name__ == "__main__":
    nsims = int(sys.argv[1]) if len(sys.argv) > 1 else 40000
    for name, cells in SHAPES.items():
        check(name, cells)

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
    gamestate = GameState(config)

    rows = []
    for name, cells in SHAPES.items():
        config.constellation_cells["draco"] = cells
        # create_books removes its temp dir on return, so put it back for the next run
        os.makedirs(gamestate.output_files.temp_path, exist_ok=True)
        create_books(gamestate, config, {"buy_draco": nsims}, 1000, 14, True, False)
        rows.append(summarise(name, cells))

    print("\n" + "=" * 96)
    print(f"buy_draco cell shapes   n={nsims:,} each   (no forced wincap slice)")
    print("=" * 96)
    print(f"{'shape':10s} {'easy/gate':>10s} {'complete':>9s} {'lit avg':>8s} {'cost':>9s} "
          f"{'max':>10s} {'max/cost':>9s} {'carpet':>9s} {'beast':>10s}")
    for r in rows:
        print(f"{r['name']:10s} {str(r['easy'])+'/'+str(r['gate']):>10s} {r['completion']:8.1f}% "
              f"{r['lit']:8.1f} {r['cost']:8,.0f}x {r['max']:10,.0f}x {r['max']/r['cost']:8.0f}x "
              f"{r['carpet']:8,.0f}x {r['beast']:9,.0f}x")
    print("\nwant: cost ABOVE ursa's 283x, completion well under corvus's 84%, max >=25,000x")
