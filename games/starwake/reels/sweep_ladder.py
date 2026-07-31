"""Ladder sweep: find the per-tier (start, top, curve) that hits the target economy.

    ./env/bin/python games/starwake/reels/sweep_ladder.py <tier> [nsims] [s:t:c ...]

    e.g.  sweep_ladder.py corvus            # the built-in grid for that tier
          sweep_ladder.py draco 20000 2:300:1.2 2:400:1.3

THE LADDER IS THREE NUMBERS, NOT FOURTEEN:

    ladder[i] = start * (top/start) ** ((i / (n-1)) ** curve)

  start  prices the COMMON case -- most completions are late and only ever see the
         bottom rungs, so this sets where the cheapest completion lands (the floor
         of the Draco cliff).
  top    prices the RARE case -- only an early completion reaches it, so this is
         the ceiling, and the ONLY thing that can put 25,000x back in reach.
  curve  decouples the two. curve=1 is the plain geometric ladder we shipped.
         curve>1 is CONVEX: the ladder stays low through the middle rungs and then
         explodes at the end.

CURVE IS WHY THIS SWEEP EXISTS. Corvus completes 94% of the time with a mean roam
of 8.81 of a possible 14, so its typical buy sits two-thirds of the way up the
ladder in log space -- with a geometric curve its body and its ceiling are welded
together, and every attempt to give it a dream doubles its price instead. A convex
curve lets the body fall (price 406 -> 200x) while the top rises (ceiling 1,776x ->
a real number). Ursa and Draco complete later (mean roam 5.02 / 4.05), so they sit
low on the ladder already and need much less curve.

TARGETS (CLAUDE.md "SWEEP JOBS"):
  corvus  price 200x   ceiling as high as continuity allows   (order: < ursa!)
  ursa    price 300x   ceiling ~25,000x
  draco   price 500x   ceiling past 25,000x with measurable at-cap frequency
ALL THREE:  widest hole <= ~2x (no win-range gap), zero-pay 0.00%, and the price
order MUST come out corvus < ursa < draco -- today it is inverted (406 > 278).

⚠ OVERWRITES THE PRODUCTION POOL for the tier it runs. Back library/ up first
(there is a copy at library_phaseB_backup/). The forced wincap slice is stripped:
a ladder whose top leaves 25,000x out of reach would make it loop forever.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(GAME))
sys.path.insert(0, ROOT)
sys.path.insert(0, GAME)
sys.path.insert(0, HERE)

from measure_tiers import read_books, summarise, RTP, CAP  # noqa: E402

# (start, top, curve) candidates per tier -- first pass, aimed at the baseline gaps.
# corvus must HALVE its price, so it needs the most curve; draco only shaves 17%.
GRIDS = {
    "corvus": [(1, 15, 1.0), (1, 200, 2.5), (1, 200, 3.5), (1, 400, 3.5),
               (1, 400, 4.5), (1, 800, 4.5), (1, 800, 5.5)],
    "ursa": [(1, 38, 1.0), (1, 120, 1.2), (1, 180, 1.5), (1, 300, 1.7),
             (1, 300, 2.0), (1, 500, 2.0)],
    "draco": [(2, 165, 1.0), (2, 250, 1.1), (2, 300, 1.2), (2, 400, 1.3),
              (2, 400, 1.5), (2, 600, 1.5)],
}
TARGET_PRICE = {"corvus": 200, "ursa": 300, "draco": 500}


def make_ladder(start, top, curve, n):
    """Convex-geometric ladder, integer rungs, guaranteed non-decreasing."""
    out = []
    for i in range(n):
        frac = (i / (n - 1)) ** curve
        out.append(max(1, int(round(start * (top / start) ** frac))))
    for i in range(1, n):
        out[i] = max(out[i], out[i - 1])
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in GRIDS:
        sys.exit(f"usage: sweep_ladder.py <{'|'.join(GRIDS)}> [nsims] [start:top:curve ...]")
    tier = args.pop(0)
    # --spins N overrides feature length for this run. The ladder's rung count
    # follows it automatically. Needed because a tier's price has a FLOOR set by the
    # raw unmultiplied feature (a completed board pays on its own), and roam length
    # is what sets that floor -- no ladder can push a price below it.
    spins = None
    if "--spins" in args:
        i = args.index("--spins")
        spins = int(args[i + 1])
        del args[i:i + 2]
    # --rungs N shortens the LADDER without touching feature length, which --spins
    # cannot do (it moves both). Needed because the rung count was originally tied to
    # num_feature_spins-1 = the THEORETICALLY longest roam, and that is not the
    # ACHIEVABLE longest roam: the top rung needs a completion on spin 1, i.e. lighting
    # a whole constellation in a single spin. Corvus (4 cells) does that 1 in 466
    # features; draco (11 cells) never does it organically, so its top two rungs only
    # ever appeared inside forced wincap books. Sizing the ladder to the depth a tier
    # actually reaches is what makes every published rung obtainable.
    rung_override = None
    if "--rungs" in args:
        i = args.index("--rungs")
        rung_override = int(args[i + 1])
        del args[i:i + 2]
    # --target N prices the sweep against a chosen number rather than the module's
    # original design targets, so a re-sweep can HOLD the shipped menu (240/268/520).
    target_override = None
    if "--target" in args:
        i = args.index("--target")
        target_override = float(args[i + 1])
        del args[i:i + 2]
    nsims = int(args.pop(0)) if args and args[0].isdigit() else 20000
    combos = [tuple(float(x) for x in a.split(":")) for a in args] or GRIDS[tier]

    os.chdir(GAME)
    from gamestate import GameState
    from game_config import GameConfig
    from src.state.run_sims import create_books

    config = GameConfig()
    if spins is not None:
        # Feature length is PER TIER, so --spins overrides ONLY the tier being swept
        # (that is the point of the split: corvus 10 while ursa/draco stay at 15).
        # freespin_triggers is keyed by scatter COUNT, so map back through scatter_tiers.
        count = {t: c for c, t in config.scatter_tiers.items()}[tier]
        config.num_feature_spins[tier] = spins
        for game_type in config.freespin_triggers:
            config.freespin_triggers[game_type][count] = spins
    for bm in config.bet_modes:
        kept = [d for d in bm.get_distributions() if d.get_criteria() != "wincap"]
        if len(kept) != len(bm.get_distributions()):
            for d in kept:
                d._quota = 1.0 / len(kept)
            bm._distributions = kept
        bm._wincap = config.wincap  # measure every variant under the one design cap
    gamestate = GameState(config)

    rungs = rung_override if rung_override is not None else config.num_feature_spins[tier] - 1
    mode = f"buy_{tier}"
    target = target_override if target_override is not None else TARGET_PRICE[tier]
    longest = config.num_feature_spins[tier] - 1
    note = "" if rungs == longest else f"  (longest possible roam {longest}; top rung clamps)"
    print(f"{tier}: {len(combos)} ladders x n={nsims:,}   {rungs} rungs{note}   "
          f"target price {target:g}x, cap {CAP:,.0f}x")

    rows = []
    for start, top, curve in combos:
        ladder = make_ladder(start, top, curve, rungs)
        config.constellation_mult_ladders[tier] = ladder
        os.makedirs(gamestate.output_files.temp_path, exist_ok=True)
        create_books(gamestate, config, {mode: nsims}, 1000, 14, True, False)
        r = summarise(tier, *read_books(mode))
        r["params"] = (start, top, curve)
        r["ladder"] = ladder
        rows.append(r)

    print("\n" + "=" * 108)
    print(f"LADDER SWEEP -- {tier}   (forced wincap slice stripped)")
    print("=" * 108)
    print(f"{'start:top:curve':>16s}{'price':>9s}{'vs target':>11s}{'median':>9s}"
          f"{'max':>10s}{'at cap':>9s}{'max/cost':>10s}{'>cost':>8s}{'hole':>8s}{'complete':>10s}")
    for r in rows:
        s, t, c = r["params"]
        print(f"{f'{s:g}:{t:g}:{c:g}':>16s}{r['cost']:>8,.0f}x{r['cost']/target:>10.2f}x"
              f"{r['median']:>8,.0f}x{r['mx']:>9,.0f}x{r['at_cap']:>8.3f}%"
              f"{r['mx']/r['cost']:>9,.0f}x{r['over']:>7.1f}%{r['hole'][2]:>7.2f}x"
              f"{r['completion']:>9.1f}%")
    print("\nladders:")
    for r in rows:
        s, t, c = r["params"]
        print(f"  {f'{s:g}:{t:g}:{c:g}':>16s}  {r['ladder']}")
    print(f"\nwant: price ~{target}x, hole <= 2x, max/cost 50-100x, "
          f"and at cap > 0 for draco (a forced wincap slice must be findable)")
