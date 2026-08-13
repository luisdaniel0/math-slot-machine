package starwake

import (
	"testing"

	"starwake/internal/sdk/engine"
)

// THE WAKE SPIN is buy_mystery_spin's whole feature: the set arrives finished, the
// beast is up before spin 1, and the feature is one roam spin. These tests pin the
// three properties the product rests on -- it really is complete, the beast really
// is placed, and act two's multiplier really does start bare so nothing is granted
// for free by skipping the charge phase.

func TestDealWokenCompletesTheSetAndWakesTheBeast(t *testing.T) {
	for _, name := range []string{"corvus", "ursa", "draco"} {
		t.Run(name, func(t *testing.T) {
			c, tier := actTwoTier(t, name)
			cst, err := NewConstellation(tier, name, c)
			if err != nil {
				t.Fatalf("deal %s: %v", name, err)
			}
			if cst.Phase() != PhaseCharge {
				t.Fatalf("a fresh deal should be charging, got phase %v", cst.Phase())
			}

			if err := cst.DealWoken(seedTable(), 0, engine.NewRNG(11)); err != nil {
				t.Fatalf("deal woken: %v", err)
			}

			if !cst.IsComplete() {
				t.Errorf("%s: set is not complete after a woken deal", name)
			}
			if cst.Phase() != PhaseRoam {
				t.Errorf("%s: phase = %v, want roam", name, cst.Phase())
			}
			if _, placed := cst.BeastOrigins(); !placed {
				t.Errorf("%s: beast was not placed", name)
			}
			if got := cst.BeastCells().Count(); got != 4 {
				t.Errorf("%s: beast covers %d cells, want a single 2x2 = 4", name, got)
			}
		})
	}
}

// A woken deal opens at its SEED and nothing more -- collected is still zero, so
// the multiplier is exactly what was rolled and every further point has to be
// earned from the stars that fall on the one spin the player paid for.
//
// The seed is why this mode can publish 25,000x at all: one spin cannot
// ACCUMULATE, and accumulation is how the 15-spin modes get there.
func TestWokenDealOpensAtItsSeed(t *testing.T) {
	c, tier := actTwoTier(t, "draco")
	cst, err := NewConstellation(tier, "draco", c)
	if err != nil {
		t.Fatalf("deal: %v", err)
	}
	if err := cst.DealWoken(seedTable(), 0, engine.NewRNG(11)); err != nil {
		t.Fatalf("deal woken: %v", err)
	}

	seed := cst.Seed()
	if seed < 2 {
		t.Fatalf("seed = %d, want a value from the table (all >= 2)", seed)
	}
	if got := cst.Multiplier(); got != seed {
		t.Errorf("multiplier = x%d on a woken deal, want the seed x%d", got, seed)
	}
	if got := cst.Collected(); got != 0 {
		t.Errorf("collected = %d before any star fell, want 0", got)
	}
	if got := cst.RoamSpins(); got != 1 {
		t.Errorf("roamSpins = %d, want 1 -- the beast is on the board for the paid spin", got)
	}
}

// ⚠ THE GUARD THAT KEEPS FIVE MODES OFF THE RE-SIM LIST. An ordinary feature must
// never touch the seed: it stays 1, so `multiplier = seed + collected` reduces to
// the old `1 + collected` exactly, and no extra rng is drawn. If this fails, every
// other mode's pool has silently shifted.
func TestOrdinaryFeatureKeepsSeedOne(t *testing.T) {
	for _, name := range []string{"corvus", "ursa", "draco"} {
		t.Run(name, func(t *testing.T) {
			c, tier := actTwoTier(t, name)
			cst, err := NewConstellation(tier, name, c)
			if err != nil {
				t.Fatalf("deal %s: %v", name, err)
			}
			cst.LightFromWins(cst.Targets())
			if err := cst.Wake(engine.NewRNG(11)); err != nil {
				t.Fatalf("wake: %v", err)
			}
			if got := cst.Seed(); got != 1 {
				t.Errorf("%s: seed = %d on an ordinary wake, want 1", name, got)
			}
			if got := cst.Multiplier(); got != 1 {
				t.Errorf("%s: multiplier = x%d at wake, want a bare x1", name, got)
			}
		})
	}
}

// The sticky wilds are consumed at wake, so a woken deal hands the player a normal
// board with the block as the only wild -- NOT a fully-lit carpet. This is the
// difference between "one spin with a beast on it" and "one spin with 11 wilds",
// and it is the reason the mode can bust at all.
func TestWokenDealLeavesOnlyTheBlockWild(t *testing.T) {
	c, tier := actTwoTier(t, "draco")
	cst, err := NewConstellation(tier, "draco", c)
	if err != nil {
		t.Fatalf("deal: %v", err)
	}
	if err := cst.DealWoken(seedTable(), 0, engine.NewRNG(11)); err != nil {
		t.Fatalf("deal woken: %v", err)
	}

	if wilds, beast := cst.WildCells(), cst.BeastCells(); wilds != beast {
		t.Errorf("roam wilds cover %d cells, want exactly the %d-cell block -- "+
			"the traced stars must stop being wild at wake",
			wilds.Count(), beast.Count())
	}
}

// A woken deal must not be reachable twice: Wake refuses a second call, which is
// what stops a wake slice that also completed normally from placing the beast
// twice and drawing rng nobody accounted for.
func TestDealWokenIsNotRepeatable(t *testing.T) {
	c, tier := actTwoTier(t, "ursa")
	cst, err := NewConstellation(tier, "ursa", c)
	if err != nil {
		t.Fatalf("deal: %v", err)
	}
	if err := cst.DealWoken(seedTable(), 0, engine.NewRNG(11)); err != nil {
		t.Fatalf("first woken deal: %v", err)
	}
	if err := cst.DealWoken(seedTable(), 0, engine.NewRNG(11)); err == nil {
		t.Error("a second woken deal succeeded; want a refusal")
	}
}

// A representative seed table for the wake tests. Deliberately NOT the shipped
// one -- these tests pin behaviour, not tuning.
func seedTable() []WeightedInt {
	return []WeightedInt{{Value: 2, Weight: 30}, {Value: 25, Weight: 15}, {Value: 100, Weight: 3}}
}
