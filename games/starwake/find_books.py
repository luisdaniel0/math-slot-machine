"""Reviewer-scenario book finder for Starwake.

A reviewer asks to WATCH something -- "show me a Draco Ascendant that wakes and
rides the ladder to the top", "show me a max win", "show me a feature that never
completes" -- and what they need back is a BOOK ID they can replay. This turns a
scenario description into ids.

WHY NOT utils/search_tool/forcetool_ids.py ALONE. That tool covers force-record key
matching well and this module reuses its matching rule, but it cannot answer a
Starwake scenario on its own:
  - it only sees the force record's LINE-WIN keys (gametype/kind/mult/symbol). Our
    signature mechanic lives in custom events -- constellationDealt / starLit /
    beastWake / beastRoam / multiplierClimb -- which the force record never indexes.
    "The beast woke" and "it never completed" are event questions, not win-key ones.
  - its find_payout_range_ids MIN branch filters `line_val < min_payout`, i.e. it
    returns payouts BELOW the minimum -- the opposite of what the name promises.
    Payout filtering here is implemented directly instead.
  - it defaults to lookup_tables/lookUpTable_<mode>.csv, the UNWEIGHTED pre-optimizer
    table. A scenario is only real if the optimizer left it reachable, so this reads
    publish_files/lookUpTable_<mode>_0.csv and defaults to requiring weight > 0.
  - it json.loads the whole force record. buy_draco's is 603 MB and expands to
    several GB of Python objects; the memory gotcha in CLAUDE.md is a VM that died
    exactly this way. Records are streamed entry by entry here.

THREE SOURCES, CHEAPEST FIRST -- an event scan only ever runs on ids that already
survived the cheap filters, and stops as soon as it has enough:
  publish_files/lookUpTable_<mode>_0.csv      id -> weight, payout   (always)
  lookup_tables/lookUpTableSegmented_<mode>   id -> criteria (tier)  (always)
  forces/force_record_<mode>.json             search keys -> ids     (--key)
  publish_files/books_<mode>.jsonl.zst        the event tape         (event filters)

PICK THE RIGHT NARROWING FOR A RARE SCENARIO. An event scan must walk the tape, so
it is only cheap when the thing sought is COMMON among the candidates (completions,
non-completions, roam-floor books -- all tens of percent). For something rare, narrow
with the force record first: a top ladder rung is recorded as `mult=<rung>`, so
`--key mult=600` finds the dragon's top rung directly instead of parsing a million
books hunting one. The scenario pack does this automatically.

USAGE
  ./../../env/bin/python find_books.py --scenarios buy_mystery
  ./../../env/bin/python find_books.py buy_draco --criteria wincap --limit 3
  ./../../env/bin/python find_books.py buy_ursa --key mult=500 --limit 5
  ./../../env/bin/python find_books.py base --key symbol=W --key kind=5 --min-payout 500
  ./../../env/bin/python find_books.py buy_mystery --tier ascendant --woke --json out.json
"""

import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game_config import GameConfig

EVENT_TYPES = ("constellationDealt", "starLit", "beastWake", "beastRoam", "multiplierClimb")
_ID_RE = re.compile(r'^\{"id":\s*(\d+)')


# --------------------------------------------------------------------------- io


def _lut_path(cfg, mode):
    return os.path.join(cfg.library_path, "publish_files", f"lookUpTable_{mode}_0.csv")


def _seg_path(cfg, mode):
    return os.path.join(cfg.library_path, "lookup_tables", f"lookUpTableSegmented_{mode}.csv")


def _force_path(cfg, mode):
    return os.path.join(cfg.library_path, "forces", f"force_record_{mode}.json")


def _books_path(cfg, mode):
    return os.path.join(cfg.library_path, "publish_files", f"books_{mode}.jsonl.zst")


def load_lut(cfg, mode):
    """id -> (weight, payout in base-bet multiples). The LUT stores payout*100."""
    out = {}
    with open(_lut_path(cfg, mode), encoding="UTF-8") as f:
        for line in f:
            i, w, p = line.split(",")
            out[int(i)] = (float(w), float(p) / 100.0)
    return out


