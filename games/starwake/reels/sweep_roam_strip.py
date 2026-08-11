"""Sweep ACT TWO's roam strip: star density x paying-symbol mix.

    ./env/bin/python games/starwake/reels/sweep_roam_strip.py [nsims] [modes...]

WHY BOTH AXES AT ONCE. Act two's payout is (symbol win) x (collected multiplier)
and the roam strip sets BOTH halves, in opposite directions:

  more stars   -> bigger multiplier, but stars are NON-PAYING and break paylines,
                  so fewer cells are left to pay. Past some density act two pays
                  LESS. There is an interior optimum, not a monotonic knob.
  richer mix   -> more premiums means the multiplier lands on something worth
                  multiplying. Free of the above tension, but it lifts the body
                  and the tail together.

Sweeping one at a time would find a local answer for whichever was fixed first,
so they move together here.

FIRST MEASUREMENT SAID ACT TWO IS THIN *AND* FLAT (n=20k, wincap stripped):
    implied price   163 / 236 / 297x   against configured 240 / 268 / 520x
    draco mean/median 1.17 against the ladder's 1.72, max 6,705x vs 25,000x
Flat is the harder problem. The ladder was geometric in roam depth so a long roam
was explosive; adding star values instead gives a SUM, and a sum of a few draws
clusters around its mean by the central limit theorem. So watch mean/median and
p99 here, not just the price -- a variant that fixes the price and leaves the
ratio at 1.2 has produced a low-volatility game wearing a high-volatility ticket.

⚠ OVERWRITES games/starwake/reels/FRROAM.csv. Backed up and restored around the
run. Books land in go/out/library (the Go engine's own tree), never in
games/starwake/library, so the converged pool is untouched.
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

import generate_reels as gr  # noqa: E402

STRIP = "FRROAM.csv"
BACKUP = os.path.join(HERE, "FRROAM.csv.sweepbak")
# ⚠ SWEEPS WRITE TO THEIR OWN TREE, NOT go/out/library.
# go/out/library holds the CONVERGED 1e6 POOL. sweep_feature_spins once left
# corvus/ursa/draco there as 20k books from its last variant (48-56 MB against
# 1.5-2.8 GB) and the next optimizer run consumed them without complaint,
# reporting RTP 1.9330 and a ceiling the real pool cannot reach. The Go binary
# takes -out, so a sweep has no reason to share the converged pool's directory.
SWEEP_OUT = os.path.join(ROOT, "go", "out", "sweep")
GO_BOOKS = os.path.join(SWEEP_OUT, "publish_files")

# Paying-symbol mixes. "lows" is what act two shipped with (a copy of FR0's
# curve); "premium" inverts it so a collected multiplier has something to land on.
MIXES = {
    "lows": {"H1": 8, "H2": 10, "H3": 12, "H4": 14,
             "L1": 16, "L2": 18, "L3": 20, "L4": 22, "L5": 24},
    "premium": {"H1": 20, "H2": 16, "H3": 13, "H4": 11,
                "L1": 9, "L2": 8, "L3": 7, "L4": 6, "L5": 6},
}

# Per-reel star counts, as multiples of the shipped 0/3/6/9/12. Reel 0 stays
# star-free at every density: a blocker on the leftmost reel kills every line
# through that row outright, while one on reel 4 only shortens a 5-kind.
BASE_DENSITY = [0, 3, 6, 9, 12]
DENSITIES = [1, 2, 3, 4]

MODES = ["buy_draco", "buy_ursa"]


def write_roam_strip(mix, density):
    spec = {
        "base": dict(MIXES[mix], W=0, S=0, M=0),
        "per_reel": {r: {"M": BASE_DENSITY[r] * density} for r in range(1, 5)},
    }
    gr.write_strip(STRIP, spec)


def run_mode(mode, nsims):
    """Sim with wincap slices stripped -- a forced cap would both hang on a thin
    variant and flatter every variant equally."""
    subprocess.run(
        ["go", "run", "./cmd/starwake", "-mode", mode, "-sims", str(nsims),
         "-no-wincap", "-quiet", "-out", SWEEP_OUT],
        cwd=os.path.join(ROOT, "go"), check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


def summarise(mode, cost, rtp):
    pays, mults, stars = [], [], []
    path = os.path.join(GO_BOOKS, f"books_{mode}.jsonl.zst")
    with open(path, "rb") as fh:
        reader = zstd.ZstdDecompressor().stream_reader(fh)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            book = json.loads(line)
            pays.append(book["payoutMultiplier"] / 100.0)
            top, n = 1, 0
            for e in book["events"]:
                if e["type"] == "starsCollected":
                    top = e["multiplier"]
                    n += len(e["stars"])
            if top > 1:
                mults.append(top)
                stars.append(n)
    pays.sort()
    mean = statistics.fmean(pays)
    median = statistics.median(pays)
    return {
        "mean": mean,
        "median": median,
        "ratio": mean / median if median else float("inf"),
        "cost": mean / rtp,
        "p99": pays[int(len(pays) * 0.99)],
        "max": pays[-1],
        "beat": sum(1 for p in pays if p >= cost) / len(pays) * 100,
        "mult": statistics.fmean(mults) if mults else 0.0,
        "stars": statistics.fmean(stars) if stars else 0.0,
    }


if __name__ == "__main__":
    nsims = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    modes = sys.argv[2:] or MODES

    sys.path.insert(0, GAME)
    os.chdir(GAME)
    from game_config import GameConfig

    config = GameConfig()
    costs = {m.get_name(): m.get_cost() for m in config.bet_modes}
    rtp = config.rtp

    shutil.copy2(os.path.join(HERE, STRIP), BACKUP)
    rows = []
    try:
        for mix in MIXES:
            for density in DENSITIES:
                write_roam_strip(mix, density)
                subprocess.run([os.path.join(ROOT, "env", "bin", "python"),
                                os.path.join(GAME, "export_go_config.py")],
                               check=True, cwd=GAME, stdout=subprocess.DEVNULL)
                for mode in modes:
                    run_mode(mode, nsims)
                    r = summarise(mode, costs[mode], rtp)
                    r.update(mix=mix, density=density, mode=mode)
                    rows.append(r)
    finally:
        shutil.move(BACKUP, os.path.join(HERE, STRIP))
        subprocess.run([os.path.join(ROOT, "env", "bin", "python"),
                        os.path.join(GAME, "export_go_config.py")],
                       check=True, cwd=GAME, stdout=subprocess.DEVNULL)

    print("\n" + "=" * 104)
    print(f"ACT TWO ROAM STRIP SWEEP   n={nsims:,}/variant   (wincap stripped)")
    print("=" * 104)
    print(f"{'mode':11s}{'mix':9s}{'dens':>5s}{'stars':>7s}{'mult':>8s}"
          f"{'mean':>9s}{'median':>9s}{'m/med':>7s}{'p99':>9s}{'max':>9s}"
          f"{'price':>8s}{'beat':>7s}")
    print("-" * 104)
    last = None
    for r in rows:
        if last and last != r["mode"]:
            print("-" * 104)
        last = r["mode"]
        print(f"{r['mode']:11s}{r['mix']:9s}{r['density']:>4d}x{r['stars']:>7.1f}"
              f"{r['mult']:>7.0f}x{r['mean']:>8.0f}x{r['median']:>8.0f}x"
              f"{r['ratio']:>7.2f}{r['p99']:>8.0f}x{r['max']:>8.0f}x"
              f"{r['cost']:>7.0f}x{r['beat']:>6.1f}%")
    print("-" * 104)
    print("\nreading it:")
    print("  stars  collected per completed feature; mult = final multiplier")
    print("  m/med  mean/median. THE VOLATILITY NUMBER -- the ladder ran 1.72 and")
    print("         act two shipped at 1.17. A variant that hits the price with a")
    print("         flat ratio is a low-volatility game on a high-volatility ticket.")
    print("  price  implied cost (mean / rtp). Targets: draco 520x, ursa 268x.")
    print("  beat   share of buys paying at least the CONFIGURED cost (market ~22%)")
