"""Main file for generating results for Starwake (celestial 5x4 lines game)."""

import sys

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    num_threads = 14   # 16-core box; buys are Python-feature-bound, more threads help
    rust_threads = 20
    # MEMORY sets this, not speed. Each thread holds every book of its CURRENT BATCH
    # in RAM until the batch is written, and the SDK derives the batch count as
    # round(sims / threads / batching_size) -- so 1e5 sims / 14 threads / 5000 rounds
    # to ONE batch and every thread holds 7,142 books at once (MORE than the 5,102 it
    # holds at 1e6, where the division gives 14 batches). A buy book is ~34 KB of JSON
    # (10 feature spins of board + event tape) against ~4.6 KB for a base book, so that
    # was ~15 GB live across 14 threads: it took the whole WSL VM down mid-buy_corvus.
    # At 1000 the in-flight set is threads*1000 = ~14k books (~2-3 GB) at ANY sim count.
    batching_size = 1000
    compression = True
    profiling = False

    # MEASURE LOOP PHASE B, production pool. The buys were previously cut to 1e5
    # only because a 1e6 buy mode (~1350 sims/s, so ~12 min) cannot finish inside a
    # foreground tool timeout -- run_modes.sh detaches the run, so that constraint
    # is gone and every mode gets the count Phase B actually needs: honest
    # corvus/ursa display ceilings and a wincap slice resolvable to >=1e-6.
    # Budget ~55-60 min of sims (the four buys are ~12 min each), then the optimizer.
    num_sim_args = {
        "base": int(1e6),
        "ante_starfall": int(1e6),
        "buy_mystery_spin": int(1e6),
        "buy_ursa": int(1e6),
        "buy_draco": int(1e6),
        "buy_mystery": int(1e6),
    }

    run_conditions = {
        "run_sims": True,
        "run_optimization": True,
        "run_analysis": False,
        "run_format_checks": False,
    }
    target_modes = list(num_sim_args.keys())

    # Optional CLI mode selection, so a long run can be driven ONE MODE PER PROCESS
    # (see run_modes.sh). Two reasons that matters: the parent process keeps every
    # mode's recorded force keys alive for the whole run, and each new mode forks 14
    # children off that ever-growing heap; and a mode that dies no longer costs the
    # modes that already succeeded -- just re-run that one name.
    #   python run.py                     -> all modes, then configs + optimizer
    #   python run.py buy_corvus          -> sims for that mode only, no optimizer
    #   python run.py buy_corvus 10000    -> same, at a throwaway count (measure loop)
    #   python run.py optimize            -> no sims; configs + optimizer, all modes
    #   python run.py optimize base       -> optimizer for that mode only
    if len(sys.argv) > 1:
        selected = sys.argv[1:]
        if selected[0] == "optimize":
            run_conditions["run_sims"] = False
            # Converging a mode's RTP means re-running the optimizer repeatedly, and
            # it re-parses that mode's force record every time (~1 GB at 1e6 sims,
            # which is nearly all of the ~5 min per mode -- the Rust solve itself is
            # ~300 ms). Optimizing one mode keeps an iteration at 5 min, not 25.
            if len(selected) > 1:
                unknown = [m for m in selected[1:] if m not in num_sim_args]
                assert not unknown, f"Unknown bet mode(s): {unknown}. Valid: {list(num_sim_args)}"
                target_modes = selected[1:]
        else:
            # A bare integer overrides the count for the selected modes: re-tuning
            # the economy means reading a mean win over and over, and 1e4 answers
            # that in ~10s where the production count takes ~12 min per mode.
            override = next((int(a) for a in selected if a.isdigit()), None)
            selected = [a for a in selected if not a.isdigit()]
            unknown = [m for m in selected if m not in num_sim_args]
            assert not unknown, f"Unknown bet mode(s): {unknown}. Valid: {list(num_sim_args)}"
            num_sim_args = {m: (override or num_sim_args[m]) for m in selected}
            run_conditions["run_optimization"] = False  # optimizer runs once, at the end

    config = GameConfig()
    gamestate = GameState(config)
    if run_conditions["run_optimization"] or run_conditions["run_analysis"]:
        optimization_setup_class = OptimizationSetup(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions["run_analysis"]:
        custom_keys = [{"symbol": "scatter"}]
        create_stat_sheet(gamestate, custom_keys=custom_keys)

    if run_conditions["run_format_checks"]:
        execute_all_tests(config)