def load_criteria(cfg, mode):
    """id -> criteria string (the optimizer fence that owns the book: tier, wincap, ...)."""
    out = {}
    with open(_seg_path(cfg, mode), encoding="UTF-8") as f:
        for line in f:
            parts = line.rstrip("\n").split(",")
            out[int(parts[0])] = parts[1]
    return out


def stream_force_entries(path):
    """Yield each {"search": [...], "bookIds": [...]} of a force record without
    materialising the file.

    The record is written by json.dumps(indent=4) as a list of flat objects, so
    tracking brace depth line by line brackets one entry exactly. Search values are
    symbol names and numbers -- never braces -- so counting characters is safe here.
    Peak memory is one entry rather than the whole 600 MB file.
    """
    depth = 0
    buf = []
    with open(path, encoding="UTF-8") as f:
        for line in f:
            opens, closes = line.count("{"), line.count("}")
            if depth == 0 and opens == 0:
                continue  # the enclosing list's own brackets
            buf.append(line)
            depth += opens - closes
            if depth == 0 and buf:
                text = "".join(buf).rstrip().rstrip(",")
                buf = []
                yield json.loads(text)


def force_key_match(cfg, mode, keysets):
    """One pass over the force record resolving MANY key-sets at once.

    `keysets` is a list of {name: value} dicts; returns a list of id-sets in the same
    order. Batching matters: the scenario pack asks for one key-set per tier, and a
    pass over buy_draco's 603 MB record is ~30 s, so four passes would dominate the
    run. Matching rule is ForceTool.find_partial_key_match's -- a PARTIAL match, so
    {"symbol": "W"} returns every recorded W combination regardless of kind or mult.
    """
    found = [set() for _ in keysets]
    for entry in stream_force_entries(_force_path(cfg, mode)):
        rec = {d["name"]: str(d["value"]) for d in entry["search"]}
        for n, ks in enumerate(keysets):
            if all(rec.get(k) == v for k, v in ks.items()):
                found[n].update(int(i) for i in entry["bookIds"])
    return found


def scan_events(cfg, mode, candidates, predicate, limit, max_scan=None):
    """Stream the book tape in id order, testing `predicate` on ids in `candidates`.

    Two things keep this quick. Non-candidate lines are rejected on a regex over the
    line's first bytes, so they are never JSON-parsed -- the id is the first field.
    And books are written in id order, so the walk stops at the largest candidate id,
    at `limit` matches, or at `max_scan` books actually examined.
    """
    import zstandard as zstd

    hits, examined = [], 0
    if not candidates:
        return hits
    stop_after = max(candidates)
    with open(_books_path(cfg, mode), "rb") as fh:
        reader = zstd.ZstdDecompressor().stream_reader(fh)
        for line in io.TextIOWrapper(reader, encoding="UTF-8"):
            m = _ID_RE.match(line)
            if m is None:
                continue
            bid = int(m.group(1))
            if bid > stop_after:
                break
            if bid not in candidates:
                continue
            book = json.loads(line)
            examined += 1
            if predicate(book):
                hits.append(book)
                if limit and len(hits) >= limit:
                    break
            if max_scan and examined >= max_scan:
                break
    return hits


# ------------------------------------------------------------------- predicates


def book_events(book, etype):
    return [e for e in book.get("events", []) if e.get("type") == etype]


def book_tier(book):
    """The dealt tier, or None if this book never entered the feature."""
    dealt = book_events(book, "constellationDealt")
    return dealt[0]["tier"] if dealt else None


def book_woke(book):
    return bool(book_events(book, "beastWake"))


def book_roam_spins(book):
    return len(book_events(book, "beastRoam"))


def book_max_mult(book):
    """Highest beast multiplier the book ever showed (0 if the beast never woke)."""
    mults = [e["multiplier"] for e in book_events(book, "beastRoam")]
    return max(mults) if mults else 0


