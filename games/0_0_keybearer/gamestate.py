from game_override import GameStateOverride


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
            # Only enter the feature if THIS simulation's criteria expects it
            # (force_freegame). check_freespin_entry() rejects (repeat=True) a
            # natural trigger in a non-feature slice (basegame / 0), keeping
            # those pools free of the Vault's fat-tailed feature wins so the
            # optimizer can hit their RTP targets. Forced slices pass through.
            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        # Stop once the wincap is hit (further spins can't pay) or the hard
        # spin cap is reached -- guarantees the feature always terminates.
        while (
            self.fs < self.tot_fs
            and not self.wincap_triggered
            and self.fs < self.config.max_fs_spins
        ):
            self.update_freespin()
            self.draw_board()

            # Super/Mega: Keys on this board charge the climbing Vault before
            # wins are evaluated, so the boost applies to this spin and stays.
            if self.fs_feature in ("super", "mega"):
                self.charge_vault()

            self.evaluate_lines_board()

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

            self.win_manager.update_gametype_wins(self.gametype)

        self.end_freespin()
