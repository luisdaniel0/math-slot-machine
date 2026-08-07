"""Per-mode benchmark table for any Stake Engine publish_files pool.

Reads modes AND costs from index.json, so it works on any game -- ours or a
competitor's downloaded pool -- with no per-game configuration.

⚠ EVERY NUMBER COMES FROM THE **OPTIMIZED** LUT (lookUpTable_<mode>_0.csv), never
the raw book pool. The pool is quota-shaped by construction: a bust rate or a
median read off it is meaningless.

    env/bin/python tools/analysis/pool_audit.py <publish_files_dir>
"""
import json
import math
import os
import sys


def load_lut(path):
    """(payout, weight) pairs from an optimized lookup table. Format: id,weight,payout*100."""
    rows = []
    total = 0
    for line in open(path, encoding="UTF-8"):
        parts = line.split(",")
        if len(parts) < 3:
            continue
        w = int(parts[1])
        rows.append((int(parts[2]) / 100.0, w))
        total += w
    return rows, total


def stats(rows, tw, cost):
    mean = sum(w * p for p, w in rows) / tw
    m2 = sum(w * p * p for p, w in rows) / tw
    std = math.sqrt(m2 - mean * mean)
    ordered = sorted(rows)
    acc, median = 0, 0.0
    for p, w in ordered:
        acc += w
        if acc >= tw / 2:
            median = p
            break

    def frac(pred):
        return sum(w for p, w in rows if pred(p)) / tw

    mx = max(p for p, _ in rows)
    cap = frac(lambda p: p >= mx)
    return {
        "rtp": mean / cost,
        "zero": 100.0 * frac(lambda p: p == 0),
        "median": median,
        "median_c": median / cost,
        "beat": 100.0 * frac(lambda p: p >= cost),
        "under25": 100.0 * frac(lambda p: p < 0.25 * cost),
        "max": mx,
        "ceil_c": mx / cost,
        "cap_rate": (1.0 / cap) if cap else 0.0,
        "std": std,
        "std_c": std / cost,
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pub = sys.argv[1]
    with open(os.path.join(pub, "index.json"), encoding="UTF-8") as f:
        modes = json.load(f)["modes"]

    print("pool: %s\n" % pub)
    hdr = ("mode", "cost", "RTP", "zero%", "median", "med/c", "beat%",
           "<.25x", "ceil/c", "std", "std/c", "max win 1 in")
    print("%-16s%8s%9s%8s%10s%8s%8s%8s%9s%9s%8s%15s" % hdr)
    for m in modes:
        lut = os.path.join(pub, "lookUpTable_%s_0.csv" % m["name"])
        if not os.path.exists(lut):
            print("%-16s  (no optimized LUT)" % m["name"])
            continue
        rows, tw = load_lut(lut)
        s = stats(rows, tw, float(m["cost"]))
        print("%-16s%7.1fx%9.4f%7.2f%%%10.2f%8.3f%7.1f%%%7.1f%%%9.1f%9.2f%8.2f%15s" % (
            m["name"], m["cost"], s["rtp"], s["zero"], s["median"], s["median_c"],
            s["beat"], s["under25"], s["ceil_c"], s["std"], s["std_c"],
            format(s["cap_rate"], ",.0f") if s["cap_rate"] else "never"))

    print()
    print("  ceil/c   = max win as a multiple of the ticket. Under a SHARED cap this")
    print("             necessarily falls as price rises -- competitors show the same.")
    print("  std/c    = cost-adjusted volatility; the only std dev comparable across modes.")
    print("  <.25x    = share of outcomes returning under a quarter of the ticket.")


if __name__ == "__main__":
    main()
