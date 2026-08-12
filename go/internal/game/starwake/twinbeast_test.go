package starwake

import (
	"testing"

	"starwake/internal/sdk/config"
	"starwake/internal/sdk/engine"
)

// Twin dragons: the ascendant tier wakes more than one block so that the rarest
// outcome in buy_mystery is visibly a different board rather than an ordinary
// draco that got lucky early.
//
// The economics live in game_optimization.py; what these tests protect is the two
// properties the engine has to guarantee -- that the blocks never stack, and that
// a one-block tier is untouched down to its rng draws.

// dealBeasts deals a tier with beastCount overridden, on the LADDER path (act two
// stripped, like deal()) so a Wake makes no ascension roll and the draw
// accounting below is exactly the placement.
func dealBeasts(t *testing.T, tierName string, count int) (*config.Config, *Constellation) {
	t.Helper()
	c, con := load(t)
	tier, err := con.Tier(tierName)
	if err != nil {
		t.Fatalf("%v", err)
	}
	tier.StarDrops = nil
	tier.BeastCount = count
	cst, err := NewConstellation(tier, tierName, c)
	if err != nil {
		t.Fatalf("deal %s with %d beasts: %v", tierName, count, err)
	}
	return c, cst
}

func wakeIt(t *testing.T, cst *Constellation, g *engine.RNG) {
	t.Helper()
	cst.LightFromWins(cst.Targets())
	if err := cst.Wake(g); err != nil {
		t.Fatal(err)
	}
}

// ⚠⚠ THE ONE THAT SAVES FIVE MODES FROM A RE-SIM. A tier without a beastCount
// must consume EXACTLY the draws it always did -- one IntN(len(origins)) per
// placement -- or corvus, ursa, draco, base and ante_starfall all shift, silently
// and with plausible numbers. Same guarantee the ascension roll's nil-check gives.
//
// Proved by draw accounting rather than by eyeballing the code: run the real
// placement, then check the stream is exactly where a reference stream that made
// the same number of IntN(12) calls would be.
func TestSingleBlockConsumesExactlyOneDrawPerPlacement(t *testing.T) {
	const seed, roams = 4242, 50

	c, cst := dealBeasts(t, "draco", 1)
	origins := len(cst.origins)
	if origins != 12 {
		t.Fatalf("a 2x2 on a %dx%d has %d origins, want 12",
			c.Game.NumReels, c.Rows(0), origins)
	}

	real := engine.NewRNG(seed)
	wakeIt(t, cst, real)
	for i := 0; i < roams; i++ {
		if err := cst.Roam(real); err != nil {
			t.Fatal(err)
		}
	}

	// Wake places once, each Roam places once.
	ref := engine.NewRNG(seed)
	for i := 0; i < 1+roams; i++ {
		ref.IntN(origins)
	}

	for i := 0; i < 8; i++ {
		got, want := real.IntN(1_000_000), ref.IntN(1_000_000)
		if got != want {
			t.Fatalf("rng streams diverged at probe %d (%d vs %d): a one-block tier is "+
				"no longer making exactly %d draws, so every existing pool has shifted",
				i, got, want, 1+roams)
		}
	}
}

// Two stacked blocks render as one and throw away the entire point of the
// mechanic, so non-overlap is a correctness property, not a nicety. Counting the
// UNION mask is what makes this an overlap assertion: two 2x2s that stack cover 4
// cells, two that do not cover 8.
func TestTwoBlocksNeverOverlap(t *testing.T) {
	c, cst := dealBeasts(t, "ascendant", 2)
	g := engine.NewRNG(7)
	wakeIt(t, cst, g)

	for spin := 0; spin < 5000; spin++ {
		origins, placed := cst.BeastOrigins()
		if !placed {
			t.Fatal("awake but not placed")
		}
		if len(origins) != 2 {
			t.Fatalf("spin %d: %d blocks placed, want 2", spin, len(origins))
		}
		if got := cst.BeastCells().Count(); got != 8 {
			t.Fatalf("spin %d: two 2x2 blocks at %v cover %d cells, want 8 -- they overlap",
				spin, origins, got)
		}
		for _, o := range origins {
			if o.Reel < 0 || o.Reel+2 > c.Game.NumReels || o.Row < 0 || o.Row+2 > c.Rows(o.Reel) {
				t.Fatalf("spin %d: block at (%d,%d) is off the grid", spin, o.Reel, o.Row)
			}
		}
		if err := cst.Roam(g); err != nil {
			t.Fatal(err)
		}
	}
}

