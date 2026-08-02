"""Export books from the production pool into the web-sdk Storybook harness.

Storybook replays real books through the real game component with no RGS, which is
the whole playtest loop. Random books are near-useless for that though -- a base
book is a dead spin 71% of the time and you will never randomly see a woken Draco.
So this exports the CURATED reviewer scenarios (max win, a beast waking, a feature
that never completes, a last-spin completion riding the roam floor...) and pins each
one to a known index, then tops up with a random sample for general feel.

    ./env/bin/python games/starwake/export_story_books.py                 # all modes
    ./env/bin/python games/starwake/export_story_books.py base buy_draco  # some modes
    ./env/bin/python games/starwake/export_story_books.py --sample 400

Writes, per mode, into web-sdk/apps/starwake/src/stories/data/:
    <mode>_books.ts      the book array
    <mode>_scenarios.ts  {scenario name -> index into that array}
"""

import argparse
import io
import json
import os
import random
import re
import sys

import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "library", "publish_files")
SCENARIOS = os.path.join(HERE, "reviewer_scenarios.json")
DEST_DEFAULT = os.path.abspath(
    os.path.join(HERE, "..", "..", "..", "web-sdk", "apps", "starwake", "src", "stories", "data")
)
MODES = ["base", "ante_starfall", "buy_corvus", "buy_ursa", "buy_draco", "buy_mystery"]


def scenario_ids(mode):
    """{book id -> scenario name} for one mode, first scenario wins on collision."""
    if not os.path.exists(SCENARIOS):
        return {}
    data = json.load(open(SCENARIOS))["modes"].get(mode, {})
    out = {}
    for name, body in data.items():
        for i, book in enumerate(body.get("books", [])):
            key = name if i == 0 else f"{name}_{i + 1}"
            out.setdefault(book["id"], key)
    return out


def read_books(mode, wanted, sample, seed=42):
    """Stream the compressed tape once, keeping wanted ids + a reservoir sample.

    The buy tapes are ~2.8 GB compressed and a book is ~34 KB of JSON, so this
    rejects non-candidate lines on a cheap id-prefix regex before ever calling
    json.loads -- the same trick find_books.py uses.
    """
    path = os.path.join(LIB, f"books_{mode}.jsonl.zst")
    if not os.path.exists(path):
        print(f"  !! {path} not found -- run the sims for {mode} first")
        return {}, []
    id_re = re.compile(rb'^\{"id":\s*(\d+)')
    rng = random.Random(seed)
    hits, reservoir, seen = {}, [], 0
    dctx = zstandard.ZstdDecompressor()
    with open(path, "rb") as fh:
        stream = io.TextIOWrapper(dctx.stream_reader(fh), encoding="utf-8")
        for line in stream:
            m = id_re.match(line.encode("utf-8", "ignore"))
            bid = int(m.group(1)) if m else None
            take = bid in wanted
            if take:
                hits[bid] = json.loads(line)
            if sample:
                seen += 1
                if len(reservoir) < sample:
                    reservoir.append(line if not take else None)
                else:
                    j = rng.randrange(seen)
                    if j < sample:
                        reservoir[j] = line if not take else None
    parsed = [json.loads(x) for x in reservoir if x]
    return hits, parsed


def write_mode(mode, dest, sample):
    wanted = scenario_ids(mode)
    print(f"{mode}: {len(wanted)} scenario books + {sample} random")
    hits, extra = read_books(mode, set(wanted), sample)
    if not hits and not extra:
        return False

    # scenarios first so their index is stable and greppable
    ordered = [hits[i] for i in wanted if i in hits]
    index = {wanted[i]: n for n, i in enumerate(x for x in wanted if x in hits)}
    ordered += extra

    banner = (
        f"// GENERATED -- {mode} books for Storybook playtesting.\n"
        f"// Regenerate: ./env/bin/python games/starwake/export_story_books.py {mode}\n"
        f"// {len(index)} curated scenario books (indices 0-{len(index)-1}), "
        f"then {len(extra)} random.\n"
    )
    with open(os.path.join(dest, f"{mode}_books.ts"), "w") as fh:
        fh.write(banner + "export default " + json.dumps(ordered, indent=1) + ";\n")
    with open(os.path.join(dest, f"{mode}_scenarios.ts"), "w") as fh:
        fh.write(
            f"// GENERATED -- scenario name -> index into {mode}_books.ts\n"
            "export default " + json.dumps(index, indent=1) + ";\n"
        )
    missing = [n for i, n in wanted.items() if i not in hits]
    if missing:
        print(f"  (not found in tape: {', '.join(missing)})")
    print(f"  wrote {len(ordered)} books, {len(index)} named scenarios")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modes", nargs="*", default=None)
    ap.add_argument("--sample", type=int, default=250, help="extra random books per mode")
    ap.add_argument("--dest", default=DEST_DEFAULT)
    args = ap.parse_args()

    os.makedirs(args.dest, exist_ok=True)
    targets = args.modes or MODES
    bad = [m for m in targets if m not in MODES]
    if bad:
        sys.exit(f"unknown mode(s): {bad}. valid: {MODES}")

    print(f"dest: {args.dest}\n")
    ok = sum(write_mode(m, args.dest, args.sample) for m in targets)
    print(f"\n{ok}/{len(targets)} modes exported")


if __name__ == "__main__":
    main()
