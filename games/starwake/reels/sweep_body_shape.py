"""Sweep the OPTIMIZER's shape knobs for buy_ursa and buy_corvus.

    ./env/bin/python games/starwake/reels/sweep_body_shape.py [modes...]

⚠ OPTIMIZER-ONLY. The book pool is never touched -- these knobs change how the
existing books are WEIGHTED, not what they are. So this is ~2.5 min per variant
with no re-sim, and every variant is reversible by editing one dict.

THE PROBLEM. Measured on the converged act two pool:

    mode         cost   nothing-0.25x   0.25-0.5x   median/cost   beat
    buy_corvus    120x       51.30%       30.96%       0.24       16.2%
    buy_ursa      268x       62.02%       12.76%       0.12       21.1%
    buy_draco     520x       44.09%       27.21%       0.27       21.7%

URSA IS THE HARSHEST BUY WHILE BEING THE SECOND CHEAPEST, which inverts the
gentleness ladder -- the showpiece should be the brutal one.

WHY, and it is act two's doing. Act ONE is unchanged, so a feature that never
completes still fills sticky wilds and pays that carpet. Draco has 11 cells to
ursa's 7, so its carpet is far thicker, and draco FAILS to complete 67.6% of the
time -- those books pay ~0.4x the ticket and land in the 0.25-0.5 band, which is
why draco holds 27.21% there. Ursa completes 62.6%, so more of its books go to
the BARE act two board, and the thin 7-cell carpet it does get lands just under
0.25x. Ursa is harsh precisely BECAUSE it succeeds more often.

TWO KNOBS, both in game_optimization.opt_params:
  mean-to-median band   the volatility identity. ursa runs 3-10, against corvus
                        1.5-5 and draco 5-20 -- ursa sits nearer draco's lottery
                        band than a coin-flip tier should.
  consolation scaling   a per-win-range weight hint. ursa already boosts 67-134x
                        and 134-536x (added when a 0.030 cap share hollowed them
                        out). ⚠ SCALING IS A HINT, NOT A CONSTRAINT -- the
                        optimizer biases toward it while solving for RTP, so the
                        delivered shape MUST be measured, never assumed.

⚠ THE OPTIMIZER IS STOCHASTIC. Three identical corvus runs gave beat rates of
15.4 / 22.0 / 16.2%. Do not read a 2-point difference between variants as a
result; look for moves bigger than that spread.
"""
import csv
import os
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


def band(criteria, lo, hi, factor):
    return {"criteria": criteria, "scale_factor": factor,
            "win_range": (lo, hi), "probability": 1.0}


# mode -> variant name -> (m2m band or None, extra scaling bands)
# Win ranges are ABSOLUTE payouts; the comments give them as fractions of cost.
VARIANTS = {
    "buy_ursa": {
        "current": (None, []),
        # Pull ursa off draco's lottery band toward corvus's grind band.
        "tighter m2m": ((2.5, 7), []),
        # Rebuild the shoulder: 0.5-1x cost (134-268) and 1-2x (268-536).
        "more shoulder": (None, [band("ursa", 134, 268, 1.8),
                                 band("ursa", 268, 536, 1.4)]),
        "both": ((2.5, 7), [band("ursa", 134, 268, 1.8),
                            band("ursa", 268, 536, 1.4)]),
    },
    "buy_corvus": {
        "current": (None, []),
        # corvus already runs the tightest band in the game (1.5-5) and has no cap
        # slice, so all its RTP is body -- scaling is nearly the only lever left.
        # 0.25-0.5x cost = 30-60, 0.5-1x = 60-120, 1-2x = 120-240.
        "shoulder": (None, [band("corvus", 30, 60, 1.6),
                            band("corvus", 60, 120, 1.8)]),
        "shoulder+": (None, [band("corvus", 30, 60, 1.4),
                             band("corvus", 60, 120, 2.0),
                             band("corvus", 120, 240, 1.5)]),
    },
}

BANDS = [(0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 1e9)]
LABELS = ["<0.25x", "0.25-.5", "0.5-1x", "1-2x", "2-5x", "5x+"]