def build_predicate(cfg, args):
    """Compose the event-level filters, or None when no book scan is needed."""
    ladders = cfg.constellation_mult_ladders
    needs = any([getattr(args, "event", None), getattr(args, "tier", None),
                 args.woke, args.no_woke, args.top_rung, args.prelit,
                 args.min_roam is not None, args.max_roam is not None])
    if not needs:
        return None

    def pred(book):
        if args.tier and book_tier(book) != args.tier:
            return False
        if args.event:
            present = {e.get("type") for e in book.get("events", [])}
            if not set(args.event).issubset(present):
                return False
        if args.woke and not book_woke(book):
            return False
        if args.no_woke and book_woke(book):
            return False
        if args.prelit:
            dealt = book_events(book, "constellationDealt")
            if not dealt or dealt[0].get("litCount", 0) <= 0:
                return False
        if args.min_roam is not None and book_roam_spins(book) < args.min_roam:
            return False
        if args.max_roam is not None and book_roam_spins(book) > args.max_roam:
            return False
        if args.top_rung:
            tier = book_tier(book)
            if tier is None:
                return False
            if book_max_mult(book) < ladders[tier][-1]:
                return False
        return True

    return pred


# ----------------------------------------------------------------------- search


def _describe(lut, crit, i, book=None):
    row = {"id": i, "payout": lut[i][1], "weight": lut[i][0], "criteria": crit.get(i)}
    if book is not None:
        row.update(tier=book_tier(book), woke=book_woke(book),
                   roamSpins=book_roam_spins(book), maxMultiplier=book_max_mult(book))
    return row


def search(cfg, mode, args, lut=None, crit=None):
    """Cheap filters first, then an event scan over whatever survives."""
    lut = lut if lut is not None else load_lut(cfg, mode)
    crit = crit if crit is not None else load_criteria(cfg, mode)

    ids = set(lut)
    if args.weighted:
        ids = {i for i in ids if lut[i][0] > 0}
    if args.criteria:
        ids = {i for i in ids if crit.get(i) == args.criteria}
    if args.min_payout is not None:
        ids = {i for i in ids if lut[i][1] >= args.min_payout}
    if args.max_payout is not None:
        ids = {i for i in ids if lut[i][1] <= args.max_payout}

    preresolved = getattr(args, "preresolved_ids", None)
    if preresolved is not None:
        ids &= preresolved
    elif args.key:
        keys = {}
        for kv in args.key:
            k, _, v = kv.partition("=")
            keys[k.strip()] = v.strip()
        ids &= force_key_match(cfg, mode, [keys])[0]

    predicate = build_predicate(cfg, args)
    if predicate is None:
        # No event question asked: rank by payout so the most watchable comes first.
        chosen = sorted(ids, key=lambda i: -lut[i][1])[: args.limit or None]
        return [_describe(lut, crit, i) for i in chosen]

    books = scan_events(cfg, mode, ids, predicate, args.limit,
                        getattr(args, "max_scan", None))
    rows = [_describe(lut, crit, b["id"], b) for b in books]
    rows.sort(key=lambda r: -r["payout"])
    return rows


# -------------------------------------------------------------------- scenarios


class _Spec:
    """A filter set shaped like parsed argv, so scenarios reuse search() unchanged."""

    def __init__(self, **kw):
        self.criteria = None
        self.min_payout = None
        self.max_payout = None
        self.key = None
        self.event = None
        self.tier = None
        self.woke = False
        self.no_woke = False
        self.prelit = False
        self.top_rung = False
        self.min_roam = None
        self.max_roam = None
        self.weighted = True
        self.limit = 2
        self.max_scan = 60000
        self.preresolved_ids = None
        for k, v in kw.items():
            setattr(self, k, v)


