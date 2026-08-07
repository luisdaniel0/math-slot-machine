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
        # These two are REVIEWER-FACING: write_configs publishes them into
        # config_fe_starwake.json as gameName / providerName. Neither was set here
        # before, so both silently inherited src/config/config.py's scaffold defaults
        # ("sample_lines" / "sample_provider") all the way into the published config.
        self.game_name = "Starwake"
        # The studio. Also the name on the tile's third required asset,
        # ProviderName-Logo.png (must be legible at small size).
        self.provider_name = "Uptown Games"
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
        # "M" is ACT TWO's multiplier star: a real reel symbol, non-paying (absent
        # from the paytable, so it breaks a payline the way a scatter does), living
        # only on the roam strip. It is registered under its own key rather than
        # under "multiplier" -- that key marks symbols whose Multiplier attribute the
        # LINE EVALUATOR reads, and a star must never contribute its value to a win.
        # Its value rides on the cell and is collected by the beast instead.
        self.special_symbols = {
            "wild": ["W"], "scatter": ["S"], "multiplier": ["W"],
            "multiplier_star": ["M"],
        }

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
        # ⚠ RUNG COUNT IS THE *ACHIEVABLE* LONGEST ROAM, NOT THE THEORETICAL ONE.
        # These were num_feature_spins[tier]-1 (9 / 14 / 14) until Jul 30 2026, on the
        # reasoning that an immediate completion leaves N-1 roam spins. That is true and
        # it is not the right number: the top rung then requires completing on SPIN 1,
        # i.e. lighting the WHOLE constellation in a single spin. Measured organically on
        # the 1e6 pool (wincap slice excluded -- a forced cap book manufactures a spin-1
        # completion and makes a dead rung look alive):
        #     corvus  4 cells  -> roam 9 of 9  reached, 1 in 466 features   HEALTHY
        #     ursa    7 cells  -> roam 13, never 14 except 1 in 4M
        #     draco  11 cells  -> roam 13 max; rungs 13-14 ONLY in forced cap books
        #     ascend 11 cells  -> roam 13 max; its top rung was NEVER reached, anywhere
        # So the old ladders advertised multipliers that could not be won -- exactly the
        # "too long advertises rungs no player can ever be paid" failure named below,
        # which the guard test missed because it only asserted len(ladder) >= longest.
        # RE-SWEPT to the depth each tier actually reaches, holding the shipped price and
        # the top VALUE (the lists shortened; 200/500/600x did not move):
        #     corvus 9 rungs 1:200:2.5  unchanged -- already organic
        #     ursa  13 rungs 1:500:2.4  price 269x vs 268x shipped, max/cost 93x
        #     draco 12 rungs 2:600:2.0  price 523x vs 520x shipped, max/cost 48x
        # BONUS, not a side effect to be surprised by later: draco's NATURAL at-cap rate
        # went 0.004% -> 0.065% (1 in 1,818), because 600x now sits at roam 12 instead of
        # roam 14. Every forced wincap slice therefore gets much easier to satisfy -- the
        # thing that made buy_ursa's slice take 24:47 on the last full run.
        # Completion rates are UNCHANGED by any of this (63.2% / 32.1% reproduced exactly
        # across every variant): the ladder is payout-only and cannot move completion.
        self.constellation_mult_ladders = {
            # 9 rungs (10 spins, longest roam 9). 1:200:2.5
            "corvus": [1, 1, 1, 2, 3, 5, 13, 44, 200],
            # 13 rungs (15 spins, longest roam 14 -- roam 14 clamps at the top). 1:500:2.4
            "ursa": [1, 1, 1, 1, 2, 2, 3, 5, 10, 23, 55, 155, 500],
            # 12 rungs (15 spins, longest roam 14 -- roam 13-14 clamp at the top). 2:600:2
            "draco": [2, 2, 2, 3, 4, 6, 11, 20, 41, 91, 223, 600],
        }

        # THE INVARIANT THE LADDERS MUST SATISFY, and the one the old guard got wrong.
        # This is the deepest roam each tier reaches ORGANICALLY at a rate worth
        # publishing -- so the ladder covers exactly that and no more. Longer and the top
        # rung is unwinnable; shorter and we clamp away a ceiling we could have paid.
        # MEASURED per tier feature on the 1e6 pool, forced wincap books EXCLUDED:
        #     corvus roam 9  1 in    466 (buy) / 1 in  19,817 (base)   <- top is normal play
        #     ursa   roam 13 1 in 17,995 (buy) / 1 in  95,152 (base)
        #     draco  roam 12 1 in 75,112 (buy) / 1 in   1.03M (base)
        #     ascend roam 12 1 in  1,289 (mystery)
        # Draco DOES touch roam 13 organically, but at 1 in 2.5M -- technically obtainable,
        # practically a rounding error, so 12 is where its ceiling is worth putting.
        # A tier is capped by its CELL COUNT: the top rung needs the whole constellation
        # lit in one spin, which 4 cells manage and 11 never do.
        self.constellation_ladder_rungs = {"corvus": 9, "ursa": 13, "draco": 12}

        # ---------------------------------------------------- DRACO ASCENDANT
        # It IS a Draco: same 11 cells, same 2x2 beast, same 12-rung ladder, same
        # 15 spins. Derived from draco rather than copied so the two can never
        # drift -- a draco re-tune automatically re-tunes its ascendant form.
        # The ONE difference is the starting state: some cells begin LIT.
        # ⚠ ASCENDANT IS WHY DRACO'S LADDER SHORTENED TO 12 RATHER THAN 13. Sharing the
        # list means sharing the rung count, and at 13 rungs ascendant's top was reached
        # 1 in 29,658 while draco's was 1 in 2.5M. 12 serves both (1 in 1,289 and
        # 1 in 75,112). Ascendant benefits most from the change: its top rung had NEVER
        # been reached at all, because it has no forced wincap slice of its own to
        # manufacture the spin-1 completion the old 14th rung required.
        self.constellation_ladder_rungs["ascendant"] = self.constellation_ladder_rungs["draco"]
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

        # ---------------------------------------------------------- ACT TWO
        # The beast stops climbing a fixed ladder and starts COLLECTING. At wake the
        # sticky wilds are consumed (the board returns to normal symbols, the 2x2 is
        # the only wild left), and each roam spin the roam strip deals multiplier
        # stars which the block collects -- all of them, wherever they landed --
        # accumulating a multiplier that pays any line crossing the block.
        #
        # WHY. Draco ended a feature with 9.9 of 20 cells lit and 11.2 wild once the
        # beast was out: every line wins, so no win means anything -- fifteen winning
        # lines that look like a jackpot and pay a third of the ticket. Meanwhile a
        # COMPLETED draco roamed ~4.0 rungs of 12, so the ladder was a rounding error
        # and the wild carpet was the entire mode. This moves the payout onto the
        # multiplier and hands the board back to paying symbols.
        #
        # COLLECTION IS GLOBAL, APPLICATION IS POSITIONAL -- read off Rage Bait's own
        # paytable ("whenever a Wild is on the board it collects every Fish... any
        # winning line passing through the Wild is multiplied that much more"). The
        # block does not have to land on a star, so there is no positional lottery;
        # but WHERE it roams still decides which wins get paid at the new value.
        # Their collect -> cascade -> collect chain does NOT transfer: we have no
        # cascades, so it is one beat per spin.
        #
        # ⚠ SETTING A TIER'S VALUES IS WHAT SWITCHES IT TO ACT TWO. A tier absent
        # from this dict runs the original ladder unchanged. Both paths exist ONLY to
        # be A/B swept against each other -- once "can act two carry the money" is
        # measured, the loser is deleted. Do not let this become a permanent fork.
        #
        # ⚠ DENSITY IS NOT HERE. How many stars land is the ROAM STRIP's density
        # (reels/generate_reels.py, weighted to the right-hand reels because a
        # non-paying symbol on reel 0 kills a win outright while one on reel 4 only
        # shortens a 5-kind). Only the VALUE of each star is rolled from this table.
        # The two trade against each other -- more stars means more multiplier but
        # fewer paying cells -- so they sit on separate surfaces and must be swept
        # together.
        #
        # ⚠ THE ROAM STRIP IS NOT NAMED HERE. It comes from each distribution's
        # reel_weights["roam"] (see _tier_condition below), so a wincap slice can
        # weight a juiced roam strip the way it already weights WCAP. Pinning one
        # strip per tier is what made the published ceiling unreachable.
        #
        # ⚠ THE SPREAD BETWEEN THESE TABLES IS DOING ALL THE TIER SEPARATION, AND IT
        # HAS TO BE FAR WIDER THAN IT LOOKS. Consuming the sticky wilds at wake also
        # consumed the differentiation: draco used to out-pay ursa because its
        # completed board carried 11 sticky wilds to ursa's 7, and after wake the
        # cells do nothing. Both tiers now roam an identical bare board with an
        # identical 2x2 block, so the star table and roam length are all that is
        # left -- and roam length runs the WRONG WAY:
        #     tier     completes   stars collected   completion x stars
        #     corvus      83.9%          ~5.5              4.6
        #     ursa        62.6%           5.7              3.6
        #     draco       32.4%           4.6              1.5
        # Draco completes half as often AND roams shorter, so on equal tables the
        # prices order corvus > ursa > draco, backwards. The table must overcome a
        # ~3x handicap.
        #
        # SWEPT (reels/sweep_star_values.py, n=20k, premium roam strip, 1x density).
        # Mean star value per tier -> implied price, and whether the ladder holds:
        #    3.8 / 5.3 /  8.2    506 / 621 /  505x   INVERTED (ursa above draco)
        #    3.8 / 5.3 / 15.4    506 / 621 /  756x   ordered
        #    3.4 / 4.7 / 20.2    451 / 556 /  922x   ordered   <- THIS ONE
        #    3.1 / 4.2 / 26.7    423 / 511 / 1141x   ordered
        # Chosen because its three tiers sit closest to PROPORTIONAL to the
        # configured prices (1.88 / 2.08 / 1.77x of target, against the shipped
        # tables' 2.11 / 2.32 / 0.97x). Similar surplus everywhere means the
        # optimizer does similar work everywhere, so the menu shape survives
        # convergence -- where a tier at 0.97x has no surplus to remove at all and
        # would have to be repriced instead.
        #
        # ⚠ IT ALSO REPAIRS BUY_MYSTERY, WHICH IS NOT WHAT IT WAS CHOSEN FOR.
        # Ascendant SHARES draco's table and completes ~90%, so it amplifies any
        # change to draco. Measured payback split against the 14.9/14.1/23.2/47.8
        # design: shipped tables give 27.1/27.1/19.4/26.4 -- ascendant's
        # rare-and-huge identity gone and the mode flattened into four near-equal
        # outcomes -- while spread gives 16.7/16.8/24.6/41.9. Two unrelated defects,
        # one variant.
        #
        # ⚠ RAISING DRACO IS THE LEVER, NOT LOWERING URSA. "Draco's stars are worth
        # a fortune" is an identity; "ursa's stars are junk" is only a nerf.
        self.constellation_star_symbol = "M"
        self.constellation_star_values = {
            "corvus": {2: 55, 3: 25, 5: 13, 10: 6, 25: 1},
            "ursa": {2: 45, 3: 25, 5: 17, 10: 9, 25: 3, 50: 1},
            "draco": {2: 16, 3: 14, 5: 18, 10: 18, 25: 15, 50: 12, 100: 7},
        }
        self.constellation_star_values["ascendant"] = self.constellation_star_values["draco"]

        # Reels. Kept on self so export_go_config reads THIS map rather than
        # restating it -- a strip added here and missed there would leave the Go
        # engine drawing the wrong reels with no error.
        self.reel_files = {"BR0": "BR0.csv", "FR0": "FR0.csv", "WCAP": "FRWCAP.csv",
                           "ASC": "ASC.csv", "ROAM": "FRROAM.csv",
                           "ROAMCAP": "FRROAMCAP.csv"}
        self.reels = {}
        for r, f in self.reel_files.items():
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

        # ACT TWO's reel set, keyed like any other. "roam" is a third reel-weights
        # entry alongside basegame and freegame: act one draws freegame, and the
        # moment the beast wakes the engine reads THIS instead.
        #
        # ⚠ IT IS A WEIGHTED PICK, NOT A PINNED STRIP, AND THAT IS THE WHOLE POINT.
        # An earlier version named one roam strip per tier, which meant a forced
        # wincap book still drew the ORDINARY roam strip -- so it hunted a 25,000x
        # book that could not exist and HUNG, exactly as the wincap warning below
        # predicts. Keying it lets a wincap slice mix in ROAMCAP at 5:1, the same
        # trick that keeps the ceiling reachable on the freegame side with WCAP.
        roam_weights = {"ROAM": 1}
        # ⚠ URSA NEEDS A HEAVIER MIX THAN DRACO FOR THE SAME CEILING. Both must
        # reach 25,000x, but ursa gets there from a weaker tier (7 cells, star table
        # topping at 50x against draco's 100x), so its forced cap cost ~1,940
        # redraws per wincap book against draco's ~117. That is not just slow: a
        # forced slice has NO retry cap, so a rate that drifts to zero HANGS rather
        # than failing, and 1-in-1,940 is one tuning change away from zero.
        # Cost of the heavier mix is aesthetic only -- wincap books are forced to
        # pay the ceiling either way, so this changes how FAST they are found, not
        # the distribution. It does mean ursa's max-win replays all share the juiced
        # strip's premium-heavy look, on top of FRWCAP already doing that to act one.
        roam_wincap_weights = {"ROAM": 1, "ROAMCAP": 5}
        ursa_roam_wincap_weights = {"ROAM": 1, "ROAMCAP": 20}

        def _tier_condition(star_count):
            """Force exactly `star_count` stars -> deal that one tier, run the feature."""
            return {
                "reel_weights": {
                    self.basegame_type: {"BR0": 1},
                    self.freegame_type: {"FR0": 1},
                    "roam": dict(roam_weights),
                },
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
            "reel_weights": {
                self.basegame_type: {"ASC": 1},
                self.freegame_type: {"FR0": 1},
                "roam": dict(roam_weights),
            },
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
        # CORVUS JOINED THEM Aug 6 2026, AT ITS OWN 9,000x CEILING -- the "stays out"
        # note that lived here is superseded and its two premises are both gone:
        #  1. It was written when corvus advertised 25,000x and targeted an act-ONE
        #     ladder top of 800. Corvus now publishes 9,000x, a figure it reaches
        #     organically, so the slice manufactures a plausible round rather than an
        #     out-of-reach one.
        #  2. The ">cost 25.1% -> 14.5%" body cost was a SINGLE-DRAW measurement. An
        #     n=8 variance run (Aug 6) put corvus's body spread at 26 POINTS run to run,
        #     so that number never distinguished a real cost from noise. The slice's
        #     actual RTP price is arithmetic and tiny: rate * cap / cost
        #     = (1/2,000,000) * 9,000 / 120 = 0.00375% of the mode's RTP.
        # WHAT IT BUYS: corvus's cap rate stops being an optimizer draw. Measured over 8
        # identical runs it ranged 1 in 2.9M to 1 in 11.2M, and ONE OF THE EIGHT missed
        # the ~1-in-10M obtainability guideline outright. A slice makes the rate a number
        # we set. It also removes the tail as a free variable, which is why the body
        # wandered 26 points while RTP converged to 0.9665 every single time.
        # ⚠ A forced slice LOOPS FOREVER if its cap drifts out of structural reach, so
        # ursa's is the one thing to watch on the first run after this change.
        def _wincap_condition(star_count, roam_mix=None):
            return {
                "reel_weights": {
                    self.basegame_type: {"BR0": 1},
                    self.freegame_type: {"FR0": 1, "WCAP": 5},
                    # The act two half of the same trick -- without it the roam
                    # phase draws ordinary reels and the forced cap never lands.
                    "roam": dict(roam_mix or roam_wincap_weights),
                },
                "scatter_triggers": {star_count: 1},
                "mult_values": fg_mult,
                "force_wincap": True,
                "force_freegame": True,
            }

        # CORVUS'S MIX IS THE HEAVIEST OF THE THREE, and for a different reason than
        # ursa's. Ursa needs ROAMCAP 20 because 25,000x is far above its comfortable
        # range. Corvus's target is only 9,000x -- but that sits at the very TOP of what
        # corvus can organically produce (natural max measured 9,158x on a 1e6 pool, so
        # >=9,000x is ~1 in 2.5M unforced). A forced slice therefore has to manufacture a
        # near-best-case round every time, which is exactly the condition the LOOPS
        # FOREVER warning above is about. 40 is a FIRST GUESS -- measure redraws per
        # wincap book on a small run before trusting it at 1e6. Draco's is ~117.
        corvus_roam_wincap_weights = {"ROAM": 1, "ROAMCAP": 40}

        corvus_wincap_condition = _wincap_condition(3, corvus_roam_wincap_weights)
        ursa_wincap_condition = _wincap_condition(4, ursa_roam_wincap_weights)
        draco_wincap_condition = _wincap_condition(5)

        # ASCENDANT'S OWN WINCAP, added Aug 6 2026 so buy_mystery's forced cap books are
        # ASCENDANT rolls rather than draco ones. NOT _wincap_condition(6): that helper
        # draws BR0 for the basegame, where six scatters succeed ~20% of the time against
        # ~92% on ASC (see ascendant_condition above). Everything else mirrors the helper.
        #
        # WHY: measured on the shipped pool, max-win rate per roll INSIDE buy_mystery was
        # draco 1 in 317 vs ascendant 1 in 939 -- backwards. Every forced cap book in the
        # mode was a draco roll, so draco got all the help and ascendant only kept its
        # organic leftovers. Ascendant is the tier that cannot be bought and carries 46%
        # of the mode's payback on 10% of its rolls; it should own the max win.
        # ⚠ THIS IS A RELABELLING, NOT A REBALANCE. The slice quota, the total cap weight
        # and mystery_cap_rtp are all unchanged, and every cap book pays exactly 25,000x
        # whichever tier produced it -- so the mode's payout distribution, p5k, p10k, CVaR
        # and ETL are untouched. Only the constellation on screen when it lands changes.
        ascendant_wincap_condition = {
            "reel_weights": {
                self.basegame_type: {"ASC": 1},
                self.freegame_type: {"FR0": 1, "WCAP": 5},
                "roam": dict(roam_wincap_weights),
            },
            "scatter_triggers": {6: 1},
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
        # 10,000x UNTIL Aug 5 2026, when it became a lie. Act two removed the
        # fully-wild-board route to the ceiling, and across a full 1e6 pool corvus
        # topped out at 9,158x -- so the published figure failed the guidelines'
        # "the maximum win amount matches the description in the game rules for each
        # mode". Corvus has NO wincap slice to force it, so this is the only lever.
        # 9,000x rather than 9,158x deliberately: 9,158 is ONE SEED'S observed
        # maximum, and publishing at the observed max leaves 1.7% of margin against
        # a number that moves whenever anything is retuned. At 9,000x the rate is
        # 1 in 2.48M against a ~1-in-10M guideline, with room to spare.
        corvus_cap = 9000.0

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
            #
            # ⚠ 240x UNTIL Aug 5 2026, WHEN IT MADE CORVUS UNBUYABLE. Measured on the
            # converged act two pool, corvus was LAST on ceiling-per-cost (38.2x
            # against ursa's 93.3x and draco's 48.1x) and second-worst on median,
            # with a beat rate inside the other three's noise -- ursa cost 12% more
            # and offered 2.7x the ceiling, because ursa reaches the global 25,000x
            # cap while corvus's is organic. No ceiling number fixes that: even at
            # 10,000x corvus was 41.7x cost, still last. A longer feature does not
            # either (reels/sweep_feature_spins.py: it works, and compresses the
            # 84/63/32 completion ladder to 93/85/55 doing it).
            # Re-optimizing the same 1e6 pool at 120x gives ceiling-per-cost 76.3x,
            # clearing draco and approaching ursa, and the max win STAYS OBTAINABLE
            # at 1 in 4.7M -- it survives because the ceiling is ~0.001% of RTP, so
            # a lower target is met by reweighting the body, not the tail.
            # The menu becomes 120 / 268 / 520 / 563: a ladder, where 240 and 268
            # were two names for the same rung.
            BetMode(
                name="buy_corvus", cost=120.0, rtp=self.rtp, max_win=corvus_cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    # ⚠ win_criteria is corvus_cap (9,000), NOT the global cap. This mode
                    # clamps at 9,000 via BetMode.max_win, so a slice searching for
                    # 25,000 would hunt a book that cannot exist and hang forever.
                    # Quota is deliberately smaller than ursa's 0.005: the optimizer
                    # weights these down to 1 in 2M regardless, so the quota only has to
                    # supply ENOUGH DISTINCT BOOKS that every max win is not the same
                    # replay -- and each one costs a redraw loop to manufacture.
                    Distribution(criteria="wincap", quota=0.002, win_criteria=corvus_cap,
                                 conditions=corvus_wincap_condition),
                    Distribution(criteria="corvus", quota=0.998, conditions=corvus_condition),
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
            # COST IS THE MEASURED OUTPUT, not the round target. RE-PRICED 526 -> 563x
            # (Jul 30 2026) by the ladder re-sweep, and the cause is worth keeping:
            # ascendant SHARES draco's ladder, and shortening draco 14 -> 12 rungs
            # rewards exactly what ascendant does best -- completing early and riding
            # the top of the ladder. Its mean went 2,249 -> 2,598x (n=20k, 100%
            # ascendant, wincap stripped) with no change to its cells, its pre-lit set
            # or the mix. New mix mean 0.350*232.0 + 0.295*260.0 + 0.250*505.5 +
            # 0.100*2598 = 544.1x, so cost = 544.1/0.9665 = 563x.
            # ASCENDANT'S PRICE LEVER IS TOO COARSE TO UNDO THIS: its only independent
            # knob is the pre-lit cell set, and the neighbouring sets bracket the target
            # badly (~956x vs ~2,249x on the original sweep), so there is no set that
            # lands back on 526. Holding 526 would have meant either decoupling
            # ascendant's ladder from draco's (losing the "it IS a draco" invariant and
            # the no-drift guarantee) or cutting ascendant below 10% of rolls (losing
            # the "1 in 10 wakes something you cannot buy" story). Taking the price
            # instead: 563x keeps the menu ordered (240/268/520/563), stays well under
            # the 1,000x buy cap, and moves ascendant's payback share 44.3% -> 47.8%,
            # CLOSER to the Rage Bait shape this mode is modelled on (10% of rolls
            # carrying 52% of payback).
            # ⚠ WATCH ON THE 1e6 RUN: ascendant now caps ORGANICALLY at 1.49% of its
            # features (it could not reach 25,000x at all before), which implies a
            # mystery cap rate near 1 in 670 -- more often than buy_draco's 1 in 963.
            # That is defensible (mystery is the dearest bet and carries a 35% chance of
            # rolling the cheap tier) but it inverts "draco is the cap play", so
            # re-measure cap-value-per-stake across the menu before shipping.
            BetMode(
                name="buy_mystery", cost=563.0, rtp=self.rtp, max_win=cap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    # Forced caps are ASCENDANT rolls (was draco until Aug 6 2026 -- see
                    # ascendant_wincap_condition for the measurement that prompted it).
                    # The single "wincap" opt fence searches payout == 25,000 and so still
                    # matches these; no opt_params change is needed, and fence order still
                    # puts wincap ahead of the kind=6 ascendant body fence, which is what
                    # keeps the forced books out of the body slice.
                    Distribution(criteria="wincap", quota=0.005, win_criteria=cap, conditions=ascendant_wincap_condition),
                    Distribution(criteria="ascendant", quota=0.100, conditions=ascendant_condition),
                    Distribution(criteria="draco", quota=0.250, conditions=draco_condition),
                    Distribution(criteria="ursa", quota=0.295, conditions=ursa_condition),
                    Distribution(criteria="corvus", quota=0.350, conditions=corvus_condition),
                ],
            ),
        ]
