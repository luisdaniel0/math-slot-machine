"""
Enumerate the beast multiplier values act two can actually pay.

WHY THIS EXISTS. The rules screen must "list all obtainable values" for special
symbols, and the design doc points that requirement at
`constellation_mult_ladders`. That ladder is DEAD -- act two replaced it with star
collection on Aug 5 2026 and `ActTwo()` is true in every tier, so the ladder branch
is unreachable everywhere (see the Aug 13 entry at the top of CLAUDE.md). Publishing
it would advertise multipliers the engine cannot pay, which is the exact failure
config.go:168 already records having shipped once:

    "rungs were set to featureSpins-1, a depth needing a spin-1 completion, so ursa
     and draco advertised multipliers no player could ever be paid."

WHAT ACT TWO ACTUALLY PAYS. constellation.go:412 --

    multiplier = 1 + collected            collected = sum of every star value taken

So the obtainable set is not a hand-written list, it is the reachable sums of the
tier's star table, shifted by one. Two consequences the rules screen needs:

  - **x2 IS UNOBTAINABLE.** It needs collected == 1 and the smallest star is 2.
    The set starts at 1 (no stars) and resumes at 3.
  - **EVERYTHING FROM x3 UP IS DENSE.** Every tier's table contains both 2 and 3,
    and {2,3} generates every integer >= 2 as a sum, so there are no holes between
    x3 and the tier's ceiling. The published set is a RANGE, not a list.

That leaves exactly one thing to measure, which is what this tool does: the CEILING.

⚠ THIS REPORTS TWO CEILINGS AND THEY ARE NOT THE SAME NUMBER. The combinatorial
bound (max stars per board x collecting spins x top star value) is what the config
permits; the observed ceiling is what a 1e6 pool actually reached. The bound is ~20x
the observation because it needs every reel window packed AND every star rolling its
top value. PUBLISH NEITHER BLINDLY -- the bound re-runs the old sin of advertising
unreachable values, and the observation is a sample, not a limit. The defensible
rules-screen claim is the RULE ("1 plus the sum of the stars collected") plus the
star value table, which IS exact and IS short.

Usage:
    ./env/bin/python games/starwake/enumerate_multipliers.py [--limit N] [pool_dir]

Reads books, not the LUT: the multiplier is an event property and never appears in
a payout column.
"""

import argparse
import io
import json
import os
import sys
from collections import defaultdict

import zstandard as zstd

DEFAULT_POOL = "go/out/library/publish_files"
CONFIG = "go/config/starwake.json"
MODES = ["base", "ante_starfall", "buy_corvus", "buy_ursa", "buy_draco", "buy_mystery"]


def star_tables(cfg):
    """The per-tier star value tables, plus corvus's ascension table."""
    out = {}
    for name, tier in cfg["gameSpecific"]["tiers"].items():
        drops = tier.get("starDrops")
        if not drops:
            continue
        out[name] = {
            "values": {v["value"]: v["weight"] for v in drops["values"]},
            "spins": tier["featureSpins"],
            "ascension": (
                {v["value"]: v["weight"] for v in drops["ascension"]["values"]}
                if drops.get("ascension")
                else None
            ),
        }
    return out


def max_stars_per_board(cfg, star_sym="M"):
    """Most stars a single roam board can show, per roam strip.

    The block never lands on reel 0 of either strip, so this is a sum over reels of
    the densest 4-row window -- the strips are read as cyclic, which is how the
    engine windows them.
    """
    reels_dir = os.path.join(os.path.dirname(CONFIG), "..", "..", "games", "starwake", "reels")
    out = {}
    for key in ("ROAM", "ROAMCAP"):
        fname = cfg["reels"].get(key)
        if not fname:
            continue
        path = os.path.normpath(os.path.join(reels_dir, fname))
        if not os.path.exists(path):
            continue
        rows = [line.rstrip("\n").split(",") for line in open(path) if line.strip()]
        ncol = max(len(r) for r in rows)
        total = 0
        per_reel = []
        for reel in range(ncol):
            strip = [r[reel] for r in rows if len(r) > reel and r[reel]]
            n = len(strip)
            best = max(
                sum(1 for k in range(4) if strip[(i + k) % n] == star_sym) for i in range(n)
            )
            per_reel.append(best)
            total += best
        out[key] = {"total": total, "per_reel": per_reel}
    return out


