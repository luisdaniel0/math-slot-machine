"""Game-specific configuration file, inherits from src/config/config.py"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "0_0_keybearer"
        self.provider_number = 0
        self.working_name = "Keybearer"
        self.wincap = 25000.0
        self.win_type = "lines"
        self.rtp = 0.9600
        self.construct_paths()

        # Game Dimensions
        self.num_reels = 5
        self.num_rows = [4] * self.num_reels
        # Board and Symbol Properties
        # Top-heavy paytable: H1 towers over the field (master-win fantasy),
        # high tier (H1-H4) clearly separated from low tier (L1-L5).
        # W pays 5-kind ONLY -- a 3/4-kind wild must never out-rank a longer
        # real-symbol line on base payout (see lines_info.md gotcha).
        # Scatter "K" has no line pay, so it is absent from the paytable.
        self.paytable = {
            (5, "W"): 80,
            (5, "H1"): 80,
            (4, "H1"): 20,
            (3, "H1"): 8,
            (5, "H2"): 40,
            (4, "H2"): 15,
            (3, "H2"): 6,
            (5, "H3"): 25,
            (4, "H3"): 10,
            (3, "H3"): 4,
            (5, "H4"): 15,
            (4, "H4"): 6,
            (3, "H4"): 2.5,
            (5, "L1"): 8,
            (4, "L1"): 2.5,
            (3, "L1"): 1,
            (5, "L2"): 6,
            (4, "L2"): 2,
            (3, "L2"): 0.8,
            (5, "L3"): 5,
            (4, "L3"): 1.5,
            (3, "L3"): 0.6,
            (5, "L4"): 4,
            (4, "L4"): 1.2,
            (3, "L4"): 0.5,
            (5, "L5"): 3,
            (4, "L5"): 1,
            (3, "L5"): 0.4,
        }

        # 20 paylines for a 5x4 board (rows indexed 0=top .. 3=bottom).
        # Redesigned from the 5x3 template so all four rows pay. Every line
        # steps by at most one row between adjacent reels (smooth/traceable).
        self.paylines = {
            # 4 straights, one per row
            1: [0, 0, 0, 0, 0],
            2: [1, 1, 1, 1, 1],
            3: [2, 2, 2, 2, 2],
            4: [3, 3, 3, 3, 3],
            # tents (peak at top) and valleys (dip at bottom)
            5: [0, 1, 2, 1, 0],
            6: [3, 2, 1, 2, 3],
            7: [1, 2, 3, 2, 1],
            8: [2, 1, 0, 1, 2],
            # full-height staircases
            9: [0, 1, 2, 3, 3],
            10: [3, 2, 1, 0, 0],
            11: [0, 0, 1, 2, 3],
            12: [3, 3, 2, 1, 0],
            # zig-zags and gentle notches
            13: [1, 0, 1, 2, 3],
            14: [2, 3, 2, 1, 0],
            15: [0, 0, 1, 1, 2],
            16: [3, 3, 2, 2, 1],
            17: [1, 1, 0, 1, 1],
            18: [2, 2, 3, 2, 2],
            19: [1, 2, 1, 0, 0],
            20: [2, 1, 2, 3, 3],
        }

        self.include_padding = True
        # "K" = Key scatter (counts toward feature triggers, no line pay).
        # "multiplier" attr lets W carry a local 2x-10x value in Standard FG.
        self.special_symbols = {"wild": ["W"], "scatter": ["K"], "multiplier": ["W"]}

        # Trigger minimums per gametype (basegame 3+, freegame 2+). Only the
        # MINIMUM key matters here -- it feeds check_fs_condition and
        # anticipation_triggers. Actual spin awards are tier-based and set in
        # game_executables (update_freespin_amount / update_fs_retrigger_amt),
        # NOT indexed by exact key count, so a key-rich board showing 6+ Keys
        # can't raise a KeyError.
        self.freespin_triggers = {
            self.basegame_type: {3: 8, 4: 12, 5: 12},
            self.freegame_type: {2: 5, 3: 5},
        }
        # Hard safety cap on total freegame spins. Super/Mega no longer
        # retrigger (fixed 12 spins), and Standard's wild-rich reel rarely
        # chains, so 20 is a comfortable ceiling that also kills the old
        # 40-60 spin drag while still guaranteeing termination.
        self.max_fs_spins = 20
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys())
            - 1,
            self.freegame_type: min(self.freespin_triggers[self.freegame_type].keys())
            - 1,
        }
        # Reels (regenerate via reels/generate_reels.py):
        #   BR0    base game        FR_STD  Standard FG (wild-rich)
        #   FR_SUP Super/Mega FG    WCAP    wincap helper (both key-rich)
        reels = {
            "BR0": "BR0.csv",
            "FR_STD": "FR_STD.csv",
            "FR_SUP": "FR_SUP.csv",
            "WCAP": "FRWCAP.csv",
        }
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR_STD"]
        # Local wild multiplier distribution, Standard FG only: 2x-10x,
        # weighted toward the low end (2x common, 10x rare).
        self.padding_symbol_values = {
            "W": {"multiplier": {2: 100, 3: 60, 4: 40, 5: 25, 10: 10}}
        }

        # ---- Climbing Vault (Super / Mega Super FG) ------------------------
        # The Vault is the engine's persistent global_multiplier. In Super and
        # Mega FG, every Key landing on the board adds a random increment below
        # to the Vault, which then multiplies EVERY line win (combined
        # multiplier strategy). The Vault persists for the whole feature.
        # Standard FG never charges the Vault (it uses local wild mults).
        # Three legible tiers so the Vault climbs in readable steps and the
        # frontend can show a clear "+N" per Key (bronze 3 / silver 10 /
        # gold 25). {value: weight}. Weighted mean ~5.5 per Key -- close to
        # the old random 2-50 table's ~4.7, so balance is largely preserved
        # while the per-Key value is now something a player can actually read.
        self.vault_increment_values = {3: 75, 10: 20, 25: 5}
        # Mega Super begins with the Vault pre-charged (bigger starting point);
        # Super begins at 1x and climbs from scratch.
        self.mega_start_vault = 10

        # ---- Distribution conditions (one per simulation slice) ------------
        # scatter_triggers forces an EXACT key count so the optimizer can
        # cleanly separate Standard (3 keys) from Super (4) from Mega (5) via
        # the recorded `kind`. mult_values are the local wild multipliers
        # (Standard FG, 2x-10x). The Super/Mega climbing Vault is a separate
        # mechanic (built next) -- its increments are NOT drawn from here.
        fg_wild_mult = {2: 100, 3: 60, 4: 40, 5: 25, 10: 10}

        standard_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR_STD": 1},
            },
            "scatter_triggers": {3: 1},
            "mult_values": {
                self.basegame_type: {1: 1},
                self.freegame_type: fg_wild_mult,
            },
            "force_wincap": False,
            "force_freegame": True,
        }

        super_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR_SUP": 1},
            },
            "scatter_triggers": {4: 1},
            "mult_values": {
                self.basegame_type: {1: 1},
                self.freegame_type: fg_wild_mult,
            },
            "force_wincap": False,
            "force_freegame": True,
        }

        # Base-mode wincap can come from a natural Mega (5 keys) or Super (4).
        base_wincap_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR_SUP": 1, "WCAP": 5},
            },
            "scatter_triggers": {4: 1, 5: 2},
            "mult_values": {
                self.basegame_type: {1: 1},
                self.freegame_type: fg_wild_mult,
            },
            "force_wincap": True,
            "force_freegame": True,
        }

        # Buy-mode wincap: Super only (Mega is natural-only / not buyable).
        buy_wincap_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR_SUP": 1, "WCAP": 5},
            },
            "scatter_triggers": {4: 1},
            "mult_values": {
                self.basegame_type: {1: 1},
                self.freegame_type: fg_wild_mult,
            },
            "force_wincap": True,
            "force_freegame": True,
        }

        basegame_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}},
            "mult_values": {self.basegame_type: {1: 1}},
            "force_wincap": False,
            "force_freegame": False,
        }

        zerowin_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}},
            "mult_values": {self.basegame_type: {1: 1}},
            "force_wincap": False,
            "force_freegame": False,
        }

        # Buy cost is PROVISIONAL (~520x). Final value = Super-FG average win
        # / 0.96, set once simulation reveals the true average.
        # Slice tables (sum of slice RTP must equal self.rtp = 0.96):
        #   base:      wincap .01 | super .25 | standard .35 | basegame .35 | 0
        #   buy_super: wincap .02 | super .94
        # wincap is listed first so its sims are claimed before the broader
        # freegame slices (a wincap sim is also a freegame sim).
        mode_maxwins = {"base": 25000, "buy_super": 25000}
        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=mode_maxwins["base"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.002,
                        win_criteria=mode_maxwins["base"],
                        conditions=base_wincap_condition,
                    ),
                    Distribution(
                        criteria="super", quota=0.05, conditions=super_condition
                    ),
                    Distribution(
                        criteria="standard", quota=0.15, conditions=standard_condition
                    ),
                    Distribution(
                        criteria="basegame", quota=0.43, conditions=basegame_condition
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.35,
                        win_criteria=0.0,
                        conditions=zerowin_condition,
                    ),
                ],
            ),
            BetMode(
                name="buy_super",
                cost=520.0,
                rtp=self.rtp,
                max_win=mode_maxwins["buy_super"],
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.01,
                        win_criteria=mode_maxwins["buy_super"],
                        conditions=buy_wincap_condition,
                    ),
                    Distribution(
                        criteria="super", quota=0.99, conditions=super_condition
                    ),
                ],
            ),
        ]
