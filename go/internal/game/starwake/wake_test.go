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

			if err := cst.DealWoken(engine.NewRNG(11)); err != nil {
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

// ⚠ THE POINT OF THE WHOLE DESIGN. Skipping act one must not be a gift. Under the
// dead multiplier ladder a set completed before spin 1 would have handed out a top
// rung free, which is exactly what NewConstellation's "pre-lit on every cell" guard
// was written to prevent. Under act two the multiplier is COLLECTED, so a woken
// deal starts at x1 and every point still has to be earned from the stars that fall
// on the one spin the player paid for.
func TestWokenDealGrantsNoMultiplier(t *testing.T) {
	c, tier := actTwoTier(t, "draco")
	cst, err := NewConstellation(tier, "draco", c)
	if err != nil {
		t.Fatalf("deal: %v", err)
	}
	if err := cst.DealWoken(engine.NewRNG(11)); err != nil {
		t.Fatalf("deal woken: %v", err)
	}

	if got := cst.Multiplier(); got != 1 {
		t.Errorf("multiplier = x%d on a woken deal, want a bare x1", got)
	}
	if got := cst.Collected(); got != 0 {
		t.Errorf("collected = %d before any star fell, want 0", got)
	}
	if got := cst.RoamSpins(); got != 1 {
		t.Errorf("roamSpins = %d, want 1 -- the beast is on the board for the paid spin", got)
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
	if err := cst.DealWoken(engine.NewRNG(11)); err != nil {
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
	if err := cst.DealWoken(engine.NewRNG(11)); err != nil {
		t.Fatalf("first woken deal: %v", err)
	}
	if err := cst.DealWoken(engine.NewRNG(11)); err == nil {
		t.Error("a second woken deal succeeded; want a refusal")
	}
}