def optimize(config, mode):
    og.stage(mode, config)
    og.write_setup(config, mode, threads=16)
    proc = subprocess.run(["cargo", "run", "--release"], cwd=og.OPT_DIR,
                          capture_output=True, text=True,
                          env={**os.environ, "PATH": os.path.expanduser("~/.cargo/bin")
                               + os.pathsep + os.environ.get("PATH", "")})
    if proc.returncode != 0:
        print(proc.stderr[-1500:])
        raise SystemExit(f"optimizer failed for {mode}")


def measure(mode, cost):
    path = os.path.join(og.SHADOW, "publish_files", f"lookUpTable_{mode}_0.csv")
    w = {}
    for r in csv.reader(open(path)):
        if len(r) >= 3:
            p = float(r[2]) / 100.0
            w[p] = w.get(p, 0.0) + float(r[1])
    tot = sum(w.values())
    top = max(w)
    mean = sum(p * v for p, v in w.items()) / tot
    run = med = 0.0
    for p in sorted(w):
        run += w[p]
        if run >= tot / 2:
            med = p
            break
    return {
        "rtp": mean / cost, "med": med, "medpc": med / cost,
        "beat": sum(v for p, v in w.items() if p >= cost) / tot * 100,
        "top": top,
        "rate": sum(v for p, v in w.items() if p >= top * 0.999) / tot,
        "bands": [sum(v for p, v in w.items() if lo * cost <= p < hi * cost) / tot * 100
                  for lo, hi in BANDS],
    }


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(VARIANTS)
    os.chdir(ROOT)
    rows = []

    try:
        for mode in wanted:
            for name, (m2m, extra) in VARIANTS[mode].items():
                # Rebuild from scratch each variant so edits cannot accumulate.
                config = GameConfig()
                OptimizationSetup(config)
                cost = {bm.get_name(): bm.get_cost() for bm in config.bet_modes}[mode]
                params = config.opt_params[mode]
                if m2m:
                    params["parameters"]["min_mean_to_median"] = m2m[0]
                    params["parameters"]["max_mean_to_median"] = m2m[1]
                if extra:
                    # ConstructScaling().return_dict() returns the LIST of bands, not
                    # a dict wrapping one.
                    params["scaling"] = list(params["scaling"]) + extra

                start = time.time()
                optimize(config, mode)
                r = measure(mode, cost)
                r.update(mode=mode, variant=name, cost=cost, secs=time.time() - start)
                rows.append(r)
                print(f"  done {mode}/{name} in {r['secs']:.0f}s", flush=True)
    finally:
        # ⚠ RESTORE, because a variant's LUT is written into the shadow game and
        # STAYS there. The first version of this script had no rollback and left
        # buy_ursa sitting on its WORST variant (63.5% of buys under 0.25x cost),
        # which the next audit would have read as the shipped shape.
        print("\nrestoring each swept mode to the committed config...", flush=True)
        for mode in wanted:
            config = GameConfig()
            OptimizationSetup(config)
            optimize(config, mode)
            print(f"  restored {mode}", flush=True)

    print("\n" + "=" * 108)
    print("BODY-SHAPE SWEEP  (optimizer-only; the book pool is untouched)")
    print("=" * 108)
    print(f"{'mode':12s}{'variant':15s}{'RTP':>8s}{'median':>9s}{'med/c':>7s}"
          f"{'beat':>7s}" + "".join(l.rjust(9) for l in LABELS) + f"{'max win 1 in':>15s}")
    print("-" * 108)
    last = None
    for r in rows:
        if last and last != r["mode"]:
            print("-" * 108)
        last = r["mode"]
        print(f"{r['mode']:12s}{r['variant']:15s}{r['rtp']:>8.4f}{r['med']:>8,.0f}x"
              f"{r['medpc']:>7.2f}{r['beat']:>6.1f}%"
              + "".join(f"{b:>8.2f}%" for b in r["bands"])
              + f"{1/r['rate']:>15,.0f}")
    print("-" * 108)
    print("\n  TARGET: pull mass out of <0.25x and into 0.25-1x. Draco's 44.09% /")
    print("  27.21% is the shape to beat; ursa currently runs 62.02% / 12.76%.")
    print("  RTP must stay 0.9665 -- a variant that moves the shape by missing RTP")
    print("  has not done anything. Ignore beat-rate moves under ~3 points.")
