import random

from game_override import GameStateOverride
from constellation import Constellation
from game_events import (
    constellation_dealt_event,
    star_lit_event,
    beast_wake_event,
    beast_roam_event,
    multiplier_climb_event,
)
from src.events.events import reveal_event


class GameState(GameStateOverride):
    """Handles game logic and events for a single simulation number/game-round."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()

            # Evaluate wins, update wallet, transmit events
            self.evaluate_lines_board()

            self.win_manager.update_gametype_wins(self.gametype)
            if self.check_fs_condition():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()

    # ------------------------------------------------------------- feature helpers
    def _deal_constellation(self):
        """Build the persistent feature state for the dealt tier and announce it.

        constellation_tier was set by update_freespin_amount (game_override.py)
        from the scatter count. Everything else comes straight from config, so the
        one place the tier's shape/beast/multiplier live is game_config.py.
        """
        tier = self.constellation_tier
        self.constellation = Constellation(
            tier=tier,
            target_cells=self.config.constellation_cells[tier],
            num_reels=self.config.num_reels,
            num_rows=self.config.num_rows[0],  # uniform (4 on every reel)
            beast_shape=self.config.constellation_beast_shapes[tier],
            beast_start_mult=self.config.beast_start_mult,
            beast_climb=self.config.beast_climb,
        )
        constellation_dealt_event(self)

    def _winning_positions(self):
        """Flat set of (reel,row) cells that were part of ANY winning line this
        spin, in unpadded engine coords -- exactly what lights constellation cells.
        """
        positions = set()
        for win in self.win_data.get("wins", []):
            for p in win["positions"]:
                positions.add((p["reel"], p["row"]))
        return positions

    def run_freespin(self):
        """Fixed 10-spin Charge -> Bloom -> Roam feature, NO retriggers.

        Per spin: draw (hold the reveal) -> stamp sticky wilds + the roaming beast
        -> reveal -> evaluate -> this spin's wins light more cells (the snowball).
        The set completing wakes the beast, which then roams with a climbing
        multiplier (Option A: the beast is the ONLY multiplier source). The
        reveal is held until after apply_wilds so the board the player sees
        actually shows its wilds (draw_board would otherwise reveal the bare draw).

        The nominal length is num_feature_spins, but a completion so late that
        fewer than min_roam_spins spins remain EXTENDS tot_fs so the woken beast
        always gets its guaranteed roam window (see the wake block below).
        """
        self.reset_fs_spin()
        self._deal_constellation()
        c = self.constellation
        beast_has_appeared = False

        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board(emit_event=False)  # draw only; reveal is emitted below

            # An awake beast rides onto THIS board before evaluation. It first
            # appears the spin AFTER completion: apply_wilds runs before the win
            # eval, so the completing spin itself can't also carry the beast.
            if c.phase == Constellation.ROAM:
                if beast_has_appeared:
                    c.roam(random)  # random module = the per-sim-seeded rng stream
                    beast_roam_event(self)
                    multiplier_climb_event(self)
                else:
                    beast_has_appeared = True  # first appearance: sits where it woke
                    beast_roam_event(self)

            c.apply_wilds(self.board, lambda: self.create_symbol("W"))
            reveal_event(self)

            self.evaluate_lines_board()

            # Charge phase: this spin's win-lines trace the constellation.
            newly = c.light_from_wins(self._winning_positions())
            if newly:
                star_lit_event(self, newly)

            # Just completed the set? Wake the beast (appears/roams next spin).
            if c.phase == Constellation.CHARGE and c.is_complete:
                c.wake(random)
                beast_wake_event(self)
                # Guarantee the roam window. The beast first appears the spin
                # AFTER wake, so a completion at spin self.fs needs at least
                # min_roam_spins spins behind it. An early completion already has
                # them (tot_fs unchanged -> "finish early = longer roam"); only a
                # LATE completion pushes tot_fs out, so "even a last-spin
                # completion still pays" (docs/ideas/starwake.md L47-48). Growing
                # tot_fs mid-feature is the same shape as a retrigger
                # (update_fs_retrigger_amt); the update_fs events then report the
                # extended total, which surfaces the guaranteed roam to the client.
                self.tot_fs = max(self.tot_fs, self.fs + self.config.min_roam_spins)

            self.win_manager.update_gametype_wins(self.gametype)

        self.end_freespin()
