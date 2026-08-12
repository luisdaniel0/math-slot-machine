"""Export game_config.py into a JSON file the Go engine reads.

WHY THIS EXISTS. The Go rewrite moves the HOT LOOP (board draw, line eval, the
constellation state machine, book writing) to Go, but deliberately leaves the
DESIGN SURFACE in Python: game_config.py stays the one place a paytable value, a
reel weight, a constellation cell or a ladder rung is edited. The measure loop
("edit a weight, re-run") is unchanged -- it just gains an export step.

The seam is data-only by construction. game_config's two helpers,
_tier_condition() and _wincap_condition(), are FACTORY FUNCTIONS evaluated once at
construction time (game_config.py:483-485, 534-535); what they return, and what is
stored on the BetMode, is a plain dict. So nothing here has to translate Python
logic into declarative data -- there is no logic left in the config to translate.

WHAT IS NOT EXPORTED, ON PURPOSE:
  - REEL STRIPS. Only the filenames ship. The CSVs in games/starwake/reels/ stay
    the single source of truth and Go parses them directly, so a
    generate_reels.py re-run reaches the engine with no re-export. Go must mirror
    Config.read_reels_csv's parsing rule: keep only alphanumeric characters per
    cell (src/config/config.py:read_reels_csv).
  - opt_params. Those belong to the Rust optimizer, which is unchanged and reads
    them through the existing Python path.

THE STRICT-KEY GUARD IS THE POINT OF THIS FILE. Every distribution condition is
checked against a known key set and every export is checked for completeness. If
game_config grows a field the Go engine does not know about, this FAILS LOUDLY
rather than writing a quietly incomplete config -- which would show up as a
subtly different game in a 1e6 pool, the exact silent-divergence failure mode
this whole port is trying to avoid.
"""

import json
import os
import sys

from game_config import GameConfig

# Written OUTSIDE library/. library/ holds the converged production pool (~11 GB,
# gitignored, not protected by any branch), and nothing in the Go pipeline may
# write there -- the sweep harnesses already demonstrate how easily that pool is
# clobbered by a tool that reuses the standard paths.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_PATH = os.path.join(REPO_ROOT, "go", "config", "starwake.json")

SCHEMA_VERSION = 1

# Every condition key the Go engine understands. A condition carrying anything
# else is a config change that has outrun the engine, and must stop the export.
KNOWN_CONDITION_KEYS = {
    "reel_weights",
    "scatter_triggers",
    "mult_values",
    "force_wincap",
    "force_freegame",
    "force_ascension",
}


def weighted_pairs(mapping: dict, key_name: str) -> list:
    """Turn an int-keyed weight dict into an ordered list of records.

    JSON object keys are strings, so {3: 1, 4: 2} would come back from a Go
    decoder as {"3": 1, "4": 2} and force string->int parsing at the far end.
    Emitting records keeps the key an integer and keeps the order stable.
    """
    return [{key_name: int(k), "weight": v} for k, v in sorted(mapping.items())]


def export_paytable(config) -> list:
    """(kind, symbol) -> value becomes a list of records.

    A tuple cannot be a JSON key at all, so this is a required reshape rather
    than a stylistic one. Sorted so the file is diffable across re-exports.
    """
    return [
        {"kind": int(kind), "symbol": sym, "value": value}
        for (kind, sym), value in sorted(
            config.paytable.items(), key=lambda kv: (kv[0][1], -kv[0][0])
        )
    ]


def export_paylines(config) -> list:
    """Payline index -> row-per-reel. Kept as records to preserve integer indices."""
    return [
        {"index": int(idx), "rows": list(rows)}
        for idx, rows in sorted(config.paylines.items())
    ]


def export_conditions(conditions: dict, criteria: str, mode_name: str) -> dict:
    """Convert one distribution's conditions, rejecting anything unrecognised."""
    unknown = set(conditions) - KNOWN_CONDITION_KEYS
    if unknown:
        raise ValueError(
            f"{mode_name}/{criteria}: condition key(s) {sorted(unknown)} are not "
            f"known to the Go engine. Add explicit handling here AND in the Go "
            f"decoder before exporting -- do not drop them silently."
        )

    out = {
        "forceWincap": bool(conditions.get("force_wincap", False)),
        "forceFreegame": bool(conditions.get("force_freegame", False)),
        "forceAscension": bool(conditions.get("force_ascension", False)),
    }

    # reel_weights is required on every distribution (Distribution enforces it).
    out["reelWeights"] = {
        gametype: dict(weights)
        for gametype, weights in conditions["reel_weights"].items()
    }

    # Absent on the non-triggering base/zero slices, which never force a count.
    if "scatter_triggers" in conditions:
        out["scatterTriggers"] = weighted_pairs(conditions["scatter_triggers"], "scatters")

    if "mult_values" in conditions:
        out["multValues"] = {
            gametype: weighted_pairs(values, "value")
            for gametype, values in conditions["mult_values"].items()
        }

    return out


