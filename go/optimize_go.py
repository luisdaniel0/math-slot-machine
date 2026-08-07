"""Run the UNCHANGED Rust optimizer against the Go engine's output.

The whole point of this step is that the optimizer is not modified at all. It
reads a force record, an unoptimized lookup table and a math config, and writes
an optimized lookup table. If Go's artifacts are correct, the existing binary
converges on them exactly as it does on Python's.

⚠ IT RUNS AGAINST A SHADOW GAME DIRECTORY, games/starwake_go/, so nothing here
can touch games/starwake/library/ -- the converged production pool (~11 GB,
gitignored, protected by no branch). The optimizer WRITES into the game dir it is
pointed at, so pointing it at the real one would overwrite shipped lookup tables.

    env/bin/python go/optimize_go.py base
    env/bin/python go/optimize_go.py base ante_starfall buy_corvus ...
"""
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "games", "starwake"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import toml  # noqa: E402

from game_config import GameConfig  # noqa: E402
from game_optimization import OptimizationSetup  # noqa: E402
from src.write_data.write_configs import make_temp_math_config  # noqa: E402

# The shadow-tree OutputFiles and the minimal gamestate the config writers need
# both already exist for the publish step; sharing them keeps the two Go entry
# points from drifting apart, which is the exact disease this file just caught.
from publish_go import GameStateShim, GoOutputFiles  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GO_OUT = os.path.join(REPO, "go", "out", "library")
SHADOW = os.path.join(REPO, "games", "starwake_go", "library")
OPT_DIR = os.path.join(REPO, "optimization_program")
SETUP = os.path.join(OPT_DIR, "src", "setup.toml")

SHADOW_GAME = "starwake_go"


def stage(mode: str, config) -> None:
    """Copy Go's artifacts into the shadow game directory."""
    for sub in ("configs", "forces", "lookup_tables", "optimization_files", "publish_files"):
        os.makedirs(os.path.join(SHADOW, sub), exist_ok=True)

    write_math_config(config)

    for sub, name in (
        ("forces", f"force_record_{mode}.json"),
        ("lookup_tables", f"lookUpTable_{mode}.csv"),
    ):
        src = os.path.join(GO_OUT, sub, name)
        if not os.path.exists(src):
            raise SystemExit(f"missing Go artifact: {src}\nRun: go/run_modes.sh <sims> {mode}")
        dst = os.path.join(SHADOW, sub, name)
        # Hard link where possible -- a 1e6 force record is ~50 MB and these are
        # on one filesystem, so linking avoids a pointless copy.
        if os.path.exists(dst):
            os.remove(dst)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)


def write_math_config(config) -> None:
    """Generate the optimizer's math config from the LIVE game config.

    ⚠ THIS USED TO COPY games/starwake/library/configs/math_config.json AND THEN
    OVERWRITE ONLY bet_modes[].{cost,rtp,max_win} FROM THE LIVE CONFIG. `fences`
    and `dresses` rode along unchecked from whenever the Python side last
    published. On Aug 6 2026 that was found to have cost buy_corvus its three
    consolation bands (commit 5e9c59c) -- written, committed, and then silently
    discarded, because the copied Jul 31 file predated them. NOTHING LOOKED
    WRONG: the synced block still read cost 120 / max_win 9,000, so the shadow
    config appeared fresh while its dress list was six days stale.

    make_temp_math_config derives bet modes, fences AND dresses from
    config.opt_params in one pass -- the same source the copy was approximating.
    Generating removes the staleness class instead of patching one instance of it.

    ⚠ USE THE CALLER'S CONFIG, NEVER A FRESH GameConfig(). Constructing a second
    one here silently emptied config.opt_params in the caller, and write_setup
    then failed with "no opt_params for mode buy_corvus".
    """
    make_temp_math_config(GameStateShim(config, GoOutputFiles(config, SHADOW)))


def write_setup(config, mode: str, threads: int) -> None:
    """Build setup.toml for one mode, pointed at the shadow game."""
    params = None
    for name, obj in config.opt_params.items():
        if name == mode:
            params = dict(obj["parameters"])
    if params is None:
        raise SystemExit(f"no opt_params for mode {mode}")

    params["game_name"] = SHADOW_GAME
    params["path_to_games"] = "../games/"
    params["run_1000_batch"] = False
    params["bet_type"] = mode
    params["threads_for_fence_construction"] = threads
    params["threads_for_show_construction"] = threads

    with open(SETUP, "w", encoding="UTF-8") as f:
        toml.dump(params, f)


def report(mode: str, cost: float) -> None:
    """Read the optimized LUT and print what a player would actually see.

    ⚠ The RAW book pool is quota-shaped -- base has 40% zero-win books by
    construction -- so every benchmark must come from the OPTIMIZED table as
    sum(weight*payout)/sum(weight), never from the pool.
    """
    path = os.path.join(SHADOW, "publish_files", f"lookUpTable_{mode}_0.csv")
    if not os.path.exists(path):
        print(f"  (no optimized LUT at {path})")
        return

    total_w = 0
    total_wp = 0.0
    zero_w = 0
    ge1_w = 0
    max_pay = 0.0
    with open(path, encoding="UTF-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue
            w = int(parts[1])
            p = int(parts[2]) / 100.0
            total_w += w
            total_wp += w * p
            if p == 0:
                zero_w += w
            if p >= cost:
                ge1_w += w
            max_pay = max(max_pay, p)

    if total_w == 0:
        print("  empty lookup table")
        return
    print(f"  RTP        {total_wp / total_w / cost:.4f}")
    print(f"  zero pay   {100.0 * zero_w / total_w:.2f}%")
    print(f"  >= 1x cost {100.0 * ge1_w / total_w:.2f}%")
    print(f"  max win    {max_pay:.2f}x")


def main() -> int:
    modes = sys.argv[1:] or ["base"]
    config = GameConfig()
    # opt_params lives on the config but is POPULATED by OptimizationSetup, not by
    # GameConfig's own constructor -- run.py builds this same object before the
    # optimizer step for exactly this reason.
    OptimizationSetup(config)
    costs = {bm.get_name(): bm.get_cost() for bm in config.bet_modes}

    for mode in modes:
        if mode not in costs:
            raise SystemExit(f"unknown mode {mode}")
        print(f"\n=== optimizing {mode} (Go pool, unchanged Rust binary) ===")
        stage(mode, config)
        write_setup(config, mode, threads=16)

        start = time.time()
        proc = subprocess.run(
            ["cargo", "run", "--release"],
            cwd=OPT_DIR, capture_output=True, text=True,
            env={**os.environ,
                 "PATH": os.path.expanduser("~/.cargo/bin") + os.pathsep + os.environ.get("PATH", "")},
        )
        elapsed = time.time() - start
        if proc.returncode != 0:
            print(proc.stdout[-3000:])
            print(proc.stderr[-3000:])
            raise SystemExit(f"optimizer failed for {mode}")

        # ⚠ The binary prints `now.elapsed().as_secs()` into a string labelled
        # "ms" (optimization_program/src/main.rs), so its own figure is SECONDS
        # mislabelled. We time it ourselves instead.
        print(f"  optimizer wall time {elapsed:.1f}s")
        for line in proc.stdout.splitlines():
            if "rtp" in line.lower() or "error" in line.lower() or "warn" in line.lower():
                print("  |", line.strip()[:160])
        report(mode, costs[mode])

    return 0


if __name__ == "__main__":
    sys.exit(main())
