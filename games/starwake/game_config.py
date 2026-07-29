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

        # Fixed-length feature, length PER TIER: corvus 10, ursa 15, draco 15.
        # This REVISES the original "scatter count scales the TIER, never the spin
        # count" rule. That rationale was about VOLATILITY (vol must come from
        # completion-time x tier, not from a longer feature) and it still holds --
        # but length turned out to be a PRICE lever, which is a different job.
        # Feature length fixes the SHAPE, ladders fix the PRICE, cell maps fix tier
        # SEPARATION. Measured (reels/sweep_ladder.py, Jul 2026):
        #   DRACO + URSA NEED 15. buy_draco's >cost rate EQUALS its completion rate
        #     exactly (the carpet tops out below cost, so you beat the ticket iff you
        #     complete), and completion is a function of how many spins you get to
        #     light cells. 10 -> 15 took draco 12% -> 32.3% completion, >cost 7.7% ->
        #     19.7% (market norm ~22%), and CLOSED the win-range gap -- the "Draco
        #     cliff", a hard compliance gate: widest hole 7.73x -> 1.19x. Ursa at 12
        #     spins collapses 63.2% -> 46.1% completion and prices at ~175x against a
        #     ~300x target, so it stays at 15 too (the tidier 10/12/15 does not work).
        #   CORVUS NEEDS 10. It already completes ~94% at 15 spins and mean-roams 8.81
        #     of a possible 14, so extra spins add no completions -- they just lengthen
        #     every roam, lifting the BODY while the ceiling stands still (its max/cost
        #     got WORSE at 15 spins, 6.7x -> 4x). No ladder gets corvus under ~375x at
        #     15 spins (swept curve up to 5.5); 12 spins reads 327x; 10 spins prices the
        #     same ladder family at 202-274x. That is the whole reason for the split.
        # No retriggers for any tier (run_freespin omits the retrigger check); bounded
        # length is load-bearing for volatility AND replay watchability.
        # 6+ scatters clamp to the 5-scatter tier (star-rich strips WILL show them --
        # exact-count indexing was a keybearer KeyError).
        # 6 stars = DRACO ASCENDANT, the mystery-exclusive fourth outcome. It is a
        # real scatter count rather than a flag, so tier selection stays uniform
        # (count -> tier) and needs no special case anywhere in the engine.
        # IT CANNOT LEAK OUT OF buy_mystery, structurally: draw_board redraws away
        # every unforced board with >=3 scatters, and the forced branch enforces an
        # EXACT count, so a 6-scatter board only exists where 6 was explicitly
        # forced -- which only the ascendant distribution does.
        self.num_feature_spins = {"corvus": 10, "ursa": 15, "draco": 15, "ascendant": 15}
        self.scatter_tiers = {3: "corvus", 4: "ursa", 5: "draco", 6: "ascendant"}
        # DERIVED, never hand-written: the engine awards spins by scatter COUNT
        # (game_override.update_freespin_amount reads freespin_triggers[gametype][count])
        # while the design thinks in TIERS. Deriving it means a length change is a
        # one-line edit above and the two views can never drift apart.
        _tier_spins = {c: self.num_feature_spins[t] for c, t in self.scatter_tiers.items()}
        self.freespin_triggers = {
            self.basegame_type: dict(_tier_spins),
            # structural only — retriggers are disabled in gamestate.run_freespin
            self.freegame_type: dict(_tier_spins),
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

        # Beast block sizes as (reel_span, row_span). ALL 2x2 as of Jul 2026 (was
        # 2x2 / 2x3 / 3x3). THE ROAM BARELY WORKS ABOVE 2x2: roam positions on a 5x4
        # are 2x2=12, 2x3=8, 3x3=6, 2x4=4, so the 3x3 dragon shuffled between six
        # spots covering 45% of the board -- the signature "beast roams each spin"
        # mechanic was undermined on the showpiece tier. One size is also one
        # frontend sprite rig and one roam animation instead of three, and 2x2 is
        # the readable market block-wild idiom.
        # TIER IDENTITY SURVIVES VIA STICKY CELLS, not beast footprint: at wake the
        # board is 8 / 11 / 15 of 20 cells wild (4/7/11 lit + the 2x2). The
        # constellation covers the sky; the beast prowls over it.
        # Still spans 2 reels, so it cannot self-pay a short wild line over a longer
        # real-symbol line (doc line 62).
        self.constellation_beast_shapes = {
            "corvus": (2, 2),
            "ursa": (2, 2),
            "draco": (2, 2),
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
        # RUNG COUNT = that tier's longest possible roam = num_feature_spins[tier] - 1,
        # so it is 9 for corvus (10 spins) and 14 for ursa/draco (15). roam() clamps at
        # the top so a length change can never run off the end -- which is exactly why
        # a mismatch is silent and dangerous: a 9-rung ladder under a 15-spin feature
        # clamps from the 9th roam on and caps that tier's ceiling with no error.
        # tests/starwake/test_run_freespin.py::test_every_ladder_covers_the_longest_
        # possible_roam is the guard; keep it passing on any length edit.
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
        # Every ladder here is GEOMETRIC, so it is really two numbers -- a start and
        # a top -- and they do separate jobs. START prices the COMMON case (most
        # completions are late and only ever see rungs 0-1), so it sets where the
        # cheapest completion lands = the bottom of the Draco cliff. TOP prices the
        # RARE case (only an early completion reaches it), so it sets the ceiling.
        # That asymmetry is why the ladder is the one knob that can lower the mean
        # and raise the max at once; a paytable cut scales body and tail together.
        # SWEPT VALUES (Jul 2026, reels/sweep_ladder.py). A ladder is THREE numbers,
        # not fourteen -- these lists are GENERATED, then pasted here so the
        # compliance "all obtainable values" table stays literal and auditable:
        #     ladder[i] = start * (top/start) ** ((i / (n-1)) ** curve)
        # curve=1 is a plain geometric ladder; curve>1 is CONVEX -- it holds the early
        # rungs down and lets the top explode, which is what decouples a tier's body
        # from its ceiling. Chosen: corvus 1:200:2.5 / ursa 1:500:2 / draco 2:600:1.5.
        #
        # WHY THESE. The sweep's central finding is that THE CEILING IS NEARLY FREE IN
        # PRICE AND EXPENSIVE IN BODY. Corvus at 10 spins moved from a 2,444x ceiling to
        # 25,000x for only 202x -> 274x of price, while its >cost rate fell 34.1% ->
        # 14.5% and median/price 0.55 -> 0.29. So the question is never "can we afford
        # the dream", it is "how much grind do we trade for it". Each tier stops at the
        # point where its own identity survives (docs/ideas/starwake.md: corvus =
        # reliable beast hunt, ursa = coin flip, draco = wild carpet + dragon lottery):
        #   CORVUS 1:200:2.5 -> price 239x, ceiling 10,661x = 45x return-on-stake (was
        #     6.7x), >cost 25.1%, widest hole 1.29x, median 0.39x ticket. Corvus CAN
        #     reach 25,000x (top 800 caps at ~1 in 2,500, easily forceable) and that was
        #     REJECTED: it drops >cost to 14.5%, below the ~22% norm and below where
        #     draco sat before the cliff fix, and the ladder goes flat -- [1,1,1,1,2,3,8,
        #     50,800] does not move for the first FIVE of nine rungs, against a pitch
        #     that says the multiplier climbs every spin. Corvus's best-in-game body is
        #     its differentiation; it is not for sale. 1:200:2.5 was also picked over
        #     more convex variants because it starts climbing by rung 3.
        #   URSA 1:500:2 -> price 266x, ceiling 17,220x, >cost 22.5%, hole 1.50x. The
        #     "ceiling is nearly free" result replicates here even harder: ursa's price
        #     sits in 266-284x across ceilings from 4,238x all the way to 17,220x,
        #     because it completes 63% at a mean roam of ~5 of 14, so the typical buy
        #     sits LOW on the ladder where the curve is still flat. Its ceiling is the
        #     cheapest in the game; taking the tall one costs ~1% of >cost.
        #   DRACO 2:600:1.5 -> price 524x, ceiling 25,000x at 0.005% (~1 in 20,000),
        #     >cost 20.0%, hole 1.22x. The at-cap frequency matters structurally, not
        #     just cosmetically: a forced-wincap slice HANGS FOREVER if the cap is out
        #     of reach, and 1 in 20,000 clears the ~1e-6 gate by ~50x. Note draco's
        #     max/cost is arithmetically capped at 50x (25,000 / 500) so its 48x is the
        #     maximum available, not a tuning miss -- do not chase the 50-100x band here.
        # PRICE FIGURES ARE n=20k AND CARRY ~+/-20x (one 20,000x outcome moves the mean
        # by 1x). Trends are solid; exact prices come from the 1e6 convergence run.
        self.constellation_mult_ladders = {
            # 9 rungs (10 spins). 1:200:2.5
            "corvus": [1, 1, 1, 2, 3, 5, 13, 44, 200],
            # 14 rungs (15 spins). 1:500:2
            "ursa": [1, 1, 1, 1, 2, 3, 4, 6, 11, 20, 40, 86, 199, 500],
            # 14 rungs (15 spins). 2:600:1.5
            "draco": [2, 2, 3, 4, 5, 8, 12, 19, 31, 53, 94, 169, 315, 600],
        }

        # ---------------------------------------------------- DRACO ASCENDANT
        # It IS a Draco: same 11 cells, same 2x2 beast, same 14-rung ladder, same
        # 15 spins. Derived from draco rather than copied so the two can never
        # drift -- a draco re-tune automatically re-tunes its ascendant form.
        # The ONE difference is the starting state: some cells begin LIT.
        for _d in ("constellation_cells", "constellation_beast_shapes",
                   "constellation_mult_ladders"):
            getattr(self, _d)["ascendant"] = getattr(self, _d)["draco"]

        # WHICH cells are pre-lit matters far more than how many -- SWEPT, n=20k
        # (reels/sweep_ascendant.py), judged on the mystery price each one implies:
        #   pre-lit            mean  complete  at cap   -> mystery cost
        #   (none)             510x     32.2%   0.00%       346x
        #   (3,2) neck         589x     34.9%   0.01%       354x
        #   (3,2)(4,0)         956x     45.2%   0.05%       392x
        #   (4,0)(4,1)       2,249x     89.6%   0.09%       526x   <- CHOSEN
        #   (3,2)(4,0)(4,1)  2,742x     90.7%   0.36%       577x
        #   3 body cells     1,339x     49.3%   0.09%       431x
        #
        # KEY FINDING -- PRE-LIGHTING AND SHAPE ARE OPPOSITE PROBLEMS. The shape rule
        # above says a reel-3 cell is a gate AND A KEY, so never harden a tier by
        # adding one. That does NOT transfer to pre-lighting: the neck is nearly
        # worthless pre-lit (510 -> 589x), while an adjacent reel-4 PAIR is
        # transformative (510 -> 2,249x, completion 32% -> 90%). Same cell count,
        # 2.4x the payout. Reel 3 already carries wilds (FR0 W=3) so it is not the
        # binding constraint; reel 4 is BONE DRY (W=0), so two permanent wilds there
        # are the only thing that makes the column reachable at all -- and every win
        # that then crosses it lights the rest of the column.
        #
        # Pre-lighting pays through TWO channels and the second dominates:
        #   1. fewer cells to trace -> completes earlier -> higher ladder rungs;
        #   2. those cells are WILDS FROM SPIN ONE -> every win is richer all feature.
        # Channel 2 is why a roam-length model underestimates badly: this set
        # completes at mean roam 6.06 where the draco roam table predicts ~1,350x,
        # and it pays 2,249x. It is also why the body-cell control still reached
        # 1,339x despite barely improving completion.
        self.constellation_prelit_cells = {
            "ascendant": [(4, 0), (4, 1)],
        }

        # Which CREATURE a tier renders as. Identity and artwork are the same thing
        # for the three normal tiers, but an Ascendant is a Draco -- the frontend
        # must draw the dragon, not invent a fourth beast. Emitted on the deal and
        # wake events so the client never has to special-case a tier name.
        self.constellation_beast_names = {
            "corvus": "corvus", "ursa": "ursa",
            "draco": "draco", "ascendant": "draco",
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
        # 5 -> 2 (Jul 2026): the floor was CARRYING ~70% of buy_draco's value and
        # creating the win-range gap. Three step-changes fire together at completion
        # (board goes near-fully wild, the multiplier switches on for the FIRST time,
        # and the floor guarantees N spins of it), so a floor of 5 put the cheapest
        # possible completion at 3,016x against a carpet that tops out at 336x --
        # a 9x hole across buy_draco's own cost, and a hard compliance gate.
        # Measured (reels/sweep_beast.py): cliff 9.0x at roam>=5, 2.5x at >=3, 1.1x
        # at >=2 = CLOSED. It also serves the doc's own "finish early = longer roam"
        # goal: that span is 5->9 spins at floor 5 (1.8x) but 2->14 at floor 2.
        # "Even a last-spin completion pays" survives -- 2 roam spins still pay well
        # above anything the carpet can produce. Restore the price in the LADDER
        # TOPS, never by putting the floor back.
        self.min_roam_spins = 2

        # Reels
        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "WCAP": "FRWCAP.csv",
                 "ASC": "ASC.csv"}
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
        # design input (the premium). Ursa and Draco both reach 25,000x and both carry a
        # forced-wincap slice; only buy_corvus has none, and it publishes an honest lower
        # ceiling instead -- see the BetMode.max_win note below for why that is a product
        # decision rather than a structural limit. Wild-mult ladder is DORMANT under Option A
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

        # DRACO ASCENDANT: 6 stars, dealt only from the ASC strip. That strip is the
        # only one that can show six -- _force_special_board places at most ONE
        # scatter per reel, so a sixth needs a reel whose window reveals two, which
        # ASC guarantees by construction (reel 2 laid down as a step-3 run). Forcing
        # 6 succeeds on ~92% of attempts there; on BR0 it would be ~20% and would
        # break silently the next time BR0's weights are touched.
        ascendant_condition = {
            "reel_weights": {self.basegame_type: {"ASC": 1}, self.freegame_type: {"FR0": 1}},
            "scatter_triggers": {6: 1},
            "mult_values": fg_mult,
            "force_wincap": False,
            "force_freegame": True,
        }

        # NOTE: "Let the Sky Decide" no longer uses a single blended condition with
        # weighted scatter_triggers. buy_mystery now draws ONE DISTRIBUTION PER TIER
        # (reusing corvus/ursa/draco/ascendant conditions above) so the optimizer can
        # fence each tier separately -- see the buy_mystery BetMode below for why the
        # blended version inverted the published tier ladder.

        # Wincap: force the tier, then weight in the juiced WCAP strip. force_wincap
        # plus a slice win_criteria repeat the draw until the book reaches the cap.
        #
        # URSA JOINED DRACO AT THE CAP (Jul 2026). It was excluded back when each tier
        # had its own beast and only the 3x3 was believed to reach 25,000x -- but every
        # beast is 2x2 now, and the 100k confirmation run measured ursa reaching the cap
        # NATURALLY (once in 99,960, before any forcing). The exclusion was a measurement
        # gap, not a structural fact.
        # CORVUS STAYS OUT, and that is a choice rather than a limit: the sweep showed it
        # can reach the cap with ladder top 800 (~1 in 2,500, easily forceable), but only
        # by trading away the best body in the game (>cost 25.1% -> 14.5%, under the ~22%
        # market norm) and flattening its ladder for five of nine rungs against a pitch
        # that says the multiplier climbs every spin. It publishes an honest 10,000x.
        # ⚠ A forced slice LOOPS FOREVER if its cap drifts out of structural reach, so
        # ursa's is the one thing to watch on the first run after this change.
        def _wincap_condition(star_count):
            return {
                "reel_weights": {
                    self.basegame_type: {"BR0": 1},
                    self.freegame_type: {"FR0": 1, "WCAP": 5},
                },
                "scatter_triggers": {star_count: 1},
                "mult_values": fg_mult,
                "force_wincap": True,
                "force_freegame": True,
            }

        ursa_wincap_condition = _wincap_condition(4)
        draco_wincap_condition = _wincap_condition(5)

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

        cap = self.wincap  # 25,000x -- reachable by Draco AND Ursa (see below)

        # PER-MODE DISPLAYED CEILINGS. BetMode.max_win is BOTH the published "max win"
        # (write_configs.py:356 -> config.json "maxWin") AND the engine clamp: run_sims
        # assigns it to config.wincap for that mode, state.py rebuilds WinManager from
        # it per thread, and executables.evaluate_wincap stops the book the moment
        # running_bet_win reaches it. So a ceiling is honest BY CONSTRUCTION once set --
        # the question is only which number to advertise. Corvus/ursa have no
        # win_criteria and force_wincap=False, and check_repeat only repeats on a
        # win_criteria mismatch, so capped books are KEPT (clamped), not redrawn.
        #
        # SETTLED Jul 28 2026 -- published ceilings are 10,000 / 25,000 / 25,000.
        # Measured on the 100k confirmation pool (wincap slice stripped, clamp lifted):
        #   corvus natural max 11,438x -> publish 10,000x   (4 books above it in 100k)
        #   ursa   natural max 25,000x -> publish 25,000x   (reached the cap unforced)
        #   draco  natural max 25,000x -> publish 25,000x
        #
        # URSA AND DRACO SHARE THE CAP, and that is deliberate. The market precedent is
        # explicit (Rage Bait's buys cost 250-500x and ALL of them reach the 25,000x
        # cap), so multiple buys at one ceiling is the norm rather than a defect. It also
        # costs nothing: publishing 15,000x instead would have clipped 5 books in 100,000
        # and moved ursa's mean by 0.077%.
        # WHAT MAKES DRACO WORTH 1.94x URSA'S PRICE IS THEN CAP FREQUENCY, NOT CEILING.
        # Cap-value-per-stake is rate * cap / cost, so the two are equal when draco's
        # rate is exactly its price ratio, 520/268 = 1.94x ursa's -- below that, draco is
        # a strictly worse cap play AND costs more, which is the failure this whole
        # arrangement has to avoid. The rates are set in game_optimization.py, where a
        # wincap slice's rtp share IS its frequency (rate = slice_rtp * cost / cap), and
        # they are targeted at ~4.5x so draco delivers ~2.3x the cap value per stake.
        #
        # BetMode.max_win is BOTH the published "max win" (write_configs.py:356 ->
        # config.json "maxWin") AND the engine clamp: run_sims assigns it to
        # config.wincap for that mode, state.py rebuilds WinManager from it per thread,
        # and executables.evaluate_wincap stops the book the moment running_bet_win
        # reaches it. So a ceiling is honest BY CONSTRUCTION once set -- the only
        # question is which number to advertise, and no deeper future sample can exceed
        # it. Corvus has no win_criteria and force_wincap=False, and check_repeat only
        # repeats on a win_criteria mismatch, so its clamped books are KEPT, not redrawn.
        # Corvus is rounded DOWN from its natural max so only the sliver above clamps and
        # RTP survives to 5dp.
        corvus_cap = 10000.0

        # BUY COSTS = measured avg win / rtp (doc L115: prices are outputs). Read off
        # reels/measure_tiers.py at n=100k with the forced-wincap slice REMOVED -- that
        # slice is a sampling quota, not a probability, so leaving it in inflates the
        # average and would price the mode off a pool the optimizer is about to
        # re-weight anyway. Measured means 232.1 / 258.6 / 502.4x -> 240 / 268 / 520x.
        # mystery is the 60/30/10 blend of those means (0.6*232.1 + 0.3*258.6 +
        # 0.1*502.4 = 267.1 -> 276x) and is PROVISIONAL: the Draco Ascendant tier will
        # change both the mix and the price. These are INPUTS to optimization even
        # though they are OUTPUTS of design -- refine them from the 1e6 pool, then
        # re-run `run.py optimize` alone (that step does not need the sims regenerated).
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
            # buy_corvus: pin the safe tier. NO forced-wincap slice -- not because the
            # cap is unreachable (it can be bought with a taller ladder) but because
            # buying it costs corvus the best body in the game. The deliberate grind
            # tier: highest >cost, lowest ceiling.
            BetMode(
                name="buy_corvus", cost=240.0, rtp=self.rtp, max_win=corvus_cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="corvus", quota=1.0, conditions=corvus_condition),
                ],
            ),
            # buy_ursa: pin the coin-flip tier -- now ALSO a 25,000x product, at a
            # deliberately rarer cap than draco (see the ceilings note above).
            BetMode(
                name="buy_ursa", cost=268.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="wincap", quota=0.005, win_criteria=cap, conditions=ursa_wincap_condition),
                    Distribution(criteria="ursa", quota=0.995, conditions=ursa_condition),
                ],
            ),
            # buy_draco: pin the greedy tier -- the 25,000x product players pay for,
            # earning its price with ~4.5x ursa's cap rate rather than a taller ceiling.
            BetMode(
                name="buy_draco", cost=520.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="wincap", quota=0.01, win_criteria=cap, conditions=draco_wincap_condition),
                    Distribution(criteria="draco", quota=0.99, conditions=draco_condition),
                ],
            ),
            # buy_mystery: "Let the Sky Decide" -- 35 / 29.5 / 25 / 10 corvus / ursa /
            # draco / ASCENDANT, plus the wincap slice.
            #
            # ONE DISTRIBUTION PER TIER, not a single blended one. The old single
            # "mystery" fence let the optimizer reshape each tier freely to hit RTP,
            # which INVERTED the published ladder -- rolling Draco paid less on
            # average than rolling Corvus, while the UI advertised Draco as the prize.
            # Per-tier distributions give each tier its own fence (kind=3/4/5/6) so
            # its shape is pinned, exactly as base/ante already do it.
            #
            # ASCENDANT IS WHY THIS MODE CAN BE PRICED ABOVE THE TIER BUYS. A mystery
            # is the probability-weighted average of what it can roll, so it is always
            # cheaper than its most expensive tier -- it reaches 500x only at ~100%
            # draco, which is buy_draco with a worse name. A fourth outcome that
            # CANNOT BE BOUGHT lifts the average without that trap.
            # COST IS THE MEASURED OUTPUT, not the round target: with Ascendant at
            # 2,249x (swept, n=20k) the mix means 0.350*232.1 + 0.295*258.6 +
            # 0.250*502.4 + 0.100*2249 = 508.0x, so cost = 508.0/0.9665 = 526x. That
            # is 5% over the 500x market-standard price; trimming Ascendant to ~9% of
            # rolls would land it on 500 exactly, which is a product call, not a math
            # one. Re-derive from the 1e6 pool either way.
            BetMode(
                name="buy_mystery", cost=526.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="wincap", quota=0.005, win_criteria=cap, conditions=draco_wincap_condition),
                    Distribution(criteria="ascendant", quota=0.100, conditions=ascendant_condition),
                    Distribution(criteria="draco", quota=0.250, conditions=draco_condition),
                    Distribution(criteria="ursa", quota=0.295, conditions=ursa_condition),
                    Distribution(criteria="corvus", quota=0.350, conditions=corvus_condition),
                ],
            ),
        ]
