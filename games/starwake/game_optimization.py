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
  buy_corvus           : corvus          buy_ursa   : ursa
  buy_draco            : wincap, draco    buy_mystery: wincap, mystery
Only Draco reaches the cap, so only draco/mystery modes carry a wincap slice;
buy_corvus/buy_ursa have none (their 2x2/2x3 beasts stop at honest lower ceilings).
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

        def feature_cond(slice_rtp, hr):
            """A tier/feature slice: rtp is authoritative, hr the trigger-rate hint
            (buys feature every spin -> hr=1; base/ante trigger 1-per-hr spins)."""
            return ConstructConditions(
                rtp=slice_rtp, hr=hr, search_conditions={"symbol": "scatter"}
            ).return_dict()

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
                    "draco": feature_cond(0.13, hr=1900),
                    "ursa": feature_cond(0.11, hr=600),
                    "corvus": feature_cond(0.10, hr=220),
                    "basegame": base_cond(0.6065, hr=3.5),
                    "0": zero_cond,
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
                    "draco": feature_cond(0.15, hr=1000),
                    "ursa": feature_cond(0.13, hr=370),
                    "corvus": feature_cond(0.12, hr=160),
                    "basegame": base_cond(0.5415, hr=3.0),
                    "0": zero_cond,
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
            # buy_ursa: the coin-flip tier. Mid-high vol.
            "buy_ursa": {
                "conditions": {"ursa": feature_cond(rtp, hr=1)},
                "scaling": ConstructScaling(tail_scaling("ursa")).return_dict(),
                "parameters": run_params(3, 10, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["ursa"], [(5.0, 20.0)], [0.3]).return_dict(),
            },
            # buy_draco: the dragon lottery -- wincap slice + very high vol.
            "buy_draco": {
                "conditions": {
                    "wincap": wincap_cond("buy_draco", 0.05),
                    "draco": feature_cond(round(rtp - 0.05, 5), hr=1),
                },
                "scaling": ConstructScaling(tail_scaling("draco")).return_dict(),
                "parameters": run_params(5, 20, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["draco"], [(50.0, 150.0)], [0.3]).return_dict(),
            },
            # buy_mystery: weighted mix -> wincap slice (its draco share) + mixed vol.
            "buy_mystery": {
                "conditions": {
                    "wincap": wincap_cond("buy_mystery", 0.04),
                    "mystery": feature_cond(round(rtp - 0.04, 5), hr=1),
                },
                "scaling": ConstructScaling(tail_scaling("mystery")).return_dict(),
                "parameters": run_params(3, 12, [10, 20, 50], [0.6, 0.2, 0.2]),
                "distribution_bias": ConstructFenceBias(["mystery"], [(20.0, 60.0)], [0.3]).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
