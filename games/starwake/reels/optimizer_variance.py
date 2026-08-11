"""How much does the optimizer move between IDENTICAL runs?

    ./env/bin/python games/starwake/reels/optimizer_variance.py [runs] [modes...]

⚠ THIS IS THE MOST IMPORTANT MEASUREMENT IN THE TUNING LOOP AND IT WAS MISSED FOR
A LONG TIME. The Rust optimizer is stochastic: same books, same config, different
lookup table. Three separate findings turned out to be nothing but this noise --

  buy_corvus beat rate      15.4 / 22.0 / 16.2%   across identical runs
  buy_corvus max win        1 in 3.4M / 3.8M / 7.3M
  buy_ursa distribution     62.02% vs 47.41% of buys under 0.25x cost, and a
                            median of 0.12x vs 0.27x -- a whole "ursa is the
                            harshest buy in the game" diagnosis that did not
                            replicate

Any config change smaller than this spread is unmeasurable, and any single-run
number quoted as a property of the GAME rather than of ONE POOL is a guess.

TWO THINGS THIS DECIDES:
  1. the noise floor -- how big a change has to be before it means anything
  2. whether shipping needs best-of-N runs, because the pool that ships is ONE
     draw. buy_corvus is the sharp case: its max-win rate has no wincap slice to
     pin it, so a bad draw can land outside the 1-in-10,000,000 gate with nothing
     in the config to blame.

Leaves each mode re-optimized on the committed config, so it is safe to run
against the live pool.
"""
import csv
import os
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(GAME))
sys.path.insert(0, GAME)
sys.path.insert(0, os.path.join(ROOT, "go"))

import optimize_go as og  # noqa: E402
from game_config import GameConfig  # noqa: E402
from game_optimization import OptimizationSetup  # noqa: E402


def once(mode):
    config = GameConfig()
    OptimizationSetup(config)
    cost = {bm.get_name(): bm.get_cost() for bm in config.bet_modes}[mode]
    og.stage(mode, config)
    og.write_setup(config, mode, threads=16)
    proc = subprocess.run(["cargo", "run", "--release"], cwd=og.OPT_DIR,
                          capture_output=True, text=True,
                          env={**os.environ, "PATH": os.path.expanduser("~/.cargo/bin")
                               + os.pathsep + os.environ.get("PATH", "")})
    if proc.returncode != 0:
        raise SystemExit(f"optimizer failed for {mode}:\n{proc.stderr[-1500:]}")

    w = {}
    path = os.path.join(og.SHADOW, "publish_files", f"lookUpTable_{mode}_0.csv")
    for r in csv.reader(open(path)):
        if len(r) >= 3:
            p = float(r[2]) / 100.0
            w[p] = w.get(p, 0.0) + float(r[1])
    tot = sum(w.values())
    top = max(w)
    run = med = 0.0
    for p in sorted(w):
        run += w[p]
        if run >= tot / 2:
            med = p
            break
    return {
        "cost": cost,
        "rtp": sum(p * v for p, v in w.items()) / tot / cost,
        "medpc": med / cost,
        "beat": sum(v for p, v in w.items() if p >= cost) / tot * 100,
        "low": sum(v for p, v in w.items() if p < 0.25 * cost) / tot * 100,
        "maxwin": tot / sum(v for p, v in w.items() if p >= top * 0.999),
    }


def spread(name, vals, fmt="{:.2f}"):
    lo, hi = min(vals), max(vals)
    mean = statistics.fmean(vals)
    rng = (hi - lo) / mean * 100 if mean else 0
    return (f"  {name:14s}" + "".join(fmt.format(v).rjust(12) for v in vals)
            + f"{fmt.format(mean).rjust(12)}{rng:>9.1f}%")


if __name__ == "__main__":
    args = sys.argv[1:]
    runs = int(args[0]) if args and args[0].isdigit() else 4
    modes = [a for a in args if not a.isdigit()] or ["buy_ursa", "buy_corvus"]
    os.chdir(ROOT)

    for mode in modes:
        print(f"\n=== {mode}: {runs} identical optimizer runs ===", flush=True)
        results = []
        for i in range(runs):
            start = time.time()
            results.append(once(mode))
            print(f"  run {i + 1} done in {time.time() - start:.0f}s", flush=True)

        hdr = "".join(f"run {i + 1}".rjust(12) for i in range(runs))
        print(f"\n  {'metric':14s}{hdr}{'mean'.rjust(12)}{'spread'.rjust(9)}")
        print("  " + "-" * (14 + 12 * runs + 21))
        print(spread("RTP", [r["rtp"] for r in results], "{:.4f}"))
        print(spread("median/cost", [r["medpc"] for r in results]))
        print(spread("beat %", [r["beat"] for r in results], "{:.1f}"))
        print(spread("< 0.25x cost", [r["low"] for r in results], "{:.1f}"))
        print(spread("max win 1 in", [r["maxwin"] for r in results], "{:,.0f}"))

    print("\nreading it:")
    print("  spread = (max - min) / mean. THIS IS THE NOISE FLOOR -- a config change")
    print("  that moves a metric by less than this has not been shown to do anything.")
    print("  RTP should be near-zero spread; it is the one thing the optimizer solves")
    print("  for exactly. Everything else is a by-product it is free to vary.")
    print("  If max-win spread is wide on buy_corvus, shipping needs best-of-N runs:")
    print("  it has no wincap slice, so a bad draw cannot be fixed in config.")
