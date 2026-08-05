package starwake

import (
	"testing"

	"starwake/internal/sdk/config"
	"starwake/internal/sdk/engine"
)

// ACT TWO tested in ISOLATION, before it is wired into a run -- the Keybearer
// lesson, where a global multiplier silently multiplied nothing until the win
// strategy was changed and no full-run metric revealed it.
//
// The shipped config carries no starDrops block and no star symbol yet (act two is
// measured against the ladder before either is committed to), so these tests
// attach a table to a real tier and stand in an existing symbol for the star. That
// keeps the cell maps, beast shape and grid identical to production -- only the
// multiplier mechanic differs.

// starStandIn is a placeholder until the real multiplier symbol is added to
// game_config.py. Any non-wild, non-scatter symbol exercises the same code path:
// RollStarValues matches on symbol ID, and the evaluator never reads a star's
// Mult because a star is never inside a winning run.
const starStandIn = "L5"

func actTwoTier(t *testing.T, name string) (*config.Config, Tier) {
	t.Helper()
	c, fc := load(t)
	tier, err := fc.Tier(name)
	if err != nil {
		t.Fatalf("%v", err)
	}
	tier.StarDrops = &StarDrops{
		RoamStrip:  "FR0", // stands in for the real roam strip
		StarSymbol: starStandIn,
		Values:     []WeightedInt{{Value: 2, Weight: 4}, {Value: 5, Weight: 2}, {Value: 25, Weight: 1}},
	}
	return c, tier
}

// woken returns a constellation already in the roam phase, plus a board and the
// star's symbol ID so a test can deal stars onto the reels by hand.
func woken(t *testing.T, name string, seed uint64) (*Constellation, *engine.Board, engine.SymID, *engine.RNG) {
	t.Helper()
	c, tier := actTwoTier(t, name)
	cst, err := NewConstellation(tier, name, c)
	if err != nil {
		t.Fatalf("deal %s: %v", name, err)
	}
	st, err := engine.NewSymbolTable(c)
	if err != nil {
		t.Fatalf("symbols: %v", err)
	}
	board, err := engine.NewBoard(c)
	if err != nil {
		t.Fatalf("board: %v", err)
	}
	g := engine.NewRNG(seed)
	cst.LightFromWins(cst.Targets())
	if err := cst.Wake(g); err != nil {
		t.Fatalf("wake: %v", err)
	}
	return cst, board, st.MustID(starStandIn), g
}

// deal stars onto specific cells, as the roam strip would.
func placeStars(b *engine.Board, star engine.SymID, cells ...config.Cell) {
	for _, c := range cells {
		b.Set(c.Reel, c.Row, engine.Cell{Sym: star})
	}
}

func clearBoard(b *engine.Board, filler engine.SymID) {
	for reel := 0; reel < b.NumReels; reel++ {
		for row := 0; row < b.NumRows[reel]; row++ {
			b.Set(reel, row, engine.Cell{Sym: filler})
		}
	}
}

// THE HEADLINE CHANGE. Draco ends act one with 9.9 of 20 cells lit and 11.2 wild
// once the beast is out -- over half the board, so every line wins and no win
// means anything. Act two hands the board back.
func TestWakeConsumesTheStickyWilds(t *testing.T) {
	cst, _, _, _ := woken(t, "draco", 7)

	wilds := cst.WildCells()
	beast := cst.BeastCells()
	if wilds != beast {
		t.Errorf("roam wilds = %d cells, want exactly the %d-cell block",
			wilds.Count(), beast.Count())
	}
	if n := wilds.Count(); n != 4 {
		t.Errorf("2x2 block covers %d cells, want 4", n)
	}
	// The record survives even though the wildness does not -- the star chart and
	// the completion ladder both still read `lit`.
	if !cst.IsComplete() || cst.Lit() != cst.Targets() {
		t.Error("lit mask was cleared at wake; it must survive as the record")
	}
}