def scenarios_for(cfg, mode, crit_values):
    """The reviewer pack for one mode, as (name, description, spec) triples.

    Everything tier-dependent is DERIVED from game_config -- ladders, tiers, roam
    floor -- rather than written out, so a future economy re-tune cannot leave this
    file quietly advertising scenarios the math no longer produces.
    """
    bet = {b.get_name(): b for b in cfg.bet_modes}[mode]
    cap = float(bet.get_wincap())
    tiers = [t for t in cfg.constellation_mult_ladders if t in crit_values]
    floor = cfg.min_roam_spins

    specs = []
    if "wincap" in crit_values:
        specs.append(("max_win", f"pays the published ceiling ({cap:,.0f}x)",
                      _Spec(criteria="wincap", limit=3)))
    specs.append(("biggest_non_cap", "largest win strictly below the ceiling",
                  _Spec(max_payout=cap - 0.01, limit=3)))

    for t in tiers:
        top = cfg.constellation_mult_ladders[t][-1]
        # REACHING the top rung is an event question -- beastRoam carries the beast's
        # multiplier every spin -- and it is deliberately NOT the same question as
        # "a win was PAID at the top rung", which is `--key mult=<top>` against the
        # force record. The force record only logs a mult on a WINNING line, so a
        # beast can sit on the top rung for a spin that pays nothing and never appear
        # under that key. Measured on the shipped pool, ursa reaches 500x outside the
        # wincap fence but only ever PAYS at 500x inside it -- so keying on the rung
        # would report "no book found" for a rung the beast demonstrably reaches.
        # Not fenced on criteria either: the top rung lives mostly in the forced
        # wincap slice, whose books are still that tier on the tape (`tier` confirms
        # it, and separates draco from ascendant -- they share a ladder).
        specs.append((f"{t}_top_rung",
                      f"{t}: beast reaches its top ladder rung ({top}x)",
                      _Spec(tier=t, top_rung=True, limit=2, max_scan=250000)))
        specs.append((f"{t}_wakes",
                      f"{t}: constellation completes, beast wakes and roams",
                      _Spec(criteria=t, woke=True, limit=2)))
        specs.append((f"{t}_never_completes",
                      f"{t}: partial progress only -- the wild carpet still pays "
                      f"(the no-win-range-gap / ETL evidence)",
                      _Spec(criteria=t, no_woke=True, limit=2)))
        specs.append((f"{t}_roam_floor",
                      f"{t}: late completion held to the guaranteed {floor}-spin roam floor",
                      _Spec(criteria=t, woke=True, min_roam=floor, max_roam=floor, limit=2)))

    if "ascendant" in crit_values:
        specs.append(("ascendant_prelit",
                      "Draco Ascendant: dealt with cells already lit from spin one",
                      _Spec(criteria="ascendant", prelit=True, limit=2)))
    if "0" in crit_values:
        specs.append(("zero_pay", "a losing spin", _Spec(criteria="0", limit=1)))
    specs.append(("smallest_paying", "the dust end -- smallest non-zero payout",
                  _Spec(min_payout=0.0001, limit=1, _ascending=True)))
    return specs


def run_scenarios(cfg, mode, out_path=None):
    print(f"\n{'=' * 96}\nREVIEWER SCENARIOS -- {mode}\n{'=' * 96}")
    lut = load_lut(cfg, mode)
    crit = load_criteria(cfg, mode)
    specs = scenarios_for(cfg, mode, set(crit.values()))

    # One force pass for every key-based scenario in the pack (see force_key_match).
    keyed = [(name, s) for name, _desc, s in specs if s.key]
    if keyed:
        keysets = []
        for _, s in keyed:
            d = {}
            for kv in s.key:
                k, _, v = kv.partition("=")
                d[k.strip()] = v.strip()
            keysets.append(d)
        print(f"resolving {len(keysets)} force key-set(s) in one pass over the record ...")
        resolved = force_key_match(cfg, mode, keysets)
        for (_, s), ids in zip(keyed, resolved):
            s.preresolved_ids = ids
            s.key = None  # already resolved; do not re-read the record in search()

    results = {}
    for name, desc, spec in specs:
        if getattr(spec, "_ascending", False):
            cand = [i for i, (w, p) in lut.items() if w > 0 and p > 0]
            cand.sort(key=lambda i: lut[i][1])
            rows = [_describe(lut, crit, i) for i in cand[: spec.limit]]
        else:
            rows = search(cfg, mode, spec, lut=lut, crit=crit)
        results[name] = {"description": desc, "books": rows}
        print(f"\n{name}\n  {desc}")
        if not rows:
            print("  -- no book found --")
        for r in rows:
            extra = ""
            if "roamSpins" in r:
                extra = (f"  tier={r['tier']}  roam={r['roamSpins']}"
                         f"  maxMult={r['maxMultiplier']}x")
            print(f"    id={r['id']:<8} payout={r['payout']:>11,.2f}x"
                  f"  criteria={str(r['criteria']):<10}{extra}")

    if out_path:
        with open(out_path, "w", encoding="UTF-8") as f:
            json.dump({"mode": mode, "scenarios": results}, f, indent=2)
        print(f"\nwrote {out_path}")
    return results


