from game_calculations import GameCalculations
from src.calculations.lines import Lines


class GameExecutables(GameCalculations):

    def evaluate_lines_board(self):
        """Populate win-data, record wins, transmit events.

        max_symbol, not the SDK default "symbol": the beast is a BLOCK wild that
        stamps its climbing multiplier on every cell it covers, and the default
        strategy SUMS multipliers across a line's winning positions. A payline
        crossing 2 cells of the block therefore paid 2*M (3*M for the 3-wide Ursa
        and Draco blocks) -- 87% of buy_corvus's entire payout came from those
        double-crossings, and the "enumerable ladder" compliance table would have
        had to publish {M, 2M, 3M}, not the intended 2..10. Option A says the
        beast is ONE multiplier; max applies it once per win.
        """
        self.win_data = Lines.get_lines(
            self.board,
            self.config,
            multiplier_method="max_symbol",
            global_multiplier=self.global_multiplier,
        )
        Lines.record_lines_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        Lines.emit_linewin_events(self)
