"""Sweep the NUMBER of constellation cells per tier.

    ./env/bin/python games/starwake/reels/sweep_cell_counts.py [nsims]

WHY. Draco's 11 cells make the board ~15 of 20 wild by the end, which looks like a
jackpot and pays ~0.33x the ticket -- the spectacle oversells the payout. Fewer
cells means less saturation AND earlier completion, which moves value from the
(boring) carpet to the (exciting) beast. But it also compresses the tier ladder,
and the ladder spread -- 84% / 63% / 32% completion -- is what justifies paying
520x for Draco instead of 240x for Corvus. So this measures the trade rather than
guessing it.

⚠ THIS OVERWRITES library/ FOR THE SWEPT MODES. Back them up first and restore
after; create_books writes to the standard paths.

WHAT SURVIVES A LADDER CHANGE. completion, cells-lit and roam depth are
ladder-independent (payout-only knobs cannot move them -- verified when the
ladders were swept). Price, ceiling and beat-the-ticket are NOT, so re-derive
those if the multiplier mechanic changes.

Difficulty comes from REEL POSITION, not count: reels 0-2 light off a 3-of-a-kind
("easy"), reel 3 needs a 4-kind, reel 4 needs a full 5-kind and carries no wilds
of its own on FR0. Each variant below keeps roughly the current easy/gate ratio
per tier so the comparison is about COUNT, not shape.
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

# variant -> tier -> cells. Corvus is unchanged everywhere (it already feels right).
VARIANTS = {
    "current 4/7/11": {
        "corvus": [(0, 1), (1, 0), (1, 2), (2, 1)],
        "ursa": [(0, 1), (0, 2), (1, 1), (1, 2), (2, 0), (3, 0), (4, 1)],
        "draco": [(0, 2), (0, 3), (1, 1), (1, 2), (2, 0), (2, 1),
                  (3, 2), (4, 0), (4, 1), (4, 2), (4, 3)],
    },
    "A  4/5/6": {
        "corvus": [(0, 1), (1, 0), (1, 2), (2, 1)],
        "ursa": [(0, 1), (0, 2), (1, 1), (3, 0), (4, 1)],
        "draco": [(0, 2), (1, 1), (2, 1), (3, 1), (4, 1), (4, 2)],
    },
    "B  4/6/8": {
        "corvus": [(0, 1), (1, 0), (1, 2), (2, 1)],
        "ursa": [(0, 1), (0, 2), (1, 1), (1, 2), (3, 0), (4, 1)],
        "draco": [(0, 2), (0, 3), (1, 1), (2, 1), (3, 1), (4, 1), (4, 2), (4, 3)],
    },
    "C  4/6/9": {
        "corvus": [(0, 1), (1, 0), (1, 2), (2, 1)],
        "ursa": [(0, 1), (0, 2), (1, 1), (1, 2), (3, 0), (4, 1)],
        "draco": [(0, 2), (0, 3), (1, 1), (1, 2), (2, 1),
                  (3, 1), (4, 1), (4, 2), (4, 3)],
    },
}

MODES = {"corvus": "buy_corvus", "ursa": "buy_ursa", "draco": "buy_draco"}


def check(variant, tier, cells):
    assert len(set(cells)) == len(cells), f"{variant}/{tier}: duplicate cells"
    assert all(0 <= r < 5 and 0 <= row < 4 for r, row in cells), f"{variant}/{tier}: off-grid"


def summarise(tier, cells, rtp):
    """Read the tape just written for this tier and score it."""
    path = f"library/publish_files/books_{MODES[tier]}.jsonl.zst"
    done, carpet, lit_end, roam_depth, wild_end = [], [], [], [], []
    with open(path, "rb") as fh:
        reader = zstd.ZstdDecompressor().stream_reader(fh)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            book = json.loads(line)
            pay = book["payoutMultiplier"] / 100.0
            lit = 0
            roams = 0
            beast_cells = 0
            woke = False
            for e in book["events"]:
                if e["type"] == "starLit":
                    lit = e["litCount"]
                elif e["type"] == "beastWake":
                    woke = True
                elif e["type"] == "beastRoam":
                    roams += 1
                    beast_cells = len(e["cells"])
            lit_end.append(lit)
            wild_end.append(lit + beast_cells)
            roam_depth.append(roams)
            (done if woke else carpet).append(pay)

    allp = done + carpet
    n = len(allp)
    mean = sum(allp) / n
    cost = mean / rtp
    easy = sum(1 for r, _ in cells if r <= 2)
    return {
        "tier": tier,
        "cells": len(cells),
        "easy_gate": f"{easy}/{len(cells) - easy}",
        "completion": len(done) / n * 100,
        "lit": sum(lit_end) / n,
        "wild": sum(wild_end) / n,
        "roam": sum(roam_depth) / n,
        "cost": cost,
        "max": max(allp),
        "beat": sum(1 for p in allp if p >= cost) / n * 100,
        "carpet": sum(carpet) / len(carpet) if carpet else 0.0,
        "beast": sum(done) / len(done) if done else 0.0,
    }


if __name__ == "__main__":
    nsims = int(sys.argv[1]) if len(sys.argv) > 1 else 20000

    for v, tiers in VARIANTS.items():
        for t, cells in tiers.items():
            check(v, t, cells)

    os.chdir(GAME)
    from gamestate import GameState
    from game_config import GameConfig
    from src.state.run_sims import create_books

    config = GameConfig()
    rtp = config.rtp

    # Strip forced-wincap slices: they manufacture a spin-1 completion and would
    # flatter every variant equally while adding a chunk of noise to the mean.
    for bm in config.bet_modes:
        kept = [d for d in bm.get_distributions() if d.get_criteria() != "wincap"]
        if len(kept) != len(bm.get_distributions()):
            for d in kept:
                d._quota = 1.0 / len(kept)
            bm._distributions = kept
    gamestate = GameState(config)

    results = {}
    for vname, tiers in VARIANTS.items():
        rows = []
        for tier, cells in tiers.items():
            config.constellation_cells[tier] = cells
            os.makedirs(gamestate.output_files.temp_path, exist_ok=True)
            create_books(gamestate, config, {MODES[tier]: nsims}, 1000, 14, True, False)
            rows.append(summarise(tier, cells, rtp))
        results[vname] = rows

    print("\n" + "=" * 108)
    print(f"CONSTELLATION CELL-COUNT SWEEP   n={nsims:,} per tier per variant   (wincap slice stripped)")
    print("=" * 108)
    hdr = (f"{'variant':16s}{'tier':8s}{'cells':>6s}{'e/g':>6s}{'complete':>10s}{'lit':>7s}"
           f"{'wild/20':>9s}{'roam':>7s}{'cost':>9s}{'max':>10s}{'beat tkt':>10s}{'carpet':>9s}{'beast':>9s}")
    print(hdr)
    print("-" * 108)
    for vname, rows in results.items():
        for i, r in enumerate(rows):
            label = vname if i == 0 else ""
            print(f"{label:16s}{r['tier']:8s}{r['cells']:>6d}{r['easy_gate']:>6s}"
                  f"{r['completion']:9.1f}%{r['lit']:7.1f}{r['wild']:9.1f}{r['roam']:7.1f}"
                  f"{r['cost']:8,.0f}x{r['max']:10,.0f}x{r['beat']:9.1f}%"
                  f"{r['carpet']:8,.0f}x{r['beast']:8,.0f}x")
        print("-" * 108)

    print("\nreading it:")
    print("  complete  needs SPREAD across tiers -- that spread is why draco costs 2x corvus")
    print("  wild/20   board saturation at feature end; the 'too packed' complaint, measured")
    print("  roam      spins the beast was awake = how deep into the multiplier ladder")
    print("  beat tkt  share of buys paying at least their own implied cost")
    print("\n  completion / lit / wild / roam are LADDER-INDEPENDENT and stay valid if the")
    print("  multiplier mechanic changes. cost / max / beat / carpet / beast do NOT.")