func TestLadderTierStillCarpetsTheBoard(t *testing.T) {
	// Regression: a tier with no starDrops must behave exactly as before, so the
	// two mechanics can be A/B swept against each other.
	_, cst := deal(t, "draco")
	if cst.ActTwo() {
		t.Fatal("a tier without starDrops must not run act two")
	}
	g := engine.NewRNG(3)
	cst.LightFromWins(cst.Targets())
	if err := cst.Wake(g); err != nil {
		t.Fatalf("wake: %v", err)
	}
	// Union, not sum -- the block sits ON TOP of lit cells, so the two overlap.
	if got, want := cst.WildCells(), cst.Lit()|cst.BeastCells(); got != want {
		t.Errorf("ladder roam wilds = %d cells, want lit|block = %d cells",
			got.Count(), want.Count())
	}
	if cst.WildCells().Count() <= 4 {
		t.Error("ladder tier lost its wild carpet during roam")
	}
	if cst.Multiplier() != loadTier(t, "draco").MultLadder[0] {
		t.Error("ladder tier did not take its rung-0 multiplier on wake")
	}
}

// The "x1 ladder feels bad" complaint, encoded. Under the ladder, draco's mean
// roam is 1.3 rungs of 12, so a typical completed feature pays at x2. Act two has
// no dead rung: the beast starts bare and the first star IS the climb.
func TestNoDeadFirstRung(t *testing.T) {
	cst, board, star, g := woken(t, "draco", 11)
	if cst.Multiplier() != 1 {
		t.Errorf("act two beast wakes at x%d, want x1 (bare)", cst.Multiplier())
	}
	if cst.Rung() != -1 {
		t.Errorf("act two should not use ladder rungs, got rung %d", cst.Rung())
	}

	placeStars(board, star, config.Cell{Reel: 2, Row: 1})
	stars := cst.RollStarValues(board, star, g)
	if len(stars) != 1 {
		t.Fatalf("dealt 1 star, found %d", len(stars))
	}
	gained, total := cst.Collect()
	if gained != stars[0].Value {
		t.Errorf("gained %d, want the star's %d", gained, stars[0].Value)
	}
	if total != 1+gained {
		t.Errorf("multiplier = %d after first collect, want %d", total, 1+gained)
	}
}

// COLLECTION IS GLOBAL. Rage Bait's rule is "whenever a Wild is on the board it
// collects EVERY Fish" -- the wild does not have to land on it. An earlier design
// had the block collect only what it covered, which invents a positional lottery
// their game does not have and makes most drops unreachable.
func TestCollectionIsGlobalIncludingUnderTheBlock(t *testing.T) {
	cst, board, star, g := woken(t, "ursa", 23)

	origin, ok := cst.BeastOrigin()
	if !ok {
		t.Fatal("beast not placed")
	}
	underBlock := config.Cell{Reel: origin.Reel, Row: origin.Row}
	farAway := config.Cell{Reel: 0, Row: 0}
	if cst.BeastCells().Has(farAway.Reel, farAway.Row) {
		farAway = config.Cell{Reel: 4, Row: 3}
	}
	placeStars(board, star, underBlock, farAway)

	stars := cst.RollStarValues(board, star, g)
	if len(stars) != 2 {
		t.Fatalf("dealt 2 stars, found %d", len(stars))
	}
	want := stars[0].Value + stars[1].Value
	gained, total := cst.Collect()
	if gained != want {
		t.Errorf("collected %d, want both stars = %d (the one under the block counts)",
			gained, want)
	}
	if total != 1+want {
		t.Errorf("multiplier = %d, want %d", total, 1+want)
	}
}

func TestMultiplierAccumulatesAcrossRoamSpins(t *testing.T) {
	cst, board, star, g := woken(t, "draco", 77)
	running := 0
	for spin := 0; spin < 8; spin++ {
		clearBoard(board, star+1)
		placeStars(board, star, config.Cell{Reel: 4, Row: spin % 4})
		stars := cst.RollStarValues(board, star, g)
		gained, total := cst.Collect()
		running += stars[0].Value
		if gained != stars[0].Value || total != 1+running {
			t.Fatalf("spin %d: gained %d total %d, want %d and %d",
				spin, gained, total, stars[0].Value, 1+running)
		}
		if cst.Collected() != running {
			t.Fatalf("spin %d: Collected() = %d, want %d", spin, cst.Collected(), running)
		}
		if err := cst.Roam(g); err != nil {
			t.Fatalf("roam: %v", err)
		}
	}
}

