package config

import (
	"path/filepath"
	"testing"
)

// These tests load the REAL exported config, not a fixture. That is the point:
// they are the end-to-end proof that the Python design surface reaches the Go
// engine intact. Expected values are transcribed from game_config.py and the
// measured figures recorded in CLAUDE.md, so a drift on either side of the seam
// fails here rather than in a 1e6 pool.

func load(t *testing.T) *Config {
	t.Helper()
	root, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatalf("resolve repo root: %v", err)
	}
	c, err := Load(filepath.Join(root, "go", "config", "starwake.json"), root)
	if err != nil {
		t.Fatalf("load config: %v", err)
	}
	return c
}

func TestGameIdentity(t *testing.T) {
	c := load(t)
	if c.Game.ID != "starwake" {
		t.Errorf("game id = %q, want starwake", c.Game.ID)
	}
	// Both were silently inheriting the SDK scaffold defaults until Jul 31 2026
	// and shipped that way into config_fe_starwake.json, so they are asserted.
	if c.Game.Name != "Starwake" || c.Game.Provider != "Uptown Games" {
		t.Errorf("identity = %q / %q, want Starwake / Uptown Games", c.Game.Name, c.Game.Provider)
	}
	if c.Game.NumReels != 5 {
		t.Errorf("numReels = %d, want 5", c.Game.NumReels)
	}
	for reel := 0; reel < c.Game.NumReels; reel++ {
		if c.Rows(reel) != 4 {
			t.Errorf("reel %d has %d rows, want 4", reel, c.Rows(reel))
		}
	}
	if c.Game.Wincap != 25000 {
		t.Errorf("wincap = %v, want 25000", c.Game.Wincap)
	}
	// 0.9669 since Aug 8 2026, and the ceiling matters more than the value: Stake
	// caps RTP at 0.967 and the band is a CRITICAL test, so breaching it blocks
	// submission outright. Assert the cap as well as the target, because a typo
	// that reads 0.9679 is the one that must never reach a pool.
	if c.Game.RTP != 0.9669 {
		t.Errorf("rtp = %v, want 0.9669", c.Game.RTP)
	}
	if c.Game.RTP > 0.967 {
		t.Errorf("rtp = %v is OVER Stake's 0.967 cap -- a critical-test failure", c.Game.RTP)
	}
}

func TestPaytable(t *testing.T) {
	c := load(t)
	want := map[PayKey]float64{
		{5, "W"}:  15, // W pays 5-kind ONLY
		{5, "H1"}: 12,
		{3, "H1"}: 3,
		{5, "L5"}: 0.5,
		{3, "L5"}: 0.2,
	}
	for k, v := range want {
		got, ok := c.Pay[k]
		if !ok {
			t.Errorf("paytable missing %d x %s", k.Kind, k.Symbol)
			continue
		}
		if got != v {
			t.Errorf("paytable %d x %s = %v, want %v", k.Kind, k.Symbol, got, v)
		}
	}
	// The wild must have no short-line entries, or a 3-wild line could outrank a
	// longer real-symbol line -- load-bearing once the feature manufactures wilds.
	for _, kind := range []int{3, 4} {
		if _, ok := c.Pay[PayKey{kind, "W"}]; ok {
			t.Errorf("paytable has a %d-kind W entry; W must pay 5-kind only", kind)
		}
	}
}

func TestPaylines(t *testing.T) {
	c := load(t)
	if len(c.Paylines) != 20 {
		t.Fatalf("got %d paylines, want 20", len(c.Paylines))
	}
	// Validate() already range-checks every row; this pins the known first line.
	first := c.Paylines[0]
	for reel, row := range first.Rows {
		if row != 0 {
			t.Errorf("payline 1 reel %d row = %d, want 0 (top straight)", reel, row)
		}
	}
}

