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
  2. Per-reel FR drying    -> fewer wilds on reels 3-4 makes reel-3/4 wins rarer,
     which hurts Draco (5 hard cells) MORE than Ursa (2), re-separating the tiers
     WITHOUT starving ignition (reels 0-2 stay wet -> Corvus + carpet still pay, no
     cold-start bust). IMPLEMENTED via the {"base","per_reel"} spec form below --
     this is the active ladder lever (measure loop iteration).
  3. Draco SHAPE (game_config.constellation_cells) -- a strip-independent lever.
The weights below are SIM-TUNABLE, iterated by the measure loop against the buy-mode
completion ladder (target corvus ~90-97% / ursa ~50% / draco ~15-25%).

Symbols: W wild, S Star (scatter+filler), H1-H4 highs (Leo/Cygnus/Aquila/Lupus),
L1-L5 low card-ranks. Higher pay => rarer (H1 rarest high, L1 rarest low).
Weights are per-reel symbol COUNTS. Reels of unequal length (a dried reel has fewer
symbols) are padded with FILLER dust so the CSV stays rectangular.
"""

import csv
import os
import random

SEED = 1
STARWAKE_REELS = os.path.dirname(os.path.abspath(__file__))
NUM_REELS = 5

# dried reels are padded back to rectangular with this symbol (cheap dust)
FILLER = "L5"

# filename -> weight SPEC: either a flat {symbol: count} table (same on every reel)
# or {"base": {...}, "per_reel": {reel: {sym: count}}} to override specific reels.
STRIP_WEIGHTS = {
    # Base: lows-heavy (frequent crumbs = hit-rate floor), wilds rare, stars only
    # to seed forced triggers + anticipation. Higher-paying symbol = lower count.
    "BR0.csv": {
        "H1": 8, "H2": 10, "H3": 12, "H4": 14,
        "L1": 18, "L2": 20, "L3": 22, "L4": 24, "L5": 26,
        "W": 2, "S": 5,
    },
    # Freegame: THE completion-ladder strip. Reels 0-2 stay wet (W=12 -> snowball
    # ignites, Corvus + carpet pay, no cold-start bust); reels 3-4 are DRIED (W=4 ->
    # the "hard" reel-3/4 cells rarely light -> Ursa drops, Draco drops MORE, the
    # tiers separate). The per-reel W counts are the ladder knob. NO stars.
    "FR0.csv": {
        "base": {
            "H1": 8, "H2": 10, "H3": 12, "H4": 14,
            "L1": 16, "L2": 18, "L3": 20, "L4": 22, "L5": 24,
            "W": 12, "S": 0,
        },
        # reel 4 dried HARDER than reel 3 (Draco has 3 reel-4 cells to Ursa's 1, and
        # 2 reel-3 cells to Ursa's 1): a bone-dry reel 4 + drier reel 3 pushes Draco
        # into "rarely wakes" territory while Ursa holds near the coin-flip.
        "per_reel": {3: {"W": 3}, 4: {"W": 0}},
    },
    # Wincap helper: wild-rich (~20%) + boosted H1 (the top 5-kind) so the FORCED
    # max-win is reachable; NO stars. Weighted 5:1 alongside FR0 in wincap books.
    "FRWCAP.csv": {
        "H1": 12, "H2": 8, "H3": 6, "H4": 6,
        "L1": 6, "L2": 6, "L3": 6, "L4": 6, "L5": 6,
        "W": 16, "S": 0,
    },
}


def reel_tables(spec):
    """Normalize a spec to a per-reel list of NUM_REELS weight tables."""
    if "base" in spec:
        overrides = spec.get("per_reel", {})
        tables = []
        for reel in range(NUM_REELS):
            w = dict(spec["base"])
            w.update(overrides.get(reel, {}))
            tables.append(w)
        return tables
    return [dict(spec) for _ in range(NUM_REELS)]  # flat: same table every reel


def build_reel(weights, target_len, rng):
    """One shuffled reel from a weight table, padded to target_len with FILLER."""
    strip = []
    for sym, count in weights.items():
        strip.extend([sym] * count)
    strip.extend([FILLER] * (target_len - len(strip)))
    rng.shuffle(strip)
    return strip


def write_strip(filename, spec):
    """Write one rectangular CSV (NUM_REELS columns), each column its own shuffle.
    Reels are padded to the longest column so per-reel drying stays rectangular."""
    rng = random.Random(SEED + hash(filename) % 10_000)
    tables = reel_tables(spec)
    target_len = max(sum(t.values()) for t in tables)
    reels = [build_reel(tables[r], target_len, rng) for r in range(NUM_REELS)]
    path = os.path.join(STARWAKE_REELS, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in range(target_len):
            writer.writerow([reels[r][row] for r in range(NUM_REELS)])
    return target_len, tables


if __name__ == "__main__":
    for filename, spec in STRIP_WEIGHTS.items():
        length, tables = write_strip(filename, spec)
        wilds = [t.get("W", 0) for t in tables]
        wstr = "/".join(map(str, wilds)) if len(set(wilds)) > 1 else str(wilds[0])
        print(f"{filename:12s} len={length:3d}/reel  W={wstr:12s}  S={tables[0].get('S', 0)}")
    print("done.")