// The star's value is stashed in the cell's own Mult field. That is only safe
// because applyMult reads Mult for cells INSIDE a winning run and a star never
// matches, so it can never be in one -- worth pinning, because a star quietly
// contributing its value to an unrelated line win would inflate RTP invisibly.
func TestStarValueLandsOnTheCellAndNotInAWin(t *testing.T) {
	cst, board, star, g := woken(t, "draco", 5)
	clearBoard(board, star+1)
	cell := config.Cell{Reel: 3, Row: 2}
	if cst.BeastCells().Has(cell.Reel, cell.Row) {
		cell = config.Cell{Reel: 0, Row: 0}
	}
	placeStars(board, star, cell)

	stars := cst.RollStarValues(board, star, g)
	if len(stars) != 1 {
		t.Fatalf("found %d stars, want 1", len(stars))
	}
	got := board.At(cell.Reel, cell.Row)
	if got.Sym != star {
		t.Error("rolling values changed the star's symbol")
	}
	if int(got.Mult) != stars[0].Value {
		t.Errorf("cell carries x%d, want the star's %d", got.Mult, stars[0].Value)
	}

	c, _ := load(t)
	st, _ := engine.NewSymbolTable(c)
	if st.IsWild(star) {
		t.Fatal("the star stand-in is wild; it would join winning runs and this test proves nothing")
	}
}

// APPLICATION IS POSITIONAL, even though collection is not. The block stamps its
// multiplier only on the cells it covers, so only lines crossing it are paid at
// the collected value -- which is what keeps WHERE it roams meaningful.
func TestMultiplierAppliesOnlyToTheBlock(t *testing.T) {
	cst, board, star, g := woken(t, "draco", 41)
	for i := 0; i < 4; i++ {
		clearBoard(board, star+1)
		placeStars(board, star, config.Cell{Reel: 0, Row: i % 4})
		cst.RollStarValues(board, star, g)
		cst.Collect()
	}
	if cst.Multiplier() <= 1 {
		t.Fatal("no multiplier accumulated; cannot test its application")
	}

	c, _ := load(t)
	st, _ := engine.NewSymbolTable(c)
	wild := st.MustID("W")
	clearBoard(board, star+1)
	cst.ApplyWilds(board, wild)

	beast := cst.BeastCells()
	stamped := 0
	for reel := 0; reel < board.NumReels; reel++ {
		for row := 0; row < board.NumRows[reel]; row++ {
			cell := board.At(reel, row)
			if beast.Has(reel, row) {
				stamped++
				if cell.Sym != wild {
					t.Errorf("(%d,%d) in the block is not wild", reel, row)
				}
				if int(cell.Mult) != cst.Multiplier() {
					t.Errorf("(%d,%d) carries x%d, want x%d",
						reel, row, cell.Mult, cst.Multiplier())
				}
			} else if cell.Sym == wild && cell.Mult > 1 {
				t.Errorf("(%d,%d) outside the block carries x%d", reel, row, cell.Mult)
			}
		}
	}
	if stamped != 4 {
		t.Errorf("stamped %d cells, want the 4 of a 2x2 block", stamped)
	}
}

// Act one must stay a plain snowball: no stars, no multiplier. The roam strip is
// what enforces this in a real run, but the state machine refuses independently so
// a config mistake cannot leak stars into the charge phase.
func TestNoStarsBeforeTheBeastWakes(t *testing.T) {
	c, tier := actTwoTier(t, "corvus")
	cst, err := NewConstellation(tier, "corvus", c)
	if err != nil {
		t.Fatalf("deal: %v", err)
	}
	st, _ := engine.NewSymbolTable(c)
	star := st.MustID(starStandIn)
	board, _ := engine.NewBoard(c)
	placeStars(board, star, config.Cell{Reel: 1, Row: 1}, config.Cell{Reel: 2, Row: 2})

	g := engine.NewRNG(2)
	if got := cst.RollStarValues(board, star, g); len(got) != 0 {
		t.Errorf("%d stars collected during charge, want 0", len(got))
	}
	if _, total := cst.Collect(); total != 1 {
		t.Errorf("multiplier moved to %d during charge, want 1", total)
	}
}

