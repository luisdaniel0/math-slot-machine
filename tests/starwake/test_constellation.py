"""Unit tests for the Charge -> Bloom -> Roam persistent state (Constellation).

Runs the state machine in ISOLATION -- no reels, no book, no full sim -- because
persistent feature state is where Keybearer's silent bugs lived (a climbing
multiplier that multiplied nothing). These lock the invariants BEFORE the engine
is wired into gamestate.run_freespin:
  - a lit cell actually becomes a wild on the board next spin (the bug class);
  - lighting is win-line-driven, target-only, and sticky (only grows);
  - a sticky wild can cause a NEW cell to light (the snowball) -- proven through
    the real Lines calculator;
  - the beast block never exits the grid over many random roams;
  - the beast multiplier climbs as an enumerable ladder and rides the beast.

Run:  ./env/bin/python -m pytest tests/starwake/test_constellation.py -v
"""

import random
import sys
import os

import pytest

# games/starwake isn't a package on sys.path; add it so we can import the module.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "games", "starwake"))
from constellation import Constellation  # noqa: E402
from game_config import GameConfig  # noqa: E402

from tests.win_calculations.game_test_config import GamestateTest, create_blank_board  # noqa: E402
from src.calculations.lines import Lines  # noqa: E402


# --------------------------------------------------------------------------- #
# Minimal 5x4 config: one straight payline on row 0, W wild pays 5-kind. Just
# enough to mint real Symbol wilds and exercise the real Lines calc.
# --------------------------------------------------------------------------- #
class TinyLinesConfig:
    def __init__(self):
        self.game_id = "starwake_test"
        self.rtp = 0.9665
        self.num_reels = 5
        self.num_rows = [4] * self.num_reels
        self.paytable = {
            (5, "W"): 60,
            (5, "H1"): 10,
            (5, "L1"): 1,
        }
        self.paylines = {1: [0, 0, 0, 0, 0]}  # row-0 straight only
        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": ["W"]}
        self.include_padding = False


@pytest.fixture
def gs():
    """Test gamestate that can mint real Symbol objects via create_symbol()."""
    g = GamestateTest(TinyLinesConfig())
    g.create_symbol_map()
    g.assign_special_sym_function()
    g.board = create_blank_board(g.config.num_reels, g.config.num_rows)
    return g


def make_constellation(target_cells, beast_shape=(2, 2), **kw):
    return Constellation(
        tier="test",
        target_cells=target_cells,
        num_reels=5,
        num_rows=4,
        beast_shape=beast_shape,
        **kw,
    )


# ------------------------------------------------------------------ deal/charge
def test_deal_initial_state():
    c = make_constellation([(0, 1), (2, 2)])
    assert c.lit == set()
    assert c.phase == Constellation.CHARGE
    assert c.beast_origin is None
    assert c.beast_cells() == set()
    assert not c.is_complete
    assert c.remaining == [(0, 1), (2, 2)]


def test_light_only_target_cells_crossed_by_a_win():
    c = make_constellation([(0, 1), (2, 2)])
    # winning-line positions include one target (0,1) and a non-target (1,1)
    newly = c.light_from_wins([(0, 1), (1, 1)])
    assert newly == [(0, 1)]
    assert c.lit == {(0, 1)}          # the target crossed -> lit
    assert (1, 1) not in c.lit        # non-target position ignored
    assert (2, 2) not in c.lit        # target not crossed stays dark


def test_lighting_is_sticky_and_idempotent():
    c = make_constellation([(0, 1), (2, 2)])
    c.light_from_wins([(0, 1)])
    assert c.lit == {(0, 1)}
    # a later spin re-crosses (0,1) but wins nowhere new: no re-light, no shrink
    newly = c.light_from_wins([(0, 1)])
    assert newly == []
    assert c.lit == {(0, 1)}
    # a spin with no wins at all keeps everything lit (sticky)
    c.light_from_wins([])
    assert c.lit == {(0, 1)}


def test_completion_detected_when_all_cells_lit():
    c = make_constellation([(0, 1), (2, 2)])
    c.light_from_wins([(0, 1)])
    assert not c.is_complete
    c.light_from_wins([(2, 2)])
    assert c.is_complete
    assert c.remaining == []


