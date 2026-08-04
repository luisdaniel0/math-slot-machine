package starwake

import (
	"path/filepath"
	"testing"

	"starwake/internal/sdk/config"
)

// Loads the REAL exported config, not a fixture -- these are the end-to-end proof
// that the Python design surface reaches the Go engine intact. Expected values are
// transcribed from game_config.py and the measured figures in CLAUDE.md, so a
// drift on either side of the seam fails here rather than in a 1e6 pool.

func load(t *testing.T) (*config.Config, *FeatureConfig) {
	t.Helper()
	root, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatalf("resolve repo root: %v", err)
	}
	c, err := config.Load(filepath.Join(root, "go", "config", "starwake.json"), root)
	if err != nil {
		t.Fatalf("load config: %v", err)
	}
	con, err := LoadFeatureConfig(c)
	if err != nil {
		t.Fatalf("load constellation: %v", err)
	}
	return c, con
}

func TestTiers(t *testing.T) {
	_, con := load(t)

	cases := []struct {
		tier      string
		cells     int
		rungs     int
		ladderTop int
		spins     int
		beastName string
	}{
		{"corvus", 4, 9, 200, 10, "corvus"},
		{"ursa", 7, 13, 500, 15, "ursa"},
		{"draco", 11, 12, 600, 15, "draco"},
		// An ascendant IS a draco: same cells, ladder and length, different
		// starting state -- and it must render as the dragon, not a fourth beast.
		{"ascendant", 11, 12, 600, 15, "draco"},
	}

	for _, tc := range cases {
		tier, err := con.Tier(tc.tier)
		if err != nil {
			t.Errorf("%v", err)
			continue
		}
		if len(tier.Cells) != tc.cells {
			t.Errorf("%s: %d cells, want %d", tc.tier, len(tier.Cells), tc.cells)
		}
		if tier.LadderRungs != tc.rungs || len(tier.MultLadder) != tc.rungs {
			t.Errorf("%s: %d ladder values / rungs=%d, want %d",
				tc.tier, len(tier.MultLadder), tier.LadderRungs, tc.rungs)
		}
		if top := tier.MultLadder[len(tier.MultLadder)-1]; top != tc.ladderTop {
			t.Errorf("%s: ladder top = %d, want %d", tc.tier, top, tc.ladderTop)
		}
		if tier.FeatureSpins != tc.spins {
			t.Errorf("%s: %d feature spins, want %d", tc.tier, tier.FeatureSpins, tc.spins)
		}
		if tier.BeastName != tc.beastName {
			t.Errorf("%s: renders as %q, want %q", tc.tier, tier.BeastName, tc.beastName)
		}
		// All beasts are 2x2 as of Jul 2026: bigger blocks have too few roam
		// positions on a 5x4 for the roam to read as movement.
		if tier.BeastShape[0] != 2 || tier.BeastShape[1] != 2 {
			t.Errorf("%s: beast %v, want [2 2]", tc.tier, tier.BeastShape)
		}
	}

	if con.MinRoamSpins != 2 {
		t.Errorf("minRoamSpins = %d, want 2", con.MinRoamSpins)
	}
}

func TestPrelitCells(t *testing.T) {
	_, con := load(t)
	// Only ascendant is dealt with cells already lit, and it is exactly the
	// adjacent reel-4 pair the sweep chose -- reel 4 is the bone-dry column, so
	// two permanent wilds there are what make it reachable at all.
	for name, tier := range con.Tiers {
		if name == "ascendant" {
			want := []config.Cell{{Reel: 4, Row: 0}, {Reel: 4, Row: 1}}
			if len(tier.PrelitCells) != 2 ||
				tier.PrelitCells[0] != want[0] || tier.PrelitCells[1] != want[1] {
				t.Errorf("ascendant pre-lit = %v, want %v", tier.PrelitCells, want)
			}
			continue
		}
		if len(tier.PrelitCells) != 0 {
			t.Errorf("%s: has pre-lit cells %v, want none", name, tier.PrelitCells)
		}
	}
}

func TestRoamOrigins(t *testing.T) {
	c, con := load(t)
	// A 2x2 block on a 5x4 grid has 4 x 3 = 12 legal origins. That count is the
	// reason every beast is 2x2: at 3x3 it drops to 6 positions covering 45% of
	// the board, and the signature "the beast roams each spin" stops reading.
	for name, tier := range con.Tiers {
		origins := tier.RoamOrigins(c)
		if len(origins) != 12 {
			t.Errorf("%s: %d roam origins, want 12", name, len(origins))
		}
		// Every origin must leave the whole block on-grid -- this is what
		// guarantees the beast never exits.
		w, h := tier.BeastShape[0], tier.BeastShape[1]
		for _, o := range origins {
			if o.Reel < 0 || o.Reel+w > c.Game.NumReels || o.Row < 0 || o.Row+h > c.Rows(o.Reel) {
				t.Errorf("%s: origin (%d,%d) puts a %dx%d block off-grid", name, o.Reel, o.Row, w, h)
			}
		}
	}
}

func TestSpinsMatchTiers(t *testing.T) {
	c, con := load(t)
	// freespin_triggers is DERIVED from num_feature_spins in Python precisely so
	// the tier-indexed design view and the count-indexed engine view cannot
	// drift. This is that guarantee, checked across the seam.
	for count, tierName := range c.TierByScatter {
		tier, err := con.Tier(tierName)
		if err != nil {
			t.Errorf("%d scatters -> %v", count, err)
			continue
		}
		got := c.SpinsByScatter[c.Game.BasegameType][count]
		if got != tier.FeatureSpins {
			t.Errorf("%d scatters (%s) awards %d spins, want %d",
				count, tierName, got, tier.FeatureSpins)
		}
	}
}