func TestScatterTiers(t *testing.T) {
	c := load(t)
	want := map[int]string{3: "corvus", 4: "ursa", 5: "draco", 6: "ascendant"}
	for count, tier := range want {
		if got := c.TierByScatter[count]; got != tier {
			t.Errorf("%d scatters -> %q, want %q", count, got, tier)
		}
	}
	// Every scatter count that deals a tier must also award spins, or a trigger
	// would land in the feature with no length.
	for count := range want {
		if _, ok := c.SpinsByScatter[c.Game.BasegameType][count]; !ok {
			t.Errorf("%d scatters deals a tier but awards no spins", count)
		}
	}
}

func TestBetModes(t *testing.T) {
	c := load(t)
	if len(c.BetModes) != 6 {
		t.Fatalf("got %d bet modes, want 6", len(c.BetModes))
	}

	cases := []struct {
		name   string
		cost   float64
		maxWin float64
		buy    bool
	}{
		{"base", 1.0, 25000, false},
		{"ante_starfall", 1.5, 25000, false},
		// buy_corvus publishes an HONEST ceiling below the global cap: it cannot
		// reach 25,000x, and MaxWin is the engine clamp as well as the advertised
		// number. 10,000x until act two removed the fully-wild-board route and a
		// full 1e6 pool topped out at 9,158x, making the published figure a lie.
		// 9,000x rather than 9,158x because 9,158 was one seed's observed maximum.
		// And 120x rather than 240x because at 240x corvus was last on
		// ceiling-per-cost behind a mode costing 12% more -- a rung nobody should
		// pick is worse than no rung.
		// ⚠ 2,500x SINCE Aug 7 2026. 9,000x was honest and useless: delivered at 1
		// in 2,000,003 against a market norm of 1 in 400-4,000. At 2,500x the
		// ceiling is the most reachable in the menu (1 in 2,417 unforced), at the
		// cost of ceiling-per-cost dropping 75x -> 20.8x. This assertion sat stale
		// and RED from that day until Aug 8, because the workflow runs pytest and
		// the sims but not `go test ./...` -- run the Go suite after a config change.
		// ⚠⚠ 25,000x SINCE Aug 8 2026, once ASCENSION made it reachable. Every mode
		// now reaches the game's headline ceiling, which is the invariant Meta
		// Gaming holds across all 18 modes of their three games and the one corvus
		// used to break. Ceiling-per-stake 20.8x -> 208x, highest in the menu, which
		// is the market pattern: the cheapest buy carries the tallest ceiling and
		// the expensive tiers earn their price on cap FREQUENCY (corvus 1 in 50,000
		// against draco's 1 in 641). Reachability is measured, not assumed --
		// P(>=25,000x) is 1 in 2,874 with ascension forced, 1 in 25M without.
		{"buy_corvus", 120, 25000, true},
		{"buy_ursa", 268, 25000, true},
		{"buy_draco", 520, 25000, true},
		{"buy_mystery", 563, 25000, true},
	}
	for _, tc := range cases {
		m, err := c.Mode(tc.name)
		if err != nil {
			t.Errorf("%v", err)
			continue
		}
		if m.Cost != tc.cost {
			t.Errorf("%s cost = %v, want %v", tc.name, m.Cost, tc.cost)
		}
		if m.MaxWin != tc.maxWin {
			t.Errorf("%s maxWin = %v, want %v", tc.name, m.MaxWin, tc.maxWin)
		}
		if m.IsBuyBonus != tc.buy {
			t.Errorf("%s isBuyBonus = %v, want %v", tc.name, m.IsBuyBonus, tc.buy)
		}
	}

	// The buy menu must stay strictly ordered, or the tier story breaks.
	prev := 0.0
	for _, name := range []string{"buy_corvus", "buy_ursa", "buy_draco", "buy_mystery"} {
		m, _ := c.Mode(name)
		if m.Cost <= prev {
			t.Errorf("buy menu out of order at %s (%v after %v)", name, m.Cost, prev)
		}
		prev = m.Cost
		// Stake caps a buy at 1000x the base bet.
		if m.Cost > 1000 {
			t.Errorf("%s costs %v, over the 1000x buy cap", name, m.Cost)
		}
	}

	// EVERY forced wincap slice must hunt a ceiling the tier can actually produce.
	// An unreachable one does not error -- it redraws with no retry cap, so the
	// run hangs rather than fails, and the only symptom is a sim that never ends.
	//
	// ⚠ THIS ASSERTION USED TO READ "buy_corvus must have NO forced slice", which
	// was right while corvus published 9,000x it could not reach. Corvus gained a
	// slice on Aug 6 2026 once its ceiling came down to 2,500x, where the tier
	// makes the cap unforced at 1 in 2,417 -- so the slice manufactures cap books
	// cheaply instead of hunting. The check is now the GENERAL invariant rather
	// than a corvus special case, since it is the property that actually matters.
	//
	// Reachability cannot be proven from config alone, so this pins the pairing it
	// CAN see -- a slice must target its own mode's MaxWin, not the global cap.
	// Measured reach with the clamp lifted (Aug 8 2026): corvus tops out at 9,158x
	// on the ordinary roam strip and 18,613x on the densest, and >=25,000x
	// extrapolates to 1 in 25 MILLION. Any future rise in corvus's ceiling needs a
	// re-measure FIRST, or this slice becomes the hang it is here to prevent.
	for _, m := range c.BetModes {
		for _, d := range m.Distributions {
			if !d.Conditions.ForceWincap {
				continue
			}
			if d.WinCriteria == nil {
				t.Errorf("%s: forced wincap slice (%s) has no winCriteria", m.Name, d.Criteria)
				continue
			}
			if *d.WinCriteria != m.MaxWin {
				t.Errorf("%s: forced slice (%s) hunts %v but the mode clamps at %v; "+
					"it would redraw forever", m.Name, d.Criteria, *d.WinCriteria, m.MaxWin)
			}
		}
	}

	// Mystery is the only mode that can roll an ascendant (6 scatters).
	for _, m := range c.BetModes {
		for _, d := range m.Distributions {
			for _, st := range d.Conditions.ScatterTriggers {
				if st.Scatters == 6 && m.Name != "buy_mystery" {
					t.Errorf("%s/%s forces 6 scatters; ascendant is mystery-exclusive", m.Name, d.Criteria)
				}
			}
		}
	}
}

