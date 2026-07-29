"""Sweep DRACO ASCENDANT's pre-lit cell set until it prices the mystery at 500x.

    ./env/bin/python games/starwake/reels/sweep_ascendant.py [nsims]

Ascendant is a Draco dealt with some cells ALREADY LIT. The knob is WHICH cells,
not how many: Draco splits into 6 easy body cells on the left reels (which light
almost by themselves) and 5 hard ones -- the dry reel-4 column plus the (3,2)
neck, which is a gate AND a key (once lit it is the reel-3 bridge a 5-kind needs
to reach reel 4).

PRE-LIGHTING PAYS THROUGH TWO CHANNELS and the second is the bigger one:
  1. fewer cells left to trace -> completes EARLIER -> higher ladder rungs;
  2. those cells are WILDS FROM SPIN ONE -> every win in the feature is richer,
     and the snowball can never cold-start.
Channel 2 is why a roam-length model underestimates: measured, 3 pre-lit cells
completed at mean roam 5.87 and paid 2,887x where the draco roam table predicts
~1,350x at that roam. So the set has to be swept, not derived.

Each variant runs buy_mystery patched to 100% ascendant (every book is one, so
the sample is not diluted 10:1) with the wincap slice stripped -- a forced slice
would both distort the mean and can loop if the cap drifts out of reach.

⚠ OVERWRITES library/publish_files/books_buy_mystery.jsonl.zst and that mode's
LUTs/force files. Move them aside first if the converged set matters.
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
CAP = 25000.0
MODE = "buy_mystery"

# The published mix, and the three tier means measured on the 100k confirmation
# pool. Mystery's cost is the probability-weighted average, so an Ascendant mean
# maps straight onto a mystery price -- that is the number each variant is judged on.
MIX = {"corvus": 0.350, "ursa": 0.295, "draco": 0.250, "ascendant": 0.100}
TIER_MEAN = {"corvus": 232.1, "ursa": 258.6, "draco": 502.4}
TARGET_COST = 500.0

# Hard cells first -- the ones that actually move the needle. Body-only is kept as
# a control: it should barely help, which is the whole point of the shape finding.
NECK, R40, R41, R42, R43 = (3, 2), (4, 0), (4, 1), (4, 2), (4, 3)
CANDIDATES = [
    [],                          # control: a plain draco
    [NECK],                      # the single most valuable cell (gate AND key)
    [R40, R41],                  # two reel-4 cells, no bridge
    [NECK, R40],
    [NECK, R40, R41],            # first pass -- measured 2,887x, too generous
    [(0, 2), (0, 3), (1, 1)],    # control: body only, should barely move
]


def mystery_cost(asc_mean):
    """What buy_mystery prices at if Ascendant averages `asc_mean`."""
    mean = sum(MIX[t] * TIER_MEAN[t] for t in TIER_MEAN) + MIX["ascendant"] * asc_mean
    return mean / RTP


def read_books():
    pays, roams, lit = [], [], []
    with open(f"library/publish_files/books_{MODE}.jsonl.zst", "rb") as f:
        reader = zstd.ZstdDecompressor().stream_reader(f)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            b = json.loads(line)
            pays.append(b["payoutMultiplier"] / 100.0)
            roams.append(sum(1 for e in b["events"] if e["type"] == "beastRoam"))
            d = [e for e in b["events"] if e["type"] == "constellationDealt"]
            lit.append(d[0]["litCount"] if d else 0)
    return pays, roams, lit


if __name__ == "__main__":
    nsims = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20000
    os.chdir(GAME)
    from gamestate import GameState
    from game_config import GameConfig
    from src.state.run_sims import create_books

    print(f"n={nsims:,}/variant   target: Ascendant mean that prices mystery at "
          f"{TARGET_COST:,.0f}x\n")
    header = (f"{'pre-lit cells':28s}{'lit':>4}{'mean':>10}{'complete':>10}"
              f"{'roam':>7}{'at cap':>8}{'median':>9}{'-> cost':>9}{'vs 500':>8}")
    print(header)
    print("-" * len(header))

    for cells in CANDIDATES:
        config = GameConfig()
        config.constellation_prelit_cells["ascendant"] = list(cells)
        # 100% ascendant, no wincap slice: undiluted sample, no forced-cap distortion
        bm = [b for b in config.bet_modes if b.get_name() == MODE][0]
        keep = [d for d in bm.get_distributions() if d.get_criteria() == "ascendant"]
        keep[0]._quota = 1.0
        bm._distributions = keep
        bm._wincap = config.wincap  # measure against the design cap, not a mode ceiling

        gamestate = GameState(config)
        os.makedirs(gamestate.output_files.temp_path, exist_ok=True)
        create_books(gamestate, config, {MODE: nsims}, 1000, 14, True, False)

        pays, roams, lit = read_books()
        n = len(pays)
        mean = sum(pays) / n
        cost = mystery_cost(mean)
        comp = sum(1 for r in roams if r) / n * 100
        roamed = [r for r in roams if r]
        label = " ".join(f"{r},{w}" for r, w in cells) or "(none - plain draco)"
        print(f"{label:28s}{(lit[0] if lit else 0):>4}{mean:>9,.0f}x{comp:>9.1f}%"
              f"{(sum(roamed)/len(roamed) if roamed else 0):>7.2f}"
              f"{sum(1 for p in pays if p >= CAP)/n*100:>7.2f}%"
              f"{sorted(pays)[n//2]:>8,.0f}x{cost:>8,.0f}x{cost/TARGET_COST:>7.2f}x")
