"""Integration tests for the Charge -> Bloom -> Roam feature loop (run_freespin).

Where test_constellation.py locks the pure state machine, THIS file locks the
gamestate WIRING -- the per-spin loop, its event tape, and (the reason this file
exists) the guaranteed roam window: a completion so late that the fixed feature
length can't fit min_roam_spins roam spins must EXTEND the feature so "even a
last-spin completion still pays" (docs/ideas/starwake.md L47-48).

The real run_freespin loop is driven verbatim; only its two reel-touching inputs
are scripted so completion timing is deterministic without a full betmode/reel
setup:
  - draw_board  -> a trivial on-grid board (apply_wilds still stamps real wilds);
  - evaluate    -> a per-spin set of winning (reel,row) positions that decides,
                   exactly, which constellation cells light this spin.
Everything else (Constellation, event emitters, tot_fs bookkeeping, end_freespin)
is the production code path.

Run:  ./env/bin/python -m pytest tests/starwake/test_run_freespin.py -v
"""

import random
import sys
import os

import pytest

# games/starwake isn't a package on sys.path; add it so gamestate + friends import.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "games", "starwake"))
from gamestate import GameState  # noqa: E402
from game_config import GameConfig  # noqa: E402
from constellation import Constellation  # noqa: E402


class ScriptedGameState(GameState):
    """A GameState whose board draw and win evaluation are scripted, so a
    feature completes on a chosen spin deterministically. Only the two
    reel-touching steps are replaced; the loop, state machine and events are real.
    """

    def configure(self, tier, wins_by_spin):
        """tier: which constellation to deal. wins_by_spin: list of iterables of
        (reel,row) -- the winning-line cells for spin 1, spin 2, ... (unpadded
        engine coords, matching Lines.get_lines and constellation target cells)."""
        self.constellation_tier = tier
        self.tot_fs = self.config.num_feature_spins  # normally set at trigger
        self._wins_by_spin = [list(w) for w in wins_by_spin]
        self._spin_ix = 0

    def draw_board(self, emit_event=True, trigger_symbol="scatter"):
        # A plain on-grid board of a real low symbol; apply_wilds stamps the
        # sticky/beast wilds over it. top/bottom/reel_positions are what
        # reveal_event reads under include_padding -- normally set by the reel
        # draw we're bypassing.
        self.board = [
            [self.create_symbol("L5") for _ in range(self.config.num_rows[r])]
            for r in range(self.config.num_reels)
        ]
        self.top_symbols = [self.create_symbol("L5") for _ in range(self.config.num_reels)]
        self.bottom_symbols = [self.create_symbol("L5") for _ in range(self.config.num_reels)]
        self.reel_positions = [0] * self.config.num_reels

    def evaluate_lines_board(self):
        # Inject this spin's scripted winning positions; spins past the script
        # win nothing (the set is already complete by then anyway).
        positions = self._wins_by_spin[self._spin_ix] if self._spin_ix < len(self._wins_by_spin) else []
        self._spin_ix += 1
        self.win_data = {
            "totalWin": 0,
            "wins": [{"positions": [{"reel": r, "row": row} for (r, row) in positions]}] if positions else [],
        }
        self.win_manager.update_spinwin(0)


def run_feature(tier, complete_on_spin, min_roam=5):
    """Drive a full feature that completes exactly on `complete_on_spin`
    (1-indexed): dark until that spin, then every target cell lights at once.
    Returns the finished gamestate (walk gs.book.events for the tape)."""
    config = GameConfig()
    config.min_roam_spins = min_roam  # singleton: set explicitly so tests don't leak
    cells = config.constellation_cells[tier]
    script = [[] for _ in range(complete_on_spin - 1)] + [list(cells)]

    gs = ScriptedGameState(config)
    gs.reset_book()
    gs.configure(tier, script)
    random.seed(20260722)  # beast placement/roam is reproducible under this seed
    gs.run_freespin()
    return gs


def events_of(gs, etype):
    return [e for e in gs.book.events if e["type"] == etype]


ROWS, REELS = 4, 5


def _on_grid(cell_dicts):
    """beastRoam cells are emitted in CLIENT coords (row+1 under padding); a beast
    cell is on-grid iff its client row is in 1..ROWS and reel in 0..REELS-1."""
    return all(0 <= c["reel"] < REELS and 1 <= c["row"] <= ROWS for c in cell_dicts)


