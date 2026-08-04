#!/usr/bin/env bash
# Run every bet mode through the Go engine.
#
#   ./run_modes.sh            all six modes at 1e6
#   ./run_modes.sh 20000      all six at a throwaway count (the measure loop)
#   ./run_modes.sh 1000000 buy_ursa buy_draco
#
# Writes to go/out/library/ -- NEVER games/starwake/library/, which holds the
# converged production pool.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

BIN=/tmp/starwake
go build -o "$BIN" ./cmd/starwake || exit 1

# ⚠ THE ONE FOOTGUN IN THIS WORKFLOW. The Go engine reads config/starwake.json,
# NOT game_config.py. Edit a paytable value or a ladder rung and forget to
# re-export, and the sim happily runs the OLD math -- silently, with plausible
# numbers. So re-export automatically whenever the Python config is newer.
CONFIG=config/starwake.json
SOURCES=(../games/starwake/game_config.py ../games/starwake/reels/*.csv)
stale=0
for src in "${SOURCES[@]}"; do
    [[ -e "$src" ]] || continue
    if [[ ! -e "$CONFIG" || "$src" -nt "$CONFIG" ]]; then stale=1; fi
done
if [[ $stale -eq 1 ]]; then
    echo "config is stale -- re-exporting from game_config.py"
    ( cd ../games/starwake && ../../env/bin/python export_go_config.py ) || exit 1
    echo
fi

SIMS="${1:-1000000}"
shift 2>/dev/null || true
MODES=("$@")
if [[ ${#MODES[@]} -eq 0 ]]; then
    MODES=(base ante_starfall buy_corvus buy_ursa buy_draco buy_mystery)
fi

start=$(date +%s)
for m in "${MODES[@]}"; do
    /usr/bin/time -f "  wall %es   peak RSS %MkB" "$BIN" -mode "$m" -sims "$SIMS"
    echo
done
echo "=== all modes finished in $(($(date +%s) - start))s ==="
