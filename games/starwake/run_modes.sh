#!/usr/bin/env bash
# Starwake measure-loop driver -- built for a detached terminal, not for the agent
# shell (a 1e6 pool outlives any 10-minute tool timeout).
#
#   ./run_modes.sh                        all six modes, then the optimizer
#   ./run_modes.sh buy_corvus buy_ursa    only those modes, no optimizer
#   ./run_modes.sh --no-optimize          all six sims, stop before the optimizer
#
# One PYTHON PROCESS PER MODE, on purpose. The parent keeps every finished mode's
# recorded force keys alive for the whole run, and each new mode forks 14 children
# off that ever-growing heap; isolating modes keeps peak RSS flat and makes a
# failure cost one mode instead of the whole pool -- just re-run that one name.
#
# Everything (including a 30s memory sample) lands in library/logs/<timestamp>.log,
# so a run that dies unattended can still be diagnosed after the fact.
set -uo pipefail

cd "$(dirname "$0")" || exit 1
PY=../../env/bin/python
ALL_MODES=(base ante_starfall buy_corvus buy_ursa buy_draco buy_mystery)

optimize=1
modes=()
for arg in "$@"; do
    case "$arg" in
        --no-optimize) optimize=0 ;;
        *) modes+=("$arg"); optimize=0 ;;
    esac
done
[[ ${#modes[@]} -eq 0 ]] && modes=("${ALL_MODES[@]}")

mkdir -p library/logs
LOG="library/logs/run_$(date +%Y%m%d_%H%M%S).log"
echo "modes: ${modes[*]}   optimizer: $optimize"
echo "log:   $(pwd)/$LOG"
echo

# Memory sampler -- the last run died of RAM, so every future run carries evidence.
(
    while :; do
        printf '[mem %s] %s\n' "$(date +%H:%M:%S)" \
            "$(free -m | awk '/^Mem:/{printf "used=%sM avail=%sM", $3, $7}')"
        sleep 30
    done
) >>"$LOG" 2>&1 &
mem_pid=$!
trap 'kill "$mem_pid" 2>/dev/null' EXIT

start=$(date +%s)
for m in "${modes[@]}"; do
    echo "=== $(date +%H:%M:%S)  SIMS: $m ===" | tee -a "$LOG"
    if ! "$PY" -u run.py "$m" 2>&1 | tee -a "$LOG"; then
        echo "!!! $m FAILED -- log: $LOG" | tee -a "$LOG"
        exit 1
    fi
done

if [[ $optimize -eq 1 ]]; then
    echo "=== $(date +%H:%M:%S)  OPTIMIZER (all modes) ===" | tee -a "$LOG"
    if ! "$PY" -u run.py optimize 2>&1 | tee -a "$LOG"; then
        echo "!!! optimizer FAILED -- log: $LOG" | tee -a "$LOG"
        exit 1
    fi
fi

echo "=== finished in $(((($(date +%s) - start)) / 60)) min -- log: $LOG ===" | tee -a "$LOG"
