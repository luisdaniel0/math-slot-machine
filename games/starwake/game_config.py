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

        # Guaranteed minimum roam window. The beast must get at least this many
        # on-board (paying) spins after it wakes so "even a last-spin completion
        # still pays" (docs/ideas/starwake.md L47-48). This is a FLOOR, not the
        # volatility lever: an early completion already roams to the fixed end
        # ("finish early = longer roam" = the fat tail, L200-201); the floor only
        # extends the feature past num_feature_spins when completion lands too
        # late to fit it. Tuning knob (design doc L255); set to 5 (up from the
        # initial 3) so a late completion still gets a satisfying roam, while an
        # early completion is unaffected and keeps its longer roam (the tail).
        self.min_roam_spins = 5

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

        # ----------------------------------------------------------- bet modes (6)
        # docs/ideas/starwake.md "Bet modes (6)". CORRECTED MODEL: the dealt TIER is
        # forced by scatter_triggers (an exact star count -> self.scatter_tiers deals
        # that constellation), NOT by strip star density. Buys pin one tier;
        # base/ante draw a natural mix (via the per-tier slice quotas); mystery draws
        # a weighted mix whose displayed odds must match the shipped math.
        #
        # COSTS and per-mode DISPLAYED max wins are OUTPUTS measured in the measure
        # loop (cost = avg win / rtp; displayed max = observed max). Costs below are
        # PLACEHOLDERS; ante's 1.5x is a design input (the premium). Every BetMode
        # max_win = the global cap so nothing is silently truncated -- but only Draco
        # (3x3) can structurally reach 25,000x, so buy_corvus/buy_ursa carry NO forced-
        # wincap slice (forcing an unreachable cap would loop) and will DISPLAY honest
        # lower ceilings once measured. Wild-mult ladder is DORMANT under Option A
        # (game_override pins every wild to x1; the beast is the only multiplier), so
        # freegame mult_values are {1:1}.
        fg_mult = {self.basegame_type: {1: 1}, self.freegame_type: {1: 1}}

        def _tier_condition(star_count):
            """Force exactly `star_count` stars -> deal that one tier, run the feature."""
            return {
                "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
                "scatter_triggers": {star_count: 1},
                "mult_values": fg_mult,
                "force_wincap": False,
                "force_freegame": True,
            }

        corvus_condition = _tier_condition(3)
        ursa_condition = _tier_condition(4)
        draco_condition = _tier_condition(5)

        # "Let the Sky Decide": weighted-random tier. These weights ARE the displayed
        # odds target (60/30/10, doc L113) -- the shipped odds are the MEASURED post-
        # optimization proportions (the wincap slice adds a little draco), verified to
        # match the UI (compliance: probabilities display accurately).
        mystery_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
            "scatter_triggers": {3: 60, 4: 30, 5: 10},
            "mult_values": fg_mult,
            "force_wincap": False,
            "force_freegame": True,
        }

        # Wincap: only Draco reaches the cap, so force 5 stars + weight in the juiced
        # WCAP strip. force_wincap + a slice win_criteria repeat the draw until it caps.
        draco_wincap_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1, "WCAP": 5}},
            "scatter_triggers": {5: 1},
            "mult_values": fg_mult,
            "force_wincap": True,
            "force_freegame": True,
        }

        # Non-triggering base spins (draw_board redraws these to <3 stars). "0" is the
        # forced-loss slice; "basegame" is the paying base slice (funds the hit floor).
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

        cap = self.wincap  # engine clamp; per-mode DISPLAYED ceilings are measured
        self.bet_modes = [
            # base (1x): natural 3/4/5-star mix (quotas ~ the 67/25/8 identity) + a
            # draco wincap slice + base/zero spins that fund the hit floor.
            BetMode(
                name="base", cost=1.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=True, is_buybonus=False,
                distributions=[
                    Distribution(criteria="wincap", quota=0.001, win_criteria=cap, conditions=draco_wincap_condition),
                    Distribution(criteria="draco", quota=0.007, conditions=draco_condition),
                    Distribution(criteria="ursa", quota=0.025, conditions=ursa_condition),
                    Distribution(criteria="corvus", quota=0.067, conditions=corvus_condition),
                    Distribution(criteria="basegame", quota=0.5, conditions=basegame_condition),
                    Distribution(criteria="0", quota=0.4, win_criteria=0.0, conditions=zerowin_condition),
                ],
            ),
            # ante_starfall (~1.5x, design input): more triggers + a richer tier mix
            # (higher ursa/draco quotas) + fewer dead spins -> smoother, LOWER vol.
            BetMode(
                name="ante_starfall", cost=1.5, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=True, is_buybonus=False,
                distributions=[
                    Distribution(criteria="wincap", quota=0.0015, win_criteria=cap, conditions=draco_wincap_condition),
                    Distribution(criteria="draco", quota=0.015, conditions=draco_condition),
                    Distribution(criteria="ursa", quota=0.045, conditions=ursa_condition),
                    Distribution(criteria="corvus", quota=0.10, conditions=corvus_condition),
                    Distribution(criteria="basegame", quota=0.5, conditions=basegame_condition),
                    Distribution(criteria="0", quota=0.3, win_criteria=0.0, conditions=zerowin_condition),
                ],
            ),
            # buy_corvus: pin the safe tier. No forced-wincap slice (2x2 can't reach the
            # cap); the displayed ceiling is an honest measured lower bound.
            BetMode(
                name="buy_corvus", cost=6.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="corvus", quota=1.0, conditions=corvus_condition),
                ],
            ),
            # buy_ursa: pin the coin-flip tier. Honest measured lower ceiling.
            BetMode(
                name="buy_ursa", cost=20.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="ursa", quota=1.0, conditions=ursa_condition),
                ],
            ),
            # buy_draco: pin the greedy tier -- THE 25,000x product. Wincap slice.
            BetMode(
                name="buy_draco", cost=100.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="wincap", quota=0.01, win_criteria=cap, conditions=draco_wincap_condition),
                    Distribution(criteria="draco", quota=0.99, conditions=draco_condition),
                ],
            ),
            # buy_mystery: "Let the Sky Decide" -- weighted mix, discounted vs picking.
            # Wincap slice funds its draco share reaching the cap.
            BetMode(
                name="buy_mystery", cost=40.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="wincap", quota=0.005, win_criteria=cap, conditions=draco_wincap_condition),
                    Distribution(criteria="mystery", quota=0.995, conditions=mystery_condition),
                ],
            ),
        ]
