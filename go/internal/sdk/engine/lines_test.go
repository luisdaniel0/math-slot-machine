package engine

import (
	"testing"

	"starwake/internal/sdk/config"
)

// The line evaluator is the subtlest thing in the port and the place a silent
// mis-port would do the most damage, so these are hand-built boards with known
// answers rather than statistical checks.

// blankBoard fills every cell so that NO payline can pay: each reel carries a
// different low symbol, so no two adjacent reels ever match. Tests then overwrite
// exactly the line under test, and any win reported is unambiguously theirs.
func blankBoard(t *testing.T, c *config.Config, st *SymbolTable) *Board {
	t.Helper()
	b, err := NewBoard(c)
	if err != nil {
		t.Fatalf("new board: %v", err)
	}
	perReel := []SymID{
		st.MustID("L1"), st.MustID("L2"), st.MustID("L3"),
		st.MustID("L4"), st.MustID("L5"),
	}
	for reel := 0; reel < b.NumReels; reel++ {
		for row := 0; row < b.NumRows[reel]; row++ {
			b.Set(reel, row, Cell{Sym: perReel[reel]})
		}
	}
	return b
}

// setLine writes symbols along payline 1 (the top straight, row 0 on every reel).
func setLine(b *Board, syms ...Cell) {
	for reel, cell := range syms {
		b.Set(reel, 0, cell)
	}
}

// winForLine finds the win on a specific payline.
//
// Needed because writing WILDS onto payline 1 also creates real wins on the other
// paylines that share its leading cells: five lines start at (0,0), and those
// passing through (1,0) too then read W,W,<reel-2 symbol> -- a genuine
// wild-substituted 3-of-a-kind. That is correct engine behaviour, not fixture
// noise, so the tests assert on the line under test rather than on a total.
func winForLine(out *WinResult, index int) (LineWin, bool) {
	for _, w := range out.Wins {
		if w.LineIndex == index {
			return w, true
		}
	}
	return LineWin{}, false
}

func evaluator(t *testing.T, c *config.Config, st *SymbolTable) (*LineEvaluator, *WinResult) {
	t.Helper()
	// Starwake uses max_symbol -- the strategy that fixed the block-wild bug.
	e, err := NewLineEvaluator(c, st, MultMaxSymbol)
	if err != nil {
		t.Fatalf("new evaluator: %v", err)
	}
	return e, NewWinResult()
}

func TestBlankBoardPaysNothing(t *testing.T) {
	c, st, _ := load(t)
	e, out := evaluator(t, c, st)
	b := blankBoard(t, c, st)

	e.Evaluate(b, 1, out)
	if out.TotalWin != 0 || len(out.Wins) != 0 {
		t.Fatalf("blank board paid %v across %d wins; the isolation fixture is broken",
			out.TotalWin, len(out.Wins))
	}
}

func TestLineWins(t *testing.T) {
	c, st, _ := load(t)
	e, out := evaluator(t, c, st)

	w := Cell{Sym: st.MustID("W"), Mult: 1}
	h1 := Cell{Sym: st.MustID("H1")}
	l1 := Cell{Sym: st.MustID("L1")}

	cases := []struct {
		name       string
		line       []Cell
		wantWin    float64
		wantKind   int
		wantSymbol string
	}{
		{
			// 3xH1 then a break. Pays the 3-kind, 3x.
			name: "plain three of a kind", line: []Cell{h1, h1, h1, l1, l1},
			wantWin: 3, wantKind: 3, wantSymbol: "H1",
		},
		{
			name: "plain five of a kind", line: []Cell{h1, h1, h1, h1, h1},
			wantWin: 12, wantKind: 5, wantSymbol: "H1",
		},
		{
			// Leading wilds extend the anchor's run: 2 wilds + 3 H1 = 5xH1.
			// The wild candidate (2xW) does not pay, so the anchor wins.
			name: "wild prefix extends the anchor", line: []Cell{w, w, h1, h1, h1},
			wantWin: 12, wantKind: 5, wantSymbol: "H1",
		},
		{
			// All wilds: no anchor at all, so the wild line itself pays 5xW.
			name: "all wilds pay as wilds", line: []Cell{w, w, w, w, w},
			wantWin: 15, wantKind: 5, wantSymbol: "W",
		},
		{
			// A wild AFTER the anchor counts toward the anchor's run, not the
			// wild prefix -- so this is 5xH1, not 1 wild + 4.
			name: "wild after anchor", line: []Cell{h1, w, h1, h1, h1},
			wantWin: 12, wantKind: 5, wantSymbol: "H1",
		},
		{
			// 3 wilds + 2 H1. W has NO 3-kind entry, so the anchor's 5-kind pays.
			// With a 3xW entry this would be the wrong answer -- which is exactly
			// why the paytable deliberately omits short wild lines.
			name: "three wilds then anchor", line: []Cell{w, w, w, h1, h1},
			wantWin: 12, wantKind: 5, wantSymbol: "H1",
		},
		{
			// Two of a kind pays nothing.
			name: "two of a kind does not pay", line: []Cell{h1, h1, l1, l1, l1},
			wantWin: 0, wantKind: 0, wantSymbol: "",
		},
		{
			// A break on reel 0 means no line win at all.
			name: "no run from reel zero", line: []Cell{l1, h1, h1, h1, h1},
			wantWin: 0, wantKind: 0, wantSymbol: "",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			b := blankBoard(t, c, st)
			setLine(b, tc.line...)
			e.Evaluate(b, 1, out)

			got, ok := winForLine(out, 1)
			if tc.wantWin == 0 {
				if ok {
					t.Fatalf("payline 1 paid %v, want nothing", got.Win)
				}
				return
			}
			if !ok {
				t.Fatalf("payline 1 did not pay (total %v across %d wins)",
					out.TotalWin, len(out.Wins))
			}
			if got.Win != tc.wantWin {
				t.Errorf("win = %v, want %v", got.Win, tc.wantWin)
			}
			if got.Kind != tc.wantKind {
				t.Errorf("kind = %d, want %d", got.Kind, tc.wantKind)
			}
			if name := st.Name(got.Symbol); name != tc.wantSymbol {
				t.Errorf("symbol = %s, want %s", name, tc.wantSymbol)
			}
		})
	}
}

