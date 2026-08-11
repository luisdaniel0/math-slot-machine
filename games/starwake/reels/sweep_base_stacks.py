"""Sweep STACKED PREMIUM SYMBOLS on BR0, to fix base-game dryness.

    ./env/bin/python games/starwake/reels/sweep_base_stacks.py [nsims]

THE DEFECT. An ordinary base spin -- no scatters, no feature -- tops out at 22x
and carries 62.8% of base RTP, with 70.75% of spins paying nothing. Share of base
RTP arriving as a win above 100x is 0.226, and base std dev is 24.77 against a
35-48 market band. It is the mode players spend 95% of their time in, and it is
the "1-2 bets before losing interest" shape the ratings page names.

⚠ 22x IS NOT A PAYTABLE CEILING. Twenty lines of H1 would be 240x. The real cause
is that a randomly-shuffled strip almost never puts a premium symbol on more than
one payline at a time. So the fix is not to make wins bigger, it is to make MANY
LINES PAY AT ONCE.

STACKING DOES THAT WITHOUT A MULTIPLIER. H1 laid down in runs of 3-4 means a stop
that lands on the run shows a solid column of Leo -- every row pays simultaneously.
Four 3-kinds instead of one, and more if it reaches reel 3.

WHAT TO WATCH:
  ceiling    max payout of an ORDINARY spin (no feature). The number being fixed.
  hit rate   stacking reduces symbol diversity, so this FALLS. Huge headroom --
             base runs 1 in 3.4 and the critical gate is 1 in 50 -- but it is the
             cost being paid and it should be paid knowingly.
  std        rises with the ceiling. That is D5, fixed by the same change.
  trigger    stacking displaces other symbols, which can move the scatter rate.
             ⚠ THE TRIGGER RATE IS THE WHOLE BASE ECONOMY -- the feature carries
             35% of base RTP -- so a variant that quietly halves it has changed a
             different game.

Measured from the RAW BOOKS, not an optimized LUT, because the ordinary-spin
CEILING is a structural property of what the strips can produce and does not
depend on weighting. Everything weight-dependent (the >100x share, the delivered
std) still has to be re-measured after the optimizer runs on the winner.
"""
import io
import json
import os
import shutil
import statistics
import subprocess
import sys

import zstandard as zstd

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(GAME))
sys.path.insert(0, HERE)
sys.path.insert(0, GAME)

import generate_reels as gr  # noqa: E402

STRIP = "BR0.csv"
BACKUP = os.path.join(HERE, "BR0.csv.stackbak")
CONFIG = os.path.join(ROOT, "go", "config", "starwake.json")
CONFIG_BAK = CONFIG + ".stackbak"
SWEEP_OUT = os.path.join(ROOT, "go", "out", "sweep")
BOOKS = os.path.join(SWEEP_OUT, "publish_files")

BASE_WEIGHTS = dict(gr.STRIP_WEIGHTS["BR0.csv"])

# name -> (stacks {symbol: run length}, weight overrides).
#
# ROUND 1 FOUND STACKING IS NEARLY FREE: hit rate held at 55.6% and the trigger
# rate at 10.00% across every variant, because stacking REARRANGES the same symbol
# counts rather than removing any. The predicted cost did not appear. Ceiling went
# 18x -> 87x and raw std 0.80 -> 1.24.
#
# ⚠ BUT NOTHING CROSSED 100x, so the "share of base RTP above 100x" metric (0.226)
# would not move at all -- ordinary spins still contribute nothing to it. Round 2
# therefore also raises the PREMIUM COUNTS, because that is what sets how often a
# reel can show a full column: H1 at count 8 with 4-runs gives only 2 stacks per
# reel, so P(one reel solid) is ~1.2% and P(three reels solid) ~1 in 500k. More
# stacks per reel is the only way to make a big alignment reachable.
# Lows come down to pay for it, keeping the strip roughly the same length.
def _richer(**over):
    w = dict(BASE_WEIGHTS)
    w.update(over)
    return w


X4 = {"H1": 4, "H2": 4}
X4_3 = {"H1": 4, "H2": 4, "H3": 4}

