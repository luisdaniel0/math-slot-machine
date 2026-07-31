"""Reproduce Stake's platform risk checks against the optimized LUTs.

Mirrors utils/analysis/distribution_functions.py at origin/main (post PR #109
cvar-norm + #110 prob-scale), which in turn mirrors the Go code the RGS team
shared: CVaR cutoff 0.999 (top 0.1%), CVaR normalized by bet cost, p5k/p10k
scaled down by a leniency factor for high-cost modes.
"""

import csv
import os
import sys

GAME_DIR = "games/starwake/library/publish_files"

# cost per mode (from the converged config)
COSTS = {
    "base": 1.0,
    "ante_starfall": 1.5,
    "buy_corvus": 240.0,
    "buy_ursa": 268.0,
    "buy_draco": 520.0,
    "buy_mystery": 563.0,
}

# 2-star rated limits (stake-engine.com/docs/approval-guidelines/math-verification)
LIMITS = {
    "p5k": 1e-2,
    "p10k": 8e-2,
    "etl40": 0.8,
    "etl10k": 0.6,
    "cvar": 700.0,
    "std_max": 50.0,
}


def get_prob_scale(bet_cost: float) -> float:
    if bet_cost >= 1000:
        return 0.2
    if bet_cost >= 500:
        return 0.5
    if bet_cost >= 200:
        return 0.8
    return 1.0


def conditional_value_at_risk(cutoff: float, dist: dict, total_weight: float) -> float:
    ordered = sorted(dist.items(), key=lambda x: x[0])
    cumulative_prob = 0.0
    tail_start = ordered[0][0] if ordered else 0.0
    for payout, weight in ordered:
        cumulative_prob += weight / total_weight
        if cumulative_prob >= cutoff:
            tail_start = payout
            break
    tail_prob = 0.0
    tail_value = 0.0
    for payout, weight in ordered:
        if payout >= tail_start:
            prob = weight / total_weight
            tail_prob += prob
            tail_value += prob * payout
    if tail_prob == 0.0:
        return 0.0
    return tail_value / tail_prob


def load_dist(path: str) -> dict:
    """LUT format: id, weight, payout*100 -> {payout: summed weight}"""
    dist = {}
    with open(path, newline="") as fh:
        for row in csv.reader(fh):
            if len(row) < 3:
                continue
            weight = float(row[1])
            payout = float(row[2]) / 100.0
            dist[payout] = dist.get(payout, 0.0) + weight
    return dist


def analyse(mode: str, cost: float):
    path = os.path.join(GAME_DIR, f"lookUpTable_{mode}_0.csv")
    if not os.path.exists(path):
        return None
    dist = load_dist(path)
    total_weight = sum(dist.values())

    p5k = p10k = etl40 = etl10k = 0.0
    expected = 0.0
    sq = 0.0
    for win, weight in dist.items():
        prob = weight / total_weight
        expected += win * prob
        sq += (win**2) * prob
        if win >= 10000:
            p10k += prob
            etl10k += win * prob
        if win >= 5000:
            p5k += prob
        if win >= 40 * cost:
            etl40 += win * prob

    scale = get_prob_scale(cost)
    cvar = conditional_value_at_risk(0.999, dist, total_weight) / cost
    std = ((sq - expected**2) ** 0.5) / cost  # cost-normalised, as published

    return {
        "rtp": expected / cost,
        "std": std,
        "p5k": p5k * scale,
        "p10k": p10k * scale,
        "p5k_raw": p5k,
        "p10k_raw": p10k,
        "scale": scale,
        "etl40": etl40 / expected if expected else 0.0,
        "etl10k": etl10k / expected if expected else 0.0,
        "cvar": cvar,
    }


def flag(value, limit, lower_is_better=True):
    if lower_is_better:
        return "OK " if value <= limit else "FAIL"
    return "OK " if value >= limit else "FAIL"


def main():
    print(f"{'mode':<14}{'cost':>7}{'rtp':>8}{'std':>8}{'p5k':>11}{'p10k':>11}"
          f"{'ETL40':>8}{'ETL10k':>8}{'CVaR':>9}")
    print("-" * 84)
    worst = {"p5k": 0.0, "p10k": 0.0, "etl40": 0.0, "etl10k": 0.0, "cvar": 0.0}
    for mode, cost in COSTS.items():
        r = analyse(mode, cost)
        if r is None:
            print(f"{mode:<14}  (LUT not found)")
            continue
        print(f"{mode:<14}{cost:>7.1f}{r['rtp']:>8.4f}{r['std']:>8.2f}"
              f"{r['p5k']:>11.2e}{r['p10k']:>11.2e}"
              f"{r['etl40']:>8.3f}{r['etl10k']:>8.3f}{r['cvar']:>9.1f}")
        for k in worst:
            worst[k] = max(worst[k], r[k])

    print("-" * 84)
    print("\nWorst-case across all modes vs 2-star limits (platform uses worst case):")
    print(f"  p5k    {worst['p5k']:.3e}  limit {LIMITS['p5k']:.0e}   "
          f"{flag(worst['p5k'], LIMITS['p5k'])}  "
          f"headroom {LIMITS['p5k']/max(worst['p5k'],1e-99):.0f}x")
    print(f"  p10k   {worst['p10k']:.3e}  limit {LIMITS['p10k']:.0e}   "
          f"{flag(worst['p10k'], LIMITS['p10k'])}  "
          f"headroom {LIMITS['p10k']/max(worst['p10k'],1e-99):.0f}x")
    print(f"  ETL40  {worst['etl40']:.3f}      limit {LIMITS['etl40']}     "
          f"{flag(worst['etl40'], LIMITS['etl40'])}")
    print(f"  ETL10k {worst['etl10k']:.3f}      limit {LIMITS['etl10k']}     "
          f"{flag(worst['etl10k'], LIMITS['etl10k'])}")
    print(f"  CVaR   {worst['cvar']:.1f}      limit {LIMITS['cvar']}     "
          f"{flag(worst['cvar'], LIMITS['cvar'])}  "
          f"headroom {LIMITS['cvar']/max(worst['cvar'],1e-9):.2f}x")


if __name__ == "__main__":
    main()