def export_bet_modes(config) -> list:
    """Serialise every BetMode and its distributions via their public getters."""
    modes = []
    for bm in config.bet_modes:
        distributions = []
        for d in bm.get_distributions():
            distributions.append(
                {
                    "criteria": d.get_criteria(),
                    "quota": d.get_quota(),
                    "fixedAmt": d.get_fixed_amt(),
                    "winCriteria": d.get_win_criteria(),
                    "conditions": export_conditions(
                        d._conditions, d.get_criteria(), bm.get_name()
                    ),
                }
            )
        modes.append(
            {
                "name": bm.get_name(),
                "cost": bm.get_cost(),
                "rtp": bm.get_rtp(),
                # BetMode.max_win is BOTH the published ceiling and the engine
                # clamp (run_sims.py:48 -> config.wincap for that mode), so Go
                # must clamp on this per-mode value, never on the global wincap.
                "maxWin": bm.get_wincap(),
                "autoCloseDisabled": bm.get_auto_close_disabled(),
                "isFeature": bm.get_feature(),
                "isBuyBonus": bm.get_buybonus(),
                "distributions": distributions,
            }
        )
    return modes


def export_constellation(config) -> dict:
    """One record per tier, with every per-tier knob resolved.

    game_config derives "ascendant" from "draco" at construction time so the two
    cannot drift; that derivation has already happened by the time we read the
    attributes, so ascendant appears here as a fully-formed tier.
    """
    tiers = {}
    for tier, cells in config.constellation_cells.items():
        tiers[tier] = {
            "cells": [[int(r), int(row)] for (r, row) in cells],
            "beastShape": list(config.constellation_beast_shapes[tier]),
            "multLadder": list(config.constellation_mult_ladders[tier]),
            "ladderRungs": config.constellation_ladder_rungs[tier],
            "prelitCells": [
                [int(r), int(row)]
                for (r, row) in config.constellation_prelit_cells.get(tier, ())
            ],
            "beastCount": int(getattr(config, "constellation_beast_count", {}).get(tier, 1)),
            "beastName": config.constellation_beast_names[tier],
            "featureSpins": config.num_feature_spins[tier],
        }

        # ACT TWO. Present only for tiers given a star-value table; a tier without
        # one runs the original climbing ladder, which is how the two mechanics are
        # A/B swept. Values are emitted as an ORDERED LIST of {value, weight} pairs,
        # never a map: Go randomises map iteration order and the engine's output has
        # to stay byte-deterministic for the published sha256s to reproduce.
        values = getattr(config, "constellation_star_values", {}).get(tier)
        if values:
            tiers[tier]["starDrops"] = {
                "starSymbol": config.constellation_star_symbol,
                "values": [
                    {"value": int(v), "weight": int(w)}
                    for v, w in sorted(values.items())
                ],
            }

            # ASCENSION rides inside starDrops because it is meaningless without
            # one -- it replaces that table for the rest of the roam. Emitted ONLY
            # for tiers that declare it: a tier without the block makes no extra
            # rng call in the engine, which is what keeps buy_ursa and buy_draco
            # byte-identical to a pre-ascension pool and out of the re-sim.
            asc = getattr(config, "constellation_ascension", {}).get(tier)
            if asc:
                tiers[tier]["starDrops"]["ascension"] = {
                    "oneIn": int(asc["one_in"]),
                    "values": [
                        {"value": int(v), "weight": int(w)}
                        for v, w in sorted(asc["values"].items())
                    ],
                }

    return {"minRoamSpins": config.min_roam_spins, "tiers": tiers}


