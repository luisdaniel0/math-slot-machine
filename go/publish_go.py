"""Produce a complete, shippable artifact set from the Go engine's pool.

Reuses the SDK's OWN publishing code (src/write_data/write_configs.py) rather
than reimplementing it in Go. Publishing runs once per pool and takes seconds --
there is nothing to gain from porting it, and a great deal to lose: config.json
carries a sha256 of every published file, and the RGS cross-checks the lookup
table's payout column against each book's payoutMultiplier.

⚠ WHY THIS FILE EXISTS AT ALL, rather than just calling generate_configs():
OutputFiles derives every path from PATH_TO_GAMES + config.game_id, but game_id
ALSO lands in published content ("gameID" in config_fe, and the fe config's own
filename). Pointing the publisher at the Go pool by renaming game_id would
therefore ship a game called "starwake_go". So the paths are redirected by
subclassing OutputFiles and game_id is left alone.

Three artifacts the Go engine does not emit, filled in here:
  force.json                        the per-mode index of searchable force keys
  event_config_<mode>.json          one example of each event type
  books_<mode>.verification.json    payout + file hashes

    env/bin/python go/publish_go.py
"""
import hashlib
import io
import json
import os
import pickle
import sys
from collections import defaultdict

import zstandard as zstd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "games", "starwake"))

from src.config.output_filenames import OutputFiles  # noqa: E402
from src.calculations.symbol import SymbolStorage  # noqa: E402
from src.write_data.write_configs import generate_configs  # noqa: E402
from src.write_data.write_data import get_sha_256  # noqa: E402

from game_config import GameConfig  # noqa: E402
from game_optimization import OptimizationSetup  # noqa: E402

# The optimizer already wrote its optimized lookup tables here.
LIBRARY = os.path.join(REPO, "games", "starwake_go", "library")
GO_OUT = os.path.join(REPO, "go", "out", "library")


class GoOutputFiles(OutputFiles):
    """OutputFiles rooted somewhere other than games/<game_id>/library.

    Only setup_output_directories is overridden; every downstream path
    (configs, books, forces, lookups) is derived from these, so redirecting the
    root redirects everything while leaving config.game_id -- and therefore the
    published gameID -- untouched.
    """

    def __init__(self, game_config, library_root):
        self._library_root = library_root
        super().__init__(game_config)

    def setup_output_directories(self):
        self.library_path = self._library_root
        self.temp_path = os.path.join(self.library_path, "temp_multi_threaded_files")
        self.config_path = os.path.join(self.library_path, "configs")
        self.force_path = os.path.join(self.library_path, "forces")
        self.book_path = os.path.join(self.library_path, "books")
        self.lookup_path = os.path.join(self.library_path, "lookup_tables")
        self.publish_path = os.path.join(self.library_path, "publish_files")
        self.optimization_path = os.path.join(self.library_path, "optimization_files")
        self.index_config_path = self.publish_path
        self.compressed_path = self.publish_path
        self.final_lookup_path = self.publish_path
        self.optimization_result_path = os.path.join(self.optimization_path, "trial_results")
        for p in ("library_path", "book_path", "compressed_path", "lookup_path",
                  "config_path", "force_path", "temp_path", "optimization_path",
                  "optimization_result_path", "publish_path"):
            self.check_folder_exists(getattr(self, p))


class GameStateShim:
    """The minimum surface generate_configs actually touches.

    It only ever reads .config, .output_files and .symbol_storage -- it never
    runs a simulation -- so a shim avoids constructing a real GameState (which
    would build a whole engine and reset RNG state) just to write JSON.
    """

    def __init__(self, config, output_files):
        self.config = config
        self.output_files = output_files
        names = set()
        for kind_sym in config.paytable:
            names.add(kind_sym[1])
        for prop in config.special_symbols:
            names.update(config.special_symbols[prop])
        self.symbol_storage = SymbolStorage(config, sorted(names))


def books(path):
    with open(path, "rb") as f:
        r = zstd.ZstdDecompressor(max_window_size=2**31).stream_reader(f)
        for line in io.TextIOWrapper(r, encoding="utf-8"):
            yield json.loads(line)


