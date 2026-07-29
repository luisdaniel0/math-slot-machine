"""Beast-size / roam-floor probe: does the Draco payout cliff close?

    ./env/bin/python games/starwake/reels/sweep_beast.py [nsims]

buy_draco has a structural win-range gap -- no book pays between 400x and 3,000x
-- which is a hard compliance gate ("no win-range gaps between small pays and the
max", doc L300-301) and sits right across its own 651x cost.

Three step-changes fire together at completion: the board goes near-fully wild,
the multiplier switches on for the FIRST time (non-completions have no multiplier
at all -- sticky stars are x1 under Option A), and min_roam_spins guarantees a
minimum number of spins of it. So the cheapest completion starts far above
anything the carpet can reach.

This measures both levers. Finding: beast size alone NARROWS the cliff but never
closes it (the carpet always tops out at 336x, since it happens before the wake);
min_roam_spins is what actually closes it.

⚠ This OVERWRITES the production buy_draco pool (create_books writes to the
standard library/ paths). Move library/{publish_files,lookup_tables,forces,
configs} buy_draco artifacts aside first and move them back after.

Only buy_draco is simulated, and the forced wincap slice is stripped -- a shrunken
beast puts 25,000x out of structural reach, and a forced-wincap slice that can
never be satisfied loops forever.
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

# (label, (reel_span, row_span), min_roam_spins)
COMBOS = [
    ("3x3", (3, 3), 5),          # committed config
    ("3x3", (3, 3), 3),
    ("3x3", (3, 3), 2),
    ("2x2", (2, 2), 5),
    ("2x2", (2, 2), 3),
    ("2x2", (2, 2), 2),
]


def widest_hole(payouts, floor=20.0):
    """Largest multiplicative span containing no outcome at all, above `floor`."""
    vals = sorted({p for p in payouts if p >= floor})
    best = (0.0, 0.0, 1.0)
    for lo, hi in zip(vals, vals[1:]):
        if lo > 0 and hi / lo > best[2]:
            best = (lo, hi, hi / lo)
    return best


def summarise(name, shape):
    done, carpet = [], []
    with open("library/publish_files/books_buy_draco.jsonl.zst", "rb") as f:
        reader = zstd.ZstdDecompressor().stream_reader(f)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            book = json.loads(line)
            pay = book["payoutMultiplier"] / 100.0
            woke = any(e["type"] == "beastWake" for e in book["events"])
            (done if woke else carpet).append(pay)
    allp = done + carpet
    n = len(allp)
    mean = sum(allp) / n
    cost = mean / 0.9665
    lo, hi, ratio = widest_hole(allp)
    return {
        "name": name,
        "roam_pos": (5 - shape[0] + 1) * (4 - shape[1] + 1),
        "completion": len(done) / n * 100,
        "cost": cost,
        "max": max(allp),
        "median": sorted(allp)[n // 2],
        "carpet_max": max(carpet) if carpet else 0.0,
        "beast_min": min(done) if done else 0.0,
        "hole_lo": lo, "hole_hi": hi, "hole_ratio": ratio,
        "over_cost": sum(1 for p in allp if p > cost) / n * 100,
    }


if __name__ == "__main__":
    nsims = int(sys.argv[1]) if len(sys.argv) > 1 else 40000

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
    for label, shape, roam in COMBOS:
        config.constellation_beast_shapes["draco"] = shape
        config.min_roam_spins = roam
        # create_books removes its temp dir on return, so put it back for the next run
        os.makedirs(gamestate.output_files.temp_path, exist_ok=True)
        create_books(gamestate, config, {"buy_draco": nsims}, 1000, 14, True, False)
        rows.append(summarise(f"{label} roam>={roam}", shape))

    print("\n" + "=" * 104)
    print(f"buy_draco beast size x roam floor   n={nsims:,} each   (no forced wincap slice)")
    print("=" * 104)
    print(f"{'config':14s}{'roam pos':>9s}{'complete':>10s}{'cost':>9s}{'median':>9s}"
          f"{'max':>10s}{'max/cost':>10s}{'>cost':>8s}   {'widest hole':>28s}")
    for r in rows:
        hole = f"{r['hole_lo']:,.0f}x -> {r['hole_hi']:,.0f}x ({r['hole_ratio']:.1f}x)"
        print(f"{r['name']:14s}{r['roam_pos']:9d}{r['completion']:9.1f}%{r['cost']:8,.0f}x"
              f"{r['median']:8,.0f}x{r['max']:9,.0f}x{r['max']/r['cost']:9.0f}x"
              f"{r['over_cost']:7.1f}%   {hole:>28s}")
    print()
    print(f"{'config':14s}{'carpet tops out':>18s}{'cheapest completion':>22s}{'cliff':>9s}")
    for r in rows:
        cliff = r["beast_min"] / r["carpet_max"] if r["carpet_max"] else 0
        print(f"{r['name']:14s}{r['carpet_max']:17,.0f}x{r['beast_min']:21,.0f}x{cliff:8.1f}x")
    print("\nwant: cliff near 1x (a continuum), cost above ursa's, max still reaching 25,000x")