# --------------------------------------------------------------- the config knob
def test_min_roam_spins_default_is_five():
    # The guaranteed roam floor (docs/ideas/starwake.md L47-48; raised 3 -> 5 so a
    # late completion still gets a satisfying roam without capping the early tail).
    assert GameConfig().min_roam_spins == 5


# ----------------------------------------------------- guaranteed roam window ***
def test_last_spin_completion_still_gets_full_roam_window():
    """The bug this fix closes: completing on the LAST charge spin used to wake
    the beast with zero spins left to roam. It must now extend to min_roam_spins."""
    gs = run_feature("draco", complete_on_spin=10)  # production floor (5)

    assert len(events_of(gs, "beastWake")) == 1, "the completed set must wake the beast"
    roams = events_of(gs, "beastRoam")
    assert len(roams) == 5, "a last-spin completion must still get min_roam_spins on-board spins"
    # feature extended past the fixed 10: 10 (completion) + 5 (floor) = 15
    assert gs.tot_fs == 15
    # the beast pays on every one of those spins and never leaves the grid
    assert all(_on_grid(r["cells"]) for r in roams)
    # the beast walks the DRACO ladder from rung 0, one rung per roam spin. A
    # last-spin completion only ever reaches rung 4 -- the accelerating top of
    # the ladder is reserved for the rare early completion, which is the tail.
    draco = GameConfig().constellation_mult_ladders["draco"]
    assert [r["multiplier"] for r in roams] == draco[:5]
    assert [e["multiplier"] for e in events_of(gs, "multiplierClimb")] == draco[1:5]


def test_late_completion_extends_by_the_minimum_only():
    """Completing at spin 6 (floor 5) leaves only spins 7..10 = 4 inside the fixed
    length -> extend by exactly one spin to 11 so five roam spins fit."""
    gs = run_feature("ursa", complete_on_spin=6)
    assert gs.tot_fs == 11
    assert len(events_of(gs, "beastRoam")) == 5


def test_completion_that_exactly_fills_the_window_does_not_extend():
    """Complete at spin 5: spins 6..10 already give five roam spins -> the fixed
    length is untouched (the floor is a floor, not an add-on)."""
    gs = run_feature("ursa", complete_on_spin=5)
    assert gs.tot_fs == 10
    assert len(events_of(gs, "beastRoam")) == 5


# ------------------------------------------------- "finish early = longer roam"
def test_early_completion_roams_to_the_fixed_end_no_extension():
    """The fat tail the floor must NOT cap: an early completion is not extended --
    it roams for all the remaining fixed spins (more than the floor), and the
    multiplier climbs the whole way."""
    gs = run_feature("corvus", complete_on_spin=3)
    assert gs.tot_fs == 10, "early completion must not extend the feature"
    roams = events_of(gs, "beastRoam")
    assert len(roams) == 7, "completing at spin 3 roams spins 4..10 -- more than the floor of 5"
    # seven roam spins = the first seven rungs of the CORVUS ladder, in order
    corvus = GameConfig().constellation_mult_ladders["corvus"]
    assert [r["multiplier"] for r in roams] == corvus[:7]
    assert all(_on_grid(r["cells"]) for r in roams)


# ----------------------------------------------------------- never completing
def test_never_completing_runs_the_fixed_length_with_no_beast():
    """No completion -> no beast, no extension, exactly the fixed feature length."""
    config = GameConfig()
    config.min_roam_spins = 5
    gs = ScriptedGameState(config)
    gs.reset_book()
    gs.configure("draco", [[] for _ in range(config.num_feature_spins)])  # never any win
    random.seed(1)
    gs.run_freespin()

    assert events_of(gs, "beastWake") == []
    assert events_of(gs, "beastRoam") == []
    assert gs.tot_fs == config.num_feature_spins
    # the loop still ran the full fixed length (one update_fs per spin)
    assert len(events_of(gs, "updateFreeSpin")) == config.num_feature_spins


# ---------------------------------------------------------- event-ordering lock
def test_wake_precedes_every_roam_and_deal_precedes_wake():
    """Tape sanity: constellationDealt, then (later) beastWake, then all roams."""
    gs = run_feature("draco", complete_on_spin=5)
    order = [e["type"] for e in gs.book.events]
    deal = order.index("constellationDealt")
    wake = order.index("beastWake")
    first_roam = order.index("beastRoam")
    last_roam = len(order) - 1 - order[::-1].index("beastRoam")
    assert deal < wake < first_roam <= last_roam
    # the beast never appears on the board before it wakes
    assert "beastRoam" not in order[:wake]
