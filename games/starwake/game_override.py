from game_executables import GameExecutables
from src.events.events import fs_trigger_event


class GameStateOverride(GameExecutables):
    """
    This class is is used to override or extend universal state.py functions.
    e.g: A specific game may have custom book properties to reset
    """

    def reset_book(self):
        super().reset_book()
        self.constellation_tier = None
        self.constellation = None  # per-feature state; created in run_freespin

    def update_freespin_amount(self, scatter_key: str = "scatter") -> None:
        """Fixed spins + tier mapping, with 6+ scatters clamped to the top tier.

        Replaces the base method's exact-count indexing (KeyError on star-rich
        boards showing more scatters than the trigger table lists).
        """
        count = min(
            self.count_special_symbols(scatter_key),
            max(self.config.freespin_triggers[self.gametype]),
        )
        self.tot_fs = self.config.freespin_triggers[self.gametype][count]
        self.constellation_tier = self.config.scatter_tiers[count]
        if self.gametype == self.config.basegame_type:
            basegame_trigger, freegame_trigger = True, False
        else:
            basegame_trigger, freegame_trigger = False, True
        fs_trigger_event(self, basegame_trigger=basegame_trigger, freegame_trigger=freegame_trigger)

    def assign_special_sym_function(self):
        self.special_symbol_functions = {
            "W": [self.assign_mult_property],
        }

    def assign_mult_property(self, symbol) -> dict:
        """Option A: the beast is the ONLY multiplier source, so every plain wild
        (natural strip wilds AND sticky lit stars) carries multiplier 1. The
        beast's climbing multiplier is stamped straight onto beast cells by
        Constellation.apply_wilds. The config's freegame mult_values are dormant
        under Option A -- kept as the seam for a possible future FLAT star mult if
        a playtest says the carpet needs juice (see the Option A/B analysis)."""
        symbol.assign_attribute({"multiplier": 1})

    def check_repeat(self):
        super().check_repeat()
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True
                return
            if win_criteria is None and self.final_win == 0:
                self.repeat = True
                return
