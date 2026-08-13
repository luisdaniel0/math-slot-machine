"""Sweep ASCENDANT's own star VALUE table, to pull buy_mystery's richness back in band.

    ./env/bin/python games/starwake/reels/sweep_ascendant_stars.py [nsims]

THE PROBLEM THIS EXISTS FOR. Twin Dragons (Aug 12 2026) gave ascendant two 2x2
blocks instead of one, and doubling the wild footprint on a 20-payline game MORE
than doubles output because wilds compound across lines. Measured: ascendant's
raw mean went 2,598x -> 10,994x and its unforced at-cap rate 1 in 67 -> 1 in 5,
taking buy_mystery's pool richness to 3.46 against a healthy band of 1.9-2.6.

RICHNESS IS THE BINDING CONSTRAINT, not RTP. The optimizer hits RTP exactly at
any richness -- it just has to DISCARD more, and its cheapest way to discard
value is to pile weight onto near-worthless books. That is the corvus disease
(that mode sat at 3.74 with +/-20 point body swings). Ascendant currently
discards ~78% of its natural value, which is the largest discard in the game.

THE LEVER IS THE STAR TABLE, because ascendant only ALIASES draco's today
(game_config.py:625) and ascendant exists ONLY inside buy_mystery -- so giving
it its own table re-sims ONE mode, where touching draco's would re-sim four.
The alternative dial is num_feature_spins["ascendant"], already per-tier.

⚠ WHAT WE ARE *NOT* TRYING TO DO. This is not a nerf. Ascendant's DELIVERED
value is set by mystery_payback (0.478 of the mode's mean), not by its supply --
so cutting supply does not cost the player anything, it just stops the optimizer
having to throw 78% of the tier away. Delivered value only moves if
mystery_payback moves. Watch that the tier can still REACH 25,000x for its
forced wincap slice: at 1 in 5 unforced there is enormous headroom, but a slice
that cannot fill its quota is a silent infinite hang, so confirm rather than assume.

⚠ APPLY THE HOUSE LESSON (game_config.py:587-593): FREQUENCY BEATS MAGNITUDE.
Thin the top rung and fatten the low/mid ones rather than deleting the 100 rung
-- a rung you never hit does nothing in either direction.

METHOD. Each variant runs buy_mystery patched to 100% ascendant with the wincap
slice stripped, so the sample is not diluted 10:1 and no forced cap distorts the
mean. The three purchasable tiers are measured ONCE up front (their tables do
not move), which is what lets us report the MODE's richness rather than just
ascendant's mean.

⚠ WRITES ONLY TO go/out/sweep, never go/out/library -- that holds the converged
1e6 pool, and sweep_feature_spins once left 20k books there which the next
optimizer run consumed without complaint, reporting RTP 1.9330.
go/config/starwake.json is overwritten and restored on exit.
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

CONFIG = os.path.join(ROOT, "go", "config", "starwake.json")
CONFIG_BAK = CONFIG + ".ascstarbak"
SWEEP_OUT = os.path.join(ROOT, "go", "out", "sweep")
GO_BOOKS = os.path.join(SWEEP_OUT, "publish_files")

MODE = "buy_mystery"
# The Aug 12 2026 roll mix. Mystery's raw mean is the quota-weighted average of
# its four tier means, which is what richness is computed from.
MIX = {"corvus": 0.350, "ursa": 0.350, "draco": 0.200, "ascendant": 0.100}
TIER_MODE = {"corvus": "buy_corvus", "ursa": "buy_ursa", "draco": "buy_draco"}
HEALTHY = (1.9, 2.6)

# value -> weight. `alias-draco` is the SHIPPED state (ascendant just points at
# draco's table). Everything below it thins the top and fattens the bottom by
# increasing amounts. Means: 20.19 / 15.41 / 11.22 / 7.98 / 5.75.
VARIANTS = {
    "alias-draco": {2: 16, 3: 14, 5: 18, 10: 18, 25: 15, 50: 12, 100: 7},
    "asc-15": {2: 20, 3: 17, 5: 19, 10: 18, 25: 13, 50: 9, 100: 4},
    "asc-11": {2: 26, 3: 20, 5: 20, 10: 16, 25: 10, 50: 6, 100: 2},
    "asc-8": {2: 32, 3: 23, 5: 20, 10: 14, 25: 7, 50: 3, 100: 1},
    "asc-6": {2: 40, 3: 25, 5: 19, 10: 10, 25: 4, 50: 1.5, 100: 0.5},
}


def mean_star(table):
    total = sum(table.values())
    return sum(v * w for v, w in table.items()) / total


# The OTHER named lever (CLAUDE.md:77-81), measured on the same footing so the
# choice between them is evidence rather than taste. ⚠ Spins are NOT a free dial
# here: the star table cannot touch act-1 lighting, but feature length can --
# fewer spins means fewer chances to trace the constellation, so completion falls.
# The file's own warning is that a jackpot tier which fails half the time is
# worse than an over-strong one.
SPIN_VARIANTS = [15, 13, 12, 10]


def export_with(asc_table, isolate_ascendant, asc_spins=None):
    """Write go/config/starwake.json from a mutated GameConfig.

    `isolate_ascendant` patches buy_mystery to 100% ascendant with no wincap
    slice, so every book in the run is the tier under measurement.
    """
    import export_go_config as ex
    from game_config import GameConfig

    config = GameConfig()
    if asc_table is not None:
        config.constellation_star_values["ascendant"] = dict(asc_table)
    if asc_spins is not None:
        # ⚠ num_feature_spins ALONE DOES NOTHING. freespin_triggers is DERIVED from
        # it inside GameConfig.__init__ (game_config.py:179-184) and is what the
        # engine actually awards from, so mutating the source dict after
        # construction is a silent no-op -- it returned byte-identical results for
        # 15/13/12/10 spins, which is how this was caught. Set both.
        config.num_feature_spins["ascendant"] = asc_spins
        asc_count = [c for c, t in config.scatter_tiers.items() if t == "ascendant"][0]
        for gametype in config.freespin_triggers:
            config.freespin_triggers[gametype][asc_count] = asc_spins
    if isolate_ascendant:
        bm = [b for b in config.bet_modes if b.get_name() == MODE][0]
        keep = [d for d in bm.get_distributions() if d.get_criteria() == "ascendant"]
        keep[0]._quota = 1.0
        bm._distributions = keep
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


def summarise(mode, cap):
    """Natural (unforced) stats for one mode's books."""
    pays, roams, lit = [], [], []
    with open(os.path.join(GO_BOOKS, f"books_{mode}.jsonl.zst"), "rb") as fh:
        reader = zstd.ZstdDecompressor().stream_reader(fh)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            b = json.loads(line)
            pays.append(b["payoutMultiplier"] / 100.0)
            roams.append(sum(1 for e in b["events"] if e["type"] == "beastRoam"))
            dealt = [e for e in b["events"] if e["type"] == "constellationDealt"]
            lit.append(dealt[0]["litCount"] if dealt else 0)
    n = len(pays)
    roamed = [r for r in roams if r]
    at_cap = sum(1 for p in pays if p >= cap)
    return {
        "mean": statistics.fmean(pays),
        "median": statistics.median(pays),
        "max": max(pays),
        # completion == the beast woke at all == there was a roam
        "complete": len(roamed) / n * 100,
        "roam": statistics.fmean(roamed) if roamed else 0.0,
        "at_cap": at_cap / n * 100,
        # "1 in N" is what a forced slice actually cares about
        "cap_one_in": (n / at_cap) if at_cap else float("inf"),
        "lit": lit[0] if lit else 0,
    }


