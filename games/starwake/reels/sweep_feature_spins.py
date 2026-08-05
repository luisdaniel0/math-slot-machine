"""Sweep FEATURE LENGTH: does a longer feature give corvus a ceiling worth buying?

    ./env/bin/python games/starwake/reels/sweep_feature_spins.py [nsims]

THE PRODUCT PROBLEM THIS IS FOR. Measured on the converged act two pool, corvus
has no reason to exist:

    mode         cost   median  med/cost   beat   ceiling  ceil/cost
    buy_corvus    240      59x    0.24    22.4%    9,158x     38.2x
    buy_ursa      268      33x    0.12    21.1%   25,000x     93.3x
    buy_draco     520     140x    0.27    21.7%   25,000x     48.1x

It is LAST on ceiling-per-cost and second-worst on median, and its 22.4% beat
rate is inside the noise of the other three. Ursa costs 12% more and offers 2.7x
the ceiling. That is a menu problem, not a ceiling-number problem -- publishing
7,500x or 10,000x does not change it.

⚠ ONLY CORVUS'S CEILING IS ORGANIC. Ursa, draco and mystery are FORCED to 25,000x
by a wincap slice, so a longer feature cannot raise their published ceiling at all
-- it only makes them richer, which the optimizer then removes. So extending every
tier proportionally raises corvus's ceiling while leaving the others' headline
numbers untouched. That asymmetry is the whole reason this might work.

WHAT TO WATCH, because more spins is not free:
  completion   more spins = more chances to fill the set, so the 84/63/32 tier
               ladder COMPRESSES. That ladder is the product.
  price        every mode already implies 1.7-2.1x its configured price. More
               surplus means the optimizer down-weights harder, which thins the
               tail it is being asked to create.
  ev/book      draco's books file is 2.82 GB against a 4.2 GB cap, and the
               10,000,000-events-per-mode question is still unresolved. +20%
               spins is roughly +20% events.
  feel         the user's own complaint was that features "take forever". Act two
               removed the wild carpet, so wins per spin are far lower now -- but
               longer is still longer.
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
sys.path.insert(0, GAME)

CONFIG = os.path.join(ROOT, "go", "config", "starwake.json")
BOOKS = os.path.join(ROOT, "go", "out", "library", "publish_files")

# tier -> feature spins
VARIANTS = {
    "current": {"corvus": 10, "ursa": 15, "draco": 15, "ascendant": 15},
    "all +20%": {"corvus": 12, "ursa": 18, "draco": 18, "ascendant": 18},
    "all +40%": {"corvus": 14, "ursa": 21, "draco": 21, "ascendant": 21},
    # Keeps the other tiers' identity untouched and spends the whole change on
    # the tier that has a problem. Costs corvus its "short and punchy" identity.
    "corvus only": {"corvus": 15, "ursa": 15, "draco": 15, "ascendant": 15},
}

MODES = {"buy_corvus": 240.0, "buy_ursa": 268.0, "buy_draco": 520.0}


def export(spins):
    import export_go_config as ex
    from game_config import GameConfig
    c = GameConfig()
    c.num_feature_spins = dict(spins)
    # freespin_triggers is DERIVED from num_feature_spins at construction, so it
    # has to be rebuilt or the engine awards the old counts while the tier config
    # advertises the new ones -- a silent mismatch, not an error.
    tier_spins = {count: spins[t] for count, t in c.scatter_tiers.items()}
    c.freespin_triggers = {c.basegame_type: dict(tier_spins),
                           c.freegame_type: dict(tier_spins)}
    payload = ex.build_payload(c)
    ex.validate(payload, c)
    with open(CONFIG, "w", encoding="UTF-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False)


def run(mode, nsims):
    subprocess.run(["go", "run", "./cmd/starwake", "-mode", mode,
                    "-sims", str(nsims), "-no-wincap", "-quiet"],
                   cwd=os.path.join(ROOT, "go"), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def summarise(mode, cost, rtp):
    pays, ev, done = [], [], 0
    with open(os.path.join(BOOKS, f"books_{mode}.jsonl.zst"), "rb") as fh:
        reader = zstd.ZstdDecompressor().stream_reader(fh)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            b = json.loads(line)
            pays.append(b["payoutMultiplier"] / 100.0)
            ev.append(len(b["events"]))
            if any(e["type"] == "beastWake" for e in b["events"]):
                done += 1
    pays.sort()
    mean = statistics.fmean(pays)
    return {
        "complete": done / len(pays) * 100,
        "mean": mean, "price": mean / rtp,
        "max": pays[-1], "maxpc": pays[-1] / cost,
        "ev": statistics.fmean(ev),
    }


if __name__ == "__main__":
    nsims = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    os.chdir(GAME)
    from game_config import GameConfig
    rtp = GameConfig().rtp

    bak = CONFIG + ".spinbak"
    shutil.copy2(CONFIG, bak)
    rows = []
    try:
        for name, spins in VARIANTS.items():
            export(spins)
            for mode, cost in MODES.items():
                run(mode, nsims)
                r = summarise(mode, cost, rtp)
                r.update(variant=name, mode=mode, spins=spins,
                         tier={"buy_corvus": "corvus", "buy_ursa": "ursa",
                               "buy_draco": "draco"}[mode])
                rows.append(r)
    finally:
        shutil.move(bak, CONFIG)

    print("\n" + "=" * 96)
    print(f"FEATURE-LENGTH SWEEP   n={nsims:,}/variant   wincap stripped")
    print("=" * 96)
    print(f"{'variant':13s}{'mode':12s}{'spins':>6s}{'complete':>10s}"
          f"{'price':>8s}{'max':>10s}{'max/cost':>10s}{'ev/book':>9s}")
    print("-" * 96)
    for name in VARIANTS:
        for r in [x for x in rows if x["variant"] == name]:
            print(f"{name if r['mode'] == 'buy_corvus' else '':13s}{r['mode']:12s}"
                  f"{r['spins'][r['tier']]:>6d}{r['complete']:>9.1f}%"
                  f"{r['price']:>7.0f}x{r['max']:>9,.0f}x{r['maxpc']:>9.1f}x"
                  f"{r['ev']:>9.1f}")
        print("-" * 96)
    print("\nreading it:")
    print("  max/cost  THE NUMBER THIS IS FOR. corvus sits at 38.2x against ursa's")
    print("            93.3x, which is why it has no pitch. It needs to clear ~48x")
    print("            (draco's) to be worth choosing on ceiling rather than on")
    print("            reliability alone.")
    print("  complete  the 84/63/32 tier ladder. If this compresses, the menu goes")
    print("            with it -- watch draco especially.")
    print("  ev/book   draco is at 2.82 GB of 4.2 GB, and the 10M-events-per-mode")
    print("            question is open. +20% spins is roughly +20% here.")