# ---------------------------------------------- lit cell -> wild on board (bug class)
def test_lit_cell_becomes_a_wild_on_the_next_board(gs):
    c = make_constellation([(0, 1)])
    c.light_from_wins([(0, 1)])
    # fresh board of non-wild symbols
    for reel in range(5):
        for row in range(4):
            gs.board[reel][row] = gs.create_symbol("H1")
    c.apply_wilds(gs.board, lambda: gs.create_symbol("W"))
    assert gs.board[0][1].check_attribute("wild") is True      # lit cell -> wild
    assert gs.board[0][0].check_attribute("wild") is False     # untouched cell unchanged


def test_snowball_sticky_wild_lights_a_new_cell(gs):
    """The core claim: a lit cell (sticky wild) inflates a win that then lights
    a previously-dark cell -- proven end-to-end through the real Lines calc."""
    c = make_constellation([(0, 0), (3, 0)])
    c.light_from_wins([(0, 0)])            # cell A already lit from an earlier spin
    # Row 0: reel0 draws L1 (breaks the H1 run), reels 1-4 draw H1.
    # Without A being wild this line is L1,H1,H1,H1,H1 -> no 5-kind -> no win.
    for reel in range(5):
        for row in range(4):
            gs.board[reel][row] = gs.create_symbol("L1" if reel == 0 else "H1")

    # Apply sticky wilds: (0,0) becomes W BEFORE evaluation (this ordering IS the snowball)
    c.apply_wilds(gs.board, lambda: gs.create_symbol("W"))
    windata = Lines.get_lines(gs.board, gs.config)
    assert windata["totalWin"] > 0, "sticky wild should have completed a 5-kind"

    # Feed the winning-line positions back in -> the far cell (3,0) should light
    win_positions = [(p["reel"], p["row"]) for w in windata["wins"] for p in w["positions"]]
    newly = c.light_from_wins(win_positions)
    assert (3, 0) in c.lit
    assert (3, 0) in newly


# ------------------------------------------------------------------ beast / roam
def test_wake_requires_completion_then_sets_roam_state():
    c = make_constellation([(0, 0), (1, 0)], beast_shape=(2, 2), mult_ladder=[3, 4, 5])
    with pytest.raises(AssertionError):
        c.wake(random.Random(0))           # not complete yet
    c.light_from_wins([(0, 0), (1, 0)])
    c.wake(random.Random(0))
    assert c.phase == Constellation.ROAM
    assert c.multiplier == 3               # rung 0 on wake
    assert c.woke_this_spin is True
    assert c.beast_origin in c._valid_origins()


def test_roam_before_wake_raises():
    c = make_constellation([(0, 0)])
    with pytest.raises(AssertionError):
        c.roam(random.Random(0))


@pytest.mark.parametrize("shape,expected", [((2, 2), 4), ((2, 3), 6), ((3, 3), 9)])
def test_beast_block_covers_shape_and_stays_on_grid(shape, expected):
    c = make_constellation([(0, 0), (1, 0)], beast_shape=shape)
    c.light_from_wins([(0, 0), (1, 0)])
    c.wake(random.Random(1))
    cells = c.beast_cells()
    assert len(cells) == expected
    assert all(0 <= r < 5 and 0 <= row < 4 for (r, row) in cells)


def test_beast_never_exits_and_multiplier_ladder_is_enumerable():
    ladder = [2, 3, 5, 8, 12]
    c = make_constellation([(0, 0), (1, 0)], beast_shape=(3, 3), mult_ladder=ladder)
    c.light_from_wins([(0, 0), (1, 0)])
    rng = random.Random(1234)
    c.wake(rng)
    assert c.multiplier == ladder[0]       # rung 0 on wake
    seen = {c.multiplier}
    for step in range(1, 500):
        c.roam(rng)
        # never exits, on every single roam
        assert all(0 <= r < 5 and 0 <= row < 4 for (r, row) in c.beast_cells())
        # walks the ladder rung by rung, then HOLDS the top -- a roam longer than
        # the ladder must never index off the end or invent an unpublished value
        assert c.multiplier == ladder[min(step, len(ladder) - 1)]
        seen.add(c.multiplier)
    # compliance: the obtainable set is exactly the published list, nothing else
    assert seen == set(ladder)


def test_accelerating_ladder_pays_a_long_roam_far_more_than_a_short_one():
    """The tail mechanism itself: rung 0 is where a late completion lands and the
    top rung is where a rare early completion lands. A flat +1 ladder made those
    two nearly equal, which is why the feature had no tail (buy_draco max was only
    6.4x its mean). Guard the SHAPE, not the exact numbers."""
    draco = GameConfig().constellation_mult_ladders["draco"]
    assert draco[-1] / draco[0] >= 20, "top rung must dwarf the first, or there is no tail"
    gaps = [b - a for a, b in zip(draco, draco[1:])]
    assert all(b >= a for a, b in zip(gaps, gaps[1:])), "steps must accelerate, never flatten"
    assert all(isinstance(v, int) and v > 0 for v in draco), "rungs must be publishable integers"


