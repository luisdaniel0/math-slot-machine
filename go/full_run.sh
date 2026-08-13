#!/usr/bin/env bash
# Full pipeline on the Go engine: sim every mode, then run the UNCHANGED Rust
# optimizer over each pool.
#
#   ./full_run.sh              1e6 per mode
#   ./full_run.sh 200000       smaller, for a quick check
#
# Everything lands in go/out/library/ and games/starwake_go/ -- never in
# games/starwake/library/, which holds the converged production pool.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

SIMS="${1:-1000000}"
MODES=(base ante_starfall buy_ursa buy_draco buy_mystery buy_mystery_spin)
LOG="out/full_run_$(date +%Y%m%d_%H%M%S).log"
mkdir -p out

{
    echo "=== Go full run: $SIMS sims/mode, $(date) ==="
    start=$(date +%s)

    echo
    echo "--- SIMS ---"
    sim_start=$(date +%s)
    ./run_modes.sh "$SIMS" || exit 1
    echo "sims total: $(( $(date +%s) - sim_start ))s"

    echo
    echo "--- OPTIMIZER (unchanged Rust binary) ---"
    opt_start=$(date +%s)
    ../env/bin/python optimize_go.py "${MODES[@]}" || exit 1
    echo "optimizer total: $(( $(date +%s) - opt_start ))s"

    echo
    echo "=== finished in $(( $(date +%s) - start ))s ==="
} 2>&1 | tee "$LOG"

echo "log: $(pwd)/$LOG"
