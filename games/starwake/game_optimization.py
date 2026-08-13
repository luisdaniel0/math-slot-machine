"""Optimization inputs for all six Starwake bet modes.

opt_params tells the optimizer how to RE-WEIGHT each mode's generated books to hit
the mode RTP (0.9665): a per-criteria RTP split (verify_optimization_input asserts
it sums to the mode RTP and that every distribution criteria appears here), a
volatility band (min/max mean-to-median), and light scaling/bias refinements.

The RTP splits, hit-rate hints, m2m bands and scaling below are FIRST-PASS starting
targets, not final. The measure loop iterates them against 1e6-sim reality: a target
a slice's books can't produce is a convergence failure -> adjust the number HERE, not
the optimizer (the two-stage lesson -- the optimizer only re-weights, it can't invent
outcomes). NOTE ConstructConditions needs rtp PLUS one of hr/av_win (rtp alone trips
its none_count guard), so every slice carries a hint even though rtp is authoritative.

Criteria per mode MUST match game_config's distribution criteria:
  base / ante_starfall : wincap, draco, ursa, corvus, basegame, 0
  buy_ursa             : wincap, ursa          buy_draco  : wincap, draco
  buy_mystery          : wincap, ascendant, draco, ursa, corvus
  buy_mystery_spin     : wincap, draco, ursa, corvus
Every mode carries a wincap slice. buy_corvus was removed Aug 13 2026 and replaced
by buy_mystery_spin; see DECISIONS.md for the measurement that decided it.

⚠ buy_mystery_spin's cap is 15,000x, NOT 25,000x, and it is the only mode that does
not publish the headline number. One spin with one 2x2 block tops out at a measured
19,778x regardless of roam density, so a slice aimed at the global cap would loop
forever. wincaps[] carries the per-mode value, so every derivation picks it up.

A WINCAP SLICE'S rtp SHARE IS ITS FREQUENCY, which is the only dial that sets how
often a mode pays its max win:

    rate = slice_rtp * cost / cap        (equivalently slice_rtp = rate * cap / cost)

so slice_rtp is literally the share of that mode's RTP delivered by cap books.
Verified against the shipped pool: base at slice_rtp 0.02 and cost 1.0 measured
P = 8.0e-07, exactly 0.02 * 1.0 / 25000.

THAT IS WHAT MAKES DRACO WORTH ITS PRICE. Ursa and Draco publish the same 25,000x
ceiling, so the ceiling cannot differentiate them -- cap-value-per-stake is
rate * cap / cost, which means they break even when draco's rate is exactly its
price ratio (520/268 = 1.94x ursa's). Below that, buying draco is strictly worse
AND more expensive.

THE CAP-SHARE LADDER (revised Jul 2026 after a stakestats survey of Rage Bait,
Coins & Cauldrons, MIKO, Waylanders Forge, Red Strike and Dojo Duel). slice_rtp IS
cap-value-per-stake, so this list is literally "who is the best max-win bet per
dollar", and it must read down the menu in the order the UI sells it:

    base              0.020
    ante              0.025
    buy_ursa          0.030  (was 0.0215 -- BELOW ante, i.e. inverted)
    buy_mystery       0.040  (was 0.0199 -- below ante AND below ursa)
    buy_mystery_spin  0.050  (1 in 2,000 at a 15,000x cap -- see below)
    buy_draco         0.075  (was 0.050 -- raised to keep the crown as the others rise)

⚠ buy_mystery_spin BREAKS THE "cap-value-per-stake" READING OF THIS LADDER, because
slice_rtp is only comparable across modes sharing a cap. Its 0.05 buys 1 in 2,000 at
15,000x; the same share at 25,000x would buy 1 in 3,333. Compare ceiling-per-cost
instead: 100x here against ursa 83x, draco 62x, mystery 50x.

The old ladder had ante beating two of the four buys, which is backwards from every
audited game: they all put the most cap value in the buys (Rage Bait: base 0.045,
super 0.056, mystery 0.064). Draco rises with the rest so draco/ursa goes 2.33x ->
2.5x -- the tier story gets stronger, not weaker. All six sit far inside the 2-star
risk gates measured off the shipped LUTs (worst p5k 1.1e-03 vs 1e-02, worst p10k
5.9e-04 vs 8e-02, worst ETL40 0.385 vs 0.8, worst CVaR 234 vs 700), which is what
made this headroom safe to spend.
"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    ConstructFenceBias,
    verify_optimization_input,
)


class OptimizationSetup:
    """Builds and verifies game_config.opt_params for every bet mode."""

    def __init__(self, game_config):
        self.game_config = game_config
        wincaps = {bm.get_name(): bm.get_wincap() for bm in game_config.bet_modes}
        costs = {bm.get_name(): bm.get_cost() for bm in game_config.bet_modes}
        rtp = game_config.rtp  # 0.9665 -- every mode converges here

        # -- small builders: keep the six entries DRY and the RTP split legible --
        def run_params(min_m2m, max_m2m, test_spins, test_weights, per_fence=10000):
            """Optimizer run config; the m2m band encodes the mode's vol identity.

            ⚠ `per_fence` was parameterised Aug 7 2026 while hunting the RTP undershoot
            on the two-fence modes (corvus 0.9661, ursa 0.9662, draco 0.9650, against
            0.9665 exact on every six-fence mode). IT DID NOT HELP -- see the note on
            buy_draco. Left as a knob because it is free, but do not expect it to move RTP.
            """
            return ConstructParameters(
                num_show=5000, num_per_fence=per_fence, min_m2m=min_m2m, max_m2m=max_m2m,
                pmb_rtp=1.0, sim_trials=5000, test_spins=test_spins,
                test_weights=test_weights, score_type="rtp",
            ).return_dict()

        def wincap_cond(mode, slice_rtp):
            """Forced 25,000x books: pin the search + av_win hint to the cap."""
            return ConstructConditions(
                rtp=slice_rtp, av_win=wincaps[mode], search_conditions=wincaps[mode]
            ).return_dict()

        def feature_cond(slice_rtp, hr, kind=None):
            """A tier/feature slice: rtp is authoritative, hr the trigger-rate hint
            (buys feature every spin -> hr=1; base/ante trigger 1-per-hr spins).

            `kind` is the scatter COUNT recorded at trigger (3/4/5 = corvus/ursa/
            draco) and it is mandatory wherever a mode has more than one tier fence.
            Fences are assigned IN ORDER and consume every book they match, so three
            fences all searching {"symbol": "scatter"} let the first one swallow all
            the feature books and the optimizer dies on the next with "matched 0
            books after prior fences were assigned". Single-tier modes (the buys)
            can omit it; buy_mystery MUST omit it, since its one fence is meant to
            cover the whole 3/4/5 blend.
            """
            search = {"symbol": "scatter"}
            if kind is not None:
                search["kind"] = kind
            return ConstructConditions(rtp=slice_rtp, hr=hr, search_conditions=search).return_dict()

        def base_cond(slice_rtp, hr):
            """Paying base-game slice: rtp + the any-win hit-rate hint."""
            return ConstructConditions(rtp=slice_rtp, hr=hr).return_dict()

        zero_cond = ConstructConditions(rtp=0.0, av_win=0, search_conditions=0).return_dict()

        # damp the mid tail / lift the upper tail of a feature criteria (shape vol)
        # ⚠⚠ MYSTERY BARBELLS WITHOUT THESE. MEASURED Aug 12 2026, TWO DRAWS.
        # Concentrating 60% of payback into ascendant leaves the corvus and draco
        # fences having to DISCARD 34% and 40% of their natural value, and the
        # optimizer's cheapest way to discard value is to pile weight onto
        # near-worthless books. Undressed, on identical books, it hollowed the middle
        # out and moved the weight to BOTH ends (draw 1 / draw 2 under-0.25x 61.7% /
        # 68.4%, against 44.4% before the roll-mix change):
        #     band x ticket   before -> after      band x ticket  before -> after
        #     0    - 0.25     40.2%  -> 61.7%      2  - 5          8.1%  ->  7.2%
        #     0.25 - 0.5      24.3%  -> 15.8%      5  - 10         3.9%  ->  6.0%
        #     0.5  - 1        14.6%  ->  4.8%      50 +            0.0%  ->  0.1%
        # The 7-point gap between the two draws is this mode's own noise; both sit in
        # the 60s, so it is the SHAPE that is wrong, not the draw. Same disease the
        # corvus rebuild note documents, and the same treatment: suppress the dump zone
        # FROM ZERO, boost the band the fence's own mean lands in, fund it off the top.
        #
        # ⚠ RANGES ARE DERIVED FROM THE TICKET, NOT TYPED IN. Every hardcoded band in
        # this file has gone stale at least once when its mode was repriced (corvus's
        # (30,60)/(60,120)/(120,240) were written for a 240x ticket and were boosting
        # the dump zone by the time it cost 120x). Deriving them means a reprice moves
        # them automatically and the annotation can never disagree with the numbers.
        _MYSTERY_EDGES = (0.0, 0.25, 0.5, 1.0, 2.0, 5.0, 50.0)  # x ticket; 50x == the cap

        def mystery_bands(criteria, factors):
            """Gapless scaling bands for one tier fence inside buy_mystery.

            GAPLESS IS THE POINT. Three bands with holes between them let the
            optimizer put whatever it likes in the holes, which is how a 21-point
            body swing showed up on corvus. Every range carries a factor here, so no
            part of the distribution is left to its discretion.
            """
            ticket = costs["buy_mystery"]
            return [
                {"criteria": criteria, "scale_factor": f,
                 "win_range": (int(lo * ticket), int(hi * ticket)), "probability": 1.0}
                for (lo, hi), f in zip(zip(_MYSTERY_EDGES, _MYSTERY_EDGES[1:]), factors)
            ]

        def tail_scaling(criteria):
            return [
                {"criteria": criteria, "scale_factor": 0.8, "win_range": (1000, 2000), "probability": 1.0},
                {"criteria": criteria, "scale_factor": 1.2, "win_range": (3000, 4000), "probability": 1.0},
            ]

        # lift the frequent small base wins (the hit floor)
        # ⚠ (2,5) ADDED Aug 7 2026 -- ITS ABSENCE WAS CREATING A HOLE. This list boosted
        # (1,2) and (10,20) and left (2,5) alone, so the optimizer down-weighted the
        # unboosted band between two boosted ones. Delivered odds ran 1 in 18 (1-2x),
        # 1 in 273 (2-5x), 1 in 211 (5-10x), 1 in 182 (10-20x) -- a 15x rarity spike and
        # back down, in a curve that is otherwise smooth. It is NOT a supply problem:
        # 2-5x holds 4.79% of raw books, more than DOUBLE 5-10x's 2.30%, and was being
        # down-weighted 13x against that band's 4.9x.
        # Found by diffing our curve against Coins and Cauldrons, which runs 1 in 21
        # smoothly through the same band (see BENCHMARKS.md). It passes the win-range-gap
        # check either way -- no zero-weight range -- but it is exactly the kind of
        # pothole a reviewer eyeballing a hit-rate table would query.
        base_small_scaling = [
            {"criteria": "basegame", "scale_factor": 1.2, "win_range": (1, 2), "probability": 1.0},
            {"criteria": "basegame", "scale_factor": 2.0, "win_range": (2, 5), "probability": 1.0},
            {"criteria": "basegame", "scale_factor": 1.5, "win_range": (10, 20), "probability": 1.0},
        ]

        def maxwin_boost(criteria, ceiling, factor):
            """Lift the weight of near-ceiling books so a published max win clears the
            'realistically obtainable' gate (docs: typically better than 1 in 10,000,000).

            ONLY needed where a mode has no forced wincap slice to set the rate directly.
            buy_corvus is that mode: its 10,000x ceiling is reached ORGANICALLY, measured
            at P = 8.52e-08 = 1 in 11.7M on the shipped pool -- ~17% the wrong side of the
            gate. Its whole cap contribution is P*ceiling/cost = 0.00036% of the mode's
            RTP, so lifting it is free in RTP terms; the constraint is book diversity, not
            budget (the pool holds only 16 at-cap corvus books vs thousands in the forced-
            slice modes). ⚠ SCALING IS A SEARCH HINT, NOT A CONSTRAINT -- the optimizer
            biases toward it while solving for RTP, so the delivered rate MUST be measured
            off the new LUT, not assumed. If it still lands under 1e-07, the deterministic
            fallback is a real wincap Distribution for buy_corvus in game_config (that is
            a re-sim, not an optimizer-only run, and it is safe from the classic
            forced-slice hang precisely because those 16 books prove the cap is reachable).
            """
            return [
                {
                    "criteria": criteria,
                    "scale_factor": factor,
                    "win_range": (int(ceiling * 0.9), int(ceiling)),
                    "probability": 1.0,
                }
            ]


        # ⚠⚠ PAYOUT-RANGE FENCES WERE TESTED HERE Aug 7 2026 AND ARE NOT AVAILABLE
        # WITHOUT A RE-SIM. Recording it so nobody re-derives it:
        #   ConstructConditions DOES turn a tuple search_conditions into
        #   identity_condition.win_range_start/end, and write_configs writes the fence
        #   name as a plain label -- the Rust matcher keys on identity_condition, not
        #   the name. So banding a single-criteria mode LOOKS free. It is not:
        #   1. FENCES MUST BE MUTUALLY EXCLUSIVE. Keeping the {"symbol":"scatter"}
        #      catch-all beside a (60,240) range fence fails with "fence 'corvus'
        #      matched 0 books after prior fences were assigned ... an earlier
        #      overlapping fence may consume all matching book IDs." A catch-all
        #      overlaps every range fence, so the whole mode has to be banded at once.
        #   2. AND THEN verify_optimization_input REFUSES: "Distribution criteria must
        #      match 'conditions' keys". Fence names are checked against the BetMode's
        #      Distribution criteria, so three payout bands need three Distributions in
        #      game_config -- which is a re-sim, not an optimizer-only run.
        # => For shape work on a single-criteria buy, USE DRESSES. Fences are only free
        #    where the mode already has one Distribution per outcome (base/ante/mystery).

        mystery_cap_rtp = 0.040
        # ⚠ REWEIGHTED Aug 12 2026 to 35 / 35 / 20 / 10 (was 35 / 29.5 / 25 / 10). This
        # MUST match the generation quotas in game_config's buy_mystery BetMode, and it
        # is a RE-SIM: quotas decide which books exist, hr decides how often each is
        # delivered, and only re-generating moves the published odds. Nothing else can
        # -- a reprice or a ceiling change provably cannot, which this file has had to
        # re-establish four separate times.
        # Only the RATIOS matter here: _roll_total below normalises them.
        mystery_roll_mix = {"corvus": 0.350, "ursa": 0.350, "draco": 0.200, "ascendant": 0.100}
        # ⚠ RE-DERIVED Aug 12 2026 for the 500x reprice. THE RULE IS EXPLICIT NOW:
        # every purchasable tier rolled inside mystery is worth the SAME FRACTION
        # (~78%) of buying it outright, and ascendant absorbs the rest. At cost 500
        # the standalone-fair values are corvus 193.4x, ursa 290.1x, draco 386.8x
        # (rtp * that tier's own price), so:
        #   corvus 0.35*152.3 = 53.3   ursa 0.35*227.7 = 79.7
        #   draco  0.20*303.6 = 60.7   asc  0.10*2697  = 269.7   (+ 20.0 cap slice)
        #   = 483.45x = rtp * 500.
        # ASCENDANT NOW CARRIES 60% OF PAYBACK ON 10% OF ROLLS (was 49.86%), which
        # is 5.79x the ticket per roll against 4.83x before -- the tier gets STRONGER
        # in absolute terms while the ticket gets cheaper. Sits between Rage Bait's
        # 52% and Captain Death's 80% (the ETL concentration cap).
        # ⚠ RTP IS STRICTLY CONSERVED: every point here comes out of the other three.
        # mystery_cap_rtp is NOT a second source -- since Aug 6 every mystery cap book
        # is an ascendant roll, so that budget already belongs to ascendant and raising
        # it only moves ascendant's own delivery from body wins to forced max wins.
        # ⚠⚠ ASCENDANT PULLED BACK 60% -> 50% OF PAYBACK, Aug 12 2026, AND THE REASON
        # IS THE BEAT RATE. At 60% the three purchasable tiers shared 40.1% of payback
        # across 90% of rolls -- 0.474x the ticket each on average -- and a fence whose
        # OWN mean is half a ticket cannot pay a full one often. Measured across three
        # dress cuts the mode's beat rate sat at 15.05 / 15.12 / 12.61%, i.e. the dresses
        # could move the body 10 points but not the beat rate at all. Ascendant alone
        # supplied ~9 of those points.
        # => BEAT RATE IS BOUGHT WITH CONCENTRATION, NOT WITH DRESSES. This is the
        #    conservation law in its sharpest form: at fixed RTP the only way 90% of
        #    rolls beat the ticket more often is for the other 10% to carry less.
        #
        # At 50% the three tiers deliver ~98% of their STANDALONE-FAIR value (what the
        # same tier costs as its own buy), so rolling one inside mystery is worth almost
        # exactly buying it, and the ticket premium is entirely the ascendant shot:
        #   corvus 0.35*189.6 = 66.4   ursa 0.35*284.4 =  99.5
        #   draco  0.20*379.2 = 75.8   asc  0.10*2415  = 241.5  (incl. 20.0 cap slice)
        # ⚠ THE COST IS THE POINT OF THE EXERCISE. Ascendant per roll goes 5.79x the
        # ticket back to 4.83x -- exactly where it was before this work -- so the tier's
        # jackpot identity now rests on TWIN DRAGONS and the 500x price rather than on
        # carrying a bigger share. Raising this number is the single lever if that turns
        # out not to be enough.
        mystery_payback = {"corvus": 0.143, "ursa": 0.215, "draco": 0.164, "ascendant": 0.478}

        _cap_weight = mystery_cap_rtp * costs["buy_mystery"] / wincaps["buy_mystery"]
        # Normalises the mix, so the shares above are read as RATIOS and their absolute
        # sum is irrelevant. (It read 0.995 while the mix was written to leave room for
        # the wincap quota; that coincidence is gone as of Aug 12 2026 and was never
        # what made the invariant hold -- sum(1/hr) + cap_weight == 1 comes out of this
        # normalisation for any mix.)
        _roll_total = sum(mystery_roll_mix.values())
        mystery_hr = {
            tier: _roll_total / (share * (1.0 - _cap_weight))
            for tier, share in mystery_roll_mix.items()
        }
        _body = rtp - mystery_cap_rtp
        mystery_rtp = {tier: round(share * _body, 6) for tier, share in mystery_payback.items()}
        # absorb float drift in the largest split so invariant B holds exactly
        mystery_rtp["ascendant"] = round(
            _body - sum(v for k, v in mystery_rtp.items() if k != "ascendant"), 6
        )

        # ------------------------------------------------- buy_mystery_spin
        # The one-spin mode. Derived exactly like mystery's above so the two
        # invariants cannot drift: sum(1/hr) + cap_weight == 1 (A) and the rtp
        # splits summing to the mode rtp (B).
        #
        # ⚠ THIS MODE'S CAP IS 15,000x, NOT 25,000x, and wincaps[] carries that -- so
        # every derivation below picks it up automatically. cap_rtp 0.05 puts the
        # max-win rate at rate = slice_rtp*cost/cap = 0.05*150/15000 = 1 in 2,000,
        # inside the 1-in-400-to-4,000 market band and close to rage_spins' 1 in
        # 1,377. It is the second-largest cap budget in the game after draco's 0.075,
        # which is what a mode selling a tail should look like.
        #
        # ⚠ BOTH DICTS BELOW ARE FIRST GUESSES AND ONLY ONE OF THEM IS CHEAP TO
        # CHANGE. spin_roll_mix must match the generation quotas in game_config and
        # moving it is a RE-SIM (quotas decide which books exist). spin_payback is
        # pure reweighting and costs nothing.
        spin_roll_mix = {"corvus": 0.15, "ursa": 0.25, "draco": 0.60}
        # Weighted by roll share x star-table mean (3.35 / 4.70 / 20.19), which on a
        # single spin is very nearly the whole economy: same 2x2 block, same one
        # spin, so the star table is the only thing separating the tiers.
        #   corvus 0.15*3.35 = 0.50   ursa 0.25*4.70 = 1.18   draco 0.60*20.19 = 12.11
        # => 3.6% / 8.5% / 87.9%. Draco carrying ~88% of payback on 60% of rolls is
        # the intended shape, not a defect -- it is what stops the mode being a coin
        # flip between two duds. RE-DERIVE FROM THE MEASURED FENCE MEANS after run 1.
        spin_payback = {"corvus": 0.036, "ursa": 0.085, "draco": 0.879}

        spin_cap_rtp = 0.05

        # Same normalisation as mystery's: the mix is read as RATIOS, and invariant A
        # (sum(1/hr) + cap_weight == 1) falls out of it for any mix.
        _spin_cap_weight = spin_cap_rtp * costs["buy_mystery_spin"] / wincaps["buy_mystery_spin"]
        _spin_roll_total = sum(spin_roll_mix.values())
        spin_hr = {
            tier: _spin_roll_total / (share * (1.0 - _spin_cap_weight))
            for tier, share in spin_roll_mix.items()
        }
        _spin_body = rtp - spin_cap_rtp
        spin_rtp = {tier: round(share * _spin_body, 6) for tier, share in spin_payback.items()}
        # absorb float drift in the largest split so invariant B holds exactly
        spin_rtp["draco"] = round(
            _spin_body - sum(v for k, v in spin_rtp.items() if k != "draco"), 6
        )

        # Same gapless construction as mystery_bands, on THIS mode's ticket. The top
        # edge is the cap expressed in tickets and is DERIVED -- every hardcoded band
        # in this game has gone stale on a reprice at least once, and this mode is
        # explicitly expected to be repriced once its mean is known.
        _SPIN_EDGES = (
            0.0, 0.25, 0.5, 1.0, 2.0, 5.0,
            wincaps["buy_mystery_spin"] / costs["buy_mystery_spin"],
        )

        def spin_bands(criteria, factors):
            ticket = costs["buy_mystery_spin"]
            return [
                {"criteria": criteria, "scale_factor": f,
                 "win_range": (int(lo * ticket), int(hi * ticket)), "probability": 1.0}
                for (lo, hi), f in zip(zip(_SPIN_EDGES, _SPIN_EDGES[1:]), factors)
            ]

        self.game_config.opt_params = {
            # base (1x): RTP mostly in the base game (the hit floor) + a natural tier
            # tail; wincap is the rare draco-to-cap slice. Sum = 0.9665.
            "base": {
                "conditions": {
                    "wincap": wincap_cond("base", 0.02),
                    "draco": feature_cond(0.13, hr=1900, kind=5),
                    "ursa": feature_cond(0.11, hr=600, kind=4),
                    "corvus": feature_cond(0.10, hr=220, kind=3),
                    # "0" BEFORE "basegame": fences are assigned in order and consume
                    # what they match, and basegame is the only fence with NO identity
                    # condition -- a catch-all must come last or it eats the zero-win
                    # books that "0" (win_range 0,0) is supposed to hold.
                    "0": zero_cond,
                    # ⚠ DERIVED, NOT HARDCODED (Aug 8 2026). This was a literal 0.6065,
                    # which silently pinned base to a 0.9665 mode RTP: raising
                    # game_config.rtp to 0.9669 tripped verify_optimization_input's
                    # "Optimization RTP does not match betmode RTP". The catch-all is the
                    # natural place to absorb the remainder, so the splits now follow the
                    # mode RTP wherever it is set.
                    "basegame": base_cond(round(rtp - 0.02 - 0.13 - 0.11 - 0.10, 5), hr=3.5),
                },
                "scaling": ConstructScaling(base_small_scaling + tail_scaling("draco")).return_dict(),
                "parameters": run_params(3, 10, [50, 100, 200], [0.3, 0.4, 0.3]),
                "distribution_bias": ConstructFenceBias(["basegame"], [(2.0, 3.0)], [0.5]).return_dict(),
            },
            # ante_starfall (1.5x): more RTP in features + more triggers + less dead
            # base -> smoother, lower vol. Sum = 0.9665.
            "ante_starfall": {
                "conditions": {
                    "wincap": wincap_cond("ante_starfall", 0.025),
                    "draco": feature_cond(0.15, hr=1000, kind=5),
                    "ursa": feature_cond(0.13, hr=370, kind=4),
                    "corvus": feature_cond(0.12, hr=160, kind=3),
                    "0": zero_cond,                      # catch-all last -- see base
                    # derived from the mode RTP, not hardcoded -- see base's note
                    "basegame": base_cond(round(rtp - 0.025 - 0.15 - 0.13 - 0.12, 5), hr=3.0),
                },
                "scaling": ConstructScaling(base_small_scaling + tail_scaling("draco")).return_dict(),
                "parameters": run_params(2, 6, [50, 100, 200], [0.3, 0.4, 0.3]),
                "distribution_bias": ConstructFenceBias(["basegame"], [(2.0, 3.0)], [0.5]).return_dict(),
            },
            "buy_ursa": {
                "conditions": {
                    "wincap": wincap_cond("buy_ursa", 0.026),
                    "ursa": feature_cond(round(rtp - 0.026, 5), hr=1.0003121),
                },
                "scaling": ConstructScaling(
                    tail_scaling("ursa")
                    + [{"criteria": "ursa", "scale_factor": 1.5,
                        "win_range": (134, 536), "probability": 1.0},
                       # 0.25-0.5x cost. The 0.030 run collapsed this band 16.4% -> 5.3%
                       # and dumped the mass into <=0.25x instead of lifting it, which is
                       # what drove ursa's median from 0.226x down to ~0.10x. Boosting it
                       # is an attempt to rebuild the shoulder between "near-total loss"
                       # and "money back" -- the part a coin-flip tier needs most.
                       {"criteria": "ursa", "scale_factor": 1.6,
                        "win_range": (67, 134), "probability": 1.0},
                       # ⚠ THE 50% COMPLETION PUSH (Aug 6 2026). Measured on the shipped
                       # pool, ursa completes 62.6% in the RAW pool but only 34.7% once
                       # weighted -- because the optimizer removes the pool's ~2x surplus
                       # by piling weight onto near-worthless books: the 0-50x band goes
                       # 12.5% raw -> 49.3% WEIGHTED. Half of ursa's probability mass pays
                       # under 0.19x the ticket. That single fact causes BOTH the collapsed
                       # completion rate and ursa being the harshest buy in the game, which
                       # the two dresses above were added to fight from the other side.
                       # NOT the m2m band: ursa sits at 5.67 inside (3,10), so that
                       # constraint is not binding and moving it does nothing.
                       # Above 268x the split is CLEAN -- non-completed books essentially
                       # never pay a full ticket -- so a payout-range dress can target
                       # completions directly. Suppress the dead band, lift the clean one.
                       # ⚠ FIRST ATTEMPT USED (1, 50) AND LEAKED. Books paying under 1x
                       # base bet fell outside the range, so the optimizer dumped the
                       # displaced weight there instead: 0-25x went 29.93% -> 39.49% while
                       # 25-50x fell, and completion moved only 34.7% -> 37.9%. Range the
                       # suppression from 0 or it is not a suppression, it is a funnel.
                       {"criteria": "ursa", "scale_factor": 0.5,
                        "win_range": (0, 56), "probability": 1.0},
                       # Target the arithmetic: 50% completion at RTP 0.9662 needs the
                       # completed set to average ~484x, which is the 268-800 band. The
                       # extreme tail is what eats the budget that band needs.
                       {"criteria": "ursa", "scale_factor": 2.2,
                        "win_range": (300, 900), "probability": 1.0},
                       {"criteria": "ursa", "scale_factor": 0.5,
                        "win_range": (1350, 25000), "probability": 1.0}]
                ).return_dict(),
                "parameters": run_params(3, 10, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["ursa"], [(5.0, 20.0)], [0.3]).return_dict(),
            },
            # buy_draco: the dragon lottery -- very high vol, and the mode that reaches
            # the shared 25,000x ceiling most often. RAISED 0.05 -> 0.075 so that lifting
            # ursa/mystery does NOT erode draco's crown: the ladder moves up together and
            # draco/ursa stays 2.5x (was 2.33x), still far past the 1.94x price-ratio
            # break-even below which buying draco would be strictly worse AND dearer.
            # 0.075 at cost 520 -> 1 in 641, vs Rage Bait's mystery at ~1 in 787 -- the
            # market puts a 25,000x on a ~500x buy at roughly this rate.
            # COSTS 2.5% OF DRACO'S BODY: that RTP moves from mid-range wins to cap books,
            # so re-check the win-range holes (was 1.00x) and the median after the run.
            # ⚠⚠ DRACO IS PINNED AT RTP 0.9650 AND FOUR FIXES HAVE BEEN TRIED AND FAILED
            # (Aug 7 2026). Recording the negatives so nobody spends the afternoon again.
            # The pattern that suggested a cause: every SIX-fence mode (base, ante,
            # mystery) converges to 0.9665 exactly, and every TWO-fence mode undershoots
            # -- corvus 0.9661, ursa 0.9662, draco 0.9650. Splitting delivered RTP per
            # fence shows draco's wincap fence hitting target (1 in 642 vs 1 in 641) and
            # its BODY fence short by 0.16%.
            #   1. m2m FLOOR. draco delivers m2m 4.10 against a configured (5, 20) band --
            #      the ONLY buy outside its band -- so the optimizer looked like it was
            #      fighting an unsatisfiable constraint. Lowering the floor to 3.5:
            #      NO CHANGE, still 0.9650.
            #   2. SAMPLE SIZE. run_params fixes num_per_fence=10000, so a 6-fence mode
            #      searches 60,000 books and a 2-fence mode only 20,000. Raising draco to
            #      30,000 (1.7x the runtime): NO CHANGE, still 0.9650.
            #   3. RTP SPLIT REALLOCATION -- the remedy this file's own header prescribes
            #      ("a target a slice's books can't produce is a convergence failure ->
            #      adjust the number HERE"). Moved the shortfall onto the wincap fence,
            #      which hits its target exactly: 0.075 -> 0.0764 with the body absorbing
            #      the delta. NO CHANGE, still 0.9650.
            #   4. PAYOUT-RANGE FENCES, to give draco the fence count the converging modes
            #      have. BLOCKED without a re-sim: verify_optimization_input asserts fence
            #      names match Distribution criteria (see the note above buy_corvus).
            # => THE CEILING IS STRUCTURAL TO DRACO'S BOOK POOL, not an optimizer setting.
            #    A re-sim is the only remaining route AND NOBODY KNOWS WHAT TO CHANGE --
            #    re-simming the same config reproduces the same books. Next step if it is
            #    ever worth 0.15%: read optimization_program's Rust source for what
            #    score_type="rtp" actually minimises. NOT a compliance issue: the spec
            #    allows 0.5% cross-mode variation and the pool sits at 0.151%.
            "buy_draco": {
                "conditions": {
                    "wincap": wincap_cond("buy_draco", 0.075),
                    # ⚠⚠ hr RE-DERIVED Aug 12 2026 FOR THE 500 -> 400 REPRICE, and it
                    # is the same trap buy_corvus documents above: hr = 1/(1-cap_rate)
                    # and cap_rate = cap_rtp * cost / cap, so a COST change moves it
                    # exactly as a CEILING change does. 0.075 * 400/25000 = 0.0012, so
                    # hr = 1/(1 - 0.0012) = 1.0012014 (was 1.0015023 at cost 500).
                    # Leaving the old value behind reserves weight for a cap slice that
                    # no longer needs it; the shortfall renormalises every weight up and
                    # lands the mode OVER Stake's 0.967 RTP cap -- a CRITICAL failure.
                    # ⚠ The cap RATE moves with the price too: 1 in 667 -> 1 in 833.
                    # Still the most frequent max win in the menu (mystery is 1 in
                    # 1,250 at cost 500), so draco keeps the cap crown.
                    "draco": feature_cond(round(rtp - 0.075, 5), hr=1.0012014),
                },
                # ⚠ TICKET-RELATIVE BAND AUDIT, Aug 12 2026 (the 500 -> 400 reprice).
                # Ranges here are BASE-BET units, so a reprice silently changes what
                # they mean -- the trap the corvus rebuild note above is written about.
                # At 500x / at 400x:  tail_scaling (1000,2000) 2-4x -> 2.5-5x ticket,
                # (3000,4000) 6-8x -> 7.5-10x; the fence bias (50,150) 0.1-0.3x ->
                # 0.125-0.375x. All three shift by the same 25% and none crosses a
                # band boundary that matters, so they are LEFT ALONE DELIBERATELY:
                # re-cutting dresses in the same run as the reprice would confound the
                # measurement, and draco's body is the thing being measured. Revisit
                # only if the reprice measurement shows the body moved.
                "scaling": ConstructScaling(tail_scaling("draco")).return_dict(),
                "parameters": run_params(5, 20, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["draco"], [(50.0, 150.0)], [0.3]).return_dict(),
            },
            # buy_mystery: 35 / 29.5 / 25 / 10 corvus / ursa / draco / ASCENDANT.
            # ONE FENCE PER TIER (kind = the scatter count recorded at trigger, 3/4/5
            # and 6 for ascendant). The old single blended fence let the optimizer
            # reshape each tier freely to hit RTP, which INVERTED the published ladder
            # -- rolling Draco averaged less than rolling Corvus while the UI sold
            # Draco as the prize. Fences are assigned in order and consume the books
            # they match, so `kind` is mandatory here exactly as in base/ante.
            #
            # RTP SPLITS are each tier's share of the mode's mean. RE-DERIVED Jul 30 2026
            # for the shortened ladders (ursa 13 rungs, draco 12, ascendant shares
            # draco's) at the MEASURED Ascendant value 2,598x (n=20k, 100% ascendant,
            # wincap stripped):
            #   corvus 0.350*232.0 =  81.2 (14.9%)   ursa  0.295*260.0 =  76.7 (14.1%)
            #   draco  0.250*505.5 = 126.4 (23.2%)   asc   0.100*2598  = 259.8 (47.8%)
            #   mean 544.1 -> cost 563x. Splits are that share of (rtp - wincap).
            # ASCENDANT CARRIES 48% OF THE MODE'S PAYBACK ON 10% OF ROLLS -- the shape
            # the audited mystery games use (Rage Bait's top tier: 10% of rolls, 52% of
            # payback), and the reason this mode can be priced above buy_draco at all.
            # The re-sweep moved it 44.3% -> 47.8%, i.e. TOWARD that reference, because
            # a shorter ladder rewards ascendant's early completions most.
            #
            # THE ROLL MIX IS UNCHANGED at 35/29.5/25/10 -- only the PAYBACK split moved.
            # hr encodes the roll share and the rtp split encodes the payback share; they
            # are different numbers and only the second one responds to a ladder change.
            #
            # CAP SHARE RAISED 0.0199 -> 0.040 (mystery_cap_rtp above). At 0.0199 this
            # 563x buy was a worse max-win bet per dollar than a 1.5x ante spin (0.025) --
            # backwards from every audited game, where the buys carry the most cap value
            # (Rage Bait: base 0.045, super 0.056, mystery 0.064). 0.040 at cost 563 ->
            # 1 in 1,110, against Rage Bait's ~1 in 787 for the same 500x-class mystery.
            # ⚠ THE OLD WORRY IS NOW HEADROOM, NOT RISK. The unforced at-cap rates
            # (ursa 1/20,000, draco 1/1,538, ascendant 1/67) roll forward to an organic
            # slice_rtp near 0.074, and the optimizer cannot suppress organic cap books
            # inside the ascendant fence -- so the DELIVERED share can drift above the
            # 0.040 asked for here. Previously that risked mystery outranking draco at
            # 0.050; with draco lifted to 0.075 the ordering survives even a large drift.
            # STILL MEASURE IT: delivered mystery cap share must stay under draco's.
            #
            # ⚠ STILL PROVISIONAL at n=20k -- re-derive every split and the mode cost
            # from the 1e6 pool. A tail rate read off 20k books is the least stable
            # number here.
            # ⚠ hr IS THE TIER MIX, AND hr=1 SILENTLY DESTROYS IT (found Jul 29 2026 on
            # the first 1e6 pool). hr is a "1 in N" frequency -- verified against base,
            # whose hr 220/600/1900/3.5 reproduce EXACTLY as measured trigger rates. So
            # hr=1 declares "this fence happens on every single book". That is harmless
            # for buy_corvus/buy_ursa/buy_draco, where one tier fence really does own
            # ~100% of the mode, and it was copied from them. Here FOUR fences each
            # claimed 100%, so the optimizer split them evenly -- 25.00% weight apiece
            # against the designed 35/29.5/25/10 -- and because each fence still hit its
            # own rtp_k as a sub-pool mean, the MODE landed on sum(rtp_k)/4 = 0.2416,
            # exactly a quarter of target. Nothing errored: verify_optimization_input
            # only checks that the splits sum and that criteria match, and the splits
            # were right the whole time. Third instance of the same family of bug as the
            # two fence-ORDER ones above: fence identity correct, fence PROPORTION wrong.
            # hr = 1 / intended share. Cross-check: rtp_k * cost * hr_k is the fence mean
            # the optimizer must produce, and it lands within 3% of every measured
            # natural tier mean (227 vs 234, 254 vs 257, 492 vs 503, 2205 vs 2251), so
            # the tiers keep the shape the sweeps gave them instead of being reshaped.
            "buy_mystery": {
                "conditions": {
                    "wincap": wincap_cond("buy_mystery", mystery_cap_rtp),
                    # ⚠ THE SHARES MUST BE EXHAUSTIVE: sum(1/hr) + wincap weight == 1.
                    # First attempt used the clean design mix (hr 10/4/3.39/2.857), whose
                    # shares sum to 0.995 because 0.5% was left for the cap slice -- but
                    # 0.5% is the cap's GENERATION QUOTA in game_config, and its actual
                    # WEIGHT is rtp*cost/cap = 0.0199*563/25000 = 0.000448, i.e. 0.045%.
                    # The optimizer filled the 0.46% shortfall by scaling every tier up,
                    # which scaled the mode's RTP by the same factor: 0.9665 * 1.004604 =
                    # 0.9709, over the 0.9670 ceiling. Exactly the quota-vs-frequency
                    # confusion the CLAUDE.md note warns about, met from the other side.
                    # Shares below are the 35/29.5/25/10 mix renormalised to 1 - 0.000448.
                    # hr = 1/roll share (UNCHANGED by the re-sweep); the first number is
                    # the PAYBACK split, which is what the new ladders moved.
                    # rtp split = PAYBACK share; hr = 1 / ROLL share. Both derived above
                    # from mystery_payback / mystery_roll_mix so raising the cap share
                    # re-solves them instead of silently breaking an invariant.
                    "ascendant": feature_cond(mystery_rtp["ascendant"], hr=mystery_hr["ascendant"], kind=6),
                    "draco": feature_cond(mystery_rtp["draco"], hr=mystery_hr["draco"], kind=5),
                    "ursa": feature_cond(mystery_rtp["ursa"], hr=mystery_hr["ursa"], kind=4),
                    "corvus": feature_cond(mystery_rtp["corvus"], hr=mystery_hr["corvus"], kind=3),
                },
                # Boost peaks on the band each fence's OWN mean lands in -- corvus must
                # average 152x (0.30x ticket), ursa 228x (0.46x), draco 304x (0.61x) --
                # so each tier piles up around its own value instead of at zero. The
                # top two bands fund it; they are where the undressed draws had grown.
                # ASCENDANT IS DELIBERATELY UNDRESSED: it averages 2,699x (5.4x ticket)
                # and completes 95.9%, so it is not what busts, and banding it would
                # fight its own fence target.
                # ⚠⚠ THE BEAT-RATE DIAL IS WHERE EACH FENCE'S PEAK SITS, NOT THE 2-5x
                # FACTOR. Measured Aug 12 2026: raising 2-5x from 0.6 to 1.0 moved the
                # mode's beat rate 15.05% -> 15.12% and the 2-5x band actually FELL
                # (4.51% -> 3.67%). The optimizer was not short of permission there; it
                # was following the peaks, which sat at 0.25-0.5x and 0.5-1x.
                # A fence CANNOT beat the ticket often if its own mean is far below one:
                # corvus must average 0.30x the ticket, ursa 0.46x, draco 0.61x
                # (Markov puts hard ceilings of 30% / 46% / 61% on their beat rates, and
                # the real numbers sit well under that once the tail is paid for). So the
                # peaks are set PER TIER, at what each can actually afford:
                # RE-CUT for the 50% split: every tier is richer now, so every peak
                # moves up one band. Means are corvus 0.38x the ticket, ursa 0.57x,
                # draco 0.76x -- draco can genuinely live at 1-2x, which it could not
                # at 60% concentration.
                #   corvus  peak 0.5-1x
                #   ursa    peak 0.5-1x, strong 1-2x shoulder
                #   draco   peak 1-2x
                "scaling": ConstructScaling(
                    mystery_bands("corvus", (0.15, 2.5, 3.0, 1.5, 1.0, 0.3))
                    + mystery_bands("ursa", (0.15, 1.8, 3.0, 2.5, 1.0, 0.3))
                    + mystery_bands("draco", (0.15, 1.2, 2.0, 3.5, 1.2, 0.3))
                    + tail_scaling("ascendant")
                ).return_dict(),
                "parameters": run_params(3, 12, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["ascendant"], [(20.0, 60.0)], [0.3]).return_dict(),
            },
            # THE MOST VOLATILE PRODUCT IN THE MENU, BY DESIGN. Target shape is
            # rage_spins: median ~0.10-0.15x the ticket and sigma/cost 3.5-4.0,
            # against draco's 2.57. Bands are cut to STARVE THE MIDDLE and feed both
            # ends -- weight piles up under 0.25x and in the tail, and the 0.5-5x
            # body is suppressed, which is what a low median with a live ceiling
            # looks like.
            #
            # ⚠ IT DOES NOT BUST, AND THAT WAS MEASURED, NOT ASSUMED. Zero-pay came
            # back 0.00% at every roam density: a 2x2 wild on a 20-line 5x4 nearly
            # always completes some line, so the "act two consumes the sticky wilds,
            # therefore a woken deal can pay nothing" reasoning is wrong in practice.
            # This is the MIKO shape (0.00% bust) rather than rage_spins' 5.95%, and
            # it keeps the market norm and our own structural property intact.
            #
            # ⚠ SUPPRESSION BANDS START AT 0 (they are gapless from the origin). A
            # range suppression that starts higher funnels the displaced weight into
            # the gap underneath it instead of removing it.
            "buy_mystery_spin": {
                "conditions": {
                    "wincap": wincap_cond("buy_mystery_spin", spin_cap_rtp),
                    # kind is the scatter count recorded at trigger. The wake slices
                    # force 3/4/5 exactly like the ordinary tier slices do -- the flag
                    # changes the FEATURE, not the trigger board -- so the fences
                    # separate on the same key they always have. Fence ORDER matters
                    # and is invisible to verify_optimization_input: wincap sits ahead
                    # of the kind=5 draco body fence, which is what keeps the forced
                    # books out of the body slice.
                    "draco": feature_cond(spin_rtp["draco"], hr=spin_hr["draco"], kind=5),
                    "ursa": feature_cond(spin_rtp["ursa"], hr=spin_hr["ursa"], kind=4),
                    "corvus": feature_cond(spin_rtp["corvus"], hr=spin_hr["corvus"], kind=3),
                },
                # bands:      0-.25  .25-.5  .5-1x   1-2x   2-5x  5-100x
                # corvus and ursa cannot build a tail on one spin (star means 3.35 and
                # 4.70), so they are shaped to sit low and cheap and let draco carry
                # the ceiling. Draco keeps a real 5x+ shoulder -- it is the only tier
                # whose star table can reach the cap at all.
                "scaling": ConstructScaling(
                    spin_bands("corvus", (3.0, 1.2, 0.5, 0.4, 0.4, 1.0))
                    + spin_bands("ursa", (3.0, 1.2, 0.5, 0.4, 0.5, 1.2))
                    + spin_bands("draco", (2.5, 1.0, 0.5, 0.4, 0.8, 2.0))
                ).return_dict(),
                # WIDE m2m ON PURPOSE. This is the most volatile product in the menu by
                # construction -- rage_spins runs a 0.054x median against a 0.967x mean,
                # i.e. m2m near 18 -- so a band cut for the tier buys (3-12) would fight
                # the mode's own identity and force the optimizer to flatten the tail it
                # exists to sell. Permissive now, re-cut once the curve is measured.
                "parameters": run_params(3, 25, [10, 20, 50], [0.6, 0.2, 0.2]),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