def test_every_tier_ladder_covers_the_longest_possible_roam():
    """An immediate completion leaves num_feature_spins[tier]-1 roam spins. Short
    ladders would silently clamp, capping the tail exactly where it is supposed to
    pay. Feature length is PER TIER (corvus 10, ursa/draco 15), so the rung count is
    checked against each tier's own length."""
    config = GameConfig()
    for tier, ladder in config.constellation_mult_ladders.items():
        longest_roam = config.num_feature_spins[tier] - 1
        assert len(ladder) >= longest_roam, f"{tier} ladder clamps before the roam ends"


def test_beast_cells_are_wild_and_carry_the_climbing_multiplier(gs):
    c = make_constellation([(0, 0), (1, 0)], beast_shape=(2, 2),
                           mult_ladder=[3, 4, 5])
    c.light_from_wins([(0, 0), (1, 0)])
    c.wake(random.Random(0))
    for reel in range(5):
        for row in range(4):
            gs.board[reel][row] = gs.create_symbol("H1")
    c.apply_wilds(gs.board, lambda: gs.create_symbol("W"))
    for (reel, row) in c.beast_cells():
        assert gs.board[reel][row].check_attribute("wild") is True
        assert gs.board[reel][row].multiplier == 3     # beast carries the mult
    # after one roam the whole block carries the climbed value
    c.roam(random.Random(0))
    c.apply_wilds(gs.board, lambda: gs.create_symbol("W"))
    for (reel, row) in c.beast_cells():
        assert gs.board[reel][row].multiplier == 4


# ------------------------------------------------------- pre-lit (Draco Ascendant)
# Ascendant is a Draco dealt with some cells ALREADY LIT -- a different initial
# state, not a different feature. These lock the two things that buys: cells that
# no longer need tracing, and wilds on the board from spin one (no cold start).
def test_no_prelit_by_default():
    """Every normal tier must be unaffected -- the default stays a dark deal."""
    c = make_constellation([(0, 1), (2, 2)])
    assert c.prelit == set()
    assert c.lit == set()


def test_prelit_cells_start_lit():
    c = make_constellation([(0, 1), (2, 2), (4, 3)], prelit_cells=[(0, 1), (4, 3)])
    assert c.lit == {(0, 1), (4, 3)}
    assert c.remaining == [(2, 2)]
    assert not c.is_complete


def test_prelit_cells_are_wild_on_the_board_before_any_win(gs):
    """The head start is not just bookkeeping: a pre-lit cell is a sticky wild on
    spin one, which is what stops an Ascendant from ever cold-starting."""
    c = make_constellation([(0, 1), (2, 2), (4, 3)], prelit_cells=[(0, 1)])
    for reel in range(5):
        for row in range(4):
            gs.board[reel][row] = gs.create_symbol("H1")
    c.apply_wilds(gs.board, lambda: gs.create_symbol("W"))
    assert gs.board[0][1].check_attribute("wild") is True
    assert gs.board[2][2].check_attribute("wild") is False  # still dark


def test_prelit_reduces_the_wins_needed_to_complete():
    """The whole economic point: fewer cells left to trace -> completes EARLIER,
    and early completion is where the ladder keeps its value."""
    cells = [(0, 1), (2, 2), (4, 3)]
    dark = make_constellation(cells)
    dark.light_from_wins([(0, 1), (2, 2)])
    assert not dark.is_complete          # still needs (4,3)

    lit = make_constellation(cells, prelit_cells=[(4, 3)])
    lit.light_from_wins([(0, 1), (2, 2)])
    assert lit.is_complete               # same spin's wins finish it


def test_prelit_must_be_part_of_the_shape():
    """A typo'd cell would silently never light and the tier could never complete."""
    with pytest.raises(AssertionError, match="not part of"):
        make_constellation([(0, 1), (2, 2)], prelit_cells=[(3, 3)])


def test_fully_prelit_is_rejected():
    """Would wake the beast before spin one and hand out the ladder for free --
    a payout that looks plausible right up to the ceiling, so fail loudly here."""
    with pytest.raises(AssertionError, match="every cell"):
        make_constellation([(0, 1), (2, 2)], prelit_cells=[(0, 1), (2, 2)])