VARIANTS = {
    "current": (None, None),
    "H1+H2 x4": (X4, None),
    "H1+H2+H3 x4": (X4_3, None),
    "x4 richer": (X4_3, _richer(H1=16, H2=16, H3=16,
                                L1=14, L2=16, L3=18, L4=20, L5=22)),
    "x4 richest": (X4_3, _richer(H1=24, H2=24, H3=20,
                                 L1=10, L2=12, L3=14, L4=16, L5=18)),
}


def write_base_strip(stacks, weights):
    base = weights or BASE_WEIGHTS
    spec = dict(base)
    if stacks:
        spec = {"base": dict(base), "stacks": stacks}
    gr.write_strip(STRIP, spec)


def sim(nsims):
    subprocess.run(["go", "run", "./cmd/starwake", "-mode", "base",
                    "-sims", str(nsims), "-quiet", "-out", SWEEP_OUT],
                   cwd=os.path.join(ROOT, "go"), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def summarise():
    """Split the raw pool into ordinary spins and feature spins."""
    plain, feature = [], []
    with open(os.path.join(BOOKS, "books_base.jsonl.zst"), "rb") as fh:
        reader = zstd.ZstdDecompressor().stream_reader(fh)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            b = json.loads(line)
            pay = b["payoutMultiplier"] / 100.0
            triggered = any(e["type"] == "freeSpinTrigger" for e in b["events"])
            (feature if triggered else plain).append(pay)

    n = len(plain) + len(feature)
    hits = sum(1 for p in plain if p > 0)
    mean = statistics.fmean(plain)
    var = statistics.fmean([(p - mean) ** 2 for p in plain])
    return {
        "ceiling": max(plain) if plain else 0.0,
        "mean": mean,
        "std": var ** 0.5,
        "hit": hits / len(plain) * 100 if plain else 0.0,
        "trigger": len(feature) / n * 100,
        "over10": sum(1 for p in plain if p >= 10) / len(plain) * 100,
        "over50": sum(1 for p in plain if p >= 50) / len(plain) * 100,
    }


if __name__ == "__main__":
    nsims = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    os.chdir(GAME)

    shutil.copy2(os.path.join(HERE, STRIP), BACKUP)
    shutil.copy2(CONFIG, CONFIG_BAK)
    rows = []
    try:
        for name, (stacks, weights) in VARIANTS.items():
            write_base_strip(stacks, weights)
            subprocess.run([os.path.join(ROOT, "env", "bin", "python"),
                            os.path.join(GAME, "export_go_config.py")],
                           check=True, cwd=GAME, stdout=subprocess.DEVNULL)
            sim(nsims)
            r = summarise()
            r["variant"] = name
            rows.append(r)
            print(f"  done {name}", flush=True)
    finally:
        shutil.move(BACKUP, os.path.join(HERE, STRIP))
        shutil.move(CONFIG_BAK, CONFIG)

    print("\n" + "=" * 96)
    print(f"BASE STACKED-SYMBOL SWEEP   n={nsims:,}   ORDINARY spins only "
          "(feature books excluded)")
    print("=" * 96)
    print(f"{'variant':15s}{'ceiling':>10s}{'mean':>9s}{'std':>9s}{'hit%':>8s}"
          f"{'>=10x':>8s}{'>=50x':>8s}{'trigger%':>10s}")
    print("-" * 96)
    for r in rows:
        print(f"{r['variant']:15s}{r['ceiling']:>9,.0f}x{r['mean']:>8.2f}x"
              f"{r['std']:>9.2f}{r['hit']:>7.1f}%{r['over10']:>7.2f}%"
              f"{r['over50']:>7.3f}%{r['trigger']:>9.2f}%")
    print("-" * 96)
    print("\nreading it:")
    print("  ceiling   what an ordinary base spin can pay. 22x is the defect.")
    print("  std       the RAW ordinary-spin std, not the published one -- the")
    print("            published figure comes from the optimized LUT and includes")
    print("            feature and wincap books. Use this to COMPARE variants only.")
    print("  hit%      falls as stacking rises. The gate is 1 in 50 (2%), so there")
    print("            is room -- but this is the price being paid.")
    print("  trigger%  MUST stay near current. The feature carries 35% of base RTP,")
    print("            so a variant that moves this has changed a different game.")
