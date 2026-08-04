package engine

import "starwake/internal/sdk/config"

// MaxPaylines bounds the reusable win buffer.
const MaxPaylines = 64

// LineWin is one paying payline.
//
// Positions are stored as a row-per-reel array covering the first Kind reels,
// because a line win is always a PREFIX run from reel 0 -- there is no way to win
// on reels 1-3 while reel 0 misses. That keeps a win allocation-free and makes
// "which cells did this win cross" a cheap loop, which matters because that
// question is what lights Starwake's constellation cells every single spin.
type LineWin struct {
	Symbol    SymID
	Kind      int
	Win       float64
	Mult      int
	WinNoMult float64
	LineIndex int
	Rows      [MaxReels]uint8
}

// WinResult holds one spin's line wins. Reused across spins; Evaluate resets it.
type WinResult struct {
	TotalWin float64
	Wins     []LineWin
	buf      [MaxPaylines]LineWin
}

// NewWinResult prepares a reusable result buffer.
func NewWinResult() *WinResult {
	w := &WinResult{}
	w.Wins = w.buf[:0]
	return w
}

// Reset clears the result for a new spin without releasing its buffer.
func (w *WinResult) Reset() {
	w.TotalWin = 0
	w.Wins = w.buf[:0]
}

// Payline is a precomputed line: the row it occupies on each reel.
type Payline struct {
	Index int
	Rows  [MaxReels]uint8
	N     int
}

// CompilePaylines converts config paylines into the fixed-size form the
// evaluator walks.
func CompilePaylines(c *config.Config) []Payline {
	out := make([]Payline, 0, len(c.Paylines))
	for _, l := range c.Paylines {
		p := Payline{Index: l.Index, N: len(l.Rows)}
		for reel, row := range l.Rows {
			p.Rows[reel] = uint8(row)
		}
		out = append(out, p)
	}
	return out
}

// LineEvaluator evaluates every payline on a board.
//
// Holds only immutable references, so one instance is shared by all spins on a
// worker; the mutable per-spin state lives in the WinResult the caller passes in.
type LineEvaluator struct {
	syms     *SymbolTable
	paylines []Payline
	wildSym  SymID
	strategy MultStrategy
}

// NewLineEvaluator builds an evaluator for a config.
func NewLineEvaluator(c *config.Config, st *SymbolTable, strategy MultStrategy) (*LineEvaluator, error) {
	wilds := c.SpecialSymbols["wild"]
	var wildSym SymID
	if len(wilds) > 0 {
		id, err := st.ID(wilds[0])
		if err != nil {
			return nil, err
		}
		wildSym = id
	}
	return &LineEvaluator{
		syms:     st,
		paylines: CompilePaylines(c),
		wildSym:  wildSym,
		strategy: strategy,
	}, nil
}

// Evaluate scores every payline, writing into out.
//
// Port of Lines.get_lines (src/calculations/lines.py). The wild handling is the
// subtle part and is worth stating explicitly, because it is where a silent
// mis-port would do the most damage:
//
//   - A run of leading WILDS is counted separately (wildMatches) from the run
//     that follows an anchor symbol (matches).
//   - The first non-wild symbol becomes the ANCHOR. After that, both the anchor
//     symbol and further wilds extend the run -- those wilds count toward
//     `matches`, NOT toward `wildMatches`.
//   - Two candidate wins are then compared: the pure-wild line paid as wilds
//     (wildMatches of W), and the whole run paid as the anchor
//     (wildMatches+matches of the anchor). THE LARGER ONE PAYS.
//
// That comparison is why Starwake's W deliberately has no 3- or 4-kind paytable
// entry: with one, a 3-wild prefix could out-pay a longer real-symbol line, and
// the feature manufactures wilds by design.
func (e *LineEvaluator) Evaluate(b *Board, globalMult int, out *WinResult) {
	out.Reset()

	for i := range e.paylines {
		line := &e.paylines[i]

		firstSym := b.Cells[0][line.Rows[0]].Sym
		inWildPrefix := e.syms.IsWild(firstSym)

		var anchor SymID
		wildMatches, matches := 0, 0
		if inWildPrefix {
			wildMatches = 1
		} else {
			anchor = firstSym
			matches = 1
		}

		for reel := 1; reel < line.N; reel++ {
			sym := b.Cells[reel][line.Rows[reel]].Sym
			if !inWildPrefix {
				// Anchored: the anchor symbol or any wild extends the run.
				if sym == anchor || e.syms.IsWild(sym) {
					matches++
					continue
				}
				break
			}
			// Still in the leading-wild run.
			if e.syms.IsWild(sym) {
				wildMatches++
				continue
			}
			anchor = sym
			matches++
			inWildPrefix = false
		}

		wildWin := e.syms.Pay(wildMatches, e.wildSym)
		var baseWin float64
		if anchor != NoSym {
			baseWin = e.syms.Pay(wildMatches+matches, anchor)
		}
		if baseWin <= 0 && wildWin <= 0 {
			continue
		}

		// The larger candidate pays; ties go to the anchor line, which is longer.
		symbol, kind, amount := anchor, wildMatches+matches, baseWin
		if wildWin > baseWin {
			symbol, kind, amount = e.wildSym, wildMatches, wildWin
		}

		win, mult := applyMult(b, e.strategy, amount, globalMult, &line.Rows, kind)

		if len(out.Wins) < MaxPaylines {
			out.Wins = append(out.Wins, LineWin{
				Symbol:    symbol,
				Kind:      kind,
				Win:       win,
				Mult:      mult,
				WinNoMult: amount,
				LineIndex: line.Index,
				Rows:      line.Rows,
			})
		}
		out.TotalWin += win
	}
}

// WinningCells calls fn for every (reel,row) covered by a winning line.
//
// This is how Starwake lights constellation cells: a cell lights when a WINNING
// PAYLINE CROSSES IT. Kept as a callback so the caller can accumulate into
// whatever shape it wants (a bitmask, in the feature's case) without this package
// allocating a slice per spin.
func (w *WinResult) WinningCells(fn func(reel, row int)) {
	for i := range w.Wins {
		win := &w.Wins[i]
		for reel := 0; reel < win.Kind; reel++ {
			fn(reel, int(win.Rows[reel]))
		}
	}
}
