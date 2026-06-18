"""Reel-strip generator for Keybearer.

Builds the four reel strips from explicit per-reel symbol-weight tables, so
strip tuning is just "edit a weight, re-run this file". Run from anywhere:

    env/bin/python games/0_0_keybearer/reels/generate_reels.py

Design intent (qualitative -- exact frequencies are tuned by SIMULATION):
  BR0    base game:    lows-heavy, wilds rare, keys calibrated so that
                       3 keys ~1/150, 4 ~1/2000, 5 ~1/100k (verify by sim).
  FR_STD Standard FG:  wild-rich (wilds carry the 2x-10x local multipliers).
  FR_SUP Super/Mega FG: key-rich, so Keys keep landing and charge the Vault;
                       fewer wilds (Super wins come from the Vault, not wilds).
  WCAP   wincap helper: key-rich + boosted top symbol so the forced max-win
                       (25,000x) is actually reachable.

Symbols: W wild, K key/scatter, H1-H4 high, L1-L5 low.
Weights below are per-reel symbol COUNTS; all five reels share the same table
(so every column has equal length and the CSV stays rectangular).
"""

import csv
import os
import random

SEED = 1
KEYBEARER_REELS = os.path.dirname(os.path.abspath(__file__))

# Each entry: filename -> {symbol: count_per_reel}
STRIP_WEIGHTS = {
    "BR0.csv": {
        "H1": 6, "H2": 8, "H3": 10, "H4": 12,
        "L1": 16, "L2": 18, "L3": 20, "L4": 20, "L5": 22,
        "W": 2, "K": 3,
    },
    "FR_STD.csv": {
        "H1": 6, "H2": 7, "H3": 8, "H4": 9,
        "L1": 12, "L2": 13, "L3": 14, "L4": 14, "L5": 14,
        "W": 14, "K": 2,
    },
    "FR_SUP.csv": {
        # Key-rich enough to keep charging the Vault, but NOT so dense that
        # 3+ Keys (the retrigger threshold) happens most spins -- that made the
        # freegame branching factor > 1 and the feature ran unbounded.
        "H1": 6, "H2": 7, "H3": 8, "H4": 9,
        "L1": 12, "L2": 13, "L3": 14, "L4": 14, "L5": 14,
        "W": 3, "K": 6,
    },
    "FRWCAP.csv": {
        "H1": 8, "H2": 6, "H3": 5, "H4": 5,
        "L1": 6, "L2": 6, "L3": 6, "L4": 6, "L5": 6,
        "W": 6, "K": 18,
    },
}

NUM_REELS = 5


def build_reel(weights, rng):
    """Return a shuffled list of symbols for one reel from a weight table."""
    strip = []
    for sym, count in weights.items():
        strip.extend([sym] * count)
    rng.shuffle(strip)
    return strip


def write_strip(filename, weights):
    rng = random.Random(SEED + hash(filename) % 10_000)
    reels = [build_reel(weights, rng) for _ in range(NUM_REELS)]
    length = len(reels[0])
    path = os.path.join(KEYBEARER_REELS, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in range(length):
            writer.writerow([reels[r][row] for r in range(NUM_REELS)])
    return length


if __name__ == "__main__":
    for filename, weights in STRIP_WEIGHTS.items():
        length = write_strip(filename, weights)
        keys = weights.get("K", 0)
        wilds = weights.get("W", 0)
        print(f"{filename:12s} len={length:3d}/reel  K={keys:2d}  W={wilds:2d}")
    # FR0.csv is superseded by FR_STD.csv
    old = os.path.join(KEYBEARER_REELS, "FR0.csv")
    if os.path.exists(old):
        os.remove(old)
        print("removed superseded FR0.csv")
    print("done.")
