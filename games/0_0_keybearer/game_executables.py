from game_calculations import GameCalculations
from src.calculations.lines import Lines
from src.calculations.statistics import get_random_outcome
from src.events.events import update_global_mult_event, fs_trigger_event

# Spins awarded on feature entry. Standard is fixed; Super/Mega draw a bounded
# starting count from config.super_spin_values (set in update_freespin_amount)
# to give predictable-but-varied feature lengths.
FEATURE_SPINS = {"standard": 8}
# Spins added per retrigger, by tier (Standard only -- Super/Mega no longer
# retrigger). A small award keeps the branching factor < 1.
RETRIGGER_SPINS = {"standard": 5, "super": 3, "mega": 3}


class GameExecutables(GameCalculations):

    def evaluate_lines_board(self):
        """Populate win-data, record wins, transmit events.

        Uses the "combined" strategy so each line win is multiplied by the
        winning symbols' local multipliers AND the global Vault multiplier.
        (The default "symbol" strategy ignores global_multiplier, which would
        make the climbing Vault do nothing.)
        """
        self.win_data = Lines.get_lines(
            self.board,
            self.config,
            global_multiplier=self.global_multiplier,
            multiplier_method="combined",
        )
        Lines.record_lines_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        Lines.emit_linewin_events(self)

    def run_freespin_from_base(self, scatter_key: str = "scatter") -> None:
        """Set the active feature from the trigger key-count, then enter FG.

        3 keys -> Standard, 4 -> Super, 5+ -> Mega (pre-charged Vault).
        """
        key_count = self.count_special_symbols(scatter_key)
        if key_count >= 5:
            self.fs_feature = "mega"
            self.global_multiplier = self.config.mega_start_vault
        elif key_count == 4:
            self.fs_feature = "super"
        else:
            self.fs_feature = "standard"
        super().run_freespin_from_base(scatter_key)

    def update_freespin_amount(self, scatter_key: str = "scatter") -> None:
        """Award entry spins by feature tier (not by exact key count).

        Standard gets a fixed count; Super/Mega draw a bounded starting count
        from config.super_spin_values so feature length varies (the volatility
        lever) while staying capped and known up front. Awarding by tier (not
        exact key count) avoids a KeyError on key-rich boards showing 6+ Keys.
        """
        if self.fs_feature in ("super", "mega"):
            self.tot_fs = get_random_outcome(self.config.super_spin_values)
        else:
            self.tot_fs = FEATURE_SPINS[self.fs_feature]
        fs_trigger_event(self, basegame_trigger=True, freegame_trigger=False)

    def update_fs_retrigger_amt(self, scatter_key: str = "scatter") -> None:
        """Add retrigger spins by tier, clamped to the hard safety cap."""
        self.tot_fs = min(
            self.tot_fs + RETRIGGER_SPINS[self.fs_feature], self.config.max_fs_spins
        )
        fs_trigger_event(self, freegame_trigger=True, basegame_trigger=False)

    def charge_vault(self, scatter_key: str = "scatter") -> None:
        """Super/Mega FG: each Key on the board adds a tiered Vault increment.

        Each Key draws a legible tier value (3 / 10 / 25) from
        config.vault_increment_values. We record every Key's position and its
        drawn value so the frontend can show a clear "+N" flying from each Key
        into the running Vault total. Standard FG never calls this.
        """
        keys_on_board = self.special_syms_on_board[scatter_key]
        if not keys_on_board:
            return
        pad = 1 if self.config.include_padding else 0
        key_charges = []
        for pos in keys_on_board:
            value = get_random_outcome(self.config.vault_increment_values)
            self.global_multiplier += value
            key_charges.append(
                {"reel": pos["reel"], "row": pos["row"] + pad, "value": value}
            )
        update_global_mult_event(self, key_charges=key_charges)

    def check_fs_condition(self, scatter_key: str = "scatter") -> bool:
        """Retrigger gate.

        Super/Mega DO NOT retrigger: their length is fixed (12 spins) so the
        feature stays short and predictable -- escalation comes from the
        climbing Vault, not from ever-more spins. Standard FG (and basegame
        entry) use the engine default (min trigger key for the gametype).
        """
        if (
            self.gametype == self.config.freegame_type
            and self.fs_feature in ("super", "mega")
        ):
            return False
        return super().check_fs_condition(scatter_key)