if __name__ == "__main__":
    nsims = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    os.chdir(GAME)
    from game_config import GameConfig

    cfg = GameConfig()
    cost = {m.get_name(): m.get_cost() for m in cfg.bet_modes}[MODE]
    rtp, cap = cfg.rtp, cfg.wincap
    ticket = rtp * cost

    shutil.copy2(CONFIG, CONFIG_BAK)
    try:
        # --- the three purchasable tiers, measured once (their tables do not move)
        print(f"n={nsims:,}/run   buy_mystery cost {cost:,.0f}x   rtp {rtp}   "
              f"cap {cap:,.0f}x\n")
        print("baseline: natural tier means (wincap stripped)")
        export_with(None, isolate_ascendant=False)
        base_mean = {}
        for tier, mode in TIER_MODE.items():
            run_mode(mode, nsims)
            r = summarise(mode, cap)
            base_mean[tier] = r["mean"]
            print(f"  {tier:10s} mean {r['mean']:>8,.1f}x   complete {r['complete']:>5.1f}%"
                  f"   roam {r['roam']:>4.2f}   max {r['max']:>9,.0f}x")
        fixed = sum(MIX[t] * base_mean[t] for t in base_mean)
        print(f"  -> the three purchasable tiers contribute {fixed:,.1f}x of the "
              f"mode's raw mean\n")

        # --- ascendant, one run per star table
        header = (f"{'variant':14s}{'star':>6}{'mean':>10}{'complete':>10}{'roam':>7}"
                  f"{'at cap':>9}{'cap 1 in':>10}{'max':>10}{'richness':>10}")
        print(header)
        print("-" * len(header))
        for name, table in VARIANTS.items():
            export_with(table, isolate_ascendant=True)
            run_mode(MODE, nsims)
            r = summarise(MODE, cap)
            mode_raw = fixed + MIX["ascendant"] * r["mean"]
            richness = mode_raw / ticket
            flag = "" if HEALTHY[0] <= richness <= HEALTHY[1] else "  <-- out of band"
            print(f"{name:14s}{mean_star(table):>6.2f}{r['mean']:>9,.0f}x"
                  f"{r['complete']:>9.1f}%{r['roam']:>7.2f}{r['at_cap']:>8.2f}%"
                  f"{r['cap_one_in']:>10,.0f}{r['max']:>9,.0f}x"
                  f"{richness:>10.2f}{flag}")

        # --- the competing lever: feature length, draco's table held
        print(f"\nfeature-spins arm (ascendant keeps draco's table; watch COMPLETION)")
        print(header.replace("variant", "spins  "))
        print("-" * len(header))
        for spins in SPIN_VARIANTS:
            export_with(None, isolate_ascendant=True, asc_spins=spins)
            run_mode(MODE, nsims)
            r = summarise(MODE, cap)
            mode_raw = fixed + MIX["ascendant"] * r["mean"]
            richness = mode_raw / ticket
            flag = "" if HEALTHY[0] <= richness <= HEALTHY[1] else "  <-- out of band"
            print(f"{str(spins) + ' spins':14s}{20.19:>6.2f}{r['mean']:>9,.0f}x"
                  f"{r['complete']:>9.1f}%{r['roam']:>7.2f}{r['at_cap']:>8.2f}%"
                  f"{r['cap_one_in']:>10,.0f}{r['max']:>9,.0f}x"
                  f"{richness:>10.2f}{flag}")
    finally:
        shutil.move(CONFIG_BAK, CONFIG)
        print(f"\nrestored {CONFIG}")
