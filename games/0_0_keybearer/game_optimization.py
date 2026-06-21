"""Set conditions/parameters for optimization program program"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    ConstructFenceBias,
    verify_optimization_input,
)


class OptimizationSetup:
    """Slice tables for Keybearer.

    The optimizer re-weights simulations so each criteria hits its target
    RTP / hit-rate. The per-slice rtp values MUST sum to the betmode rtp
    (0.96); the criteria names MUST match the Distribution criteria defined
    in game_config.py. Standard vs Super are separated by the recorded key
    count (`kind`): 3 -> Standard, 4 -> Super.
    """

    def __init__(self, game_config):
        self.game_config = game_config
        wincaps = {}
        for bm in game_config.bet_modes:
            wincaps[bm.get_name()] = bm.get_wincap()

        self.game_config.opt_params = {
            # base RTP 0.96 = wincap .01 + super .23 + mega .02 + standard .35 + basegame .35
            "base": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.01,
                        av_win=wincaps["base"],
                        search_conditions=wincaps["base"],
                    ).return_dict(),
                    "super": ConstructConditions(
                        rtp=0.23,
                        hr=2000,
                        search_conditions={"symbol": "scatter", "kind": 4},
                    ).return_dict(),
                    "mega": ConstructConditions(
                        rtp=0.02,
                        hr=100000,
                        search_conditions={"symbol": "scatter", "kind": 5},
                    ).return_dict(),
                    "standard": ConstructConditions(
                        rtp=0.35,
                        hr=180,
                        search_conditions={"symbol": "scatter", "kind": 3},
                    ).return_dict(),
                    "basegame": ConstructConditions(rtp=0.35, hr=12).return_dict(),
                    "0": ConstructConditions(
                        rtp=0, av_win=0, search_conditions=0
                    ).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {
                            "criteria": "basegame",
                            "scale_factor": 1.2,
                            "win_range": (1, 2),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "standard",
                            "scale_factor": 1.2,
                            "win_range": (50, 150),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "super",
                            "scale_factor": 1.2,
                            "win_range": (1000, 4000),
                            "probability": 1.0,
                        },
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=6,
                    max_m2m=12,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["basegame"],
                    bias_ranges=[(2.0, 3.0)],
                    bias_weights=[0.5],
                ).return_dict(),
            },
            # buy_super RTP 0.96 = wincap .02 + super .92 + mega .02 (buy->Mega ≈ 1/150)
            "buy_super": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.02,
                        av_win=wincaps["buy_super"],
                        search_conditions=wincaps["buy_super"],
                    ).return_dict(),
                    "super": ConstructConditions(
                        rtp=0.92,
                        hr="x",
                        search_conditions={"symbol": "scatter", "kind": 4},
                    ).return_dict(),
                    "mega": ConstructConditions(
                        rtp=0.02,
                        hr=150,
                        search_conditions={"symbol": "scatter", "kind": 5},
                    ).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {
                            "criteria": "super",
                            "scale_factor": 1.2,
                            "win_range": (1, 50),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "super",
                            "scale_factor": 0.8,
                            "win_range": (1000, 2000),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "super",
                            "scale_factor": 1.2,
                            "win_range": (3000, 8000),
                            "probability": 1.0,
                        },
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                ).return_dict(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["super"],
                    bias_ranges=[(200.0, 500.0)],
                    bias_weights=[0.3],
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
