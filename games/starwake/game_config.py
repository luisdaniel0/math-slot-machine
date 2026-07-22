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
        self.game_id = "starwake"
        self.provider_number = 0
        self.working_name = "Starwake"
        self.wincap = 25000.0
        self.win_type = "lines"
        # converge ~0.9665 so displayed RTP rounds to 96.7% while staying under
        # the 0.967 Stake cap (see docs/ideas/starwake.md Benchmarks)
        self.rtp = 0.9665
        self.construct_paths()

        # Game Dimensions
        self.num_reels = 5
        self.num_rows = [4] * self.num_reels
        # Board and Symbol Properties
        # Values are total-bet multiples PER LINE, stacking across lines.
        # W pays 5-kind ONLY (no 3/4-kind entries -> short wild lines can never
        # override longer real-symbol lines; critical because the feature
        # manufactures sticky wilds). Top at 50x (cooler than keybearer's 80)
        # because the carpet + climbing beast amplify substituted 5-kinds.
        # Low 3-kinds pay dust on purpose: frequent-crumb texture (market's
        # biggest paying bucket is 0.25-0.5x) funds the hit-rate floor cheaply,
        # keeping the RTP budget in the tail. Steep ladders (~x4/step) = vol.
        # H1=Leo, H2=Cygnus, H3=Aquila, H4=Lupus; lows = card-rank line-art.
        self.paytable = {
            (5, "W"): 60,
            (5, "H1"): 50,
            (4, "H1"): 12,
            (3, "H1"): 3,
            (5, "H2"): 25,
            (4, "H2"): 8,
            (3, "H2"): 2,
            (5, "H3"): 15,
            (4, "H3"): 5,
            (3, "H3"): 1.5,
            (5, "H4"): 12,
            (4, "H4"): 4,
            (3, "H4"): 1,
            (5, "L1"): 5,
            (4, "L1"): 1.5,
            (3, "L1"): 0.5,
            (5, "L2"): 4,
            (4, "L2"): 1.2,
            (3, "L2"): 0.4,
            (5, "L3"): 3,
            (4, "L3"): 1.0,
            (3, "L3"): 0.3,
            (5, "L4"): 2.5,
            (4, "L4"): 0.8,
            (3, "L4"): 0.2,
            (5, "L5"): 2,
            (4, "L5"): 0.6,
            (3, "L5"): 0.2,
        }

        # 20 lines spanning all 4 rows (proven set from the keybearer 5x4 build)
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
        # "S" is the Star: bonus trigger by count (3/4/5 -> Corvus/Ursa/Draco)
        # in base, and the constellation-cell filler inside the feature
        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": ["W"]}

        # Fixed-length feature: EVERY tier awards the same 10 spins. Scatter
        # count scales the TIER (which constellation is dealt), never the spin
        # count — vol must come from completion-time x tier, not feature length.
        # No retriggers for any tier (run_freespin omits the retrigger check);
        # bounded length is load-bearing for volatility AND replay watchability.
        # 6+ scatters clamp to the 5-scatter tier (star-rich strips WILL show
        # them — exact-count indexing was a keybearer KeyError).
        self.num_feature_spins = 10
        self.scatter_tiers = {3: "corvus", 4: "ursa", 5: "draco"}
        self.freespin_triggers = {
            self.basegame_type: {c: self.num_feature_spins for c in (3, 4, 5)},
            # structural only — retriggers are disabled in gamestate.run_freespin
            self.freegame_type: {c: self.num_feature_spins for c in (3, 4, 5)},
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys())
            - 1,
            self.freegame_type: min(self.freespin_triggers[self.freegame_type].keys())
            - 1,
        }

        # Constellation cell-maps: which (reel, row) cells each tier occupies on the
        # 5x4 grid. A cell lights when a WINNING PAYLINE crosses it (win-line fill),
        # then becomes a sticky wild. Difficulty is driven by reel position: the left
        # 3 reels sit in the paid run of almost any win (light easily); reels 3-4 need
        # 4-5 symbol wins to reach (rarely light). So more cells on reels 3-4 = harder
        # tier. Hard-cell counts: Corvus 0, Ursa 2, Draco 5 — that IS the tier ladder.
        # FIRST-PASS placements: exact completion rates are sim-derived now (analytic
        # coupon-collector model retired), so expect to nudge individual cells in the
        # measure loop. Shapes are independent (never on screen together) — cell reuse
        # across tiers is fine. See docs/ideas/starwake.md + the cell-map figure.
        self.constellation_cells = {
            # 4-star diamond, all on the easy left reels -> completes ~always
            "corvus": [(0, 1), (1, 0), (1, 2), (2, 1)],
            # 7-star dipper: 4-star bowl (left, easy) + 3-star handle whose tip
            # reaches 2 hard cells (3,0),(4,1) -> coin-flip completion
            "ursa": [(0, 1), (0, 2), (1, 1), (1, 2), (2, 0), (3, 0), (4, 1)],
            # 11-star serpent: 6-star body (left, easy = the wild carpet) + 5 hard
            # head/tail cells on reels 3-4 -> rarely completes (dragon lottery)
            "draco": [
                (0, 2), (0, 3), (1, 1), (1, 2), (2, 0), (2, 1),
                (3, 0), (3, 1), (4, 1), (4, 2), (4, 3),
            ],
        }

        # Beast block sizes as (reel_span, row_span). The block "spans 2-3 reels"
        # so it can't self-pay a short wild line over a longer real-symbol line
        # (doc line 62). Corvus/Ursa span 2 reels, Draco 3 -> matches "2-3 reels".
        self.constellation_beast_shapes = {
            "corvus": (2, 2),
            "ursa": (2, 3),
            "draco": (3, 3),
        }
        # Option A (see the sticky-star analysis): the BEAST is the only multiplier
        # source. Sticky lit stars are plain wilds (x1); the beast carries an
        # enumerable climbing ladder -- starts at beast_start_mult on wake, +climb
        # each roam spin. Both are TUNING knobs (doc lines 255-257) and the primary
        # high-vol dial alongside the tier spread.
        self.beast_start_mult = 2
        self.beast_climb = 1

        # Reels
        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "WCAP": "FRWCAP.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]
        self.padding_symbol_values = {
            "W": {"multiplier": {2: 100, 3: 50, 4: 50, 5: 50, 10: 30, 20: 20, 50: 5}}
        }

        freegame_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {3: 50, 4: 20, 5: 5},
            "mult_values": {
                self.basegame_type: {1: 1},
                self.freegame_type: {
                    2: 60,
                    3: 80,
                    4: 50,
                    5: 20,
                    10: 15,
                    20: 10,
                    50: 5,
                },
            },
            "force_wincap": False,
            "force_freegame": True,
        }

        basegame_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}},
            "mult_values": {self.basegame_type: {1: 1}},
            "force_wincap": False,
            "force_freegame": False,
        }

        wincap_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1, "WCAP": 5},
            },
            "mult_values": {
                self.basegame_type: {1: 1},
                self.freegame_type: {
                    2: 10,
                    3: 20,
                    4: 50,
                    5: 60,
                    10: 100,
                    20: 90,
                    50: 50,
                },
            },
            "scatter_triggers": {4: 1, 5: 2},
            "force_wincap": True,
            "force_freegame": True,
        }

        zerowin_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}},
            "mult_values": {
                self.basegame_type: {1: 1},
                self.freegame_type: {2: 100, 3: 80, 4: 50, 5: 20, 10: 10, 20: 5, 50: 1},
            },
            "force_wincap": False,
            "force_freegame": False,
        }

        mode_maxwins = {"base": self.wincap, "bonus": self.wincap}
        # Contains all game-logic simulation conditions
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
                        quota=0.001,
                        win_criteria=mode_maxwins["base"],
                        conditions=wincap_condition,
                    ),
                    Distribution(
                        criteria="freegame", quota=0.1, conditions=freegame_condition
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.4,
                        win_criteria=0.0,
                        conditions=zerowin_condition,
                    ),
                    Distribution(
                        criteria="basegame", quota=0.5, conditions=basegame_condition
                    ),
                ],
            ),
            BetMode(
                name="bonus",
                cost=100.0,
                rtp=self.rtp,
                max_win=mode_maxwins["bonus"],
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["bonus"],
                        conditions=wincap_condition,
                    ),
                    Distribution(
                        criteria="freegame", quota=0.1, conditions=freegame_condition
                    ),
                ],
            ),
        ]
