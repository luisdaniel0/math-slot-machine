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
AND more expensive. The slices below target ~4.5x, giving draco ~2.3x the cap value
per stake, with room to move: this ratio is the tier story and should be re-checked
against the 1e6 pool, not assumed to have survived re-convergence.
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
        rtp = game_config.rtp  # 0.9665 -- every mode converges here

        # -- small builders: keep the six entries DRY and the RTP split legible --
        def run_params(min_m2m, max_m2m, test_spins, test_weights):
            """Optimizer run config; the m2m band encodes the mode's vol identity."""
            return ConstructParameters(
                num_show=5000, num_per_fence=10000, min_m2m=min_m2m, max_m2m=max_m2m,
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
        base_small_scaling = [
            {"criteria": "basegame", "scale_factor": 1.2, "win_range": (1, 2), "probability": 1.0},
            {"criteria": "basegame", "scale_factor": 1.5, "win_range": (10, 20), "probability": 1.0},
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
                    "basegame": base_cond(0.6065, hr=3.5),
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
                    "basegame": base_cond(0.5415, hr=3.0),
                },
                "scaling": ConstructScaling(base_small_scaling + tail_scaling("draco")).return_dict(),
                "parameters": run_params(2, 6, [50, 100, 200], [0.3, 0.4, 0.3]),
                "distribution_bias": ConstructFenceBias(["basegame"], [(2.0, 3.0)], [0.5]).return_dict(),
            },
            # buy_corvus: the safe tier -- all RTP in the corvus feature. Low vol.
            "buy_corvus": {
                "conditions": {"corvus": feature_cond(rtp, hr=1)},
                "scaling": ConstructScaling(tail_scaling("corvus")).return_dict(),
                "parameters": run_params(1.5, 5, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["corvus"], [(2.0, 5.0)], [0.4]).return_dict(),
            },
            # buy_ursa: the coin-flip tier, now also a 25,000x product. Mid-high vol.
            # slice_rtp 0.0215 at cost 268 -> cap rate 0.0215*268/25000 = 1 in 4,342,
            # against draco's 1 in 962: a 4.5x gap, comfortably past the 1.94x
            # break-even where draco would stop being worth its price.
            "buy_ursa": {
                "conditions": {
                    "wincap": wincap_cond("buy_ursa", 0.0215),
                    "ursa": feature_cond(round(rtp - 0.0215, 5), hr=1),
                },
                "scaling": ConstructScaling(tail_scaling("ursa")).return_dict(),
                "parameters": run_params(3, 10, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["ursa"], [(5.0, 20.0)], [0.3]).return_dict(),
            },
            # buy_draco: the dragon lottery -- very high vol, and the mode that reaches
            # the shared 25,000x ceiling most often. slice_rtp 0.05 at cost 520 ->
            # 1 in 962; 5.2% of draco's whole RTP is delivered at the cap, vs ursa's
            # 2.2%. That gap IS draco's justification now that the ceiling is shared.
            "buy_draco": {
                "conditions": {
                    "wincap": wincap_cond("buy_draco", 0.05),
                    "draco": feature_cond(round(rtp - 0.05, 5), hr=1),
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
            # RTP SPLITS are each tier's share of the mode's mean, at the MEASURED
            # Ascendant value (2,249x, swept at n=20k):
            #   corvus 0.350*232.1 =  81.2 (16.0%)   ursa  0.295*258.6 =  76.3 (15.0%)
            #   draco  0.250*502.4 = 125.6 (24.7%)   asc   0.100*2249  = 224.9 (44.3%)
            #   mean 508.0 -> cost 526x. Splits are that share of (rtp - wincap).
            # ASCENDANT CARRIES 44% OF THE MODE'S PAYBACK ON 10% OF ROLLS -- the shape
            # the audited mystery games use (Rage Bait's top tier: 10% of rolls, 52% of
            # payback), and the reason this mode can be priced above buy_draco at all.
            #
            # The cap share is derived from the tier rates like the tiers themselves:
            #   P(cap) = 0.295*(1/4339) + 0.250*(1/962) + 0.100*(1/1111) = 4.18e-04
            #   slice_rtp = 4.18e-04 * 25000/526 = 0.0199
            # Ascendant's own 1-in-1,111 is the swept at-cap rate: it completes ~90% of
            # the time and rides the top rungs, so it reaches 25,000x ~26x more readily
            # than a plain draco (0.09% vs 0.00% unforced at 20k).
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
                    "wincap": wincap_cond("buy_mystery", 0.0199),
                    # ⚠ THE SHARES MUST BE EXHAUSTIVE: sum(1/hr) + wincap weight == 1.
                    # First attempt used the clean design mix (hr 10/4/3.39/2.857), whose
                    # shares sum to 0.995 because 0.5% was left for the cap slice -- but
                    # 0.5% is the cap's GENERATION QUOTA in game_config, and its actual
                    # WEIGHT is rtp*cost/cap = 0.0199*526/25000 = 0.000419, i.e. 0.042%.
                    # The optimizer filled the 0.46% shortfall by scaling every tier up,
                    # which scaled the mode's RTP by the same factor: 0.9665 * 1.004604 =
                    # 0.9709, over the 0.9670 ceiling. Exactly the quota-vs-frequency
                    # confusion the CLAUDE.md note warns about, met from the other side.
                    # Shares below are the 35/29.5/25/10 mix renormalised to 1 - 0.000419.
                    "ascendant": feature_cond(0.4191, hr=9.9542, kind=6),  # 10.046%
                    "draco": feature_cond(0.2340, hr=3.9817, kind=5),      # 25.115%
                    "ursa": feature_cond(0.1422, hr=3.3743, kind=4),       # 29.636%
                    "corvus": feature_cond(0.1513, hr=2.8440, kind=3),     # 35.161%
                },
                "scaling": ConstructScaling(tail_scaling("ascendant") + tail_scaling("draco")).return_dict(),
                "parameters": run_params(3, 12, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["ascendant"], [(20.0, 60.0)], [0.3]).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
