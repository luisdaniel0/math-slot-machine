package starwake

import (
	"testing"

	"starwake/internal/sdk/config"
	"starwake/internal/sdk/engine"
)

// Ported from tests/starwake/test_constellation.py. The feature engine is tested
// in ISOLATION before it is wired into a run -- the Keybearer lesson, where a
// global multiplier silently multiplied nothing until the win strategy was
// changed, and no full-run metric revealed it.

func deal(t *testing.T, tierName string) (*config.Config, *Constellation) {
	t.Helper()
	c, con := load(t)
	tier, err := con.Tier(tierName)
	if err != nil {
		t.Fatalf("%v", err)
	}
	cst, err := NewConstellation(tier, tierName, c)
	if err != nil {
		t.Fatalf("deal %s: %v", tierName, err)
	}
	return c, cst
}

func TestDealStartsDark(t *testing.T) {
	for _, tier := range []string{"corvus", "ursa", "draco"} {
		_, cst := deal(t, tier)
		if cst.Lit() != 0 {
			t.Errorf("%s: starts with %d cells lit, want 0", tier, cst.Lit().Count())
		}
		if cst.Phase() != PhaseCharge {
			t.Errorf("%s: starts in phase %v, want charge", tier, cst.Phase())
		}
		if cst.IsComplete() {
			t.Errorf("%s: complete before any spin", tier)
		}
	}
}

func TestAscendantStartsPrelit(t *testing.T) {
	_, cst := deal(t, "ascendant")
	// Ascendant is a Draco dealt with the reel-4 pair already lit -- that is the
	// whole difference between the two, and it is why it completes ~90% against
	// draco's ~32%.
	if got := cst.Lit().Count(); got != 2 {
		t.Fatalf("ascendant starts with %d lit, want 2", got)
	}
	if !cst.Lit().Has(4, 0) || !cst.Lit().Has(4, 1) {
		t.Errorf("ascendant pre-lit cells are not (4,0) and (4,1)")
	}
	if cst.IsComplete() {
		t.Error("ascendant complete before any spin")
	}
}

func TestLightingIsStickyAndMonotonic(t *testing.T) {
	_, cst := deal(t, "ursa")
	cells := cst.TargetCells()

	// Light the first cell.
	newly := cst.LightFromWins(Bit(cells[0].Reel, cells[0].Row))
	if len(newly) != 1 || newly[0] != cells[0] {
		t.Fatalf("first light reported %v, want [%v]", newly, cells[0])
	}

	// Re-crossing an already-lit cell reports nothing new and changes nothing.
	before := cst.Lit()
	newly = cst.LightFromWins(Bit(cells[0].Reel, cells[0].Row))
	if len(newly) != 0 {
		t.Errorf("re-lighting reported %v, want nothing", newly)
	}
	if cst.Lit() != before {
		t.Error("re-lighting changed the lit set")
	}

	// A win crossing a NON-constellation cell must light nothing.
	var offShape CellMask
	for reel := 0; reel < 5; reel++ {
		for row := 0; row < 4; row++ {
			if !cst.Targets().Has(reel, row) {
				offShape |= Bit(reel, row)
			}
		}
	}
	newly = cst.LightFromWins(offShape)
	if len(newly) != 0 {
		t.Errorf("off-shape cells lit %v", newly)
	}
	if cst.Lit().Count() != 1 {
		t.Errorf("lit count = %d, want 1", cst.Lit().Count())
	}
}

func TestCompletionAndWake(t *testing.T) {
	_, cst := deal(t, "corvus")
	g := engine.NewRNG(1)

	// Waking early is a programming error, not a game outcome.
	if err := cst.Wake(g); err == nil {
		t.Fatal("wake before completion should fail")
	}

	cst.LightFromWins(cst.Targets())
	if !cst.IsComplete() {
		t.Fatal("lighting every target cell did not complete the set")
	}
	if err := cst.Wake(g); err != nil {
		t.Fatalf("wake: %v", err)
	}
	if cst.Phase() != PhaseRoam {
		t.Error("phase did not advance to roam")
	}
	if !cst.WokeThisSpin {
		t.Error("WokeThisSpin not set on the wake spin")
	}
	// Rung 0 is what the beast shows the spin it appears.
	tier := loadTier(t, "corvus")
	if got, want := cst.Multiplier(), tier.MultLadder[0]; got != want {
		t.Errorf("multiplier on wake = %d, want %d", got, want)
	}
	// Waking twice is also an error.
	if err := cst.Wake(g); err == nil {
		t.Error("waking an already-awake beast should fail")
	}
}

func loadTier(t *testing.T, name string) Tier {
	t.Helper()
	_, con := load(t)
	tier, err := con.Tier(name)
	if err != nil {
		t.Fatalf("%v", err)
	}
	return tier
}

// The beast must NEVER leave the grid. The fat tail depends on how long it stays,
// not on the path it takes, so exiting would be both a visual bug and a payout one.
func TestBeastNeverExitsTheGrid(t *testing.T) {
	c, cst := deal(t, "draco")
	g := engine.NewRNG(99)
	cst.LightFromWins(cst.Targets())
	if err := cst.Wake(g); err != nil {
		t.Fatal(err)
	}

	for spin := 0; spin < 5000; spin++ {
		origin, placed := cst.BeastOrigin()
		if !placed {
			t.Fatal("beast is awake but not placed")
		}
		if origin.Reel < 0 || origin.Reel+2 > c.Game.NumReels ||
			origin.Row < 0 || origin.Row+2 > c.Rows(origin.Reel) {
			t.Fatalf("spin %d: 2x2 beast at (%d,%d) is off a %dx%d grid",
				spin, origin.Reel, origin.Row, c.Game.NumReels, c.Rows(0))
		}
		if got := cst.BeastCells().Count(); got != 4 {
			t.Fatalf("spin %d: 2x2 beast covers %d cells", spin, got)
		}
		if err := cst.Roam(g); err != nil {
			t.Fatal(err)
		}
	}
}