// Both blocks must actually move. A second block pinned to one corner would pass
// the overlap test while looking like scenery.
func TestBothBlocksRoam(t *testing.T) {
	_, cst := dealBeasts(t, "ascendant", 2)
	g := engine.NewRNG(11)
	wakeIt(t, cst, g)

	seen := [2]map[config.Cell]bool{{}, {}}
	for spin := 0; spin < 500; spin++ {
		origins, _ := cst.BeastOrigins()
		for i, o := range origins {
			seen[i][o] = true
		}
		if err := cst.Roam(g); err != nil {
			t.Fatal(err)
		}
	}
	for i, s := range seen {
		if len(s) < 4 {
			t.Errorf("block %d only ever visited %d position(s) in 500 spins -- it is not roaming", i, len(s))
		}
	}
}

// A pool has to be reproducible from its seed, and the extra draw the second
// block makes is part of that stream.
func TestTwinPlacementIsDeterministic(t *testing.T) {
	first := func() []config.Cell {
		_, cst := dealBeasts(t, "ascendant", 2)
		g := engine.NewRNG(2024)
		wakeIt(t, cst, g)
		for i := 0; i < 20; i++ {
			if err := cst.Roam(g); err != nil {
				t.Fatal(err)
			}
		}
		got, _ := cst.BeastOrigins()
		return append([]config.Cell(nil), got...)
	}
	a, b := first(), first()
	if len(a) != len(b) {
		t.Fatalf("same seed placed %d then %d blocks", len(a), len(b))
	}
	for i := range a {
		if a[i] != b[i] {
			t.Errorf("block %d landed at %v then %v from the same seed", i, a[i], b[i])
		}
	}
}

// The grid's packing number, not its origin count, is what bounds beastCount. A
// 2x2 on a 5x4 has 12 origins but only 4 disjoint placements, and validating
// against 12 would wave through a beastCount that can only be met by stacking.
func TestMaxDisjointIsThePackingNumber(t *testing.T) {
	c, con := load(t)
	tier, err := con.Tier("ascendant")
	if err != nil {
		t.Fatal(err)
	}
	if got := tier.maxDisjoint(c); got != 4 {
		t.Errorf("2x2 on 5x4 packs %d disjoint blocks, want 4", got)
	}
	if got := len(tier.RoamOrigins(c)); got != 12 {
		t.Errorf("...but still has %d roam origins, want 12", got)
	}
}

func TestBeastCountBeyondThePackingNumberIsRejected(t *testing.T) {
	c, con := load(t)
	tier, err := con.Tier("ascendant")
	if err != nil {
		t.Fatal(err)
	}
	tier.BeastCount = 5
	con.Tiers["ascendant"] = tier
	if err := con.validate(c); err == nil {
		t.Fatal("beastCount 5 accepted on a grid that packs 4 -- blocks would have to stack")
	}
}

// Zero means one. The field is optional so that every tier without it keeps its
// old behaviour and its old rng shape.
func TestZeroBeastCountMeansOne(t *testing.T) {
	_, con := load(t)
	for name, tier := range con.Tiers {
		if tier.BeastCount == 0 && tier.Beasts() != 1 {
			t.Errorf("%s: unset beastCount resolved to %d, want 1", name, tier.Beasts())
		}
	}
}
