"""Starwake feature events (Charge -> Bloom -> Roam).

Kept game-local because they're specific to this mechanic. The event_config
generator (src/write_data/write_data.py:107) auto-discovers any event `type`
from the books, so nothing needs registering -- these appear in
event_config_bonus.json after a run. Each follows the house event shape (cf.
src/events/events.py reveal_event): build a dict with index = len(book.events),
a `type` string, a payload, then book.add_event.

All (reel,row) positions are emitted in CLIENT coordinates -- row + 1 when the
board is padded -- to line up with reveal_event / win_info_event, which do the
same shift so the top padding symbol occupies client row 0.
"""


def _client_cells(gamestate, cells):
    """Unpadded (reel,row) engine cells -> client-coordinate dicts."""
    off = 1 if gamestate.config.include_padding else 0
    return [{"reel": int(reel), "row": int(row) + off} for (reel, row) in cells]


def constellation_dealt_event(gamestate):
    """Feature start: which tier was dealt and the dim outline cells to draw.

    `prelit` is empty for every normal tier. For DRACO ASCENDANT it carries the
    cells that are already burning at the deal -- they are sticky wilds from spin
    one, so the frontend must draw them lit (and the board wild) before the first
    spin resolves, not fade them in on a starLit beat. `beast` is the creature to
    render, which is NOT the tier for ascendant: it is a Draco, dealt hot.
    """
    c = gamestate.constellation
    prelit = sorted(c.prelit)
    event = {
        "index": len(gamestate.book.events),
        "type": "constellationDealt",
        "tier": c.tier,
        "beast": gamestate.config.constellation_beast_names.get(c.tier, c.tier),
        "cells": _client_cells(gamestate, c.target_cells),
        "totalCells": len(c.target_cells),
        "prelit": _client_cells(gamestate, prelit),
        "litCount": len(prelit),
    }
    gamestate.book.add_event(event)


def star_lit_event(gamestate, newly_lit):
    """One or more cells lit this spin because a winning line traced them."""
    c = gamestate.constellation
    event = {
        "index": len(gamestate.book.events),
        "type": "starLit",
        "newlyLit": _client_cells(gamestate, newly_lit),
        "litCount": len(c.lit),
        "totalCells": len(c.target_cells),
        "complete": c.is_complete,
    }
    gamestate.book.add_event(event)


def beast_wake_event(gamestate):
    """Set complete -> the beast awakens (it appears and roams from next spin)."""
    c = gamestate.constellation
    event = {
        "index": len(gamestate.book.events),
        "type": "beastWake",
        "tier": c.tier,
        "beast": gamestate.config.constellation_beast_names.get(c.tier, c.tier),
        "beastShape": {"reels": c.beast_w, "rows": c.beast_h},
    }
    gamestate.book.add_event(event)


def beast_roam_event(gamestate):
    """The beast's covered cells and current multiplier this spin."""
    c = gamestate.constellation
    event = {
        "index": len(gamestate.book.events),
        "type": "beastRoam",
        "cells": _client_cells(gamestate, c.beast_cells()),
        "multiplier": int(c.multiplier),
    }
    gamestate.book.add_event(event)


def multiplier_climb_event(gamestate):
    """The beast multiplier ticked up this roam spin (an enumerable ladder value)."""
    c = gamestate.constellation
    event = {
        "index": len(gamestate.book.events),
        "type": "multiplierClimb",
        "multiplier": int(c.multiplier),
    }
    gamestate.book.add_event(event)
