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

	// 12 symbols: W, S, H1-H4, L1-L5, and M -- act two's multiplier star, which
	// is non-paying and so reaches the table only via the roam strip.
	if got := st.Count(); got != 12 {
		t.Errorf("interned %d symbols, want 12", got)
	}
	// M must be neither wild nor scatter: wild would let it join winning runs and
	// contribute its collected value to a line, scatter would let it trigger.
	m := st.MustID("M")
	if st.IsWild(m) || st.IsScatter(m) {
		t.Error("the multiplier star must be a plain non-paying symbol")
	}
	for kind := 1; kind <= st.MaxKind(); kind++ {
		if pay := st.Pay(kind, m); pay != 0 {
			t.Errorf("M pays %v at kind %d; it must never pay", pay, kind)
		}
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

// A forced scatter must be able to land on EVERY row, including when that
// requires a negative stop.
//
// REGRESSION. The stop is offset back from the symbol's own strip position so the
// scatter can appear on any row, so it goes NEGATIVE whenever the chosen scatter
// sits within num_rows of the strip's start -- BR0 reel 4 carries one at position
// 0. "Is this reel forced" used to be encoded as "stop >= 0", so those placements
// were silently discarded and the reel got a RANDOM stop instead. The retry loop
// hid it completely: it redraws until the scatter COUNT is right, so every board
// was well-formed and every count correct while the position distribution was
// wrong. Measured against Python's pool, the three wrapped stops came out ~40x
// too rare (33 vs ~1,350 each per 40k forced boards).
//
// Asserting on the count -- which TestForceScatters already does -- cannot see
// this. Only the distribution of stops can.
func TestForcedScatterReachesWrappedStops(t *testing.T) {
	c, st, rs := load(t)
	b, _ := NewBoard(c)
	g := NewRNG(3)
	trigger := c.AnticipationTriggers[c.Game.BasegameType]

	strip, _ := rs.Strip("BR0")
	const reel = 4
	length := len(strip[reel])
	rows := c.Rows(reel)

	// Find a scatter close enough to the strip start that placing it on a lower
	// row demands a negative (wrapping) stop. Without one the test proves nothing.
	scatterPos := -1
	for pos := 0; pos < rows-1; pos++ {
		if st.IsScatter(strip[reel][pos]) {
			scatterPos = pos
			break
		}
	}
	if scatterPos < 0 {
		t.Skipf("BR0 reel %d has no scatter within %d of the strip start, so no "+
			"forced stop there can wrap -- this regression is unreachable on these strips",
			reel, rows-1)
	}

	// The stops that place that scatter somewhere on the board.
	want := map[int]int{}
	for offset := 0; offset < rows; offset++ {
		want[((scatterPos-offset)%length+length)%length] = 0
	}

	for i := 0; i < 20000; i++ {
		if err := b.ForceScatters(rs, "BR0", strip, st, 3, trigger, g); err != nil {
			t.Fatalf("force 3 on BR0: %v", err)
		}
		if _, ok := want[b.ReelPositions[reel]]; ok {
			want[b.ReelPositions[reel]]++
		}
	}

	// Each of the offsets is drawn uniformly, so the wrapped stops must show up at
	// broadly the same rate as the non-wrapped one. A loose floor keeps this a
	// structural check rather than a sampling-noise tripwire.
	best := 0
	for _, n := range want {
		if n > best {
			best = n
		}
	}
	for stop, n := range want {
		if n*5 < best {
			t.Errorf("reel %d stop %d seen %d times against a best of %d -- forced "+
				"placements needing a wrapping stop are being dropped", reel, stop, n, best)
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
