"""Reproduce Stake's platform math verification against the optimized LUTs.

    env/bin/python games/starwake/check_risk_gates.py [publish_files_dir]

Mirrors stake-engine.com/docs/approval-guidelines/math-verification as of the
Aug 2026 rollout, which replaced "any failing test blocks the game" with a
two-tier scheme:

  CRITICAL      every one must pass or the game cannot be submitted for review.
  NON-CRITICAL  failing does NOT block. Instead each failed CLASS reduces the
                maximum exposure and maximum bet cost, and those two caps decide
                which bet-level template the game is assigned. Fail enough and no
                template fits.

⚠ THE PENALTY IS A STEP FUNCTION, AND AT 2-STAR THE FIRST FAILURE IS FREE
(0 and 1 failed classes both keep the full $15M / $100k caps). So the number to
watch is not "do we pass everything" -- it is "are we at 2 or more".

⚠ TWO CORRECTIONS vs the version of this file that predates the rollout:
  1. p5k/p10k are NOT scaled by cost multiplier. The docs are now explicit --
     "these are raw probabilities and are not scaled by cost multiplier" -- so
     the old get_prob_scale() leniency factor (0.2/0.5/0.8 by cost band) was
     understating every buy mode. Removed; the raw probability is what counts.
  2. p10k's limit is 0.005, not the 8e-2 recorded in CLAUDE.md -- 16x tighter.
Both corrections only tighten things, so any previously recorded PASS should be
re-read off this file rather than trusted.
"""

import csv
import os
import sys

GAME_DIR = sys.argv[1] if len(sys.argv) > 1 else "games/starwake/library/publish_files"


def _costs():
    """Cost per mode, read from game_config rather than restated here.

    ⚠ THESE WERE HARDCODED UNTIL Aug 5 2026, AND IT PRODUCED A FALSE FAILURE. After
    buy_corvus was repriced 240 -> 120 the optimizer converged correctly at 0.9665,
    but this file still divided by 240 and reported RTP 0.4832 -- tripping the
    "every mode RTP in 90.0-96.7%" CRITICAL test and printing SUBMISSION BLOCKED for
    a pool that was fine. A gate checker that can invent a critical failure from a
    stale constant is worse than no gate checker.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    from game_config import GameConfig
    return {bm.get_name(): bm.get_cost() for bm in GameConfig().bet_modes}


COSTS = _costs()

CRITICAL = {
    "base_std_min": 0.6,
    "rtp_min": 0.90,
    "rtp_max": 0.967,
    "rtp_spread_max": 0.005,
    "max_payout": 500_000.0,
    "max_cost": 2_000.0,
    "hit_rate_min": 1 / 50,  # a non-zero win no rarer than 1 in 50 spins
}

# Non-critical limits per rating. Failing any check in a CLASS costs that class once.
RATINGS = {
    "2-Star": {
        "max_payout": 50_000.0,
        "max_cost": 1_000.0,
        "base_std": 50.0,
        "cvar_per_stake": 700.0,
        "cvar_absolute": 20_000.0,
        "p5k": 0.010,
        "p10k": 0.005,
        "etl40": 0.8,
        "etl10k": 0.6,
        "etl_sum": 1.3,
        # failed classes -> (max exposure $, max bet cost $)
        "penalty": {0: (15e6, 100e3), 1: (15e6, 100e3), 2: (10e6, 50e3),
                    3: (5e6, 50e3), 4: (1e6, 10e3), 5: (500e3, 10e3), 6: (100e3, 5e3)},
    },
    "3-Star": {
        "max_payout": 100_000.0,
        "max_cost": 2_000.0,
        "base_std": 60.0,
        "cvar_per_stake": 700.0,
        "cvar_absolute": 50_000.0,
        "p5k": 0.050,
        "p10k": 0.010,
        "etl40": 0.9,
        "etl10k": 0.8,
        "etl_sum": 1.5,
        "penalty": {0: (50e6, 500e3), 1: (25e6, 500e3), 2: (15e6, 250e3),
                    3: (10e6, 100e3), 4: (5e6, 50e3), 5: (1e6, 10e3), 6: (500e3, 10e3)},
    },
}

# Which checks collapse into one failure class. "A class counts once no matter
# how many modes trip it", so several buys blowing the same check is still one.
CLASSES = {
    "Maximum Payout Multiplier": ["max_payout"],
    "Cost Multiplier": ["max_cost"],
    "Base Volatility (Std Dev)": ["base_std"],
    "Risk Limit (CVaR)": ["cvar_per_stake", "cvar_absolute"],
    "Expected Tail Liability": ["etl40", "etl10k", "etl_sum"],
    "Tail Probability": ["p5k", "p10k"],
}

# Bet-level templates the platform picks from ($ base bet).
TEMPLATES = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
US_EU_MAX = 100  # the docs cap US/EU at $100 whatever the template allows


def conditional_value_at_risk(cutoff, dist, total_weight):
    """Mean payout GIVEN the round landed in the worst (1-cutoff) of outcomes.
    Accumulate from the smallest payout up, take everything from the crossing
    point on -- the convention confirmed against the RGS team's own Go code."""
    ordered = sorted(dist.items())
    cumulative = 0.0
    tail_start = ordered[0][0] if ordered else 0.0
    for payout, weight in ordered:
        cumulative += weight / total_weight
        if cumulative >= cutoff:
            tail_start = payout
            break
    tail_prob = tail_value = 0.0
    for payout, weight in ordered:
        if payout >= tail_start:
            prob = weight / total_weight
            tail_prob += prob
            tail_value += prob * payout
    return tail_value / tail_prob if tail_prob else 0.0


