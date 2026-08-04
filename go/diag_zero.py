"""Find a zero-paying book and dump its event tape.

Buy modes must never pay zero (CLAUDE.md: "ours is structural -- any lit star
pays"), so a zero book in a buy pool is a divergence, not a rare outcome.
"""
import io
import json
import sys
from collections import Counter

import zstandard as zstd


def books(path, limit):
    with open(path, "rb") as f:
        r = zstd.ZstdDecompressor(max_window_size=2**31).stream_reader(f)
        for i, line in enumerate(io.TextIOWrapper(r, encoding="utf-8")):
            if i >= limit:
                return
            yield json.loads(line)


def main():
    path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 200000
    want_zero = "--zero" in sys.argv

    scanned = 0
    for b in books(path, limit):
        scanned += 1
        if want_zero and b["payoutMultiplier"] != 0:
            continue
        types = [e["type"] for e in b["events"]]
        print(f"id={b['id']} payout={b['payoutMultiplier']} criteria={b.get('criteria')} "
              f"events={len(b['events'])}")
        print(" ", dict(Counter(types)))
        for e in b["events"]:
            t = e["type"]
            if t in ("freeSpinTrigger", "constellationDealt", "starLit", "beastWake",
                     "updateFreeSpin", "freeSpinEnd", "finalWin", "winInfo"):
                s = json.dumps(e)
                print("   ", s[:220])
        return
    print(f"no matching book in {scanned} scanned")


if __name__ == "__main__":
    main()
