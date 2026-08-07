"""Sweep ACT TWO's per-tier star VALUE tables, to restore the tier price ladder.

    ./env/bin/python games/starwake/reels/sweep_star_values.py [nsims]

THE PROBLEM THIS EXISTS FOR. Consuming the sticky wilds at wake also consumed the
TIER DIFFERENTIATION. Under the ladder, draco out-paid ursa because its completed
board carried 11 sticky wilds to ursa's 7 -- the cells kept working all feature.
After wake they do nothing, so both tiers roam an identical bare board with an
identical 2x2 block, and the only things left separating them are the star value
table and how long they roam.

And roam length runs the WRONG WAY. Measured at premium/1x:

    tier     completes   stars collected   completion x stars
    corvus      83.9%          ~5.5              4.6
    ursa        62.6%           5.7              3.6
    draco       32.4%           4.6              1.5

Draco completes half as often and roams SHORTER, so on identical tables the
prices would order corvus > ursa > draco -- exactly backwards. Measured on the
shipped tables, ursa already implies 621x against draco's 505x.

SO THE VALUE TABLE HAS TO OVERCOME A ~3x HANDICAP, and the shipped spread
(mean star 3.8 / 5.3 / 8.2) is nowhere near it. Working back from the target
price ratio, draco's mean star wants to be ~6x corvus's, not 2.2x. That means
the fix is mostly to make DRACO RICHER rather than ursa poorer -- which is also
the better product: "draco's stars are worth a fortune" is a real identity,
where "ursa's stars are junk" is just a nerf.

⚠ OVERWRITES FRROAM.csv and go/config/starwake.json. Both restored on exit.
Books land in go/out/SWEEP -- never go/out/library, which holds the converged pool.
(That line used to say go/out/library and was wrong; the -out flag fixed it.)
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

STRIP = "FRROAM.csv"
STRIP_BAK = os.path.join(HERE, "FRROAM.csv.valbak")
CONFIG = os.path.join(ROOT, "go", "config", "starwake.json")
CONFIG_BAK = CONFIG + ".valbak"
# ⚠ SWEEPS WRITE TO THEIR OWN TREE, NOT go/out/library.
# go/out/library holds the CONVERGED 1e6 POOL. sweep_feature_spins once left
# corvus/ursa/draco there as 20k books from its last variant (48-56 MB against
# 1.5-2.8 GB) and the next optimizer run consumed them without complaint,
# reporting RTP 1.9330 and a ceiling the real pool cannot reach. The Go binary
# takes -out, so a sweep has no reason to share the converged pool's directory.
SWEEP_OUT = os.path.join(ROOT, "go", "out", "sweep")
GO_BOOKS = os.path.join(SWEEP_OUT, "publish_files")

# The winning mix from sweep_roam_strip.py: premium-heavy, so the collected
# multiplier has something worth multiplying.
PREMIUM = {"H1": 20, "H2": 16, "H3": 13, "H4": 11,
           "L1": 9, "L2": 8, "L3": 7, "L4": 6, "L5": 6}
BASE_DENSITY = [0, 3, 6, 9, 12]

# value -> weight, per tier. Ascendant always follows draco.
VARIANTS = {
    "shipped": {
        "corvus": {2: 50, 3: 25, 5: 15, 10: 8, 25: 2},
        "ursa": {2: 40, 3: 25, 5: 18, 10: 11, 25: 5, 50: 1},
        "draco": {2: 32, 3: 22, 5: 20, 10: 14, 25: 8, 50: 3, 100: 1},
    },
    # Leave corvus and ursa alone; only draco gets richer. Isolates whether the
    # ladder can be restored WITHOUT taking anything away from the cheap tiers.
    "draco+": {
        "corvus": {2: 50, 3: 25, 5: 15, 10: 8, 25: 2},
        "ursa": {2: 40, 3: 25, 5: 18, 10: 11, 25: 5, 50: 1},
        "draco": {2: 20, 3: 16, 5: 20, 10: 18, 25: 13, 50: 9, 100: 4},
    },
    "spread": {
        "corvus": {2: 55, 3: 25, 5: 13, 10: 6, 25: 1},
        "ursa": {2: 45, 3: 25, 5: 17, 10: 9, 25: 3, 50: 1},
        "draco": {2: 16, 3: 14, 5: 18, 10: 18, 25: 15, 50: 12, 100: 7},
    },
    "wide": {
        "corvus": {2: 60, 3: 24, 5: 11, 10: 4, 25: 1},
        "ursa": {2: 50, 3: 25, 5: 15, 10: 7, 25: 2, 50: 1},
        "draco": {2: 12, 3: 11, 5: 16, 10: 18, 25: 16, 50: 15, 100: 12},
    },
    # ── CORVUS TAIL VARIANTS (Aug 7 2026) ────────────────────────────────────
    # `spread` is the SHIPPED table. Measured on the converged pool, corvus has
    # no distribution between 2,500x and its 9,000x ceiling: 8,295 books in
    # 2,500-5,000, 142 in 5,000-8,100, and ONE book in 8,100-9,000 out of 1e6.
    # So its published max win is unreachable (1 in 2,000,003 delivered, against
    # a market norm of 1 in 400-4,000) and contributes 0.1% of the mode's
    # variance. No optimizer dress can fix that -- the books do not exist.
    #
    # Corvus's star table stops at 25x where ursa reaches 50x and draco 100x, so
    # its collected multiplier cannot get large enough to produce that band.
    # These three add a high rung and pay for it out of the 5x/10x middle, which
    # keeps the mean star BELOW ursa's 4.65 so the price ladder survives.
    # ursa and draco are held at `spread` so the corvus effect is isolated --
    # the same technique as `draco+` above.
    "corvus+50": {
        "corvus": {2: 56, 3: 25, 5: 12, 10: 5, 25: 1, 50: 1},          # star 3.72
        "ursa": {2: 45, 3: 25, 5: 17, 10: 9, 25: 3, 50: 1},
        "draco": {2: 16, 3: 14, 5: 18, 10: 18, 25: 15, 50: 12, 100: 7},
    },
    "corvus+100": {
        "corvus": {2: 56, 3: 25, 5: 12, 10: 5, 25: 1, 100: 0.4},       # star 3.64
        "ursa": {2: 45, 3: 25, 5: 17, 10: 9, 25: 3, 50: 1},
        "draco": {2: 16, 3: 14, 5: 18, 10: 18, 25: 15, 50: 12, 100: 7},
    },
    "corvus+both": {
        "corvus": {2: 57, 3: 25, 5: 11, 10: 5, 25: 1, 50: 0.7, 100: 0.3},  # star 3.84
        "ursa": {2: 45, 3: 25, 5: 17, 10: 9, 25: 3, 50: 1},
        "draco": {2: 16, 3: 14, 5: 18, 10: 18, 25: 15, 50: 12, 100: 7},
    },
}

DENSITIES = [1, 2]
MODES = {"buy_corvus": "corvus", "buy_ursa": "ursa", "buy_draco": "draco"}


def mean_star(table):
    total = sum(table.values())
    return sum(v * w for v, w in table.items()) / total


def write_roam_strip(density):
    gr.write_strip(STRIP, {
        "base": dict(PREMIUM, W=0, S=0, M=0),
        "per_reel": {r: {"M": BASE_DENSITY[r] * density} for r in range(1, 5)},
    })


def export_with(values):
    import export_go_config as ex
    from game_config import GameConfig
    config = GameConfig()
    config.constellation_star_values = dict(values)
    config.constellation_star_values["ascendant"] = values["draco"]
    payload = ex.build_payload(config)
    ex.validate(payload, config)
    with open(CONFIG, "w", encoding="UTF-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False)


def run_mode(mode, nsims):
    subprocess.run(
        ["go", "run", "./cmd/starwake", "-mode", mode, "-sims", str(nsims),
         "-no-wincap", "-quiet", "-out", SWEEP_OUT],
        cwd=os.path.join(ROOT, "go"), check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def summarise(mode, cost, rtp):
    pays, mults = [], []
    with open(os.path.join(GO_BOOKS, f"books_{mode}.jsonl.zst"), "rb") as fh:
        reader = zstd.ZstdDecompressor().stream_reader(fh)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            book = json.loads(line)
            pays.append(book["payoutMultiplier"] / 100.0)
            top = 1
            for e in book["events"]:
                if e["type"] == "starsCollected":
                    top = e["multiplier"]
            if top > 1:
                mults.append(top)
    pays.sort()
    mean = statistics.fmean(pays)
    median = statistics.median(pays)
    n = len(pays)
    # ⚠ TAIL SUPPLY, added Aug 7 2026, and it is the point of the corvus variants.
    # The optimizer can only weight books that EXIST, so what matters for a
    # reachable max win is how many the engine produces up there -- not how the
    # weights are later arranged. Wincap is stripped on this run (-no-wincap), so
    # `max` is the NATURAL ceiling and these counts are natural supply.
    return {
        "mean": mean, "median": median,
        "ratio": mean / median if median else float("inf"),
        "price": mean / rtp,
        "max": pays[-1],
        "beat": sum(1 for p in pays if p >= cost) / len(pays) * 100,
        "mult": statistics.fmean(mults) if mults else 0.0,
        "t20": sum(1 for p in pays if p >= 20 * cost) / n * 100,
        "t40": sum(1 for p in pays if p >= 40 * cost) / n * 100,
        "t60": sum(1 for p in pays if p >= 60 * cost) / n * 100,
    }


if __name__ == "__main__":
    nsims = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    os.chdir(GAME)
    from game_config import GameConfig

    cfg = GameConfig()
    costs = {m.get_name(): m.get_cost() for m in cfg.bet_modes}
    rtp = cfg.rtp

    shutil.copy2(os.path.join(HERE, STRIP), STRIP_BAK)
    shutil.copy2(CONFIG, CONFIG_BAK)
    rows = []
    try:
        for density in DENSITIES:
            write_roam_strip(density)
            for name, values in VARIANTS.items():
                export_with(values)
                for mode, tier in MODES.items():
                    run_mode(mode, nsims)
                    r = summarise(mode, costs[mode], rtp)
                    r.update(variant=name, density=density, mode=mode,
                             star=mean_star(values[tier]), target=costs[mode])
                    rows.append(r)
    finally:
        shutil.move(STRIP_BAK, os.path.join(HERE, STRIP))
        shutil.move(CONFIG_BAK, CONFIG)

    print("\n" + "=" * 100)
    print(f"ACT TWO STAR-VALUE SWEEP   n={nsims:,}/variant   premium roam strip, wincap stripped")
    print("=" * 100)
    for density in DENSITIES:
        print(f"\n--- star density {density}x " + "-" * 74)
        print(f"{'variant':11s}{'mode':12s}{'star':>6s}{'mult':>7s}{'price':>8s}"
              f"{'vs':>7s}{'m/med':>7s}{'max':>9s}{'beat':>7s}"
              f"{'>=20x':>8s}{'>=40x':>8s}{'>=60x':>8s}   ladder?")
        for name in VARIANTS:
            got = [r for r in rows if r["variant"] == name and r["density"] == density]
            prices = {r["mode"]: r["price"] for r in got}
            ok = prices.get("buy_corvus", 0) < prices.get("buy_ursa", 0) < prices.get("buy_draco", 0)
            for i, r in enumerate(got):
                mark = ("  ORDERED" if ok else "  INVERTED") if i == 0 else ""
                print(f"{name if i == 0 else '':11s}{r['mode']:12s}{r['star']:>6.1f}"
                      f"{r['mult']:>6.0f}x{r['price']:>7.0f}x"
                      f"{r['price']/r['target']:>6.2f}x{r['ratio']:>7.2f}"
                      f"{r['max']:>8.0f}x{r['beat']:>6.1f}%"
                      f"{r['t20']:>7.3f}%{r['t40']:>7.3f}%{r['t60']:>7.3f}%{mark}")
            print()
    print("reading it:")
    print("  star    mean value of one star for that tier -- the knob being swept")
    print("  price   implied cost (mean / rtp); vs = price / configured target")
    print("  ladder  corvus < ursa < draco on price. WITHOUT THIS THERE IS NO MENU:")
    print("          a cheaper tier paying more than an expensive one is not a")
    print("          product, and it is what the shipped tables currently do.")
    print("  m/med   volatility. The ladder ran 1.72; act two shipped at 1.17.")
    print("  >=20/40/60x  TAIL SUPPLY as multiples of that mode's OWN ticket, wincap")
    print("          stripped. This is the column the corvus variants exist for: the")
    print("          shipped table produces almost nothing above ~20x ticket on corvus,")
    print("          which is why its 75x-ticket max win is unreachable. Weights cannot")
    print("          create books, so if supply does not move here, nothing downstream")
    print("          can fix the max win.")
