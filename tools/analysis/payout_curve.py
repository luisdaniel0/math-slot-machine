"""Payout curve + variance decomposition for one mode. The competitor-comparison tool.

Two outputs:
  1. CHANCE OF MULTIPLIER OR BETTER -- the same table StakeCruncher shows for any
     published game, so a rival's page can be read straight into a diff against ours.
  2. VARIANCE DECOMPOSITION by payout band -- which part of the distribution actually
     produces the headline standard deviation.

⚠ RUN (2) BEFORE CONCLUDING ANYTHING ABOUT VOLATILITY. Measured Aug 2026, Starwake's
base carried 77.7% of its E[X^2] in the single 25,000x cap outcome: strip it and std dev
fell 25.36 -> 11.96. A rival at a similar headline std dev had only 35% in its cap. Two
games can share a volatility number and have completely different distributions.

    env/bin/python tools/analysis/payout_curve.py <publish_files_dir> <mode>
"""
import json
import math
import os
import sys

STEPS = [0.25, 0.5, 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000]
BANDS = [(0, 1), (1, 10), (10, 100), (100, 500), (500, 2000), (2000, 10000),
         (10000, 26000), (26000, 10 ** 9)]


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    pub, mode = sys.argv[1], sys.argv[2]
    with open(os.path.join(pub, "index.json"), encoding="UTF-8") as f:
        cost = next(float(m["cost"]) for m in json.load(f)["modes"] if m["name"] == mode)

    rows, tw = [], 0
    for line in open(os.path.join(pub, "lookUpTable_%s_0.csv" % mode), encoding="UTF-8"):
        parts = line.split(",")
        if len(parts) < 3:
            continue
        w = int(parts[1])
        rows.append((int(parts[2]) / 100.0, w))
        tw += w

    mean = sum(w * p for p, w in rows) / tw
    m2 = sum(w * p * p for p, w in rows) / tw
    var = m2 - mean * mean
    print("%s  cost %gx   mean %.4f  RTP %.4f  variance %.1f  std %.3f (cost-adj %.2f)\n"
          % (mode, cost, mean, mean / cost, var, math.sqrt(var), math.sqrt(var) / cost))

    print("CHANCE OF MULTIPLIER OR BETTER (per spin)")
    print("  %-12s %11s %16s" % ("multiplier", "chance", "odds"))
    mx = max(p for p, _ in rows)
    for s in STEPS:
        if s > mx:
            break
        n = sum(w for p, w in rows if p >= s)
        if not n:
            continue
        print("  %-12s %10.4f%% %16s" % ("%gx" % s, 100.0 * n / tw,
                                         "1 in " + format(tw / n, ",.1f")))

    print("\nVARIANCE DECOMPOSITION -- contribution to E[X^2] by payout band")
    print("  %-16s %14s %10s %16s" % ("band", "contribution", "share", "odds"))
    for lo, hi in BANDS:
        c = sum(w * p * p for p, w in rows if lo <= p < hi) / tw
        n = sum(w for p, w in rows if lo <= p < hi)
        if not n:
            continue
        print("  %-16s %14.1f %9.1f%% %16s" % (
            "%g-%g" % (lo, hi), c, 100.0 * c / m2,
            "1 in " + format(tw / n, ",.0f")))

    capc = sum(w * p * p for p, w in rows if p >= mx) / tw
    print("\n  THE %s MAX WIN ALONE contributes %.1f of %.1f = %.1f%% of E[X^2]"
          % (format(mx, ",.0f") + "x", capc, m2, 100.0 * capc / m2))
    rest = var - capc
    if rest > 0:
        print("  Strip it and std dev would be %.3f (from %.3f)"
              % (math.sqrt(rest), math.sqrt(var)))


if __name__ == "__main__":
    main()
