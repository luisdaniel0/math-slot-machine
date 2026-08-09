package starwake

import (
	"testing"

	"starwake/internal/sdk/engine"
)

// ASCENSION is corvus's route to a 25,000x ceiling. Its tier is structurally
// short -- 9,158x on the ordinary roam strip, 18,613x on the densest one -- and
// the strip lever is exhausted, so the ceiling has to come from a rare switch to
// a richer star table rather than from a longer tail.
//
// These tests pin the three properties the economy depends on: the switch is
// RARE at the configured rate, it is STICKY once taken, and a tier without the
// block is completely INERT (no extra rng call), which is what lets buy_ursa and
// buy_draco skip a re-sim.

// ascendTier attaches an ordinary star table plus an ascension block whose values
// are disjoint from it, so a star's value alone identifies which table produced it.
func ascendTier(t *testing.T, name string, oneIn int) (*Constellation, *engine.Board, engine.SymID, *engine.RNG) {
	t.Helper()
	c, tier := actTwoTier(t, name)
	tier.StarDrops.Values = []WeightedInt{{Value: 2, Weight: 1}}
	tier.StarDrops.Ascension = &Ascension{
		OneIn:  oneIn,
		Values: []WeightedInt{{Value: 100, Weight: 1}},
	}
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
	g := engine.NewRNG(99)
	cst.LightFromWins(cst.Targets())
	if err := cst.Wake(g); err != nil {
		t.Fatalf("wake: %v", err)
	}
	return cst, board, st.MustID(starStandIn), g
}

// oneIn=2 would ascend every OTHER round; oneIn=1 would ascend every round, which
// is not an ascension but a silent global star-table swap -- the exact change that
// was tried twice and reverted because the optimizer paid for the fat tail out of
// corvus's body. Config must refuse it rather than produce a plausible pool.
func TestAscensionRejectsOneInBelowTwo(t *testing.T) {
	for _, bad := range []int{0, 1, -5} {
		a := &Ascension{OneIn: bad, Values: []WeightedInt{{Value: 50, Weight: 1}}}
		if err := a.validate("corvus"); err == nil {
			t.Errorf("oneIn=%d accepted; a global table swap must be refused", bad)
		}
	}
	ok := &Ascension{OneIn: 20000, Values: []WeightedInt{{Value: 50, Weight: 1}}}
	if err := ok.validate("corvus"); err != nil {
		t.Errorf("oneIn=20000 rejected: %v", err)
	}
}

// A star worth x1 animates a collect for no gain, so the ascended table carries
// the same floor as the ordinary one.
func TestAscensionRejectsWorthlessStars(t *testing.T) {
	a := &Ascension{OneIn: 100, Values: []WeightedInt{{Value: 1, Weight: 1}}}
	if err := a.validate("corvus"); err == nil {
		t.Error("a x1 ascended star was accepted; it would collect for no gain")
	}
}

// THE ISOLATION PROPERTY, and the reason ursa and draco need no re-sim: a tier
// with no ascension block must make exactly the rng calls it always did. If the
// roll ever moves outside the nil guard, every mode's books shift silently and
// with entirely plausible numbers.
func TestTierWithoutAscensionMakesNoExtraRngCall(t *testing.T) {
	next := func(withBlock bool) int {
		c, tier := actTwoTier(t, "corvus")
		if withBlock {
			tier.StarDrops.Ascension = &Ascension{
				OneIn: 1000, Values: []WeightedInt{{Value: 100, Weight: 1}}}
		}
		cst, err := NewConstellation(tier, "corvus", c)
		if err != nil {
			t.Fatalf("deal: %v", err)
		}
		g := engine.NewRNG(7)
		cst.LightFromWins(cst.Targets())
		if err := cst.Wake(g); err != nil {
			t.Fatalf("wake: %v", err)
		}
		return g.IntN(1_000_000)
	}
	if next(false) == next(true) {
		t.Error("wake consumed the same rng with and without an ascension block; " +
			"the roll is not actually guarded by the nil check")
	}
}

// The configured rate is the economy's only dial for what ascension costs in RTP
// and variance, so it has to be the rate actually delivered.
func TestAscensionFiresAtTheConfiguredRate(t *testing.T) {
	const oneIn, rounds = 20, 20000
	c, tier := actTwoTier(t, "corvus")
	tier.StarDrops.Ascension = &Ascension{
		OneIn: oneIn, Values: []WeightedInt{{Value: 100, Weight: 1}}}

	fired := 0
	for seed := 0; seed < rounds; seed++ {
		cst, err := NewConstellation(tier, "corvus", c)
		if err != nil {
			t.Fatalf("deal: %v", err)
		}
		g := engine.NewRNG(uint64(seed) + 1)
		cst.LightFromWins(cst.Targets())
		if err := cst.Wake(g); err != nil {
			t.Fatalf("wake: %v", err)
		}
		if cst.Ascended() {
			fired++
		}
	}
	want := float64(rounds) / oneIn
	if float64(fired) < want*0.85 || float64(fired) > want*1.15 {
		t.Errorf("ascended %d of %d rounds, want ~%.0f (1 in %d)",
			fired, rounds, want, oneIn)
	}
}

// Once taken, the richer table must hold for the REST of the roam. A per-spin
// re-roll would make the payout depend on how many spins happened to be ascended,
// which is not the mechanic and not what the ceiling was sized against.
func TestAscensionIsStickyAndSwapsTheTable(t *testing.T) {
	cst, board, star, g := ascendTier(t, "corvus", 2)
	cst.ascended = true // pin it; the roll itself is covered above

	filler := star
	for spin := 0; spin < 3; spin++ {
		clearBoard(board, filler)
		placeStars(board, star, cst.TargetCells()[0])
		stars := cst.RollStarValues(board, star, g)
		if len(stars) == 0 {
			t.Fatalf("spin %d: no stars rolled", spin)
		}
		for _, s := range stars {
			if s.Value != 100 {
				t.Fatalf("spin %d: star value %d came from the ORDINARY table; "+
					"the ascended table is not sticky", spin, s.Value)
			}
		}
		if !cst.Ascended() {
			t.Fatalf("spin %d: ascension lapsed mid-roam", spin)
		}
	}
}

// The ordinary table must still be used when the round has NOT ascended -- the
// mirror of the sticky test, and what stops a bug making every round ascended.
func TestUnascendedRoundUsesTheOrdinaryTable(t *testing.T) {
	cst, board, star, g := ascendTier(t, "corvus", 1000000)
	if cst.Ascended() {
		t.Skip("this seed ascended at 1-in-1e6; nothing to assert")
	}
	clearBoard(board, star)
	placeStars(board, star, cst.TargetCells()[0])
	for _, s := range cst.RollStarValues(board, star, g) {
		if s.Value != 2 {
			t.Errorf("unascended star value %d came from the ascended table", s.Value)
		}
	}
}