def load_dist(path):
    """LUT format: id, weight, payout*100 -> {payout: summed weight}"""
    dist = {}
    with open(path, newline="") as fh:
        for row in csv.reader(fh):
            if len(row) < 3:
                continue
            payout = float(row[2]) / 100.0
            dist[payout] = dist.get(payout, 0.0) + float(row[1])
    return dist


def analyse(mode, cost):
    path = os.path.join(GAME_DIR, f"lookUpTable_{mode}_0.csv")
    if not os.path.exists(path):
        return None
    dist = load_dist(path)
    total_weight = sum(dist.values())

    p5k = p10k = etl40 = etl10k = expected = sq = hit = 0.0
    for win, weight in dist.items():
        prob = weight / total_weight
        expected += win * prob
        sq += win**2 * prob
        if win > 0:
            hit += prob
        if win >= 5000:
            p5k += prob
        if win >= 10000:
            p10k += prob
            etl10k += win * prob
        if win >= 40 * cost:
            etl40 += win * prob

    # CVaR absolute is the raw expected payout in the tail; per-stake divides by
    # cost. The absolute one is new in the Aug 2026 rollout and is what stops a
    # buy mode passing trivially just because its ticket is expensive.
    cvar_abs = conditional_value_at_risk(0.999, dist, total_weight)
    return {
        "rtp": expected / cost,
        "base_std": (sq - expected**2) ** 0.5 / cost,
        "max_payout": max(dist),
        "max_cost": cost,
        "hit_rate": hit,
        "p5k": p5k,
        "p10k": p10k,
        "etl40": etl40 / expected if expected else 0.0,
        "etl10k": etl10k / expected if expected else 0.0,
        "cvar_per_stake": cvar_abs / cost,
        "cvar_absolute": cvar_abs,
    }


def mark(ok):
    return "OK  " if ok else "FAIL"


