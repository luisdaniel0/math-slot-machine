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
	}
	return nil
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
