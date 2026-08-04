package engine

import (
	"errors"
	"math"
	"path/filepath"
	"testing"

	"starwake/internal/sdk/config"
)

func load(t *testing.T) (*config.Config, *SymbolTable, *ReelSet) {
	t.Helper()
	root, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatalf("resolve repo root: %v", err)
	}
	c, err := config.Load(filepath.Join(root, "go", "config", "starwake.json"), root)
	if err != nil {
		t.Fatalf("load config: %v", err)
	}
	st, err := NewSymbolTable(c)
	if err != nil {
		t.Fatalf("symbol table: %v", err)
	}
	rs, err := NewReelSet(c, st)
	if err != nil {
		t.Fatalf("reel set: %v", err)
	}
	return c, st, rs
}

func TestSymbolTable(t *testing.T) {
	_, st, _ := load(t)

	// 11 symbols: W, S, H1-H4, L1-L5.
	if got := st.Count(); got != 11 {
		t.Errorf("interned %d symbols, want 11", got)
	}
	if st.Name(NoSym) != "" {
		t.Errorf("slot 0 should be reserved/empty, got %q", st.Name(NoSym))
	}

	w := st.MustID("W")
	s := st.MustID("S")
	h1 := st.MustID("H1")

	if !st.IsWild(w) {
		t.Error("W is not wild")
	}
	if st.IsWild(h1) || st.IsWild(s) {
		t.Error("only W should be wild")
	}
	if !st.IsScatter(s) {
		t.Error("S is not a scatter")
	}
	if st.IsScatter(w) || st.IsScatter(h1) {
		t.Error("only S should be a scatter")
	}

	// Paytable via array index rather than a tuple-keyed hash.
	if got := st.Pay(5, w); got != 15 {
		t.Errorf("5xW = %v, want 15", got)
	}
	if got := st.Pay(5, h1); got != 12 {
		t.Errorf("5xH1 = %v, want 12", got)
	}
	if got := st.Pay(3, h1); got != 3 {
		t.Errorf("3xH1 = %v, want 3", got)
	}
	// W pays 5-kind ONLY: a shorter wild run must never outrank a longer real line.
	for _, kind := range []int{1, 2, 3, 4} {
		if got := st.Pay(kind, w); got != 0 {
			t.Errorf("%dxW = %v, want 0 (W pays 5-kind only)", kind, got)
		}
	}
	// Out-of-range kinds are ordinary non-wins, not errors -- the line evaluator
	// probes before it knows a run is payable.
	if got := st.Pay(0, h1); got != 0 {
		t.Errorf("0xH1 = %v, want 0", got)
	}
	if got := st.Pay(99, h1); got != 0 {
		t.Errorf("99xH1 = %v, want 0", got)
	}
}

func TestBoardDrawShape(t *testing.T) {
	c, st, rs := load(t)
	b, err := NewBoard(c)
	if err != nil {
		t.Fatalf("new board: %v", err)
	}
	strip, err := rs.Strip("BR0")
	if err != nil {
		t.Fatal(err)
	}
	g := NewRNG(1)

	for i := 0; i < 200; i++ {
		b.Draw("BR0", strip, st, c.AnticipationTriggers[c.Game.BasegameType], g)
		for reel := 0; reel < b.NumReels; reel++ {
			stop := b.ReelPositions[reel]
			if stop < 0 || stop >= len(strip[reel]) {
				t.Fatalf("reel %d stop %d out of range", reel, stop)
			}
			for row := 0; row < b.NumRows[reel]; row++ {
				got := b.At(reel, row).Sym
				// Every cell must be the strip symbol at the wrapped offset.
				want := strip[reel][(stop+row)%len(strip[reel])]
				if got != want {
					t.Fatalf("cell (%d,%d) = %s, want %s (stop %d)",
						reel, row, st.Name(got), st.Name(want), stop)
				}
				if got == NoSym {
					t.Fatalf("cell (%d,%d) is unset", reel, row)
				}
			}
		}
	}
}

