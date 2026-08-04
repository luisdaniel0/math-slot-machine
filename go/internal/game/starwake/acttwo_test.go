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
// The shipped config carries no starDrops block yet (act two is measured against
// the ladder before either is committed to), so these tests attach a table to a
// real tier rather than inventing a synthetic one. That keeps the cell maps, beast
// shape and grid identical to production -- only the multiplier mechanic differs.

func actTwoTier(t *testing.T, name string) (*config.Config, Tier) {
	t.Helper()
	c, fc := load(t)
	tier, err := fc.Tier(name)
	if err != nil {
		t.Fatalf("%v", err)
	}
	tier.StarDrops = &StarDrops{
		Count:  []WeightedInt{{Value: 1, Weight: 1}, {Value: 2, Weight: 1}, {Value: 3, Weight: 1}},
		Values: []WeightedInt{{Value: 2, Weight: 4}, {Value: 5, Weight: 2}, {Value: 25, Weight: 1}},
	}
	return c, tier
}

// woken returns a constellation already in the roam phase.
func woken(t *testing.T, name string, seed uint64) (*Constellation, *engine.RNG) {
	t.Helper()
	c, tier := actTwoTier(t, name)
	cst, err := NewConstellation(tier, name, c)
	if err != nil {
		t.Fatalf("deal %s: %v", name, err)
	}
	g := engine.NewRNG(seed)
	cst.LightFromWins(cst.Targets())
	if err := cst.Wake(g); err != nil {
		t.Fatalf("wake: %v", err)
	}
	return cst, g
}

// THE HEADLINE CHANGE. Draco ends act one with 9.9 of 20 cells lit and 11.2 wild
// once the beast is out -- over half the board, so every line wins and no win
// means anything. Act two hands the board back.
func TestWakeConsumesTheStickyWilds(t *testing.T) {
	cst, _ := woken(t, "draco", 7)

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
	cst, g := woken(t, "draco", 11)
	if cst.Multiplier() != 1 {
		t.Errorf("act two beast wakes at x%d, want x1 (bare)", cst.Multiplier())
	}
	if cst.Rung() != -1 {
		t.Errorf("act two should not use ladder rungs, got rung %d", cst.Rung())
	}

	// Drop until something lands, then the multiplier must move immediately.
	for i := 0; i < 20; i++ {
		if len(cst.DropStars(g)) > 0 {
			gained, total := cst.Collect()
			if gained <= 0 {
				t.Fatal("stars dropped but collecting gained nothing")
			}
			if total != 1+gained {
				t.Errorf("multiplier = %d after first collect, want %d", total, 1+gained)
			}
			return
		}
		if err := cst.Roam(g); err != nil {
			t.Fatalf("roam: %v", err)
		}
	}
	t.Fatal("no stars dropped in 20 spins; the count table cannot be exercised")
}

// COLLECTION IS GLOBAL. Rage Bait's rule is "whenever a Wild is on the board it
// collects EVERY Fish" -- the wild does not have to land on it. An earlier design
// had the block collect only what it covered, which invents a positional lottery
// their game does not have and makes most drops unreachable.
func TestCollectionIsGlobalAndAccumulates(t *testing.T) {
	cst, g := woken(t, "ursa", 23)

	running := 0
	for spin := 0; spin < 15; spin++ {
		stars := cst.DropStars(g)
		want := 0
		for _, s := range stars {
			want += s.Value
			if cst.BeastCells().Has(s.Cell.Reel, s.Cell.Row) {
				t.Fatalf("spin %d: star landed under the block at (%d,%d)",
					spin, s.Cell.Reel, s.Cell.Row)
			}
		}
		gained, total := cst.Collect()
		if gained != want {
			t.Fatalf("spin %d: collected %d, want every star on the board = %d",
				spin, gained, want)
		}
		running += want
		if total != 1+running {
			t.Fatalf("spin %d: multiplier = %d, want 1+%d", spin, total, running)
		}
		if cst.Collected() != running {
			t.Fatalf("spin %d: Collected() = %d, want %d", spin, cst.Collected(), running)
		}
		if err := cst.Roam(g); err != nil {
			t.Fatalf("roam: %v", err)
		}
	}
	if running == 0 {
		t.Fatal("15 roam spins collected nothing; the table cannot be exercised")
	}
}

// Nothing persists. Under global collection there is never anything left over, so
// last spin's stars must not still be sitting on the board.
func TestStarsDoNotPersist(t *testing.T) {
	cst, g := woken(t, "draco", 5)
	for spin := 0; spin < 10; spin++ {
		before := cst.DropStars(g)
		snapshot := append([]Star(nil), before...)
		cst.Collect()
		if err := cst.Roam(g); err != nil {
			t.Fatalf("roam: %v", err)
		}
		after := cst.DropStars(g)
		if len(snapshot) > 0 && len(after) > 0 && &snapshot[0] == &after[0] {
			t.Fatal("DropStars returned the previous spin's slice")
		}
		// Distinct cells within a spin -- two stars on one cell is unrenderable.
		seen := map[config.Cell]bool{}
		for _, s := range after {
			if seen[s.Cell] {
				t.Fatalf("spin %d: two stars on cell (%d,%d)", spin, s.Cell.Reel, s.Cell.Row)
			}
			seen[s.Cell] = true
		}
		cst.Collect()
	}
}

