"""Reel-strip generator for Starwake.

Builds the three reel strips from explicit per-reel symbol-weight tables, so
strip tuning is just "edit a weight, re-run this file". Run from anywhere:

    env/bin/python games/starwake/reels/generate_reels.py

WHAT THE STRIPS DO (and, importantly, DON'T do) in this engine
--------------------------------------------------------------
Trigger RATE and TIER MIX are NOT set by strip star density. draw_board redraws
away any >=3-scatter board in the non-forced `basegame` branch and FORCES the
scatter count in the `freegame`/`wincap` branches, so triggering is driven by the
betmode DISTRIBUTIONS in game_config (quotas + `scatter_triggers` weights). Proof:
the bonus-mode tier mix tracks freegame `scatter_triggers` {3:50,4:20,5:5}
(~67/25/8%), not any strip. So the strips' actual jobs are:

  BR0    base game:   the win mix -- lows-heavy so small wins are FREQUENT (the
                      basegame hit-rate is the global RTP dial; tune at 1e6, not
                      on quick runs -- Keybearer lesson). Wilds RARE (they
                      substitute and inflate base wins/vol). ~5 stars/reel purely
                      so force_special_board has scatters to place, plus 0-2-star
                      anticipation texture -- NOT to set the trigger rate.
  FR0    freegame:    the real tuning surface. Wild-RICH: sticky lit stars + these
                      strip wilds are what make wins escalate (the snowball), which
                      drives BOTH completion rates and roam payouts. NO stars
                      (retriggers are disabled and cell-fill is win-line-driven, so
                      a scatter here is dead weight that only dilutes win density).
  FRWCAP wincap help: wild-rich + boosted top symbol (H1) so a FORCED max-win
                      (25,000x) is actually reachable. NO stars.

COMPLETION LADDER (the known open bug): on the scaffold strips Draco (~59%)
over-completes vs Ursa (~52%); Draco must be the RAREST. The snowball makes
5-kind wins common, and a 5-kind spans all reels so it crosses the "hard" reels
3-4 cells anyway, collapsing the reel-position difficulty the cell-maps rely on.
Levers, in order of preference, all measured on NATURAL (bonus-mode) sims:
  1. FR wild density here  -> snowball intensity (dampen = drier completion ladder).
  2. Per-reel FR drying    -> fewer wilds on reels 3-4 makes reel-4 wins rarer,
     which hurts Draco (5 hard cells) MORE than Ursa (2), re-separating the tiers.
     Not shipped yet: build_reel takes a flat table today; add per-reel overrides
     here when the measure loop calls for it.
  3. Draco SHAPE (game_config.constellation_cells) -- a strip-independent lever.
First-pass weights below are UNIFORM per reel and SIM-TUNABLE -- they exist to
give the measure loop a principled baseline, not to be final.

Symbols: W wild, S Star (scatter+filler), H1-H4 highs (Leo/Cygnus/Aquila/Lupus),
L1-L5 low card-ranks. Higher pay => rarer (H1 rarest high, L1 rarest low).
Weights are per-reel symbol COUNTS; every reel shares one table so the CSV stays
rectangular (equal column length).
"""

import csv
import os
import random

SEED = 1
STARWAKE_REELS = os.path.dirname(os.path.abspath(__file__))
NUM_REELS = 5

# filename -> {symbol: count_per_reel}
STRIP_WEIGHTS = {
    # Base: lows-heavy (frequent crumbs = hit-rate floor), wilds rare, stars only
    # to seed forced triggers + anticipation. Higher-paying symbol = lower count.
    "BR0.csv": {
        "H1": 8, "H2": 10, "H3": 12, "H4": 14,
        "L1": 18, "L2": 20, "L3": 22, "L4": 24, "L5": 26,
        "W": 2, "S": 5,
    },
    # Freegame: wild-rich (~8%) to power the snowball; NO stars. This is the strip
    # the completion ladder is tuned on -- drop W to dry completions, raise to wet.
    "FR0.csv": {
        "H1": 8, "H2": 10, "H3": 12, "H4": 14,
        "L1": 16, "L2": 18, "L3": 20, "L4": 22, "L5": 24,
        "W": 12, "S": 0,
    },
    # Wincap helper: wild-rich (~20%) + boosted H1 (the top 5-kind) so the FORCED
    # max-win is reachable; NO stars. Weighted 5:1 alongside FR0 in wincap books.
    "FRWCAP.csv": {
        "H1": 12, "H2": 8, "H3": 6, "H4": 6,
        "L1": 6, "L2": 6, "L3": 6, "L4": 6, "L5": 6,
        "W": 16, "S": 0,
    },
}


def build_reel(weights, rng):
    """Return a shuffled list of symbols for one reel from a weight table."""
    strip = []
    for sym, count in weights.items():
        strip.extend([sym] * count)
    rng.shuffle(strip)
    return strip


def write_strip(filename, weights):
    """Write one rectangular CSV (NUM_REELS columns), each column its own shuffle."""
    rng = random.Random(SEED + hash(filename) % 10_000)
    reels = [build_reel(weights, rng) for _ in range(NUM_REELS)]
    length = len(reels[0])
    path = os.path.join(STARWAKE_REELS, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in range(length):
            writer.writerow([reels[r][row] for r in range(NUM_REELS)])
    return length


if __name__ == "__main__":
    for filename, weights in STRIP_WEIGHTS.items():
        length = write_strip(filename, weights)
        wild = weights.get("W", 0)
        star = weights.get("S", 0)
        print(
            f"{filename:12s} len={length:3d}/reel  "
            f"W={wild:2d} ({100 * wild / length:4.1f}%)  S={star:2d}"
        )
    print("done.")