def stage_go_artifacts(modes):
    """Hard-link the Go engine's books into the publish tree.

    The optimizer already placed the optimized LUTs here; the books have to join
    them because config.json hashes them and index.json names them.
    """
    dst_dir = os.path.join(LIBRARY, "publish_files")
    os.makedirs(dst_dir, exist_ok=True)
    for mode in modes:
        name = f"books_{mode}.jsonl.zst"
        src, dst = os.path.join(GO_OUT, "publish_files", name), os.path.join(dst_dir, name)
        if not os.path.exists(src):
            raise SystemExit(f"missing Go books: {src}\nRun: go/sw all 1000000")
        if os.path.exists(dst):
            os.remove(dst)
        try:
            os.link(src, dst)
        except OSError:
            import shutil
            shutil.copy2(src, dst)


def write_force_json(modes, force_path):
    """force.json: per mode, every searchable key and the values it takes.

    ⚠ REBUILT FROM SCRATCH, never appended to. write_data.py's version reads the
    existing file and sets data[mode], so it can NEVER drop a mode -- which is
    how a stale `bonus` entry survived into a reviewer-facing artifact and made
    force.json advertise seven modes while index.json had six.
    """
    data = {}
    for mode in modes:
        record_path = os.path.join(force_path, f"force_record_{mode}.json")
        keys = defaultdict(set)
        with open(record_path, encoding="UTF-8") as f:
            for entry in json.load(f):
                for term in entry["search"]:
                    keys[str(term["name"])].add(str(term["value"]))
        data[mode] = {k: sorted(v) for k, v in keys.items()}

    with open(os.path.join(force_path, "force.json"), "w", encoding="UTF-8") as f:
        json.dump(data, f, indent=4)
    return data


def write_event_configs(modes, publish_path, config_path):
    """event_config_<mode>.json: one example instance of each event type.

    Auto-discovered from the books exactly as write_library_events does, so any
    event a future feature adds appears here with no registration step.
    """
    counts = {}
    for mode in modes:
        examples = {}
        path = os.path.join(publish_path, f"books_{mode}.jsonl.zst")
        for book in books(path):
            for event in book["events"]:
                t = event["type"]
                if t not in examples:
                    examples[t] = {k: v for k, v in event.items() if k != "index"}
            # The vocabulary saturates quickly; scanning the whole 1e6 pool to
            # re-find the same 14 types would cost minutes for nothing.
            if len(examples) >= 14 and book["id"] > 50000:
                break
        with open(os.path.join(config_path, f"event_config_{mode}.json"), "w",
                  encoding="UTF-8") as f:
            json.dump(examples, f, indent=4)
        counts[mode] = len(examples)
    return counts


