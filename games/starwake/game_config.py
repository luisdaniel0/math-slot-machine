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
        # manufactures sticky wilds).
        # ASYMMETRIC RESCALE (measure loop): 5-kinds /4, 4-kinds /2, 3-kinds HELD.
        # The wild carpet extends nearly every line to full length, so the feature
        # takes 61% of its money from 5-kinds while the base game takes only 13%
        # (measured, pre-multiplier, over 40k base + 3k feature books). Cutting the
        # TOP of the ladder therefore drains the feature x2.49 while costing the
        # base only x1.29 -- a uniform cut of the same feature size would have cost
        # the base x2.50. Holding the 3-kinds keeps the dust intact: frequent-crumb
        # texture (market's biggest paying bucket is 0.25-0.5x) funds the hit-rate
        # floor cheaply, keeping the RTP budget in the tail.
        # The trade this makes: ladder steepness drops from ~x4/step to ~x2/step,
        # so volatility must come from where the design always said it does --
        # completion-time x tier tail -- not from symbol steepness.
        # H1=Leo, H2=Cygnus, H3=Aquila, H4=Lupus; lows = card-rank line-art.
        self.paytable = {
            (5, "W"): 15,
            (5, "H1"): 12,
            (4, "H1"): 6,
            (3, "H1"): 3,
            (5, "H2"): 6,
            (4, "H2"): 4,
            (3, "H2"): 2,
            (5, "H3"): 4,
            (4, "H3"): 2.5,
            (3, "H3"): 1.5,
            (5, "H4"): 3,
            (4, "H4"): 2,
            (3, "H4"): 1,
            (5, "L1"): 1.2,
            (4, "L1"): 0.75,
            (3, "L1"): 0.5,
            (5, "L2"): 1,
            (4, "L2"): 0.6,
            (3, "L2"): 0.4,
            (5, "L3"): 0.75,
            (4, "L3"): 0.5,
            (3, "L3"): 0.3,
            (5, "L4"): 0.6,
            (4, "L4"): 0.4,
            (3, "L4"): 0.2,
            (5, "L5"): 0.5,
            (4, "L5"): 0.3,
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
            # head cells -> rarely completes (dragon lottery). Hard cells = the
            # FULL reel-4 column (4,0..4,3) + one reel-3 neck (3,2). RESHAPED from
            # the old (3,0)(3,1)+(4,1)(4,2)(4,3) which plateaued ~46% (too warm).
            # KEY FINDING (sim-derived, no clean analytic rate): completion is
            # driven overwhelmingly by how many hard cells sit on reel 4 -- the
            # DRIEST strip (FR0 reel-4 W=0), so a reel-4 cell can only light when a
            # winning line crosses it, not from a native wild. Reel-3 (FR0 W=3) is
            # a much softer gate; a single easy reel-3 neck (row 2, high payline
            # traffic) is the fine knob. Full reel-4 column alone = ~11-15%; adding
            # the (3,2) neck lifts it to ~28% (measured, buy_draco 4k books) = the
            # ~30% dragon-lottery target. Ladder now corvus ~95 / ursa ~54 / draco
            # ~28. Thematically the dragon's head forms LAST, only once the wild
            # carpet floods the whole right edge. Nudge the neck (row 1 -> ~36%,
            # rows 0/3 hard -> ~11-15%) if the measure loop wants a different rate.
            #
            # SHAPE SWEEP (sweep_draco_cells.py, n=40k each, FR0 W=4/3/0):
            #   easy/gate  6/5 (this)  11.9%  cost  651x  max/cost 30x   <- best
            #              8/3         40.4%  cost 1965x  max/cost 11x
            #              5/6         19.7%  cost 1111x  max/cost 18x
            #              7/4         16.2%  cost  894x  max/cost 24x
            # This shape won on every axis, so it STAYS -- and note the reason 5/6
            # loses. A reel-3 cell is a gate AND A KEY: once lit it is a sticky wild
            # sitting on reel 3, which is precisely the bridge a 5-kind needs to
            # reach the reel-4 column. ONE neck cell is a net gate; TWO flip it into
            # a net key and completion goes UP despite there being more cells to
            # light. Cell count is not difficulty -- position relative to the dry
            # column is. Do not "harden" Draco by adding reel-3 cells.
            "draco": [
                (0, 2), (0, 3), (1, 1), (1, 2), (2, 0), (2, 1),
                (3, 2), (4, 0), (4, 1), (4, 2), (4, 3),
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
        # enumerable ladder, one rung per roam spin. This list IS the compliance
        # "all obtainable values" table, so it is written out rather than derived.
        #
        # The SHAPE is the tail, and the tail is the product. A flat +1 climb
        # (the first-pass 2..10) made the luckiest run only ~3x an ordinary one,
        # which measured out as buy_draco mean 787x / max 5,040x -- a dependable
        # grinder with 28.8% of features over 1000x and NO reachable 25,000x.
        # Accelerating rungs fix that without touching the median: the early rungs
        # stay near the old values, so a LATE completion (common -> short roam)
        # plays as before, while a rare EARLY completion rides all nine rungs.
        # Nine rungs = the longest possible roam (num_feature_spins - 1); roam()
        # clamps at the top so a length change can never run off the end.
        #
        # Tier spread is the other half of the identity (CLAUDE.md): corvus stays
        # the tame "reliable beast hunt", draco becomes the lottery.
        # Every ladder STARTS AT 1-2, not 2-3. Measured: the feature's raw payout
        # before any multiplier already costs 89/101/165x against a 50/100/200x
        # budget, so a starting rung above 1 is a tax charged on the common case
        # (a short roam) on every single feature. Low early rungs pull the mean
        # down; high tops push the ceiling up; the same edit does both, which no
        # paytable change can. Corvus accelerates too -- it completes 96% of the
        # time and used to pay nearly the same every run (max/cost 4x), so even
        # the "reliable" tier needs a reason to want a FAST completion.
        self.constellation_mult_ladders = {
            "corvus": [1, 1, 2, 3, 4, 6, 8, 11, 15],
            "ursa": [1, 2, 3, 5, 8, 12, 18, 26, 38],
            "draco": [2, 3, 6, 11, 20, 35, 60, 100, 165],
        }

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
        # loop (cost = avg win / rtp; displayed max = observed max); ante's 1.5x is a
        # design input (the premium). Only Draco (3x3) can structurally reach 25,000x,
        # so buy_corvus/buy_ursa carry NO forced-wincap slice (forcing an unreachable
        # cap would loop) and publish measured lower ceilings instead -- see the
        # BetMode.max_win note below. Wild-mult ladder is DORMANT under Option A
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

        cap = self.wincap  # 25,000x -- reachable by Draco only

        # PER-MODE DISPLAYED CEILINGS. BetMode.max_win is BOTH the published "max win"
        # (write_configs.py:356 -> config.json "maxWin") AND the engine clamp: run_sims
        # assigns it to config.wincap for that mode, state.py rebuilds WinManager from
        # it per thread, and executables.evaluate_wincap stops the book the moment
        # running_bet_win reaches it. So a ceiling is honest BY CONSTRUCTION once set --
        # the question is only which number to advertise. Corvus/ursa have no
        # win_criteria and force_wincap=False, and check_repeat only repeats on a
        # win_criteria mismatch, so capped books are KEPT (clamped), not redrawn.
        #
        # Measured on the converged 1e6 pool (post-optimization lookup tables):
        #   corvus natural max 1,515.35x -> publish 1,500x  (1 in 136,561, RTP -0.00000)
        #   ursa   natural max 4,773.80x -> publish 4,750x  (1 in 671,949, RTP -0.00000)
        # Rounded DOWN to the nearest clean number under the natural max: the sliver
        # above it is all that clamps, so RTP is untouched to 5dp and the Phase B
        # convergence survives, while corvus keeps the 6.7x max/cost ratio the
        # accelerating ladder was re-tuned to buy (it was 4x before). Cutting deeper
        # would make the ceiling far more frequent (corvus 1,250x is 1 in 2,262) at the
        # cost of that ratio -- a volatility change, not a display fix, so it waits for
        # the structural/playtest pass. Both are DECISIONS the clamp enforces, not
        # sample statistics: a deeper future sample cannot push the true max past them.
        corvus_cap = 1500.0
        ursa_cap = 4750.0

        # BUY COSTS = measured avg win / rtp (doc L115: prices are outputs). Read off
        # sweep_fr0.py at n=40k with the forced-wincap slice REMOVED -- that slice is a
        # sampling quota, not a probability, so leaving it in inflates the average and
        # would price the mode off a pool the optimizer is about to re-weight anyway.
        # corvus/ursa are single-distribution modes, so their pools ARE natural.
        # mystery is the 60/30/10 blend of the three tier means (0.6*217 + 0.3*274 +
        # 0.1*630 = 275x). These are INPUTS to optimization even though they are
        # OUTPUTS of design -- refine them from the 1e6 pool, then re-run `run.py
        # optimize` alone (the optimizer step does not need the sims regenerated).
        # base stays 1.0 by definition; ante is a bet multiplier chosen by design.
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
            # global cap); publishes -- and clamps at -- its own measured ceiling.
            BetMode(
                name="buy_corvus", cost=224.0, rtp=self.rtp, max_win=corvus_cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="corvus", quota=1.0, conditions=corvus_condition),
                ],
            ),
            # buy_ursa: pin the coin-flip tier. Same story as corvus, higher ceiling.
            BetMode(
                name="buy_ursa", cost=283.0, rtp=self.rtp, max_win=ursa_cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="ursa", quota=1.0, conditions=ursa_condition),
                ],
            ),
            # buy_draco: pin the greedy tier -- THE 25,000x product. Wincap slice.
            BetMode(
                name="buy_draco", cost=651.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="wincap", quota=0.01, win_criteria=cap, conditions=draco_wincap_condition),
                    Distribution(criteria="draco", quota=0.99, conditions=draco_condition),
                ],
            ),
            # buy_mystery: "Let the Sky Decide" -- weighted mix, discounted vs picking.
            # Wincap slice funds its draco share reaching the cap.
            BetMode(
                name="buy_mystery", cost=285.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="wincap", quota=0.005, win_criteria=cap, conditions=draco_wincap_condition),
                    Distribution(criteria="mystery", quota=0.995, conditions=mystery_condition),
                ],
            ),
        ]
