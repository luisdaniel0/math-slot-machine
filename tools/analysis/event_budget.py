"""Outcome count, event count and file size per mode, against the RGS publish limits.

LIMITS, settled Aug 7 2026 with the Stake Engine team:
  OUTCOMES per mode   10,000,000   Happle (RGS), thread "10 mil outcomes per mode limit":
                                   "modes must not exceed 10 million outcomes".
  FILE SIZE per mode        3.14GB Taylor (RGS). The published docs say 4.2GB. USE 3.14.

⚠ THE DOCS WORD THE FIRST LIMIT AS "no game mode can contain more than 10,000,000 EVENTS"
AND THAT IS A TRAP. Read literally it counts events inside books, which would make the
same page's own advice ("run 100,000-1,000,000 simulations") impossible for any slot with
more than 10 events per round -- i.e. all of them. It counts OUTCOMES. This script prints
both so the distinction stays visible.

Events per book still matter, but as a FILE SIZE input, not a compliance limit.

    env/bin/python tools/analysis/event_budget.py <publish_files_dir>
"""
import io
import json
import os
import sys

import zstandard as zstd

OUTCOME_CAP = 10_000_000
FILE_CAP_GB = 3.14


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pub = sys.argv[1]
    with open(os.path.join(pub, "index.json"), encoding="UTF-8") as f:
        modes = [m["name"] for m in json.load(f)["modes"]]

    print("%-16s %12s %8s %13s %10s %9s %8s" % (
        "mode", "outcomes", "% cap", "events", "ev/book", "file", "% cap"))
    for mode in modes:
        path = os.path.join(pub, "books_%s.jsonl.zst" % mode)
        if not os.path.exists(path):
            print("%-16s  (no books file)" % mode)
            continue
        size_gb = os.path.getsize(path) / (1024 ** 3)
        n = ev = 0
        f = open(path, "rb")
        reader = zstd.ZstdDecompressor(max_window_size=2 ** 31).stream_reader(f)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            n += 1
            ev += line.count("\"type\":")   # cheap: one per event, no JSON parse
        flag = "  OVER" if n > OUTCOME_CAP or size_gb > FILE_CAP_GB else ""
        print("%-16s %12s %7.1f%% %13s %10.1f %8.2fGB %7.1f%%%s" % (
            mode, format(n, ","), 100.0 * n / OUTCOME_CAP, format(ev, ","),
            ev / n if n else 0, size_gb, 100.0 * size_gb / FILE_CAP_GB, flag))

    print()
    print("  The OUTCOME column is the compliance limit. The EVENT column is not a limit;")
    print("  it drives file size, which is where a feature-heavy game actually runs out.")


if __name__ == "__main__":
    main()
