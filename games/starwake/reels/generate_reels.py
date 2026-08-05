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
import zlib

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
    # Freegame: THE completion-ladder strip. Reels 0-2 wet enough that the snowball
    # ignites (Corvus stays a reliable beast hunt, no cold-start bust); reels 3-4
    # DRIED so the "hard" reel-3/4 cells rarely light -> Ursa drops, Draco drops
    # MORE, the tiers separate. The per-reel W counts are the ladder knob. NO stars.
    #
    # Measured sweep at n=40k/mode (sweep_fr0.py), buy-mode cost = mean/rtp:
    #   W=12/3/0  completion 96.4/54.5/28.7%   cost   460/661/2030x
    #   W= 4/3/0  completion 83.6/33.0/11.9%   cost   333/381/ 832x
    #   W= 2/1/0  completion 78.2/23.9/ 7.5%   cost   299/276/ 539x
    # Drying moves the COMPLETION RATE, not the payout per completion (draco's
    # beast phase held 6,451 -> 6,074 -> 5,945x across all three). So it is the
    # right lever for Draco's "rarely completes" identity and the wrong one for
    # Corvus's price. 4/3/0 is the interim hold: Corvus still reads as reliable,
    # Draco's carpet thins to 95x, and Draco's remaining gap is cell-shape work.
    "FR0.csv": {
        "base": {
            "H1": 8, "H2": 10, "H3": 12, "H4": 14,
            "L1": 16, "L2": 18, "L3": 20, "L4": 22, "L5": 24,
            "W": 4, "S": 0,
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
    # ACT TWO roam strip -- the ONLY strip carrying the multiplier star "M".
    #
    # Drawn while the beast is awake and nowhere else. Act one keeps FR0, so a star
    # can never land in the charge phase where there is no beast to collect it and
    # a visibly inert symbol would be worse than either design.
    #
    # ⚠ M IS NON-PAYING, SO IT BREAKS A PAYLINE THE WAY A SCATTER DOES, AND THE COST
    # DEPENDS ENTIRELY ON THE REEL. On a left-to-right lines game a blocker on reel 0
    # kills every win through that row outright; one on reel 4 only shortens a 5-kind
    # to a 4-kind. So density is weighted to the RIGHT: reel 0 stays clean, and the
    # count climbs across the board. That also matches where act two's wins come from
    # -- with the wild carpet gone, 5-kinds are rare and the left reels are carrying
    # the 3-kinds that pay the body.
    #
    # ⚠ DENSITY AND VALUE TRADE AGAINST EACH OTHER AND THERE IS AN INTERIOR OPTIMUM.
    # More stars = more multiplier but fewer paying cells to multiply, so pushing
    # density past some point makes act two pay LESS. Density lives here; the value
    # table lives in game_config.constellation_star_values. Sweep them together.
    # FIRST-PASS NUMBERS, UNMEASURED -- this is the thing the next sweep is for.
    #
    # No wilds: the block is the only wild in act two, by design. No stars ("S"):
    # the feature cannot retrigger.
    "FRROAM.csv": {
        "base": {
            "H1": 8, "H2": 10, "H3": 12, "H4": 14,
            "L1": 16, "L2": 18, "L3": 20, "L4": 22, "L5": 24,
            "W": 0, "S": 0, "M": 0,
        },
        "per_reel": {1: {"M": 3}, 2: {"M": 6}, 3: {"M": 9}, 4: {"M": 12}},
    },
    # ACT TWO wincap helper -- the roam-phase twin of FRWCAP, mixed in at 5:1 on
    # forced-wincap slices only.
    #
    # WHY IT EXISTS. A forced wincap slice redraws until it finds a book paying the
    # mode's ceiling, with no retry cap, so a ceiling out of structural reach HANGS
    # rather than failing. Act two's payout is (symbol win) x (collected multiplier)
    # and BOTH halves are thin on the ordinary roam strip: measured max win was
    # 6,705x against a published 25,000x. So this strip fattens both halves at once
    # -- star density roughly 4x ROAM's so the multiplier actually accumulates, and
    # premium-heavy paying symbols so there is something worth multiplying.
    #
    # ⚠ IT IS NOT SIMPLY "MORE STARS". Past some density the board runs out of
    # paying cells and act two pays LESS -- stars are non-paying and break paylines.
    # That is why the premiums are boosted alongside: the two must move together.
    # Reel 0 stays star-free so the leftmost reel can always start a win.
    "FRROAMCAP.csv": {
        "base": {
            "H1": 20, "H2": 14, "H3": 10, "H4": 8,
            "L1": 6, "L2": 6, "L3": 6, "L4": 6, "L5": 6,
            "W": 0, "S": 0, "M": 0,
        },
        "per_reel": {1: {"M": 12}, 2: {"M": 24}, 3: {"M": 36}, 4: {"M": 48}},
    },
    # DRACO ASCENDANT trigger strip -- the ONLY strip that can show 6 stars.
    #
    # WHY IT EXISTS. _force_special_board (src/calculations/board.py) places at most
    # ONE scatter per reel: it picks a reel, sets a stop on a scatter, then zeroes
    # that reel's probability. On five reels it can therefore only ever place five.
    # A 6-scatter board happens only when one reel's 4-row window happens to reveal
    # a SECOND scatter -- and force_special_board is a bare `while True` with no
    # retry cap, so if no reel can ever show two, forcing 6 HANGS FOREVER.
    # BR0 can currently do it by accident (one pair 3 apart on reel 2, ~20% of
    # forced attempts, ~5 retries). Relying on that would be a silent time bomb:
    # BR0 is the base-game tuning surface, and any weight edit reshuffles it and
    # could delete that pair, turning buy_mystery's ascendant slice into a hang
    # with no error and no obvious cause. So Ascendant gets its own strip.
    #
    # HOW IT FORCES 6 DETERMINISTICALLY. Reel 2's scatters are laid down as one
    # evenly-STEP-3 run: a stop on any of them puts the next one at stop+3, still
    # inside the 4-row window, so reel 2 shows exactly TWO. Every other reel uses
    # gap>=4, so each shows exactly ONE. 1+1+2+1+1 = 6 on the first attempt. Only
    # the last scatter of the run has no partner ahead of it, so the success rate
    # is (k-1)/k -- k=12 gives ~92%, i.e. ~1.1 attempts instead of ~5.
    # NOTE this is the one place the SDK docstring's "ensure the reels do not have
    # stacked scatter symbols" is deliberately violated, because a controlled
    # double is the only way to reach 6 on a 5-reel board.
    #
    # Weights are otherwise BR0's, so the trigger board reads as a normal base
    # spin -- the tell is the sixth star, not a different-looking board.
    "ASC.csv": {
        "base": {
            "H1": 8, "H2": 10, "H3": 12, "H4": 14,
            "L1": 18, "L2": 20, "L3": 22, "L4": 24, "L5": 26,
            "W": 2, "S": 5,
        },
        "per_reel": {2: {"S": 12}},
        "scatter_layout": {"gap": 4, "run": {2: 3}},
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


def _positions_min_gap(n, k, gap, rng):
    """k positions on a circle of length n, every circular gap >= `gap`.

    Uniform over valid configurations: the k gaps must sum to n and each is at
    least `gap`, so distribute the slack (n - k*gap) randomly across them.
    """
    slack = n - k * gap
    if slack < 0:
        raise ValueError(f"cannot place {k} scatters {gap} apart on a strip of {n}")
    cuts = sorted(rng.randrange(slack + 1) for _ in range(k - 1))
    parts = [b - a for a, b in zip([0] + cuts, cuts + [slack])]
    pos, cur = [], rng.randrange(n)
    for p in parts:
        pos.append(cur % n)
        cur += gap + p
    return pos


def _positions_run(n, k, step, rng):
    """k positions in ONE evenly-stepped run from a random offset."""
    if k * step > n:
        raise ValueError(f"a {k}-scatter run at step {step} does not fit in {n}")
    start = rng.randrange(n)
    return [(start + i * step) % n for i in range(k)]


def build_reel(weights, target_len, rng, scatter_layout=None, reel=None):
    """One shuffled reel from a weight table, padded to target_len with FILLER.

    With no `scatter_layout` the scatters are shuffled in with everything else
    (the original behaviour -- BR0/FR0/FRWCAP must stay bit-identical, so this
    path makes exactly the same rng calls it always did). A layout instead places
    scatters at controlled positions and shuffles only the remaining symbols
    around them; see STRIP_WEIGHTS["ASC.csv"] for why that control is needed.
    """
    if scatter_layout is None:
        strip = []
        for sym, count in weights.items():
            strip.extend([sym] * count)
        strip.extend([FILLER] * (target_len - len(strip)))
        rng.shuffle(strip)
        return strip

    n_s = weights.get("S", 0)
    body = []
    for sym, count in weights.items():
        if sym != "S":
            body.extend([sym] * count)
    body.extend([FILLER] * (target_len - len(body) - n_s))
    rng.shuffle(body)

    run_steps = scatter_layout.get("run", {})
    if reel in run_steps:
        pos = _positions_run(target_len, n_s, run_steps[reel], rng)
    else:
        pos = _positions_min_gap(target_len, n_s, scatter_layout["gap"], rng)
    pos = set(pos)
    filler = iter(body)
    return ["S" if i in pos else next(filler) for i in range(target_len)]


def write_strip(filename, spec):
    """Write one rectangular CSV (NUM_REELS columns), each column its own shuffle.
    Reels are padded to the longest column so per-reel drying stays rectangular."""
    # crc32, NOT hash(): Python randomises str hashing per process, so seeding off
    # hash(filename) reshuffled EVERY strip on every regeneration. That makes the
    # measure loop unattributable -- edit an FR0 weight and BR0/FRWCAP silently
    # change too, so the base game moves underneath whatever you were measuring.
    # crc32 is stable across processes, so a strip only changes when its own
    # weights change.
    rng = random.Random(SEED + zlib.crc32(filename.encode()) % 10_000)
    tables = reel_tables(spec)
    layout = spec.get("scatter_layout")
    target_len = max(sum(t.values()) for t in tables)
    reels = [build_reel(tables[r], target_len, rng, layout, r) for r in range(NUM_REELS)]
    path = os.path.join(STARWAKE_REELS, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in range(target_len):
            writer.writerow([reels[r][row] for r in range(NUM_REELS)])
    return target_len, tables


if __name__ == "__main__":
    for filename, spec in STRIP_WEIGHTS.items():
        length, tables = write_strip(filename, spec)
        def per_reel(sym):
            v = [t.get(sym, 0) for t in tables]
            return "/".join(map(str, v)) if len(set(v)) > 1 else str(v[0])

        print(f"{filename:12s} len={length:3d}/reel  "
              f"W={per_reel('W'):12s}  S={per_reel('S')}")
    print("done.")