def main():
    results = {m: analyse(m, c) for m, c in COSTS.items()}
    missing = [m for m, r in results.items() if r is None]
    if missing:
        print(f"⚠ no optimized LUT for: {', '.join(missing)}  (in {GAME_DIR})\n")
    results = {m: r for m, r in results.items() if r}
    if not results:
        sys.exit(f"no lookUpTable_<mode>_0.csv found in {GAME_DIR}")

    print(f"pool: {GAME_DIR}\n")
    print(f"{'mode':<15}{'cost':>7}{'rtp':>8}{'maxWin':>10}{'hit%':>8}"
          f"{'p5k':>10}{'p10k':>10}{'ETL40':>8}{'ETL10k':>8}"
          f"{'CVaR/st':>9}{'CVaR abs':>10}")
    print("-" * 103)
    for mode, r in results.items():
        print(f"{mode:<15}{r['max_cost']:>7.1f}{r['rtp']:>8.4f}{r['max_payout']:>10,.0f}"
              f"{r['hit_rate']*100:>8.2f}{r['p5k']:>10.2e}{r['p10k']:>10.2e}"
              f"{r['etl40']:>8.3f}{r['etl10k']:>8.3f}"
              f"{r['cvar_per_stake']:>9.1f}{r['cvar_absolute']:>10,.0f}")

    # ---- CRITICAL --------------------------------------------------------
    rtps = [r["rtp"] for r in results.values()]
    base = results.get("base")
    cheapest = min(results.items(), key=lambda kv: kv[1]["max_cost"])[0]
    crit = [
        ("base mode exists at 1.0x and is cheapest",
         base is not None and base["max_cost"] == 1.0 and cheapest == "base",
         f"cheapest = {cheapest}"),
        ("base std dev >= 0.6",
         base is not None and base["base_std"] >= CRITICAL["base_std_min"],
         f"{base['base_std']:.2f}" if base else "-"),
        ("every mode RTP in 90.0-96.7%",
         all(CRITICAL["rtp_min"] <= x <= CRITICAL["rtp_max"] for x in rtps),
         f"{min(rtps)*100:.2f}-{max(rtps)*100:.2f}%"),
        ("cross-mode RTP spread <= 0.5%",
         max(rtps) - min(rtps) <= CRITICAL["rtp_spread_max"],
         f"{(max(rtps)-min(rtps))*100:.3f}%"),
        ("max payout multiplier <= 500,000x",
         max(r["max_payout"] for r in results.values()) <= CRITICAL["max_payout"],
         f"{max(r['max_payout'] for r in results.values()):,.0f}x"),
        ("max cost multiplier <= 2,000x",
         max(r["max_cost"] for r in results.values()) <= CRITICAL["max_cost"],
         f"{max(r['max_cost'] for r in results.values()):,.0f}x"),
        ("non-zero hit rate no rarer than 1 in 50",
         min(r["hit_rate"] for r in results.values()) >= CRITICAL["hit_rate_min"],
         f"worst 1 in {1/min(r['hit_rate'] for r in results.values()):.1f}"),
    ]
    print("\nCRITICAL -- all must pass or the game cannot be submitted")
    print("-" * 103)
    for name, ok, detail in crit:
        print(f"  {mark(ok)}  {name:<45} {detail}")
    if not all(ok for _, ok, _ in crit):
        print("\n  ⚠ SUBMISSION BLOCKED -- a critical test fails.")

    # ---- NON-CRITICAL ----------------------------------------------------
    for rating, lim in RATINGS.items():
        print(f"\nNON-CRITICAL -- {rating}   (worst case across modes)")
        print("-" * 103)
        failed_classes = []
        for cls, checks in CLASSES.items():
            lines, cls_failed = [], False
            for chk in checks:
                if chk == "etl_sum":
                    worst = max(r["etl40"] + r["etl10k"] for r in results.values())
                elif chk == "base_std":
                    worst = base["base_std"] if base else 0.0
                else:
                    worst = max(r[chk] for r in results.values())
                ok = worst <= lim[chk]
                cls_failed |= not ok
                fmt = f"{worst:,.0f}" if worst >= 100 else (
                    f"{worst:.2e}" if worst < 0.01 else f"{worst:.3f}")
                lim_fmt = f"{lim[chk]:,.0f}" if lim[chk] >= 100 else f"{lim[chk]:g}"
                lines.append(f"      {mark(ok)}  {chk:<18} {fmt:>12}  limit {lim_fmt}")
            if cls_failed:
                failed_classes.append(cls)
            print(f"  [{'X' if cls_failed else ' '}] {cls}")
            for ln in lines:
                print(ln)

        n = len(failed_classes)
        exposure, bet_cost = lim["penalty"][min(n, 6)]
        max_payout = max(r["max_payout"] for r in results.values())
        max_cost = max(r["max_cost"] for r in results.values())
        # A template is valid when BOTH worst-case payout and worst-case round
        # cost stay inside the reduced caps.
        by_exposure = exposure / max_payout
        by_cost = bet_cost / max_cost
        allowed = min(by_exposure, by_cost)
        template = max([t for t in TEMPLATES if t <= allowed], default=None)

        print(f"\n  failed classes: {n}"
              + (f"  ({', '.join(failed_classes)})" if failed_classes else ""))
        print(f"  caps after penalty: exposure ${exposure:,.0f}   bet cost ${bet_cost:,.0f}")
        print(f"  max bet by exposure  {max_payout:,.0f}x -> ${by_exposure:,.2f}")
        print(f"  max bet by bet cost  {max_cost:,.0f}x -> ${by_cost:,.2f}   <- binding"
              if by_cost < by_exposure else
              f"  max bet by bet cost  {max_cost:,.0f}x -> ${by_cost:,.2f}")
        if template is None:
            print("  bet-level template: NONE FITS -- game cannot publish at this rating")
        else:
            note = "" if template <= US_EU_MAX else f"  (US/EU still capped at ${US_EU_MAX})"
            print(f"  bet-level template: ${template}{note}")
            if n <= 1:
                nxt = lim["penalty"][min(n + 1, 6)]
                nxt_allowed = min(nxt[0] / max_payout, nxt[1] / max_cost)
                nxt_t = max([t for t in TEMPLATES if t <= nxt_allowed], default=0)
                print(f"  one more failure -> ${nxt_t} template")


if __name__ == "__main__":
    main()