// THE REGRESSION TEST FOR THE BLOCK-WILD BUG.
//
// The beast stamps one multiplier onto all four cells of its 2x2 block. Under the
// "symbol" strategy those multipliers are SUMMED, so a payline crossing two block
// cells paid 2*M -- an advertised x200 rung silently paying x400, and 87% of
// buy_corvus's payout coming from double-crossings. "max_symbol" applies it once.
func TestBlockMultiplierAppliedOnceNotSummed(t *testing.T) {
	c, st, _ := load(t)
	b := blankBoard(t, c, st)

	beast := Cell{Sym: st.MustID("W"), Mult: 200}
	plain := Cell{Sym: st.MustID("W"), Mult: 1}
	h1 := Cell{Sym: st.MustID("H1")}
	// Two beast cells on the winning line, as a 2x2 block crossing it would give.
	setLine(b, beast, beast, h1, h1, h1)

	maxEval, out := evaluator(t, c, st)
	maxEval.Evaluate(b, 1, out)
	got, ok := winForLine(out, 1)
	if !ok {
		t.Fatalf("payline 1 did not pay")
	}
	if got.Mult != 200 {
		t.Errorf("max_symbol applied x%d, want x200 (the advertised rung)", got.Mult)
	}
	if got.Win != 12*200 {
		t.Errorf("win = %v, want %v", got.Win, 12*200.0)
	}

	// And the old behaviour, pinned so the difference stays visible: summing
	// would pay x400 for the same board.
	sumEval, err := NewLineEvaluator(c, st, MultSumSymbol)
	if err != nil {
		t.Fatalf("build sum evaluator: %v", err)
	}
	sumOut := NewWinResult()
	sumEval.Evaluate(b, 1, sumOut)
	summed, ok := winForLine(sumOut, 1)
	if !ok {
		t.Fatal("payline 1 did not pay under the sum strategy")
	}
	if summed.Mult != 400 {
		t.Errorf("sum strategy applied x%d, expected x400 -- if this changed, the "+
			"bug's shape changed too", summed.Mult)
	}

	// A plain x1 wild must not scale anything.
	b2 := blankBoard(t, c, st)
	setLine(b2, plain, plain, h1, h1, h1)
	maxEval.Evaluate(b2, 1, out)
	plainWin, ok := winForLine(out, 1)
	if !ok {
		t.Fatal("payline 1 did not pay with plain wilds")
	}
	if plainWin.Mult != 1 {
		t.Errorf("plain wilds applied x%d, want x1", plainWin.Mult)
	}
}

// Every cell a winning line crosses must be reported -- this is what lights
// Starwake's constellation cells, so an off-by-one here would silently change
// every tier's completion rate and every buy price with it.
func TestWinningCells(t *testing.T) {
	c, st, _ := load(t)
	e, out := evaluator(t, c, st)
	b := blankBoard(t, c, st)

	h1 := Cell{Sym: st.MustID("H1")}
	setLine(b, h1, h1, h1, Cell{Sym: st.MustID("L4")}, Cell{Sym: st.MustID("L5")})
	e.Evaluate(b, 1, out)

	var cells []config.Cell
	out.WinningCells(func(reel, row int) {
		cells = append(cells, config.Cell{Reel: reel, Row: row})
	})

	// A 3-kind on the top straight crosses exactly reels 0-2 at row 0. The two
	// reels beyond the run must NOT be reported.
	want := []config.Cell{{Reel: 0, Row: 0}, {Reel: 1, Row: 0}, {Reel: 2, Row: 0}}
	if len(cells) != len(want) {
		t.Fatalf("reported %v, want %v", cells, want)
	}
	for i := range want {
		if cells[i] != want[i] {
			t.Errorf("cell %d = %v, want %v", i, cells[i], want[i])
		}
	}
}

// Line evaluation is the hottest code in the engine -- 20 paylines on every spin,
// ~1e7 spins per mode. It must not allocate.
func BenchmarkEvaluate(bench *testing.B) {
	t := &testing.T{}
	c, st, rs := load(t)
	e, out := evaluator(t, c, st)
	b, _ := NewBoard(c)
	strip, _ := rs.Strip("FR0") // wild-rich: the expensive case, plenty of wins
	g := NewRNG(1)
	b.Draw("FR0", strip, st, 99, g)

	bench.ReportAllocs()
	bench.ResetTimer()
	for i := 0; i < bench.N; i++ {
		e.Evaluate(b, 1, out)
	}
}
