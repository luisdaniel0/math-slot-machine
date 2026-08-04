# math-sdk — Uptown Games fork

Fork of the Stake Engine math SDK. One game is in active development: **Starwake**,
a 5x4 / 20-payline constellation slot. A Go port of the SDK's hot loop lives in `go/`.

Learner project: build step-by-step, explain decisions, don't bulk-complete. The user
drives design calls.

## Read this before touching the math

**`games/starwake/CLAUDE.md`** is the game's working memory — design spec, build
status, every measured result and the reasoning behind each economy decision. Most
"open questions" are already answered there, usually at the cost of a sim run. Read it
before proposing any change to the paytable, reels, feature, ladders, prices or
optimizer config, even if the file you are editing lives outside `games/starwake/`.

Design doc with full rationale: `docs/ideas/starwake.md`.

## Repo-wide rules

- ⚠ **`origin` is `StakeEngine/math-sdk`, the PUBLIC upstream SDK. NEVER push to it.**
  `mine` is the fork (`luisdaniel0/math-slot-machine`) and is the only push target.
- Work lands on **`main`** in `mine`. Feature branches are fine but must be merged
  back — commits stranded on an unmerged branch do not count as contributions and are
  not backed up. Merge with `--no-ff` so a migration can be reverted as one unit.
- **`optimization_program/src/setup.toml` is generated** by every optimizer run (it
  records the last bet_type and m2m bounds). It is tracked, but never commit it.
- **`library/` is gitignored.** Git protects the code, not the 14 GB pool. The pool's
  known-good marker is the tag `starwake-math-v1` (the exact code state that produced
  the converged 1e6 pool) — `git checkout starwake-math-v1` returns to working math.
- `AGENTS.md` is a symlink to this file. Do not edit it separately; it used to be a
  hand-copied duplicate and silently drifted out of date.

## Layout

    games/starwake/           the game: config, feature engine, sweep harnesses, tools
      CLAUDE.md               ← the game's working memory (read this)
      reels/                  strip generator + every sweep harness
      library/                books, LUTs, publish artifacts (gitignored, 14 GB)
    go/                       Go port of the sim engine (see "The Go engine" below)
    src/                      upstream SDK — shared by every game, change with care
    optimization_program/     the Rust optimizer (PigFarmRust), unchanged from upstream
    docs/ideas/               design docs for Starwake and parked concepts
    docs/math_docs/           upstream SDK documentation, not ours
    utils/analysis/           upstream analysis helpers (CVaR, distributions)

## The Go engine

The hot loop is ported to Go; Python keeps the design surface (`game_config.py`), the
analysis tools and the publishing path, and the optimizer stays Rust.

    sims, 6 modes x 1e6     74 min -> 2.5 min
    full pipeline          106 min -> 20 min
    measure loop (20k)        ~15s -> 0.5s

    go/run_modes.sh [sims] [modes...]   sims only, writes to go/out/library/
    go/full_run.sh  [sims]              sims + the Rust optimizer, end to end

⚠ **The Go engine reads `go/config/starwake.json`, NOT `game_config.py`.** Edit a
paytable value and forget to re-export and the sim runs the OLD math — silently, with
plausible numbers. `run_modes.sh` re-exports automatically when the Python config is
newer; if you invoke the binary directly, run `games/starwake/export_go_config.py`
yourself.

⚠ Go writes to `go/out/library/`, never to `games/starwake/library/`. Keep it that way.

## Common commands

    ./env/bin/python -m pytest tests/starwake/ -v              unit tests
    ./env/bin/python games/starwake/reels/generate_reels.py    regenerate strips
    ./env/bin/python games/starwake/check_risk_gates.py        compliance gates
    cd games/starwake && ../../env/bin/python run.py optimize buy_mystery
                                                              optimizer only, ~5 min

Reading results: compute every benchmark from the **optimized LUT**
(`library/publish_files/lookUpTable_<mode>_0.csv`, format `id,weight,payout*100`), not
from the raw book pool — the pool is quota-shaped by construction and a bust rate read
off it is meaningless.

## Long-running work

Sims and the optimizer are 100% local compute and cost no model tokens once launched.
Launch anything long with `setsid nohup ... &` so it outlives the session; verify with
`ps -o pid,ppid,sid` that its session id differs from the shell's.