// The ladder is the published "all obtainable multiplier values" table, so it
// must climb exactly one rung per roam and then hold at the top -- never index
// past the end, never skip a value.
func TestLadderClimbsOneRungPerRoamThenClamps(t *testing.T) {
	_, cst := deal(t, "corvus")
	tier := loadTier(t, "corvus")
	g := engine.NewRNG(5)

	cst.LightFromWins(cst.Targets())
	if err := cst.Wake(g); err != nil {
		t.Fatal(err)
	}

	for i, want := range tier.MultLadder {
		if got := cst.Multiplier(); got != want {
			t.Fatalf("rung %d: multiplier %d, want %d", i, got, want)
		}
		if got := cst.Rung(); got != i {
			t.Fatalf("rung index = %d, want %d", got, i)
		}
		if err := cst.Roam(g); err != nil {
			t.Fatal(err)
		}
	}

	// Past the end it clamps at the top value rather than panicking or wrapping.
	top := tier.MultLadder[len(tier.MultLadder)-1]
	for i := 0; i < 10; i++ {
		if got := cst.Multiplier(); got != top {
			t.Fatalf("after the ladder ends, multiplier %d, want clamp at %d", got, top)
		}
		if err := cst.Roam(g); err != nil {
			t.Fatal(err)
		}
	}
}

// A lit cell must actually read as a wild on the board, and only beast cells may
// carry a multiplier above 1. This is the coupling that the Keybearer bug broke.
func TestApplyWildsStampsBoard(t *testing.T) {
	c, cst := deal(t, "corvus")
	_, st, rs := loadEngine(t)
	g := engine.NewRNG(3)

	b, err := engine.NewBoard(c)
	if err != nil {
		t.Fatal(err)
	}
	strip, _ := rs.Strip("FR0")
	b.Draw("FR0", strip, st, 99, g)

	cst.LightFromWins(cst.Targets())
	if err := cst.Wake(g); err != nil {
		t.Fatal(err)
	}
	wild := st.MustID("W")
	cst.ApplyWilds(b, wild)

	beast := cst.BeastCells()
	for reel := 0; reel < b.NumReels; reel++ {
		for row := 0; row < b.NumRows[reel]; row++ {
			cell := b.At(reel, row)
			lit := cst.Lit().Has(reel, row)
			inBeast := beast.Has(reel, row)

			if lit || inBeast {
				if cell.Sym != wild {
					t.Errorf("(%d,%d) is lit/beast but reads %s", reel, row, st.Name(cell.Sym))
				}
				want := uint16(1)
				if inBeast {
					want = uint16(cst.Multiplier())
				}
				if cell.Mult != want {
					t.Errorf("(%d,%d) multiplier %d, want %d", reel, row, cell.Mult, want)
				}
			} else if cell.Mult > 1 {
				// Nothing outside the beast may carry a multiplier above 1.
				t.Errorf("(%d,%d) is neither lit nor beast but carries x%d", reel, row, cell.Mult)
			}
		}
	}
}

// THE SNOWBALL, end to end through the real line evaluator: stamping sticky wilds
// onto a board must make it pay more than the same board bare. This is the
// mechanic the whole game rides on, so it is verified against real wins rather
// than asserted structurally.
func TestStickyWildsIncreaseWins(t *testing.T) {
	c, cst := deal(t, "draco")
	_, st, rs := loadEngine(t)
	g := engine.NewRNG(17)

	e, err := engine.NewLineEvaluator(c, st, engine.MultMaxSymbol)
	if err != nil {
		t.Fatal(err)
	}
	bare := engine.NewWinResult()
	wilded := engine.NewWinResult()

	b, _ := engine.NewBoard(c)
	strip, _ := rs.Strip("FR0")
	wild := st.MustID("W")

	improved, sampled := 0, 0
	for i := 0; i < 300; i++ {
		b.Draw("FR0", strip, st, 99, g)
		e.Evaluate(b, 1, bare)
		bareWin := bare.TotalWin

		// Light the whole constellation, then re-stamp the same board.
		_, fresh := deal(t, "draco")
		fresh.LightFromWins(fresh.Targets())
		fresh.ApplyWilds(b, wild)
		e.Evaluate(b, 1, wilded)

		sampled++
		if wilded.TotalWin < bareWin {
			t.Fatalf("draw %d: stamping wilds REDUCED the win (%v -> %v)",
				i, bareWin, wilded.TotalWin)
		}
		if wilded.TotalWin > bareWin {
			improved++
		}
	}
	_ = cst
	// Eleven wilds on a 20-cell board should improve the great majority of draws.
	if improved*2 < sampled {
		t.Errorf("wilds improved only %d of %d draws; the snowball is not working",
			improved, sampled)
	}
}

func loadEngine(t *testing.T) (*config.Config, *engine.SymbolTable, *engine.ReelSet) {
	t.Helper()
	c, _ := load(t)
	st, err := engine.NewSymbolTable(c)
	if err != nil {
		t.Fatal(err)
	}
	rs, err := engine.NewReelSet(c, st)
	if err != nil {
		t.Fatal(err)
	}
	return c, st, rs
}
