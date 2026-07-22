"""Persistent state for the Charge -> Bloom -> Roam feature (Starwake's one mechanic).

This object holds EVERYTHING that must survive across the fixed feature spins:
which constellation cells are lit (sticky wilds), which phase we're in, where the
beast block sits, and the beast's climbing multiplier. It is deliberately kept
free of GameState so it can be unit-tested on its own (the Keybearer lesson:
"persistent state is where silent bugs live -- unit-test the feature engine
before any full run"). The ONLY coupling to the real board is `apply_wilds`,
which takes a `make_wild` callback -- tests pass a fake, the engine passes
`create_symbol("W")`.

Rules encoded here (source of truth = docs/ideas/starwake.md + CLAUDE.md):
  - A cell lights when a WINNING PAYLINE crosses it (win-line fill; the old
    star-landing/lambda rule is retired). A lit cell is a sticky wild for the
    rest of the feature -> snowball.
  - Complete the set -> the beast wakes: an oversized block wild (Corvus 2x2 /
    Ursa 2x3 / Draco 3x3) that ROAMS to a random valid position each spin and
    NEVER exits the grid (the tail depends on how long it stays, not the path).
  - The multiplier lives on the beast (not a global meter): it starts on wake
    and climbs +1 each spin. Enumerable ladder (compliance lists every value).
Values like start-multiplier / climb are TUNING knobs (design doc lines 255-257);
they are constructor args, not magic numbers baked into the logic.
"""


class Constellation:
    """State machine for one dealt constellation across one feature."""

    CHARGE = "charge"  # filling cells via win-lines; beast asleep
    ROAM = "roam"      # set complete; beast awake and roaming

    def __init__(
        self,
        tier,
        target_cells,
        num_reels,
        num_rows,
        beast_shape,
        beast_start_mult=2,
        beast_climb=1,
    ):
        """
        tier:            "corvus" | "ursa" | "draco" (label only, for events).
        target_cells:    list of (reel, row) the constellation occupies.
        num_reels:       grid width.
        num_rows:        grid height (uniform; Starwake is 4 on every reel).
        beast_shape:     (reel_span, row_span) of the block wild on completion.
        beast_start_mult:multiplier the beast shows the spin it wakes.
        beast_climb:     added to the multiplier every roam spin after wake.
        """
        self.tier = tier
        self.target_cells = [tuple(c) for c in target_cells]
        self.num_reels = num_reels
        self.num_rows = num_rows
        self.beast_w, self.beast_h = beast_shape
        self.beast_start_mult = beast_start_mult
        self.beast_climb = beast_climb

        # --- persistent state (this is the stuff that must survive the loop) ---
        self.lit = set()             # (reel,row) cells lit so far -- sticky, grows only
        self.phase = self.CHARGE
        self.multiplier = 1          # only meaningful once the beast is awake
        self.beast_origin = None     # (reel,row) top-left of the block; None until wake
        # --- per-spin scratch (consumed by the event emitters each spin) ---
        self.newly_lit = []          # cells lit THIS spin -> starLit events
        self.woke_this_spin = False  # True on the wake spin only -> beastWake event

    # ------------------------------------------------------------------ charge
    def light_from_wins(self, win_positions):
        """Light any still-dark target cell that a winning line crossed this spin.

        win_positions: iterable of (reel,row) that were part of ANY winning line.
        Returns the list of cells newly lit (for starLit events). Idempotent:
        already-lit cells are never re-lit, so `lit` only ever grows (sticky).
        """
        crossed = {tuple(p) for p in win_positions}
        newly = [c for c in self.target_cells if c not in self.lit and c in crossed]
        self.lit.update(newly)
        self.newly_lit = newly
        return newly

    @property
    def is_complete(self):
        """Every constellation cell is lit."""
        return len(self.lit) == len(self.target_cells)

    @property
    def remaining(self):
        """Cells still dark (useful for events / debugging)."""
        return [c for c in self.target_cells if c not in self.lit]

    # -------------------------------------------------------------- beast/roam
    def _valid_origins(self):
        """Every top-left position where the block fits fully on the grid.

        This is what guarantees the beast NEVER exits: we only ever choose an
        origin from here, so all beast cells are on-grid by construction.
        """
        return [
            (reel, row)
            for reel in range(self.num_reels - self.beast_w + 1)
            for row in range(self.num_rows - self.beast_h + 1)
        ]

    def beast_cells(self):
        """The (reel,row) cells the block currently covers (empty if asleep)."""
        if self.beast_origin is None:
            return set()
        r0, row0 = self.beast_origin
        return {
            (r0 + dr, row0 + drow)
            for dr in range(self.beast_w)
            for drow in range(self.beast_h)
        }

    def wild_cells(self):
        """All cells that should read as wild on the board this spin.

        The union of the sticky lit stars and the beast block. If the beast has
        roamed on top of a lit star, that cell simply appears once (a set).
        """
        return set(self.lit) | self.beast_cells()

    def wake(self, rng):
        """Complete -> the beast wakes: enter ROAM, place the block, set the mult.

        Only valid once the set is complete. `rng` needs `.choice` (a
        random.Random or the random module) so placement is reproducible under
        the engine's per-sim seeding.
        """
        assert self.is_complete, "beast cannot wake before the set is complete"
        assert self.phase == self.CHARGE, "beast already awake"
        self.phase = self.ROAM
        self.multiplier = self.beast_start_mult
        self.beast_origin = rng.choice(self._valid_origins())
        self.woke_this_spin = True

    def roam(self, rng):
        """A post-wake spin: move the block to a new valid cell and climb the mult."""
        assert self.phase == self.ROAM, "roam() before the beast woke"
        self.beast_origin = rng.choice(self._valid_origins())
        self.multiplier += self.beast_climb
        self.woke_this_spin = False

    # ------------------------------------------------------------------- board
    def apply_wilds(self, board, make_wild):
        """Stamp a wild onto every wild cell of a freshly drawn board.

        Called once per feature spin AFTER the draw and BEFORE line evaluation --
        that ordering is the snowball (existing wilds inflate this spin's wins,
        which then light more cells). `make_wild()` returns a fresh wild symbol
        (engine: create_symbol("W"); tests: a fake). Beast cells additionally
        carry the current climbing multiplier -- that is what "the multiplier
        lives on the beast" means in board terms.
        """
        beast = self.beast_cells()
        for (reel, row) in self.wild_cells():
            sym = make_wild()
            if (reel, row) in beast and hasattr(sym, "assign_attribute"):
                sym.assign_attribute({"multiplier": self.multiplier})
            board[reel][row] = sym