func TestReelStrips(t *testing.T) {
	c := load(t)
	for _, id := range []string{"BR0", "FR0", "WCAP", "ASC"} {
		strip, ok := c.Strips[id]
		if !ok {
			t.Errorf("missing reel strip %s", id)
			continue
		}
		if len(strip) != c.Game.NumReels {
			t.Errorf("%s: %d reels, want %d", id, len(strip), c.Game.NumReels)
		}
		for reel := range strip {
			if strip.Len(reel) == 0 {
				t.Errorf("%s reel %d is empty", id, reel)
			}
		}
	}

	// FR0's dryness gradient IS the tier ladder: wilds on the left reels feed the
	// snowball while reel 4 is bone dry, so draco's reel-4 cells can only light
	// from a winning line reaching them. If reel 4 ever gains a wild, draco's
	// completion rate moves and every buy price with it.
	fr0 := c.Strips["FR0"]
	if n := fr0.SymbolCounts(4)["W"]; n != 0 {
		t.Errorf("FR0 reel 4 has %d wilds, want 0 (the dry column draco depends on)", n)
	}
	// No stars inside the feature: there are no retriggers, so a scatter there
	// would be a dead symbol occupying a paying position.
	for reel := 0; reel < c.Game.NumReels; reel++ {
		if n := fr0.SymbolCounts(reel)["S"]; n != 0 {
			t.Errorf("FR0 reel %d has %d stars, want 0", reel, n)
		}
	}

	// ASC exists solely to make 6 scatters forceable: _force_special_board places
	// at most ONE scatter per reel, so a sixth requires a reel whose 4-row window
	// shows two. Without that, forcing 6 is an uncapped retry loop that hangs.
	asc := c.Strips["ASC"]
	total := 0
	for reel := 0; reel < c.Game.NumReels; reel++ {
		total += asc.SymbolCounts(reel)["S"]
	}
	if total < 6 {
		t.Errorf("ASC has %d stars across all reels; cannot force 6", total)
	}
}