// The draw must reproduce the strip's own symbol composition. This is the real
// correctness check on the draw: a wrapping or indexing bug shifts the observed
// frequencies away from the strip even while every cell still looks valid.
func TestDrawMatchesStripComposition(t *testing.T) {
	c, st, rs := load(t)
	b, _ := NewBoard(c)
	strip, _ := rs.Strip("BR0")
	g := NewRNG(42)

	const draws = 20000
	seen := make(map[SymID]int)
	for i := 0; i < draws; i++ {
		b.Draw("BR0", strip, st, 99, g) // 99 disables anticipation here
		for reel := 0; reel < b.NumReels; reel++ {
			for row := 0; row < b.NumRows[reel]; row++ {
				seen[b.At(reel, row).Sym]++
			}
		}
	}

	// Expected share: every stop is uniform, so each reel contributes
	// rows/len(reel) of its own composition.
	expected := make(map[SymID]float64)
	var totalWeight float64
	for reel := 0; reel < b.NumReels; reel++ {
		rows := float64(b.NumRows[reel])
		length := float64(len(strip[reel]))
		for _, sym := range strip[reel] {
			expected[sym] += rows / length
		}
		totalWeight += rows
	}

	totalSeen := float64(draws) * totalWeight
	for sym, count := range seen {
		want := expected[sym] * float64(draws) / totalSeen
		got := float64(count) / totalSeen
		// Generous band: this catches structural bugs, not sampling noise.
		if math.Abs(got-want) > 0.01 {
			t.Errorf("symbol %s share %.4f, want ~%.4f", st.Name(sym), got, want)
		}
	}
}

func TestForceScatters(t *testing.T) {
	c, st, rs := load(t)
	b, _ := NewBoard(c)
	g := NewRNG(7)
	trigger := c.AnticipationTriggers[c.Game.BasegameType]

	// 3/4/5 on BR0 -- the counts base and the tier buys force.
	strip, _ := rs.Strip("BR0")
	for _, want := range []int{3, 4, 5} {
		for i := 0; i < 100; i++ {
			if err := b.ForceScatters(rs, "BR0", strip, st, want, trigger, g); err != nil {
				t.Fatalf("force %d on BR0: %v", want, err)
			}
			if got := b.ScatterCount(); got != want {
				t.Fatalf("forced %d scatters, board shows %d", want, got)
			}
		}
	}

	// 6 on ASC -- the Ascendant deal. _force_special_board places at most ONE
	// scatter per reel, so a 6th requires a reel window revealing two, which is
	// the entire reason the ASC strip exists.
	asc, _ := rs.Strip("ASC")
	for i := 0; i < 100; i++ {
		if err := b.ForceScatters(rs, "ASC", asc, st, 6, trigger, g); err != nil {
			t.Fatalf("force 6 on ASC: %v", err)
		}
		if got := b.ScatterCount(); got != 6 {
			t.Fatalf("forced 6 scatters, board shows %d", got)
		}
	}
}

// The Python original is a bare `while True` with no retry cap, so an
// unsatisfiable forced count hangs forever instead of failing -- the documented
// reason a forced wincap slice whose cap drifts out of reach shows up as a run
// that never finishes. This proves the Go port errors instead.
func TestForceImpossibleCountFailsInsteadOfHanging(t *testing.T) {
	c, st, rs := load(t)
	b, _ := NewBoard(c)
	g := NewRNG(11)

	// FR0 carries NO scatters at all, so any forced count is impossible.
	fr0, _ := rs.Strip("FR0")
	err := b.ForceScatters(rs, "FR0", fr0, st, 3, 99, g)
	if err == nil {
		t.Fatal("forcing 3 scatters on the scatterless FR0 strip should fail")
	}
	var forceErr *ErrForceFailed
	if !errors.As(err, &forceErr) {
		t.Fatalf("want *ErrForceFailed, got %T: %v", err, err)
	}
	if forceErr.Want != 3 {
		t.Errorf("error reports want=%d, expected 3", forceErr.Want)
	}
}

func TestAnticipation(t *testing.T) {
	c, st, rs := load(t)
	b, _ := NewBoard(c)
	strip, _ := rs.Strip("BR0")
	g := NewRNG(3)
	trigger := c.AnticipationTriggers[c.Game.BasegameType]

	for i := 0; i < 500; i++ {
		b.Draw("BR0", strip, st, trigger, g)
		// Anticipation must never decrease left to right -- the client ramps the
		// slowdown reel by reel, and the Python engine raises RuntimeError if it
		// ever goes backwards.
		for reel := 1; reel < b.NumReels; reel++ {
			if b.Anticipation[reel-1] > b.Anticipation[reel] {
				t.Fatalf("anticipation decreases at reel %d: %v", reel, b.Anticipation[:b.NumReels])
			}
		}
	}
}

// The board draw must not allocate. A board is drawn ~1e7 times per mode, so an
// allocation here would dominate the whole run.
func BenchmarkDraw(bench *testing.B) {
	c, st, rs := load(&testing.T{})
	b, _ := NewBoard(c)
	strip, _ := rs.Strip("BR0")
	g := NewRNG(1)
	trigger := c.AnticipationTriggers[c.Game.BasegameType]

	bench.ReportAllocs()
	bench.ResetTimer()
	for i := 0; i < bench.N; i++ {
		b.Draw("BR0", strip, st, trigger, g)
	}
}