def write_verification(modes, publish_path, lookup_path, config_path):
    """books_<mode>.verification.json: payout hash + file hash + entry count.

    ⚠ payout_hash is md5(pickle.dumps(list_of_ints)) -- PYTHON-SPECIFIC
    serialisation that Go cannot reproduce, which is the one concrete reason
    this step has to happen in Python rather than in the engine.

    Payouts are read from the unoptimized LUT in file order. That is id order,
    which is the order Python's per-thread sidecars merge in, so the hash agrees.
    """
    out = {}
    for mode in modes:
        lut = os.path.join(lookup_path, f"lookUpTable_{mode}.csv")
        payouts = []
        with open(lut, encoding="UTF-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    payouts.append(int(parts[2]))

        book_file = os.path.join(publish_path, f"books_{mode}.jsonl.zst")
        verification = {
            "payout_hash": hashlib.md5(pickle.dumps(payouts)).hexdigest(),
            "file_hash": get_sha_256(book_file),
            "num_entries": len(payouts),
        }
        with open(os.path.join(config_path, f"books_{mode}.verification.json"), "w",
                  encoding="UTF-8") as f:
            json.dump(verification, f, indent=2)
        out[mode] = len(payouts)
    return out


def verify(modes, output_files):
    """Cross-check the published set the way a reviewer would.

    Every one of these has been a real defect on this project: force.json naming
    a mode index.json did not, and config.json carrying a sha256 that no longer
    matched its file.
    """
    problems = []
    publish = output_files.publish_path
    config_path = output_files.config_path

    with open(os.path.join(publish, "index.json"), encoding="UTF-8") as f:
        index_modes = {m["name"] for m in json.load(f)["modes"]}
    with open(os.path.join(output_files.force_path, "force.json"), encoding="UTF-8") as f:
        force_modes = set(json.load(f))
    with open(os.path.join(config_path, "config.json"), encoding="UTF-8") as f:
        be = json.load(f)
    be_modes = {m["name"] for m in be["bookShelfConfig"]}

    if not (index_modes == force_modes == be_modes == set(modes)):
        problems.append(f"mode sets differ -- index={sorted(index_modes)} "
                        f"force={sorted(force_modes)} config={sorted(be_modes)}")

    # ⚠ THE STALE-LUT TRAP. A sim rewrites the books and the unoptimized LUT but
    # NOT the optimized one, so re-running a mode at a different count leaves an
    # optimized table whose book ids no longer exist. Every hash still matches
    # its own file, so a hash check cannot see it -- the pool is simply serving
    # weights for books that are not there. Compare the id spaces directly.
    for mode in modes:
        raw = os.path.join(output_files.lookup_path, f"lookUpTable_{mode}.csv")
        opt = os.path.join(publish, f"lookUpTable_{mode}_0.csv")
        if not (os.path.exists(raw) and os.path.exists(opt)):
            continue
        with open(raw, encoding="UTF-8") as f:
            raw_ids = sum(1 for line in f if line.strip())
        max_opt_id = -1
        with open(opt, encoding="UTF-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    max_opt_id = max(max_opt_id, int(parts[0]))
        if max_opt_id >= raw_ids:
            problems.append(
                f"{mode}: optimized LUT references book id {max_opt_id} but the pool "
                f"only has {raw_ids} books -- the optimized table is STALE, re-run "
                f"`sw optimize {mode}`")

    # Every sha256 in config.json must match the file it names.
    for entry in be["bookShelfConfig"]:
        for section in ("booksFile", "forceFile"):
            if section not in entry:
                continue
            rel, sha = entry[section].get("file"), entry[section].get("sha256")
            if not rel or not sha:
                continue
            for base in (publish, output_files.force_path):
                candidate = os.path.join(base, os.path.basename(rel))
                if os.path.exists(candidate):
                    if get_sha_256(candidate) != sha:
                        problems.append(f"{entry['name']}/{section}: sha256 mismatch on {rel}")
                    break
        for table in entry.get("tables", []):
            rel, sha = table.get("file"), table.get("sha256")
            if not rel or not sha:
                continue
            candidate = os.path.join(publish, os.path.basename(rel))
            if os.path.exists(candidate) and get_sha_256(candidate) != sha:
                problems.append(f"{entry['name']}: sha256 mismatch on {rel}")
    return problems


def main():
    config = GameConfig()
    OptimizationSetup(config)  # populates config.opt_params
    modes = [bm.get_name() for bm in config.bet_modes]

    output_files = GoOutputFiles(config, LIBRARY)
    gamestate = GameStateShim(config, output_files)

    print(f"publishing {len(modes)} modes from the Go pool")
    stage_go_artifacts(modes)

    for mode in modes:
        lut = os.path.join(output_files.publish_path, f"lookUpTable_{mode}_0.csv")
        if not os.path.exists(lut):
            raise SystemExit(f"no optimized LUT for {mode} -- run: go/sw optimize")

    write_force_json(modes, output_files.force_path)
    ev = write_event_configs(modes, output_files.publish_path, output_files.config_path)
    vf = write_verification(modes, output_files.publish_path,
                            output_files.lookup_path, output_files.config_path)
    print(f"  force.json, event configs ({min(ev.values())}-{max(ev.values())} types), "
          f"verification ({min(vf.values()):,} books min)")

    generate_configs(gamestate)
    print("  config.json, index.json, config_fe, math_config")

    problems = verify(modes, output_files)
    print()
    if problems:
        for p in problems:
            print(f"  !! {p}")
        print(f"PUBLISH: {len(problems)} problem(s)")
        return 1
    print(f"PUBLISH: consistent -- index, force and config all name the same "
          f"{len(modes)} modes, every sha256 matches its file")
    print(f"  {output_files.publish_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
