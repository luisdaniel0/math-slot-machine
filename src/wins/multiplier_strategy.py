"""Global multipliers, symbol multipliers, combined multipliers or no actions
    All functions return [final_win_amount], [applied multiplier]"""

from typing import List, Dict
from src.calculations.board import Board


def apply_mult(
    board: Board,
    strategy: str,
    win_amount: float = 0.0,
    global_multiplier: int = 1,
    positions: list = [],
    multiplier_key: str = "multiplier",
):
    """Apply multiplier method to win_amount and winning symbol positions."""
    # Dispatched, not table-built: the previous dict evaluated EVERY strategy on
    # every line win just to index one of them.
    if strategy == "global":
        return apply_global_mult(win_amount, global_multiplier)
    if strategy == "symbol":
        return apply_added_symbol_mult(board, win_amount, positions, multiplier_key=multiplier_key)
    if strategy == "max_symbol":
        return apply_max_symbol_mult(board, win_amount, positions, multiplier_key=multiplier_key)
    if strategy == "combined":
        return apply_combined_mult(board, win_amount, global_multiplier, positions, multiplier_key=multiplier_key)
    raise KeyError(strategy)


def apply_global_mult(win_amount: float, global_multiplier: int) -> tuple:
    """Enhance win global multiplier"""
    return (round(win_amount * global_multiplier, 2), global_multiplier)


def apply_added_symbol_mult(board: Board, win_amount: float, positions: List[Dict], multiplier_key: str) -> tuple:
    """Get multiplier attribute from all winning positions"""
    symbol_multiplier = 0
    for pos in positions:
        if (
            board[pos["reel"]][pos["row"]].check_attribute(multiplier_key)
            and board[pos["reel"]][pos["row"]].get_attribute(multiplier_key) > 1
        ):
            symbol_multiplier += board[pos["reel"]][pos["row"]].get_attribute(multiplier_key)
    return (round(win_amount * max(symbol_multiplier, 1), 2), max(symbol_multiplier, 1))


def apply_max_symbol_mult(board: Board, win_amount: float, positions: List[Dict], multiplier_key: str) -> tuple:
    """Highest multiplier among the winning positions, rather than their sum.

    For a BLOCK symbol that stamps one multiplier across every cell it covers,
    summing pays k*M to a line crossing k of those cells -- so a published x10
    ladder silently becomes x20/x30 and the block's contribution scales with the
    geometry of the payline instead of the advertised value. Max applies the
    multiplier once per win, which is what "the multiplier applies to wins this
    symbol takes part in" means.
    """
    symbol_multiplier = 1
    for pos in positions:
        symbol = board[pos["reel"]][pos["row"]]
        if symbol.check_attribute(multiplier_key):
            symbol_multiplier = max(symbol_multiplier, symbol.get_attribute(multiplier_key))
    return (round(win_amount * symbol_multiplier, 2), symbol_multiplier)


def apply_combined_mult(
    board: Board, win_amount: float, global_multiplier: int, positions: List[Dict], multiplier_key
) -> tuple:
    """Apply symbol multipliers and then global multiplier"""
    win, sym_mult = apply_added_symbol_mult(board, win_amount, positions, multiplier_key)
    return (win * global_multiplier  , sym_mult * global_multiplier)