# --------------------------------------------------------------------------- cli


def main():
    cfg = GameConfig()
    modes = [b.get_name() for b in cfg.bet_modes]

    ap = argparse.ArgumentParser(
        description="Find Starwake book ids for reviewer scenarios.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("USAGE")[-1])
    ap.add_argument("mode", nargs="?", help=f"bet mode: {', '.join(modes)}")
    ap.add_argument("--scenarios", metavar="MODE", nargs="?", const="__all__",
                    help="emit the curated reviewer pack (a mode name, or bare for all)")
    ap.add_argument("--criteria", help="optimizer fence / tier, e.g. draco, ascendant, wincap")
    ap.add_argument("--min-payout", type=float, help="base-bet multiples")
    ap.add_argument("--max-payout", type=float, help="base-bet multiples")
    ap.add_argument("--key", action="append",
                    help="force-record key, e.g. --key symbol=W --key kind=5 (repeatable, AND)")
    ap.add_argument("--event", action="append", choices=EVENT_TYPES,
                    help="book must contain this event type (repeatable, AND)")
    ap.add_argument("--tier", help="dealt tier from constellationDealt")
    ap.add_argument("--woke", action="store_true", help="beast woke")
    ap.add_argument("--no-woke", action="store_true", help="beast never woke")
    ap.add_argument("--prelit", action="store_true", help="dealt with cells already lit (ascendant)")
    ap.add_argument("--top-rung", action="store_true", help="beast reached its tier's top rung")
    ap.add_argument("--min-roam", type=int, help="at least this many roam spins")
    ap.add_argument("--max-roam", type=int, help="at most this many roam spins")
    ap.add_argument("--weighted", action="store_true", default=True,
                    help="only books the optimizer left reachable (default)")
    ap.add_argument("--any-weight", dest="weighted", action="store_false",
                    help="include zero-weight books")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--max-scan", type=int, default=200000,
                    help="give up after examining this many candidate books")
    ap.add_argument("--json", dest="json_out", help="write results to this path")
    args = ap.parse_args()

    if args.scenarios:
        targets = modes if args.scenarios == "__all__" else [args.scenarios]
        for m in targets:
            assert m in modes, f"unknown mode {m}; valid: {modes}"
        if len(targets) == 1:
            run_scenarios(cfg, targets[0], args.json_out)
            return
        combined = {m: run_scenarios(cfg, m) for m in targets}
        if args.json_out:
            with open(args.json_out, "w", encoding="UTF-8") as f:
                json.dump({"modes": combined}, f, indent=2)
            print(f"\nwrote {args.json_out}")
        missing = [(m, n) for m, r in combined.items()
                   for n, v in r.items() if not v["books"]]
        print(f"\n{'=' * 96}\nSCENARIOS WITH NO BOOK "
              f"({len(missing)} of {sum(len(r) for r in combined.values())})\n{'=' * 96}")
        for m, n in missing:
            print(f"  {m:<16} {n}")
        return

    assert args.mode, "specify a bet mode, or use --scenarios"
    assert args.mode in modes, f"unknown mode {args.mode}; valid: {modes}"
    rows = search(cfg, args.mode, args)
    print(f"{len(rows)} book(s)")
    for r in rows:
        extra = ""
        if "roamSpins" in r:
            extra = f"  tier={r['tier']}  roam={r['roamSpins']}  maxMult={r['maxMultiplier']}x"
        print(f"  id={r['id']:<8} payout={r['payout']:>11,.2f}x"
              f"  weight={r['weight']:<14,.0f} criteria={str(r['criteria']):<10}{extra}")
    if args.json_out:
        with open(args.json_out, "w", encoding="UTF-8") as f:
            json.dump({"mode": args.mode, "books": rows}, f, indent=2)
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
