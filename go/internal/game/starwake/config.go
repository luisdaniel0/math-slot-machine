// Package starwake holds everything specific to the Starwake game: the
// Charge -> Bloom -> Roam constellation feature and the config block describing it.
//
// The generic SDK (internal/sdk/...) knows nothing about constellations. It hands
// this package the raw "constellation" JSON block and this package decodes it, so
// a second game can reuse the SDK without inheriting Starwake's vocabulary.
package starwake

import (
	"bytes"
	"encoding/json"
	"fmt"

	"starwake/internal/sdk/config"
)

// WeightedInt is one (value, weight) row of a discrete distribution.
//
// A slice of pairs rather than a map[int]int on purpose: map iteration order is
// randomised in Go, and the engine's output must stay byte-deterministic so
// published sha256s are reproducible.
type WeightedInt struct {
	Value  int `json:"value"`
	Weight int `json:"weight"`
}

// StarDrops is ACT TWO's multiplier-star table for one tier.
//
// Presence of this block is what SWITCHES A TIER TO ACT TWO. When set, the tier
// consumes its sticky wilds at wake and the beast accumulates a multiplier by
// collecting stars; when absent the tier runs the original climbing ladder.
// ⚠ TRANSITIONAL. Both paths exist only so the two can be A/B swept against each
// other to answer "can act 2 carry the money". Once that is measured, the loser
// is DELETED -- do not let this become a permanent fork.
//
// ⚠ THERE IS NO COUNT TABLE, AND THAT IS THE POINT. How many stars land is decided
// by the ROAM STRIP's density, because stars are real reel symbols; only the value
// of each one is rolled from config. Density and value trade against each other
// during tuning -- more stars means more multiplier but fewer paying cells -- so
// they are deliberately kept on separate surfaces: density in reels/, value here.
type StarDrops struct {
	// RoamStrip is the reel set drawn while the beast is awake. It is the only
	// strip carrying the star symbol, which is what keeps stars out of act one
	// where there is no beast to collect them.
	RoamStrip string `json:"roamStrip"`
	// StarSymbol is the non-paying symbol the beast collects.
	StarSymbol string `json:"starSymbol"`
	// Values is each star's multiplier value, drawn independently per star.
	Values []WeightedInt `json:"values"`
}

// Tier is one constellation's full definition.
//
// "ascendant" arrives already resolved: game_config.py derives it from draco at
// construction time (same cells, beast, ladder and length; only the pre-lit set
// differs), so it reaches Go as an ordinary tier rather than a special case.
type Tier struct {
	Cells        []config.Cell `json:"cells"`
	BeastShape   []int         `json:"beastShape"`
	MultLadder   []int         `json:"multLadder"`
	LadderRungs  int           `json:"ladderRungs"`
	PrelitCells  []config.Cell `json:"prelitCells"`
	BeastName    string        `json:"beastName"`
	FeatureSpins int           `json:"featureSpins"`
	StarDrops    *StarDrops    `json:"starDrops,omitempty"`
}

// FeatureConfig is the feature-wide config plus every tier definition.
type FeatureConfig struct {
	MinRoamSpins int             `json:"minRoamSpins"`
	Tiers        map[string]Tier `json:"tiers"`
}

// LoadFeatureConfig decodes the game-specific block out of a loaded SDK config
// and checks the invariants that would otherwise only surface as a wrong pool.
func LoadFeatureConfig(c *config.Config) (*FeatureConfig, error) {
	if len(c.GameSpecific) == 0 {
		return nil, fmt.Errorf("config has no constellation block")
	}
	var con FeatureConfig
	dec := json.NewDecoder(bytes.NewReader(c.GameSpecific))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&con); err != nil {
		return nil, fmt.Errorf("decode constellation: %w", err)
	}
	if err := con.validate(c); err != nil {
		return nil, fmt.Errorf("constellation invalid: %w", err)
	}
	return &con, nil
}