// Nothing carries over between spins: each RollStarValues replaces the list, so a
// collect can never take last spin's stars a second time.
func TestStarsDoNotCarryOver(t *testing.T) {
	cst, board, star, g := woken(t, "draco", 9)
	clearBoard(board, star+1)
	placeStars(board, star, config.Cell{Reel: 0, Row: 0}, config.Cell{Reel: 0, Row: 1})
	cst.RollStarValues(board, star, g)
	first, _ := cst.Collect()

	if err := cst.Roam(g); err != nil {
		t.Fatalf("roam: %v", err)
	}
	clearBoard(board, star+1) // a barren spin
	if got := cst.RollStarValues(board, star, g); len(got) != 0 {
		t.Fatalf("found %d stars on a barren board", len(got))
	}
	gained, total := cst.Collect()
	if gained != 0 {
		t.Errorf("collected %d on a barren spin, want 0", gained)
	}
	if total != 1+first {
		t.Errorf("multiplier = %d, want the running %d -- it must not re-collect",
			total, 1+first)
	}
}

// The engine's output must stay byte-deterministic so published sha256s are
// reproducible -- which means the value table must never be iterated as a map.
func TestStarValuesAreDeterministic(t *testing.T) {
	run := func() []Star {
		cst, board, star, g := woken(t, "draco", 1234)
		var all []Star
		for i := 0; i < 8; i++ {
			clearBoard(board, star+1)
			placeStars(board, star,
				config.Cell{Reel: 0, Row: 0},
				config.Cell{Reel: 2, Row: 2},
				config.Cell{Reel: 4, Row: 3})
			all = append(all, cst.RollStarValues(board, star, g)...)
			cst.Collect()
			if err := cst.Roam(g); err != nil {
				t.Fatalf("roam: %v", err)
			}
		}
		return all
	}
	a, b := run(), run()
	if len(a) != len(b) || len(a) == 0 {
		t.Fatalf("same seed produced %d then %d stars", len(a), len(b))
	}
	for i := range a {
		if a[i] != b[i] {
			t.Fatalf("star %d differs between identical seeds: %+v vs %+v", i, a[i], b[i])
		}
	}
}

func TestStarDropConfigValidation(t *testing.T) {
	c, _ := load(t)
	valid := []WeightedInt{{Value: 2, Weight: 1}, {Value: 100, Weight: 1}}

	bad := []struct {
		name  string
		drops StarDrops
	}{
		{"no roam strip", StarDrops{StarSymbol: "M", Values: valid}},
		{"unknown roam strip", StarDrops{RoamStrip: "NOPE", StarSymbol: "M", Values: valid}},
		{"no star symbol", StarDrops{RoamStrip: "FR0", Values: valid}},
		{"empty values", StarDrops{RoamStrip: "FR0", StarSymbol: "M"}},
		{"x1 star is a no-op", StarDrops{RoamStrip: "FR0", StarSymbol: "M",
			Values: []WeightedInt{{Value: 1, Weight: 1}}}},
		{"duplicate value", StarDrops{RoamStrip: "FR0", StarSymbol: "M",
			Values: []WeightedInt{{Value: 2, Weight: 1}, {Value: 2, Weight: 1}}}},
		{"zero total weight", StarDrops{RoamStrip: "FR0", StarSymbol: "M",
			Values: []WeightedInt{{Value: 2, Weight: 0}}}},
	}
	for _, tc := range bad {
		if err := tc.drops.validate("test", c); err == nil {
			t.Errorf("%s: accepted, want rejected", tc.name)
		}
	}

	ok := StarDrops{RoamStrip: "FR0", StarSymbol: "M", Values: valid}
	if err := ok.validate("test", c); err != nil {
		t.Errorf("valid table rejected: %v", err)
	}
}
