"""
Delivered tier frequencies, read the only way that means anything.

⚠ THE POOL CANNOT ANSWER THIS. buy_mystery's ascendant quota is 0.100 and corvus
ascension is oneIn 20,000 -- but a quota is a CONSTRUCTION target, and buy_corvus's
wincap slice sets forceAscension=True, so the raw pool over-represents ascension by
~60x. Frequencies must be weighted by the OPTIMIZED LUT, which is what the player
actually draws from.

Joins book id -> tier (from the books) against id -> weight (from the LUT).

Usage:
    ./env/bin/python games/starwake/tier_frequency.py [mode ...]
"""

import csv
import io
import json
import os
import sys
from collections import defaultdict

import zstandard as zstd

POOL = "go/out/library/publish_files"
LUT = "games/starwake_go/library/publish_files"


def tiers_by_id(mode):
    """id -> (tier, ascended) for every book that dealt a constellation."""
    path = os.path.join(POOL, f"books_{mode}.jsonl.zst")
    out = {}
    with open(path, "rb") as fh:
        stream = io.TextIOWrapper(
            zstd.ZstdDecompressor().stream_reader(fh), encoding="utf-8"
        )
        for line in stream:
            book = json.loads(line)
            tier = None
            asc = False
            for ev in book["events"]:
                t = ev.get("type")
                if t == "constellationDealt":
                    tier = ev["tier"]
                elif t == "constellationAscend":
                    asc = True
            if tier:
                out[book["id"]] = (tier, asc)
    return out


def main():
    modes = sys.argv[1:] or ["buy_mystery", "buy_corvus"]
    for mode in modes:
        lut = os.path.join(LUT, f"lookUpTable_{mode}_0.csv")
        if not os.path.exists(lut):
            print(f"{mode}: no optimized LUT at {lut}")
            continue
        tiers = tiers_by_id(mode)

        weight = defaultdict(float)
        payout = defaultdict(float)
        total = 0.0
        total_pay = 0.0
        for row in csv.reader(open(lut)):
            if len(row) < 3:
                continue
            bid, w, p = int(row[0]), float(row[1]), float(row[2]) / 100.0
            total += w
            total_pay += w * p
            tier, asc = tiers.get(bid, ("(no feature)", False))
            key = f"{tier}+ascended" if asc else tier
            weight[key] += w
            payout[key] += w * p

        print(f"\n=== {mode}   mean {total_pay/total:,.2f}x ===")
        print(f"  {'tier':18} {'delivered':>10} {'1 in':>10} {'% of RTP':>10}")
        for key in sorted(weight, key=lambda k: -weight[k]):
            f = weight[key] / total
            share = payout[key] / total_pay if total_pay else 0.0
            onein = f"{1/f:,.1f}" if f else "-"
            print(f"  {key:18} {f:>9.3%} {onein:>10} {share:>9.1%}")


if __name__ == "__main__":
    main()
