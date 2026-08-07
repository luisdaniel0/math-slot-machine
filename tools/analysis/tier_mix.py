"""Delivered sub-outcome mix inside one mode, keyed on an event field. LUT-weighted.

For any mode that rolls between several inner outcomes -- Starwake's buy_mystery rolls
corvus/ursa/draco/ascendant -- this reports what the PLAYER actually gets: the roll mix,
each roll's share of payback, its completion rate and its max-win rate.

⚠ THIS IS A COMPLIANCE TOOL. If the game advertises the odds of each inner outcome, the
DISPLAYED MIX MUST BE THE DELIVERED MIX. The optimizer reweights books, so a mix that was
correct in the raw pool can drift. Measure it on the pool being shipped.

⚠ AN INNER OUTCOME IS NOT THE SAME PRODUCT AS THE STANDALONE MODE OF THE SAME NAME.
Measured Aug 2026: ursa completed 63.7% of the time inside buy_mystery and 34.7% bought
directly, because each mode spends its own budget differently. Do not let frontend copy
imply they are equivalent.

    env/bin/python tools/analysis/tier_mix.py <publish_files_dir> <mode> [event] [field]
                                                   (defaults: constellationDealt / tier)
"""
import io
import json
import os
import sys
from collections import defaultdict

import zstandard as zstd


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    pub, mode = sys.argv[1], sys.argv[2]
    event = sys.argv[3] if len(sys.argv) > 3 else "constellationDealt"
    field = sys.argv[4] if len(sys.argv) > 4 else "tier"

    weights = {}
    for line in open(os.path.join(pub, "lookUpTable_%s_0.csv" % mode), encoding="UTF-8"):
        parts = line.split(",")
        if len(parts) >= 3:
            weights[int(parts[0])] = int(parts[1])

    tw = 0
    w_by = defaultdict(int)
    pay_by = defaultdict(float)
    done_by = defaultdict(int)
    cap_by = defaultdict(int)
    mx = 0.0
    f = open(os.path.join(pub, "books_%s.jsonl.zst" % mode), "rb")
    reader = zstd.ZstdDecompressor(max_window_size=2 ** 31).stream_reader(f)
    books = []
    for line in io.TextIOWrapper(reader, encoding="utf-8"):
        book = json.loads(line)
        w = weights.get(book["id"], 0)
        if not w:
            continue
        pay = book.get("payoutMultiplier", 0) / 100.0
        mx = max(mx, pay)
        key, woke = None, False
        for e in book["events"]:
            if e["type"] == event and key is None:
                key = e.get(field)
            elif e["type"] == "beastWake":
                woke = True
        books.append((key, w, pay, woke))
        tw += w
        w_by[key] += w
        pay_by[key] += w * pay
        if woke:
            done_by[key] += w

    for key, w, pay, _ in books:
        if pay >= mx:
            cap_by[key] += w

    tot_pay = sum(pay_by.values())
    print("%s -- delivered mix by %s.%s (LUT-weighted). max win %s\n"
          % (mode, event, field, format(mx, ",.0f") + "x"))
    print("  %-14s %10s %14s %12s %16s" % ("outcome", "rolls", "payback share",
                                           "completion", "max-win rate"))
    for key in sorted(w_by, key=lambda k: -w_by[k]):
        w = w_by[key]
        cap = cap_by[key]
        print("  %-14s %9.3f%% %13.2f%% %11.1f%% %16s" % (
            key, 100.0 * w / tw, 100.0 * pay_by[key] / tot_pay,
            100.0 * done_by[key] / w,
            ("1 in " + format(w / cap, ",.0f")) if cap else "never"))
    print("\n  Compare the rolls column against whatever the game rules display.")


if __name__ == "__main__":
    main()
