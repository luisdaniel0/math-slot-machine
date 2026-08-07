"""Split a mode's books on an EVENT PREDICATE and weight the halves by the LUT.

The generic form of "did the feature complete, and what did each half pay?". Point it at
whatever event marks the boundary -- for Starwake that is `beastWake`, which separates
act 1 (charge) from act 2 (roam).

Reports, LUT-WEIGHTED:
  - what fraction of DELIVERED probability reaches the event
  - mean payout before vs after it, over all books and over reaching books only
  - the share of payback that lands after the event

⚠ RAW-POOL AND DELIVERED COMPLETION ARE DIFFERENT NUMBERS AND THEY DISAGREE BADLY.
Starwake's raw pool showed 84/62/32 across tiers; weighted by the shipped LUT it was
90/35/30. A sim printout gives you the first; players experience the second. ALWAYS SAY
WHICH ONE YOU MEAN.

    env/bin/python tools/analysis/book_split.py <publish_files_dir> <mode> [event]
                                                                   (default: beastWake)
"""
import io
import json
import os
import sys

import zstandard as zstd


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    pub, mode = sys.argv[1], sys.argv[2]
    marker = sys.argv[3] if len(sys.argv) > 3 else "beastWake"

    with open(os.path.join(pub, "index.json"), encoding="UTF-8") as f:
        cost = next(float(m["cost"]) for m in json.load(f)["modes"] if m["name"] == mode)

    weights = {}
    for line in open(os.path.join(pub, "lookUpTable_%s_0.csv" % mode), encoding="UTF-8"):
        parts = line.split(",")
        if len(parts) >= 3:
            weights[int(parts[0])] = int(parts[1])

    tw = reach_w = 0
    before = after = 0.0
    before_r = after_r = 0.0
    f = open(os.path.join(pub, "books_%s.jsonl.zst" % mode), "rb")
    reader = zstd.ZstdDecompressor(max_window_size=2 ** 31).stream_reader(f)
    for line in io.TextIOWrapper(reader, encoding="utf-8"):
        book = json.loads(line)
        w = weights.get(book["id"], 0)
        if not w:
            continue
        tw += w
        seen = False
        b = a = 0.0
        for e in book["events"]:
            if e["type"] == marker:
                seen = True
            elif e["type"] == "setWin":
                amt = e.get("amount", 0) / 100.0
                if seen:
                    a += amt
                else:
                    b += amt
        before += w * b
        after += w * a
        if seen:
            reach_w += w
            before_r += w * b
            after_r += w * a

    tot = before + after
    print("%s  cost %gx   marker event: %s\n" % (mode, cost, marker))
    print("  reached %s (weighted)      %.1f%%" % (marker, 100.0 * reach_w / tw))
    print("  ALL BOOKS      before %9.2fx   after %9.2fx   AFTER SHARE %5.1f%%"
          % (before / tw, after / tw, 100.0 * after / tot if tot else 0))
    if reach_w:
        totr = before_r + after_r
        print("  REACHING ONLY  before %9.2fx   after %9.2fx   AFTER SHARE %5.1f%%"
              % (before_r / reach_w, after_r / reach_w,
                 100.0 * after_r / totr if totr else 0))
        print("  payoff when reached: %.2fx of the %gx ticket"
              % ((before_r + after_r) / reach_w / cost, cost))
        miss_w = tw - reach_w
        if miss_w:
            miss = (tot - before_r - after_r) / miss_w
            print("  consolation when NOT reached: %.2fx = %.2fx of ticket"
                  % (miss, miss / cost))

    print()
    print("  ⚠ CONSERVATION: reach_rate * payoff + (1-reach_rate) * consolation == RTP * cost.")
    print("    Everything is pinned but the split. You can have OFTEN-BUT-SMALLER or")
    print("    RARELY-BUT-BIGGER; 'often and bigger' does not exist.")


if __name__ == "__main__":
    main()