func (con *FeatureConfig) validate(c *config.Config) error {
	if con.MinRoamSpins < 1 {
		return fmt.Errorf("minRoamSpins = %d; the beast must get at least one paying spin",
			con.MinRoamSpins)
	}
	if len(con.Tiers) == 0 {
		return fmt.Errorf("no tiers")
	}

	for name, t := range con.Tiers {
		// THE LADDER INVARIANT, and the one the original Python guard got wrong.
		// It asserted len(ladder) >= longest roam, which catches only a ladder
		// that is too SHORT. Too LONG is the failure that actually shipped: rungs
		// were set to featureSpins-1, a depth needing a spin-1 completion, so ursa
		// and draco advertised multipliers no player could ever be paid. Equality
		// against the MEASURED achievable depth is the correct check.
		if len(t.MultLadder) != t.LadderRungs {
			return fmt.Errorf("tier %s: %d ladder values but ladderRungs=%d",
				name, len(t.MultLadder), t.LadderRungs)
		}
		if t.LadderRungs == 0 {
			return fmt.Errorf("tier %s: the beast needs at least one multiplier rung", name)
		}
		for i := 1; i < len(t.MultLadder); i++ {
			if t.MultLadder[i] < t.MultLadder[i-1] {
				return fmt.Errorf("tier %s: ladder decreases at rung %d", name, i)
			}
		}

		seen := make(map[config.Cell]bool, len(t.Cells))
		for _, cell := range t.Cells {
			if cell.Reel < 0 || cell.Reel >= c.Game.NumReels ||
				cell.Row < 0 || cell.Row >= c.Rows(cell.Reel) {
				return fmt.Errorf("tier %s: cell (%d,%d) off grid", name, cell.Reel, cell.Row)
			}
			if seen[cell] {
				return fmt.Errorf("tier %s: duplicate cell (%d,%d)", name, cell.Reel, cell.Row)
			}
			seen[cell] = true
		}

		for _, cell := range t.PrelitCells {
			if !seen[cell] {
				return fmt.Errorf("tier %s: pre-lit cell (%d,%d) is not part of the shape",
					name, cell.Reel, cell.Row)
			}
		}
		// A fully pre-lit deal would wake the beast before a single spin and hand
		// out the top of the ladder for free -- plausible-looking right up to the
		// ceiling, so it must be loud here rather than silent in a 1e6 pool.
		if len(t.PrelitCells) >= len(t.Cells) {
			return fmt.Errorf("tier %s: fully pre-lit -- would complete before spin 1", name)
		}

		if len(t.BeastShape) != 2 {
			return fmt.Errorf("tier %s: beastShape must be [reels,rows]", name)
		}
		// The roam is the signature mechanic. A block with one legal origin does
		// not roam at all -- this is what ruled out the 3x3 dragon on a 5x4.
		if n := len(t.RoamOrigins(c)); n < 2 {
			return fmt.Errorf("tier %s: beast %dx%d has only %d roam position(s)",
				name, t.BeastShape[0], t.BeastShape[1], n)
		}

		if t.FeatureSpins < 1 {
			return fmt.Errorf("tier %s: %d feature spins", name, t.FeatureSpins)
		}

		if t.StarDrops != nil {
			if err := t.StarDrops.validate(name, c); err != nil {
				return err
			}
		}
	}
	return nil
}

func (sd *StarDrops) validate(tier string, c *config.Config) error {
	if sd.RoamStrip == "" {
		return fmt.Errorf("tier %s: starDrops.roamStrip is empty", tier)
	}
	// Without this the roam would silently fall back to the charge strip, which
	// carries no stars -- act two would run, collect nothing, and pay x1 all the
	// way through while looking entirely normal.
	if _, ok := c.Reels[sd.RoamStrip]; !ok {
		return fmt.Errorf("tier %s: starDrops.roamStrip %q is not a configured reel set",
			tier, sd.RoamStrip)
	}
	if sd.StarSymbol == "" {
		return fmt.Errorf("tier %s: starDrops.starSymbol is empty", tier)
	}
	// A star worth x1 adds nothing and would animate a collect for no gain, so the
	// floor is 2 -- the same floor Rage Bait's fish use.
	return validWeights(tier, "starDrops.values", sd.Values, 2)
}

func validWeights(tier, field string, rows []WeightedInt, minValue int) error {
	if len(rows) == 0 {
		return fmt.Errorf("tier %s: %s is empty", tier, field)
	}
	total := 0
	seen := make(map[int]bool, len(rows))
	for _, row := range rows {
		if row.Value < minValue {
			return fmt.Errorf("tier %s: %s value %d is below the %d floor",
				tier, field, row.Value, minValue)
		}
		if row.Weight < 0 {
			return fmt.Errorf("tier %s: %s value %d has negative weight", tier, field, row.Value)
		}
		if seen[row.Value] {
			return fmt.Errorf("tier %s: %s value %d appears twice", tier, field, row.Value)
		}
		seen[row.Value] = true
		total += row.Weight
	}
	if total <= 0 {
		return fmt.Errorf("tier %s: %s has zero total weight", tier, field)
	}
	return nil
}

// Pick draws one value from a weighted table. Total weight is recomputed per call
// rather than cached: these tables have a handful of rows and are drawn once per
// roam spin, so the arithmetic is free next to keeping the config immutable.
func pickWeighted(rows []WeightedInt, roll func(int) int) int {
	total := 0
	for _, row := range rows {
		total += row.Weight
	}
	r := roll(total)
	for _, row := range rows {
		r -= row.Weight
		if r < 0 {
			return row.Value
		}
	}
	return rows[len(rows)-1].Value // unreachable while total > 0
}

// RoamOrigins lists every top-left position where the beast block fits fully on
// the grid. Choosing only from this set is what guarantees the beast never exits.
func (t Tier) RoamOrigins(c *config.Config) []config.Cell {
	w, h := t.BeastShape[0], t.BeastShape[1]
	var origins []config.Cell
	for reel := 0; reel+w <= c.Game.NumReels; reel++ {
		for row := 0; row+h <= c.Rows(reel); row++ {
			origins = append(origins, config.Cell{Reel: reel, Row: row})
		}
	}
	return origins
}

// Tier looks up a tier by name.
func (con *FeatureConfig) Tier(name string) (Tier, error) {
	t, ok := con.Tiers[name]
	if !ok {
		return Tier{}, fmt.Errorf("unknown tier %q", name)
	}
	return t, nil
}