def scan(path, limit=None):
    """Per-tier multiplier observations from one book pool."""
    seen = defaultdict(set)
    books = defaultdict(int)
    peak = {}
    with open(path, "rb") as fh:
        stream = io.TextIOWrapper(
            zstd.ZstdDecompressor().stream_reader(fh), encoding="utf-8"
        )
        for i, line in enumerate(stream):
            if limit and i >= limit:
                break
            book = json.loads(line)
            tier = None
            ascended = False
            for ev in book["events"]:
                t = ev.get("type")
                if t == "constellationDealt":
                    tier = ev["tier"]
                elif t == "constellationAscend":
                    ascended = True
                elif t == "starsCollected":
                    key = f"{tier}+asc" if ascended else tier
                    seen[key].add(ev["multiplier"])
                    if ev["multiplier"] > peak.get(key, (0, None))[0]:
                        peak[key] = (ev["multiplier"], book["id"])
            if tier:
                books[f"{tier}+asc" if ascended else tier] += 1
    return seen, books, peak


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pool", nargs="?", default=DEFAULT_POOL)
    ap.add_argument("--limit", type=int, default=None, help="books per pool (default: all)")
    args = ap.parse_args()

    cfg = json.load(open(CONFIG))
    tables = star_tables(cfg)
    boards = max_stars_per_board(cfg)

    print("=" * 79)
    print("STAR VALUES -- the enumerable table, and the one the rules screen should carry")
    print("=" * 79)
    for name, t in tables.items():
        vals = t["values"]
        tot = sum(vals.values())
        pretty = "  ".join(f"x{v}:{w/tot:5.1%}" for v, w in sorted(vals.items()))
        print(f"  {name:11} spins={t['spins']:>3}  {pretty}")
        if t["ascension"]:
            atot = sum(t["ascension"].values())
            ap_ = "  ".join(f"x{v}:{w/atot:5.1%}" for v, w in sorted(t["ascension"].items()))
            print(f"  {'':11} ascended   {ap_}")

    print()
    print("=" * 79)
    print("COMBINATORIAL CEILING -- what the config permits, NOT what to publish")
    print("=" * 79)
    for key, b in boards.items():
        print(f"  {key:8} max stars on one board = {b['total']:>3}  per reel {b['per_reel']}")
    dense = max(b["total"] for b in boards.values()) if boards else 0
    print()
    for name, t in tables.items():
        # Stars are rolled only once the beast is roaming, so the completing spin
        # itself collects nothing: at most featureSpins-1 collecting spins.
        spins = t["spins"] - 1
        top = max(t["values"])
        print(
            f"  {name:11} <= {spins:>2} collecting spins x {dense} stars x x{top:<3}"
            f" = collected {spins*dense*top:>6,}  -> multiplier x{spins*dense*top+1:,}"
        )

    print()
    print("=" * 79)
    print(f"OBSERVED -- pool at {args.pool}")
    print("=" * 79)
    agg = defaultdict(set)
    agg_books = defaultdict(int)
    agg_peak = {}
    for mode in MODES:
        path = os.path.join(args.pool, f"books_{mode}.jsonl.zst")
        if not os.path.exists(path):
            print(f"  {mode:15} MISSING")
            continue
        seen, books, peak = scan(path, args.limit)
        parts = []
        for tier in sorted(seen):
            agg[tier] |= seen[tier]
            agg_books[tier] += books[tier]
            if peak[tier][0] > agg_peak.get(tier, (0, None))[0]:
                agg_peak[tier] = peak[tier]
            parts.append(f"{tier} max x{max(seen[tier]):,}")
        print(f"  {mode:15} {'  '.join(parts) if parts else '(no act two rounds)'}")
        sys.stdout.flush()

    print()
    print(f"  {'tier':12} {'rounds':>9} {'distinct':>9} {'observed set':>22}   peak book")
    for tier in sorted(agg):
        s = agg[tier]
        lo, hi = min(s), max(s)
        holes = sum(1 for v in range(lo, hi + 1) if v not in s)
        print(
            f"  {tier:12} {agg_books[tier]:>9,} {len(s):>9,} "
            f"{'x1, x' + str(lo) + '..x' + format(hi, ','):>22}   "
            f"id {agg_peak[tier][1]} ({holes:,} unsampled in range)"
        )

    print()
    print("  x2 obtainable anywhere:", any(2 in s for s in agg.values()), "(expected: False)")
    print("  x1 is the pre-collection state and is always obtainable.")


if __name__ == "__main__":
    main()
