"""Compare the Go engine's output against Python's measured figures.

THIS IS THE SAFETY NET. The RGS format checks verify shape and statistics, not
whether the game is the one that was designed -- a mis-ported rule produces books
that are perfectly well-formed, pass every check, and quietly encode a different
game. Every serious bug on this project has been silent and was caught by reading
distributions, so that is what this does.

The bar is STATISTICAL parity, not bit-exact: Stake receives books and weights,
never the generator (docs/rgs_docs/data_format.md), so reproducing CPython's
Mersenne Twister would buy nothing.

Reference figures are MEASURED FROM PYTHON'S OWN SHIPPED POOL (1e6/mode), not
transcribed from CLAUDE.md. That matters: CLAUDE.md's 100k confirmation table
predates the Jul 30 2026 ladder re-sweep (ursa 14 -> 13 rungs, draco 14 -> 12),
so its `>cost` figures for those two tiers are stale by ~1.5-2 percentage points
-- and corvus, whose 9-rung ladder did not change, still matches it exactly. That
mismatch looked like a Go bug until the same harness was pointed at Python's pool
and reproduced it. Re-measure with:

    env/bin/python go/parity.py games/starwake/library/publish_files

Both pools STRIP the forced wincap slice -- it is a sampling quota, not a
probability, so leaving it in inflates every mean.

    env/bin/python go/parity.py go/out/library/publish_files
"""
import io
import json
import statistics
import sys
from pathlib import Path

import zstandard as zstd

# mode -> (tier, cost, completion %, mean, median, >cost %, mean roam)
#
# Measured off the shipped Python pool (1e6/mode, wincap slice stripped) on
# Aug 3 2026. Re-measure and paste back in whenever the Python engine's config
# changes, so the harness always compares against what Python ACTUALLY produces.
REFERENCE = {
    "buy_corvus": ("corvus", 240.0, 83.71, 232.81, 94.95, 25.09, 4.90),
    "buy_ursa": ("ursa", 268.0, 62.60, 263.84, 131.90, 20.23, 4.98),
    "buy_draco": ("draco", 520.0, 32.06, 498.40, 282.80, 18.61, 4.03),
}


def books(path):
    with open(path, "rb") as f:
        r = zstd.ZstdDecompressor(max_window_size=2**31).stream_reader(f)
        for line in io.TextIOWrapper(r, encoding="utf-8"):
            yield json.loads(line)


def analyse(path, cost):
    """Walk one mode's books, stripping the forced wincap slice."""
    payouts = []
    completed = 0
    roams = []
    top_rung = {}
    zero = 0

    for b in books(path):
        # The wincap slice is a GENERATION QUOTA, not a probability. Including it
        # adds a fixed lump of 25,000x books and prices the mode off a pool the
        # optimizer is about to re-weight anyway.
        if b.get("criteria") == "wincap":
            continue

        payout = b["payoutMultiplier"] / 100.0
        payouts.append(payout)
        if payout == 0:
            zero += 1

        woke = False
        roam = 0
        best_mult = 0
        for e in b["events"]:
            t = e["type"]
            if t == "beastWake":
                woke = True
            elif t == "beastRoam":
                roam += 1
                best_mult = max(best_mult, e.get("multiplier", 0))
        if woke:
            completed += 1
            roams.append(roam)
        if best_mult:
            top_rung[best_mult] = top_rung.get(best_mult, 0) + 1

    n = len(payouts)
    return {
        "books": n,
        "completion": 100.0 * completed / n if n else 0,
        "mean": statistics.fmean(payouts) if payouts else 0,
        "median": statistics.median(payouts) if payouts else 0,
        "over_cost": 100.0 * sum(1 for p in payouts if p > cost) / n if n else 0,
        "mean_roam": statistics.fmean(roams) if roams else 0,
        "max": max(payouts) if payouts else 0,
        "zero": 100.0 * zero / n if n else 0,
        "top_rung": max(top_rung) if top_rung else 0,
    }


def band(label, got, want, tol_pct, unit=""):
    """Report one metric against its expected value."""
    if want == 0:
        return f"    {label:14s} {got:10.2f}{unit}"
    delta = 100.0 * (got - want) / want
    mark = "OK " if abs(delta) <= tol_pct else "!! "
    return (f"  {mark}{label:14s} {got:10.2f}{unit}   want {want:8.2f}{unit}"
            f"   {delta:+6.2f}%")


def main():
    root = Path(sys.argv[1])
    failures = 0

    for mode, (tier, cost, exp_comp, exp_mean, exp_med, exp_over, exp_roam) in REFERENCE.items():
        path = root / f"books_{mode}.jsonl.zst"
        if not path.exists():
            print(f"{mode}: MISSING {path}")
            failures += 1
            continue

        r = analyse(path, cost)
        print(f"\n{mode}  ({tier}, cost {cost:.0f}x, {r['books']:,} books, wincap slice stripped)")
        # Tolerances: completion and mean are structural and should be tight.
        # Median and >cost are distribution-shape checks and noisier at this
        # sample size; mean roam is tight because the roam-depth distribution is
        # invariant (CLAUDE.md: it reproduced exactly across every ladder sweep).
        print(band("completion %", r["completion"], exp_comp, 3.0))
        print(band("mean", r["mean"], exp_mean, 5.0, "x"))
        print(band("median", r["median"], exp_med, 12.0, "x"))
        print(band("> cost %", r["over_cost"], exp_over, 8.0))
        print(band("mean roam", r["mean_roam"], exp_roam, 5.0))
        print(f"    {'zero pay %':14s} {r['zero']:10.2f}      want 0.00")
        print(f"    {'max win':14s} {r['max']:10.2f}x")
        print(f"    {'top rung hit':14s} {r['top_rung']:10.0f}x")

        for label, got, want, tol in (
            ("completion", r["completion"], exp_comp, 3.0),
            ("mean", r["mean"], exp_mean, 5.0),
            ("mean roam", r["mean_roam"], exp_roam, 5.0),
        ):
            if abs(100.0 * (got - want) / want) > tol:
                failures += 1
        if r["zero"] != 0:
            failures += 1

    print()
    if failures:
        print(f"PARITY: {failures} metric(s) outside tolerance")
        return 1
    print("PARITY: all checked metrics within tolerance of the Python reference")
    return 0


if __name__ == "__main__":
    sys.exit(main())
