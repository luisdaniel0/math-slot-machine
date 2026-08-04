"""Compare the EVENT SCHEMA of Go's books against Python's, key by key.

WHY THIS MATTERS MORE THAN THE MATH CHECKS. The events array is the frontend
contract: the web-sdk reads it to drive every animation. A Go book can be
math-perfect, pass every RGS check and every parity metric, and still break the
game if one event key is renamed, missing, or a different JSON type. No payout
check can see that.

So this walks both pools and, for every event `type`, records:
  - the set of keys that ever appear
  - the JSON type of each key
  - which keys are always present vs sometimes absent (omitempty hazards)

    env/bin/python go/schema_diff.py
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

REPO = Path(__file__).resolve().parents[1]
GO = REPO / "go" / "out" / "library" / "publish_files"
PY = REPO / "games" / "starwake" / "library" / "publish_files"


def jtype(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, list):
        if not v:
            return "list[]"
        return f"list[{jtype(v[0])}]"
    if isinstance(v, dict):
        return "obj{" + ",".join(sorted(v.keys())) + "}"
    return type(v).__name__


def scan(path, limit):
    """type -> {key: (types seen, count present)}, plus how many of each type."""
    keys = defaultdict(lambda: defaultdict(set))
    present = defaultdict(lambda: defaultdict(int))
    seen = defaultdict(int)
    book_keys = defaultdict(set)

    with open(path, "rb") as f:
        r = zstd.ZstdDecompressor(max_window_size=2**31).stream_reader(f)
        for i, line in enumerate(io.TextIOWrapper(r, encoding="utf-8")):
            if i >= limit:
                break
            b = json.loads(line)
            for k, v in b.items():
                book_keys[k].add(jtype(v))
            for e in b["events"]:
                t = e["type"]
                seen[t] += 1
                for k, v in e.items():
                    keys[t][k].add(jtype(v))
                    present[t][k] += 1
    return keys, present, seen, book_keys


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    problems = 0

    for mode in ("base", "buy_mystery"):
        gp, pp = GO / f"books_{mode}.jsonl.zst", PY / f"books_{mode}.jsonl.zst"
        if not gp.exists() or not pp.exists():
            print(f"{mode}: missing pool, skipping")
            continue

        print(f"\n{'='*72}\n{mode}  (first {limit:,} books of each)\n{'='*72}")
        gk, gpres, gseen, gbook = scan(gp, limit)
        pk, ppres, pseen, pbook = scan(pp, limit)

        # Book-level keys (id / payoutMultiplier / events are RGS-required).
        if set(gbook) != set(pbook):
            print(f"  !! book keys differ: go={sorted(gbook)} python={sorted(pbook)}")
            problems += 1
        else:
            print(f"  book keys OK: {sorted(gbook)}")

        only_go = set(gseen) - set(pseen)
        only_py = set(pseen) - set(gseen)
        if only_go:
            print(f"  !! event types only in Go:     {sorted(only_go)}")
            problems += 1
        if only_py:
            print(f"  !! event types only in Python: {sorted(only_py)}")
            problems += 1

        for t in sorted(set(gseen) & set(pseen)):
            gkeys, pkeys = set(gk[t]), set(pk[t])
            issues = []
            if gkeys - pkeys:
                issues.append(f"extra in Go: {sorted(gkeys - pkeys)}")
            if pkeys - gkeys:
                issues.append(f"MISSING in Go: {sorted(pkeys - gkeys)}")
            for k in sorted(gkeys & pkeys):
                gt, pt = gk[t][k], pk[t][k]
                # list[] vs list[obj] is just an empty-vs-populated sample, not a
                # type conflict -- only flag genuinely disjoint scalar types.
                gt2 = {x.split("[")[0] for x in gt}
                pt2 = {x.split("[")[0] for x in pt}
                if not (gt2 & pt2):
                    issues.append(f"{k}: go={sorted(gt)} python={sorted(pt)}")
                # A key Python always emits but Go sometimes omits is an
                # omitempty hazard -- the frontend may read it unconditionally.
                g_always = gpres[t][k] == gseen[t]
                p_always = ppres[t][k] == pseen[t]
                if p_always and not g_always:
                    issues.append(
                        f"{k}: Python always emits it, Go omits on "
                        f"{gseen[t]-gpres[t][k]}/{gseen[t]} events")

            if issues:
                problems += len(issues)
                print(f"  !! {t}")
                for i in issues:
                    print(f"       {i}")
            else:
                print(f"  OK {t:22s} {len(gkeys)} keys, {gseen[t]:,} events")

    print()
    if problems:
        print(f"SCHEMA: {problems} difference(s) -- review before trusting the frontend")
        return 1
    print("SCHEMA: Go and Python event tapes are structurally identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