def validate(payload: dict, config) -> None:
    """Cross-checks that would otherwise fail much later, in a 1e6 pool.

    These mirror invariants already asserted in tests/starwake/, re-stated here
    because the export is a NEW place they can break: a reshape bug here produces
    a valid-looking JSON file describing a different game.
    """
    grid = (config.num_reels, config.num_rows[0])

    for tier, t in payload["gameSpecific"]["tiers"].items():
        # The ladder guard that the original test got wrong: rung count must be
        # EXACTLY the measured achievable roam depth. Too short silently clamps a
        # ceiling; too long advertises a multiplier no player can be paid.
        if len(t["multLadder"]) != t["ladderRungs"]:
            raise ValueError(
                f"{tier}: ladder has {len(t['multLadder'])} rungs but "
                f"ladderRungs says {t['ladderRungs']}"
            )

        for (reel, row) in t["cells"]:
            if not (0 <= reel < grid[0] and 0 <= row < grid[1]):
                raise ValueError(f"{tier}: cell ({reel},{row}) is off a {grid} grid")

        if len(set(map(tuple, t["cells"]))) != len(t["cells"]):
            raise ValueError(f"{tier}: duplicate constellation cells")

        prelit = set(map(tuple, t["prelitCells"]))
        if not prelit <= set(map(tuple, t["cells"])):
            raise ValueError(f"{tier}: pre-lit cells are not part of the shape")
        if prelit and len(prelit) >= len(t["cells"]):
            raise ValueError(f"{tier}: fully pre-lit -- would complete before spin 1")

        # The beast must have somewhere to roam, or the signature mechanic is dead.
        bw, bh = t["beastShape"]
        origins = (grid[0] - bw + 1) * (grid[1] - bh + 1)
        if origins < 2:
            raise ValueError(f"{tier}: beast {bw}x{bh} has {origins} roam positions")

        # Every block needs a spot that is not on top of another one. This is a
        # PACKING question, not an origin count: a 2x2 on a 5x4 has 12 origins but
        # only 4 disjoint placements, so checking against 12 would wave through a
        # beastCount that can only be met by stacking blocks -- which renders as one
        # block and silently loses the mechanic. Mirrors Tier.maxDisjoint in Go so
        # the two ends cannot disagree about what is loadable.
        packed = (grid[0] // bw) * (grid[1] // bh)
        if t["beastCount"] < 1:
            raise ValueError(f"{tier}: beastCount {t['beastCount']} must be >= 1")
        if t["beastCount"] > packed:
            raise ValueError(
                f"{tier}: beastCount {t['beastCount']} but only {packed} disjoint "
                f"{bw}x{bh} blocks fit a {grid[0]}x{grid[1]} grid"
            )

    exported = {m["name"] for m in payload["betModes"]}
    expected = {bm.get_name() for bm in config.bet_modes}
    if exported != expected:
        raise ValueError(f"bet mode mismatch: exported {exported}, config has {expected}")

    for m in payload["betModes"]:
        # Quotas are RELATIVE WEIGHTS, not probabilities: get_sim_splits
        # (src/state/run_sims.py) seeds counts from int(num_sims * quota) and then
        # tops up or trims by weighted random choice until the total matches the
        # requested sim count, so a set summing to anything > 0 is normalised.
        # ante_starfall legitimately sums to 0.9615. Reported, never fatal --
        # Go must reproduce the same normalisation rather than assume 1.0.
        if any(d["fixedAmt"] is not None for d in m["distributions"]):
            continue
        total = sum(d["quota"] for d in m["distributions"])
        if abs(total - 1.0) > 1e-9:
            print(f"  note: {m['name']} quotas sum to {total:.4f} (normalised at run time)")


def build_payload(config) -> dict:
    """Assemble the whole config document."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedBy": "games/starwake/export_go_config.py",
        "game": {
            "id": config.game_id,
            "name": config.game_name,
            "provider": config.provider_name,
            "providerNumber": config.provider_number,
            "winType": config.win_type,
            "rtp": config.rtp,
            "wincap": config.wincap,
            "numReels": config.num_reels,
            "numRows": list(config.num_rows),
            "includePadding": config.include_padding,
            "basegameType": config.basegame_type,
            "freegameType": config.freegame_type,
        },
        "paytable": export_paytable(config),
        "paylines": export_paylines(config),
        "specialSymbols": {k: list(v) for k, v in config.special_symbols.items()},
        # Filenames only -- Go reads the CSVs so the strips keep one source of truth.
        # Mirrors game_config's own map rather than restating it, so a new strip
        # cannot reach the Python config and silently miss the Go one -- the roam
        # strip failing to export would leave act two drawing FR0, collecting
        # nothing, and paying x1 all the way through while looking entirely normal.
        "reels": dict(config.reel_files),
        "reelsDir": "games/starwake/reels",
        "anticipationTriggers": dict(config.anticipation_triggers),
        "freespinTriggers": {
            gametype: [
                {"scatters": int(count), "spins": spins}
                for count, spins in sorted(triggers.items())
            ]
            for gametype, triggers in config.freespin_triggers.items()
        },
        "scatterTiers": [
            {"scatters": int(count), "tier": tier}
            for count, tier in sorted(config.scatter_tiers.items())
        ],
        # The GAME-SPECIFIC block. The Go SDK deliberately does not decode this --
        # it hands the raw JSON to the owning game, so a second game reuses the
        # SDK without inheriting Starwake's vocabulary. Hence the neutral key.
        "gameSpecific": export_constellation(config),
        "betModes": export_bet_modes(config),
    }


def main() -> int:
    config = GameConfig()
    payload = build_payload(config)
    validate(payload, config)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="UTF-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False)
        f.write("\n")

    rel = os.path.relpath(OUTPUT_PATH, REPO_ROOT)
    print(f"wrote {rel}")
    print(
        f"  {len(payload['paytable'])} paytable entries, "
        f"{len(payload['paylines'])} paylines, "
        f"{len(payload['gameSpecific']['tiers'])} tiers, "
        f"{len(payload['betModes'])} bet modes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
