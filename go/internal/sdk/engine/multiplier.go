package engine

import "math"

// MultStrategy decides how symbol multipliers on a winning line combine.
//
// Port of src/wins/multiplier_strategy.py.
type MultStrategy uint8

const (
	// MultNone applies no multiplier.
	MultNone MultStrategy = iota
	// MultGlobal applies a single game-wide multiplier.
	MultGlobal
	// MultSumSymbol SUMS the multipliers of every winning position.
	//
	// ⚠ THIS IS THE ONE THAT CAUSED THE BLOCK-WILD BUG. Starwake's beast stamps
	// its multiplier on all four cells of its 2x2 block, and a payline crossing
	// two of them was paid 2*M -- so an advertised x200 rung silently paid x400,
	// and 87% of buy_corvus's entire payout came from double-crossings. Correct
	// for scattered single-cell multipliers, wrong for any block symbol.
	MultSumSymbol
	// MultMaxSymbol applies the HIGHEST multiplier among the winning positions,
	// once. This is what "the multiplier applies to wins this symbol takes part
	// in" actually means for a block, and what Starwake uses.
	MultMaxSymbol
	// MultCombined applies symbol multipliers, then the global multiplier.
	MultCombined
)

// ParseMultStrategy resolves the strategy name used in game config.
func ParseMultStrategy(name string) (MultStrategy, bool) {
	switch name {
	case "", "none":
		return MultNone, true
	case "global":
		return MultGlobal, true
	case "symbol":
		return MultSumSymbol, true
	case "max_symbol":
		return MultMaxSymbol, true
	case "combined":
		return MultCombined, true
	}
	return MultNone, false
}

// roundCents rounds to 2dp, matching Python's round(x, 2) on the win amounts.
//
// Payouts are accumulated and finally published as integer hundredths
// (docs/rgs_docs/data_format.md requires uint64 payout multipliers), so rounding
// at the same point Python does keeps the two engines comparable cent for cent.
func roundCents(v float64) float64 { return math.Round(v*100) / 100 }

// applyMult returns the multiplied win and the multiplier that was applied.
//
// positions are the winning cells; globalMult is the game-wide multiplier (1 when
// unused). Reads multipliers straight off the board cells -- Cell.Mult of 0 means
// the cell carries none, matching Python's `None`.
func applyMult(
	b *Board, strategy MultStrategy, win float64, globalMult int,
	rows *[MaxReels]uint8, n int,
) (float64, int) {
	switch strategy {
	case MultNone:
		return roundCents(win), 1

	case MultGlobal:
		return roundCents(win * float64(globalMult)), globalMult

	case MultSumSymbol:
		sum := 0
		for reel := 0; reel < n; reel++ {
			// Python only adds multipliers strictly greater than 1, so a plain
			// x1 wild contributes nothing to the sum.
			if m := int(b.Cells[reel][rows[reel]].Mult); m > 1 {
				sum += m
			}
		}
		if sum < 1 {
			sum = 1
		}
		return roundCents(win * float64(sum)), sum

	case MultMaxSymbol:
		best := 1
		for reel := 0; reel < n; reel++ {
			if m := int(b.Cells[reel][rows[reel]].Mult); m > best {
				best = m
			}
		}
		return roundCents(win * float64(best)), best

	case MultCombined:
		w, symMult := applyMult(b, MultSumSymbol, win, 1, rows, n)
		return w * float64(globalMult), symMult * globalMult
	}
	return roundCents(win), 1
}