// APPLICATION IS POSITIONAL, even though collection is not. The block stamps its
// multiplier only on the cells it covers, so only lines crossing it are paid at
// the collected value -- which is what keeps WHERE it roams meaningful.
func TestMultiplierAppliesOnlyToTheBlock(t *testing.T) {
	c, tier := actTwoTier(t, "draco")
	cst, err := NewConstellation(tier, "draco", c)
	if err != nil {
		t.Fatalf("deal: %v", err)
	}
	g := engine.NewRNG(41)
	cst.LightFromWins(cst.Targets())
	if err := cst.Wake(g); err != nil {
		t.Fatalf("wake: %v", err)
	}
	for i := 0; i < 6; i++ {
		cst.DropStars(g)
		cst.Collect()
	}
	if cst.Multiplier() <= 1 {
		t.Fatal("no multiplier accumulated; cannot test its application")
	}

	st, err := engine.NewSymbolTable(c)
	if err != nil {
		t.Fatalf("symbols: %v", err)
	}
	wild := st.MustID("W")
	board, err := engine.NewBoard(c)
	if err != nil {
		t.Fatalf("board: %v", err)
	}
	cst.ApplyWilds(board, wild)

	beast := cst.BeastCells()
	stamped := 0
	for reel := 0; reel < board.NumReels; reel++ {
		for row := 0; row < board.NumRows[reel]; row++ {
			cell := board.At(reel, row)
			inBlock := beast.Has(reel, row)
			if inBlock {
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

func TestNoDropsBeforeTheBeastWakes(t *testing.T) {
	c, tier := actTwoTier(t, "corvus")
	cst, err := NewConstellation(tier, "corvus", c)
	if err != nil {
		t.Fatalf("deal: %v", err)
	}
	g := engine.NewRNG(2)
	// Act one is unchanged: the charge phase must stay a plain snowball, with no
	// stars on the board and no multiplier.
	if got := cst.DropStars(g); len(got) != 0 {
		t.Errorf("%d stars dropped during charge, want 0", len(got))
	}
	if _, total := cst.Collect(); total != 1 {
		t.Errorf("multiplier moved to %d during charge, want 1", total)
	}
}

// The engine's output must stay byte-deterministic so published sha256s are
// reproducible -- which means the drop tables must never be iterated as maps.
func TestDropsAreDeterministic(t *testing.T) {
	run := func() []Star {
		cst, g := woken(t, "draco", 1234)
		var all []Star
		for i := 0; i < 8; i++ {
			all = append(all, cst.DropStars(g)...)
			cst.Collect()
			if err := cst.Roam(g); err != nil {
				t.Fatalf("roam: %v", err)
			}
		}
		return all
	}
	a, b := run(), run()
	if len(a) != len(b) {
		t.Fatalf("same seed produced %d then %d stars", len(a), len(b))
	}
	for i := range a {
		if a[i] != b[i] {
			t.Fatalf("star %d differs between identical seeds: %+v vs %+v", i, a[i], b[i])
		}
	}
	if len(a) == 0 {
		t.Fatal("no stars dropped; determinism was not actually exercised")
	}
}

func TestStarDropConfigValidation(t *testing.T) {
	cases := []struct {
		name  string
		drops StarDrops
	}{
		{"empty count", StarDrops{
			Values: []WeightedInt{{Value: 2, Weight: 1}}}},
		{"empty values", StarDrops{
			Count: []WeightedInt{{Value: 1, Weight: 1}}}},
		{"never drops", StarDrops{
			Count:  []WeightedInt{{Value: 0, Weight: 1}},
			Values: []WeightedInt{{Value: 2, Weight: 1}}}},
		{"x1 star is a no-op", StarDrops{
			Count:  []WeightedInt{{Value: 1, Weight: 1}},
			Values: []WeightedInt{{Value: 1, Weight: 1}}}},
		{"duplicate value", StarDrops{
			Count:  []WeightedInt{{Value: 1, Weight: 1}},
			Values: []WeightedInt{{Value: 2, Weight: 1}, {Value: 2, Weight: 1}}}},
		{"zero total weight", StarDrops{
			Count:  []WeightedInt{{Value: 1, Weight: 0}},
			Values: []WeightedInt{{Value: 2, Weight: 1}}}},
	}
	for _, tc := range cases {
		if err := tc.drops.validate("test"); err == nil {
			t.Errorf("%s: accepted, want rejected", tc.name)
		}
	}

	ok := StarDrops{
		Count:  []WeightedInt{{Value: 0, Weight: 3}, {Value: 2, Weight: 1}},
		Values: []WeightedInt{{Value: 2, Weight: 1}, {Value: 100, Weight: 1}},
	}
	if err := ok.validate("test"); err != nil {
		t.Errorf("valid table rejected: %v", err)
	}
}
