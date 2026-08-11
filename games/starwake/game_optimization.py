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
  buy_corvus           : corvus          buy_ursa   : wincap, ursa
  buy_draco            : wincap, draco    buy_mystery: wincap, mystery
Every mode except buy_corvus carries a wincap slice. Corvus publishes an honest
10,000x instead -- it CAN be made to reach the cap, but only by trading away the
best body in the game (see game_config's ceilings note).

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

    buy_corvus  ~0      (10,000x ceiling, no cap slice -- a deliberate non-lottery)
    base         0.020
    ante         0.025
    buy_ursa     0.030  (was 0.0215 -- BELOW ante, i.e. inverted)
    buy_mystery  0.040  (was 0.0199 -- below ante AND below ursa)
    buy_draco    0.075  (was 0.050 -- raised to keep the crown as the others rise)

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

        # -- buy_mystery: DERIVE both invariants instead of hand-typing them --
        # Two different numbers, and mixing them up has already cost one 1e6 run:
        #   ROLL mix  -> hr (how often each tier is dealt)
        #   PAYBACK   -> rtp split (how much of the mode's mean each tier carries)
        # Invariant A: sum(1/hr) + wincap_weight == 1   (shares must be exhaustive)
        # Invariant B: sum(rtp splits) + wincap_rtp == mode rtp, exact to 5dp
        #              (verify_optimization_input asserts round(...,5) equality)
        # Deriving them means a change to the cap share can no longer silently break
        # either one -- the failure mode both times was arithmetic, not design.
        # buy_corvus's cap share. RE-DERIVED Aug 7 2026 when the ceiling was cut
        # 9,000x -> 2,500x to make it reachable (see game_config's corvus_cap note).
        # rate = slice_rtp * cost / cap, so 0.008333 * 120 / 2500 = 1 in 2,500 --
        # essentially the rate corvus already produces unforced (P(>=2,500x) measured
        # 1 in 2,417), so the slice PINS what the engine naturally does rather than
        # manufacturing something it does not. That is the point: without a slice the
        # delivered rate is an optimizer draw, and corvus's was measured across eight
        # identical runs at 1 in 2.9M to 11.2M with one of the eight missing its gate.
        # ⚠ IT IS NO LONGER FREE. At 9,000x/1-in-2M the slice cost 0.00375% of the
        # mode's RTP; at 2,500x/1-in-2,500 it costs 0.83%. Still the smallest cap share
        # in the game (draco 7.5%, mystery 4.0%, ursa 2.6%, base 2.0%) and appropriate
        # for the cheapest tier with the smallest ceiling.
        # ⚠ RE-DERIVED Aug 8 2026 for the 25,000x ceiling. A slice's rtp share IS its
        # frequency: rate = slice_rtp * cost / cap, so at cap 25,000 and cost 120,
        # slice_rtp = rate * 208.333.
        #     1 in 10,000  ->  0.020833      1 in 50,000  ->  0.0041667
        #     1 in 20,000  ->  0.010417      1 in 100,000 ->  0.0020833
        # 1 in 50,000 chosen: it must be the RAREST max win in the menu (draco 1 in
        # 641, ursa 1 in 3,588) because corvus is the cheapest ticket AND has to be
        # the least volatile mode. The cap's variance contribution is
        # slice_rtp * cap/cost = rate * (cap/cost)^2, so a rarer cap costs
        # QUADRATICALLY less variance -- 0.87 here against 2.17 at 1 in 20,000 and
        # 4.34 at 1 in 10,000. That is the whole reason corvus can carry a 208x
        # ceiling-per-stake and still sit below ursa's 1.96 std.
        # ⚠ 1 in 20,000 SINCE Aug 8 2026 (was 1 in 50,000, slice_rtp 0.0025).
        # slice_rtp = rate * cap / cost = (1/20000) * 25000/200 = 0.00625.
        # WHY IT MOVED: at 1 in 50,000 corvus's max win was 12.5x outside the market
        # band (400-4,000), i.e. a ceiling that reads as unreachable to anyone
        # comparing games. At 1 in 20,000 it is still the RAREST in this menu by 6.2x
        # (ursa 1 in 3,205, draco 1 in 667) but stops looking like an outlier.
        # WHAT IT DOES NOT BUY: session feel. The cap sits at 125x the ticket while a
        # "big win" is 10x, so P(>=10x) barely moves (48.7% -> 49.0% of sessions).
        # What it buys is max-win SIGHTINGS, 0.60% -> 1.49% of 300-spin sessions.
        # ⚠ THE CEILING ON THIS IS CORVUS'S OWN TIER ORDERING, not compliance. Corvus
        # must stay under ursa's 1.88 std, which binds at ~1 in 15,260; the cap-value
        # ladder does not bind until 1 in 4,808 and the risk gates not at all (corvus
        # p5k 2.5e-05 against a 0.05 limit). 20,000 leaves margin because the limit
        # was computed with the body held constant, and moving rtp into the cap
        # hardens the body.
        corvus_cap_rtp = 0.00625

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
        mystery_roll_mix = {"corvus": 0.350, "ursa": 0.295, "draco": 0.250, "ascendant": 0.100}
        mystery_payback = {"corvus": 0.149, "ursa": 0.141, "draco": 0.232, "ascendant": 0.478}

        _cap_weight = mystery_cap_rtp * costs["buy_mystery"] / wincaps["buy_mystery"]
        _roll_total = sum(mystery_roll_mix.values())  # 0.995 by design, NOT 1.0
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
            # buy_corvus: the safe tier -- all RTP in the corvus feature. Low vol.
            # No wincap fence (game_config gives this mode no wincap Distribution), so
            # its 10,000x ceiling is organic. maxwin_boost lifts it over the
            # "realistically obtainable" gate; see that helper for why and for the
            # fallback. MEASURE P(10,000x) on the new LUT -- target >= 1e-07.
            # ⚠ THE CONSOLATION BANDS BELOW ARE LOAD-BEARING AND THE TAIL BOOST IS
            # THEIR PRICE. Repricing corvus 240 -> 120 left it returning under a
            # quarter of the ticket on 59.1% of buys with a 0.17x median -- harsh for
            # the entry tier a first-time buyer reaches for. Boosting 0.25-0.5x,
            # 0.5-1x and 1-2x cost (30-60 / 60-120 / 120-240 in base-bet terms) moves
            # that to 42.3% and 0.29x, a 17-point shift and larger than the ~8 points
            # of optimizer run-to-run noise on this mode.
            # ⚠ AN EARLIER TWO-BAND VERSION PUSHED THE MAX WIN TO 1 IN 14.5M, OUTSIDE
            # the "realistically obtainable" gate. Corvus has no wincap slice, so
            # weight moved into the body comes straight out of an unprotected tail --
            # measured 1 in 6.76M with these three bands, but it MUST be re-measured
            # on whatever pool ships rather than assumed. See maxwin_boost above.
            # ⚠ WINCAP FENCE ADDED Aug 6 2026. It must come FIRST -- fences are assigned
            # in order and consume what they match, so the body fence would otherwise
            # swallow the cap books. slice_rtp sets the rate exactly: the relation
            # rate = slice_rtp * cost / cap is not an approximation, it reproduces every
            # other mode's measured cap frequency to within one part in a million
            # (base 0.02 -> 1 in 1,250,000 measured 1,250,001; ursa 0.026 -> 3,588 vs
            # 3,589; draco 0.075 -> 641 vs 642). 3.75e-05 * 120 / 9,000 = 1 in 2,000,000,
            # a 5x margin under the ~1-in-10M obtainability guideline -- chosen for margin
            # because corvus's UNSLICED rate drew anywhere from 1 in 2.9M to 1 in 11.2M
            # across 8 identical runs.
            # ⚠ EXPERIMENT Aug 7 2026 -- PAYOUT-RANGE FENCE. ConstructConditions turns a
            # TUPLE search_conditions into identity_condition.win_range_start/end, and
            # write_configs writes fence_info["name"] as a plain label -- matching is by
            # identity_condition, NOT by name. So a single-criteria mode can carry
            # several fences split by PAYOUT BAND, each with its own rtp target.
            # WHY IT MATTERS: corvus's missing middle is a WEIGHTING artifact, not a
            # supply one -- 21.7% of its books pay 60-240x (0.5-2x ticket) and only 6.5%
            # of delivered weight lands there, because the optimizer must strip ~73% of a
            # 3.7x-surplus pool and dumps it into the cheapest band with supply (30-60x
            # goes 5.2% raw -> 31.8% delivered). A dress only biases; a FENCE PINS the
            # band's RTP outright.
            # ⚠ FENCE ORDER IS LOAD-BEARING: fences consume the books they match, so the
            # range fence MUST precede the {"symbol":"scatter"} catch-all, which matches
            # every corvus book.
            # ⚠ AND SHARES MUST STAY EXHAUSTIVE: sum(1/hr) + wincap weight == 1. The
            # catch-all's hr is therefore 1/(1 - mid_share - wincap_weight), not 1.
            "buy_corvus": {
                "conditions": {
                    "wincap": wincap_cond("buy_corvus", corvus_cap_rtp),
                    # ⚠ hr IS DERIVED FROM THE CAP RATE, NOT TUNED. The invariant is
                    # sum(1/hr) + wincap_weight == 1, so hr = 1 / (1 - cap_rate)
                    # where cap_rate = cap_rtp * cost / cap. Leaving the old
                    # 1.0004001 behind when the ceiling moved 2,500x -> 25,000x
                    # reserved 0.0004 of weight for a cap that now needs 0.00002;
                    # the shortfall renormalised every weight up by 1.00038 and put
                    # the mode at RTP 0.9673 -- OVER Stake's 0.967 cap, which is a
                    # CRITICAL test and blocks submission outright. Measured exactly
                    # that on all four sweep variants before the cause was found.
                    # Here: cap_rate = 0.00625 * 200/25000 = 5.0e-05, so
                    # hr = 1/(1 - 5.0e-05) = 1.0000500.
                    "corvus": feature_cond(round(rtp - corvus_cap_rtp, 7), hr=1.0000500),
                },
                # ⚠ tail_scaling AND maxwin_boost BOTH REMOVED Aug 7 2026 with the
                # 2,500x ceiling, because both had become wrong or redundant:
                #  - tail_scaling damps (1000,2000) at 0.8 and lifts (3000,4000) at 1.2.
                #    Above a 2,500x cap the second band CANNOT EXIST, and the first is
                #    no longer "mid tail" -- it is the shoulder right below the ceiling,
                #    which is the last thing corvus should be suppressing.
                #  - maxwin_boost exists (see its docstring) ONLY for modes with no
                #    forced wincap slice, to nudge an organic ceiling over the
                #    obtainability gate. corvus GAINED a slice on Aug 6, so the boost
                #    has been redundant since then and would now fight it: the slice
                #    sets the rate exactly, a search hint only biases toward one.
                # What remains is the three consolation bands, which are what actually
                # protect corvus's body -- and protecting the body is the whole reason
                # the 9,000x tail-build was reverted.
                # ⚠ REBUILT Aug 7 2026 -- THE OLD DRESSES WERE BOOSTING THE DUMP ZONE.
                # They ran 1.25 on (30,60), 1.6 on (60,120), 1.3 on (120,240), written
                # when corvus cost 240x so those bands meant 0.125-1x of the ticket. At
                # 120x they mean 0.25-2x, and (30,60) had become the band the optimizer
                # already dumps into: raw supply there is 5.2% of books and it delivered
                # 31.8% of weight -- a 6.1x up-weight, WITH a 1.25 dress on top of it.
                # Meanwhile 60-240x holds 21.7% of raw books and delivered only 6.5%.
                # So corvus had almost no "nearly got it back" or "small win" band and
                # was the LEAST forgiving buy in the menu (19.3% return >=0.5x ticket
                # against ursa's 39.0%) -- inverting the intended tier identity, since
                # corvus is meant to be the safe entry tier.
                # This is the treatment that moved ursa 60.2% -> 43.1% under a quarter
                # ticket: suppress the dump zone FROM 0, boost the target band, and fund
                # it out of the top rather than letting the optimizer pick.
                # ⚠ MADE GAPLESS Aug 8 2026 TO STOP THE BODY BEING A LOTTERY. The
                # three bands above left two ranges unconstrained -- (240,600) and,
                # after the ceiling moved to 25,000x, the whole (2500,25000) tail.
                # MEASURED over 3 optimize draws on IDENTICAL books (the sim is
                # deterministic, so all three weighted the same pool): under-0.25x
                # came out 29.6% / 51.2% / 30.3%, a 21.6-POINT SWING in what players
                # actually experience, while RTP converged to 0.96690 every time.
                # Corvus's raw pool is 3.74x richer than its price needs -- the
                # widest mismatch in the game (ursa 2.57, draco 2.28, mystery 1.94)
                # -- so the optimizer has enormous freedom in what to weight, and
                # THAT FREEDOM IS THE VARIANCE. Ursa, whose body std is a tight 1.19
                # against corvus's 1.67-2.30, is far more constrained.
                # Every band carries a factor now, so no range is left to the
                # optimizer's discretion. Ranges are in base-bet units; corvus costs
                # 120x, so the ticket multiples are noted per line.
                "scaling": ConstructScaling(
                    [{"criteria": "corvus", "scale_factor": 0.25,
                        "win_range": (0, 56), "probability": 1.0},        # <0.25x: the dump zone
                       {"criteria": "corvus", "scale_factor": 0.6,
                        "win_range": (50, 100), "probability": 1.0},       # 0.25-0.5x
                       {"criteria": "corvus", "scale_factor": 3.0,
                        "win_range": (100, 200), "probability": 1.0},      # 0.5-1x: nearly got it back
                       {"criteria": "corvus", "scale_factor": 3.0,
                        "win_range": (200, 400), "probability": 1.0},     # 1-2x: small win
                       {"criteria": "corvus", "scale_factor": 1.2,
                        "win_range": (400, 1000), "probability": 1.0},     # 2-5x   (was a gap)
                       {"criteria": "corvus", "scale_factor": 0.7,
                        "win_range": (1000, 2000), "probability": 1.0},    # 5-10x
                       {"criteria": "corvus", "scale_factor": 0.5,
                        "win_range": (2000, 4000), "probability": 1.0},   # 10-20.8x
                       {"criteria": "corvus", "scale_factor": 0.5,
                        "win_range": (4000, 25000), "probability": 1.0}]  # 20.8-208x (was a gap)
                ).return_dict(),
                "parameters": run_params(1.5, 5, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["corvus"], [(2.0, 5.0)], [0.4]).return_dict(),
            },
            # buy_ursa: the coin-flip tier, now also a 25,000x product. Mid-high vol.
            # RAISED 0.0215 -> 0.030 -> SETTLED AT 0.026. At 0.0215 this buy was a worse
            # max-win bet per dollar than grinding ante_starfall (0.025), inverting the
            # market pattern (every audited game puts more cap value in its buys). But
            # 0.030 OVERSHOT: the optimizer funded the bigger cap slice by packing ursa's
            # consolation band down, and buys returning <=0.25x cost went 53.4% -> 67.7%
            # with the median halving 0.226 -> 0.118x. That made URSA THE HARSHEST BUY IN
            # THE GAME -- harsher than draco (38.6%) -- which inverts the tier identity,
            # since ursa is meant to be the COIN FLIP and draco the lottery.
            # 0.026 keeps ursa above ante (the ordering fix that motivated this) at a
            # buys/base ratio of 1.3x, which is exactly the market's (Rage Bait base
            # 0.045 vs buys 0.056-0.064). Cap rate 0.026*268/25000 = 1 in 3,588.
            # The extra scaling entry protects the 0.5-2x cost consolation band
            # (134-536x base-bet) that the 0.030 run hollowed out -- a coin-flip tier
            # needs a real middle, not just a tail.
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
                    "draco": feature_cond(round(rtp - 0.075, 5), hr=1.0015023),
                },
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
                "scaling": ConstructScaling(tail_scaling("ascendant") + tail_scaling("draco")).return_dict(),
                "parameters": run_params(3, 12, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["ascendant"], [(20.0, 60.0)], [0.3]).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
