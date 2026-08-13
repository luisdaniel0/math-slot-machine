// Package config loads the game definition exported from Python.
//
// The Go engine owns the HOT LOOP; game_config.py stays the design surface. The
// contract between them is go/config/starwake.json, written by
// games/starwake/export_go_config.py. Nothing here may invent or default a game
// value -- if a field is missing the load fails, because a silently defaulted
// paytable entry or ladder rung produces a valid-looking pool describing a
// different game, which is the one failure mode this port has to avoid.
//
// Reel STRIPS are not in the JSON. They are read straight from the CSVs in
// games/starwake/reels/ so those files stay the single source of truth and a
// generate_reels.py re-run needs no re-export.
package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// SupportedSchema is the exporter schema this package understands. A bump on the
// Python side without a matching change here must fail loudly rather than
// decode partially.
const SupportedSchema = 1

// Game holds the top-level identity and grid geometry.
type Game struct {
	ID             string `json:"id"`
	Name           string `json:"name"`
	Provider       string `json:"provider"`
	ProviderNumber int    `json:"providerNumber"`
	WinType        string `json:"winType"`
	RTP            float64
	Wincap         float64 `json:"wincap"`
	NumReels       int     `json:"numReels"`
	NumRows        []int   `json:"numRows"`
	IncludePadding bool    `json:"includePadding"`
	BasegameType   string  `json:"basegameType"`
	FreegameType   string  `json:"freegameType"`
}

// UnmarshalJSON is hand-rolled only to catch the RTP field, whose Python name
// differs from the Go convention the rest of the struct follows.
func (g *Game) UnmarshalJSON(b []byte) error {
	type alias Game
	aux := struct {
		RTP float64 `json:"rtp"`
		*alias
	}{alias: (*alias)(g)}
	if err := json.Unmarshal(b, &aux); err != nil {
		return err
	}
	g.RTP = aux.RTP
	return nil
}

// PayKey identifies one paytable row: N of a given symbol.
type PayKey struct {
	Kind   int
	Symbol string
}

// PayEntry is the wire form of a paytable row.
type PayEntry struct {
	Kind   int     `json:"kind"`
	Symbol string  `json:"symbol"`
	Value  float64 `json:"value"`
}

// Payline is one line's row index per reel.
type Payline struct {
	Index int   `json:"index"`
	Rows  []int `json:"rows"`
}

// FreespinTrigger maps a scatter count to the spins it awards.
type FreespinTrigger struct {
	Scatters int `json:"scatters"`
	Spins    int `json:"spins"`
}

// ScatterTier maps a scatter count to the constellation tier it deals.
type ScatterTier struct {
	Scatters int    `json:"scatters"`
	Tier     string `json:"tier"`
}

// Cell is a (reel, row) position on the grid.
type Cell struct {
	Reel int
	Row  int
}

// UnmarshalJSON decodes the [reel, row] pair form the exporter writes.
func (c *Cell) UnmarshalJSON(b []byte) error {
	var pair []int
	if err := json.Unmarshal(b, &pair); err != nil {
		return err
	}
	if len(pair) != 2 {
		return fmt.Errorf("cell must be [reel,row], got %d values", len(pair))
	}
	c.Reel, c.Row = pair[0], pair[1]
	return nil
}

// Scatter counts and multiplier values arrive as RECORDS rather than an
// int-keyed map, because JSON object keys are always strings and round-tripping
// them through strconv at load time is a needless failure surface.

// ScatterTriggerWeight decodes {"scatters": N, "weight": W}.
type ScatterTriggerWeight struct {
	Scatters int `json:"scatters"`
	Weight   int `json:"weight"`
}

// MultValueWeight decodes {"value": N, "weight": W}.
type MultValueWeight struct {
	Value  int `json:"value"`
	Weight int `json:"weight"`
}

// Conditions constrain how one distribution's boards are drawn.
type Conditions struct {
	ReelWeights     map[string]map[string]int    `json:"reelWeights"`
	ScatterTriggers []ScatterTriggerWeight       `json:"scatterTriggers"`
	MultValues      map[string][]MultValueWeight `json:"multValues"`
	ForceWincap     bool                         `json:"forceWincap"`
	ForceFreegame   bool                         `json:"forceFreegame"`
	// ForceAscension pins a tier's rare star-table switch ON for this slice.
	//
	// WHY A SLICE NEEDS IT. A wincap slice reaches its ceiling by redrawing until
	// the payout matches winCriteria, with no retry cap. Corvus's 25,000x is only
	// reachable in an ascended round, and ascension is deliberately rare (1 in
	// ~20,000), so an unforced slice would redraw through ~20,000 ordinary rounds
	// per candidate -- the hang this whole mechanic exists to avoid. Forcing it
	// makes cap books cheap to manufacture WITHOUT touching the natural rate,
	// which is what keeps the advertised max-win frequency a dial we set via the
	// slice's rtp share rather than a side effect of the ascension rate.
	ForceAscension bool `json:"forceAscension"`
	// Wake deals the constellation ALREADY COMPLETE and wakes the beast before
	// spin 1, turning the feature into a single roam spin. It is what makes
	// buy_mystery_spin a one-spin product (Miko Spin / Rage Spins shape) without
	// a tier, a strip or a scatter count of its own.
	//
	// WHY A CONDITION AND NOT A TIER. Wake variants keyed at scatter counts 7-10
	// are unreachable: a forced draw places at most one scatter per reel, so a 6th
	// already needs a reel window revealing two and a 7th needs two such reels.
	// In Python an unreachable forced count hangs forever rather than failing.
	// Riding the slice keeps the trigger board ordinary -- 3, 4 or 5 stars.
	Wake bool `json:"wake"`
	// ForceSeed pins a wake slice's seed to at least the configured floor.
	//
	// A cap book on ONE spin needs three rare things at once: a big line win, a
	// high seed, and a heavy star drop. Measured organic max is 23,072x at 3e6, so
	// a 25,000x slice asks the generator for a better-than-record board every
	// time -- 8.4 MILLION redraws per book. Guaranteeing the seed makes the hunt a
	// much commoner event.
	//
	// GENERATION COST ONLY. The delivered max-win frequency is
	// rate = slice_rtp*cost/cap, an optimizer weight we choose, so this leaves the
	// natural seed distribution and the player-facing rate untouched -- exactly
	// the argument ForceAscension above rests on.
	ForceSeed bool `json:"forceSeed"`
}

// Distribution is one slice of a bet mode's simulated outcomes.
type Distribution struct {
	Criteria string  `json:"criteria"`
	Quota    float64 `json:"quota"`
	// Null for every starwake distribution today; a fixed count rather than a
	// proportion when set.
	FixedAmt *int `json:"fixedAmt"`
	// Null unless the slice only accepts books paying exactly this much -- the
	// mechanism behind the forced wincap slices.
	WinCriteria *float64   `json:"winCriteria"`
	Conditions  Conditions `json:"conditions"`
}

// BetMode is one purchasable (or base) mode.
type BetMode struct {
	Name string  `json:"name"`
	Cost float64 `json:"cost"`
	RTP  float64 `json:"rtp"`
	// MaxWin is BOTH the published ceiling and the engine clamp for this mode.
	// Never clamp on Game.Wincap: buy_corvus publishes an honest 10,000x and
	// must be clamped there, not at the global 25,000x.
	MaxWin            float64        `json:"maxWin"`
	AutoCloseDisabled bool           `json:"autoCloseDisabled"`
	IsFeature         bool           `json:"isFeature"`
	IsBuyBonus        bool           `json:"isBuyBonus"`
	Distributions     []Distribution `json:"distributions"`
}

// Strip is one reel set: Strip[reel] is that reel's symbol sequence.
type Strip [][]string

// Config is the whole game definition plus the derived lookups the hot loop wants.
type Config struct {
	SchemaVersion        int                          `json:"schemaVersion"`
	GeneratedBy          string                       `json:"generatedBy"`
	Game                 Game                         `json:"game"`
	Paytable             []PayEntry                   `json:"paytable"`
	Paylines             []Payline                    `json:"paylines"`
	SpecialSymbols       map[string][]string          `json:"specialSymbols"`
	Reels                map[string]string            `json:"reels"`
	ReelsDir             string                       `json:"reelsDir"`
	AnticipationTriggers map[string]int               `json:"anticipationTriggers"`
	FreespinTriggers     map[string][]FreespinTrigger `json:"freespinTriggers"`
	ScatterTiers         []ScatterTier                `json:"scatterTiers"`
	BetModes             []BetMode                    `json:"betModes"`

	// GameSpecific is the owning game's own feature block, left UNDECODED here.
	//
	// This package is the game-agnostic SDK: it knows about reels, paylines,
	// paytables, bet modes and distributions, which every lines game has. It must
	// not know what a constellation is -- or a vault, or a cascade. The game
	// decodes this itself (see internal/game/starwake), which is what keeps a
	// second game from inheriting the first one's vocabulary.
	GameSpecific json.RawMessage `json:"gameSpecific"`

	// ---- derived at load; not present in the JSON ----

	// Pay resolves a (kind, symbol) to its per-line payout. The hot loop hits
	// this twice per payline per spin, so it is a map rather than a scan.
	Pay map[PayKey]float64
	// TierByScatter is the count -> tier mapping the engine reads on a trigger.
	TierByScatter map[int]string
	// SpinsByScatter[gametype][count] is the awarded feature length.
	SpinsByScatter map[string]map[int]int
	// Strips holds every reel set named in Reels, keyed by its id (BR0, FR0...).
	Strips map[string]Strip
	// IsWild / IsScatter answer the two attribute questions the line evaluator
	// asks per cell. Python did this with getattr plus a set lookup; a map hit
	// on an interned symbol name is already far cheaper, and the engine will
	// lower these to a bitfield on the Symbol struct.
	IsWild    map[string]bool
	IsScatter map[string]bool

	modeByName map[string]*BetMode
}

// Load reads the exported config and every reel strip it names.
//
// repoRoot anchors ReelsDir, which is repo-relative so the same config file works
// regardless of the working directory the engine is launched from.
func Load(configPath, repoRoot string) (*Config, error) {
	raw, err := os.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("read config: %w", err)
	}

	var c Config
	dec := json.NewDecoder(strings.NewReader(string(raw)))
	// An unknown field means the exporter has moved ahead of the engine. Fail
	// rather than decode a partial game.
	dec.DisallowUnknownFields()
	if err := dec.Decode(&c); err != nil {
		return nil, fmt.Errorf("decode config: %w", err)
	}

	if c.SchemaVersion != SupportedSchema {
		return nil, fmt.Errorf(
			"config schema v%d but this engine supports v%d -- re-run export_go_config.py "+
				"or update the Go decoder", c.SchemaVersion, SupportedSchema)
	}

	c.derive()
	if err := c.loadStrips(repoRoot); err != nil {
		return nil, err
	}
	if err := c.Validate(); err != nil {
		return nil, fmt.Errorf("config invalid: %w", err)
	}
	return &c, nil
}

// derive builds the lookup tables the hot loop uses.
func (c *Config) derive() {
	c.Pay = make(map[PayKey]float64, len(c.Paytable))
	for _, p := range c.Paytable {
		c.Pay[PayKey{Kind: p.Kind, Symbol: p.Symbol}] = p.Value
	}

	c.TierByScatter = make(map[int]string, len(c.ScatterTiers))
	for _, s := range c.ScatterTiers {
		c.TierByScatter[s.Scatters] = s.Tier
	}

	c.SpinsByScatter = make(map[string]map[int]int, len(c.FreespinTriggers))
	for gametype, triggers := range c.FreespinTriggers {
		m := make(map[int]int, len(triggers))
		for _, t := range triggers {
			m[t.Scatters] = t.Spins
		}
		c.SpinsByScatter[gametype] = m
	}

	c.IsWild = make(map[string]bool)
	c.IsScatter = make(map[string]bool)
	for _, s := range c.SpecialSymbols["wild"] {
		c.IsWild[s] = true
	}
	for _, s := range c.SpecialSymbols["scatter"] {
		c.IsScatter[s] = true
	}

	c.modeByName = make(map[string]*BetMode, len(c.BetModes))
	for i := range c.BetModes {
		c.modeByName[c.BetModes[i].Name] = &c.BetModes[i]
	}
}

// loadStrips reads every named reel CSV.
func (c *Config) loadStrips(repoRoot string) error {
	c.Strips = make(map[string]Strip, len(c.Reels))
	for id, filename := range c.Reels {
		path := filepath.Join(repoRoot, filepath.FromSlash(c.ReelsDir), filename)
		strip, err := ReadStripCSV(path, c.Game.NumReels)
		if err != nil {
			return fmt.Errorf("reel strip %q: %w", id, err)
		}
		c.Strips[id] = strip
	}
	return nil
}

// Mode returns a bet mode by name.
func (c *Config) Mode(name string) (*BetMode, error) {
	m, ok := c.modeByName[name]
	if !ok {
		names := make([]string, 0, len(c.modeByName))
		for n := range c.modeByName {
			names = append(names, n)
		}
		return nil, fmt.Errorf("unknown bet mode %q (have %s)", name, strings.Join(names, ", "))
	}
	return m, nil
}

// Rows returns the row count for a reel. Starwake is uniform (4 everywhere) but
// the SDK models it per reel, so the engine asks rather than assumes.
func (c *Config) Rows(reel int) int { return c.Game.NumRows[reel] }

// Validate re-checks the invariants the Python exporter also enforces.
//
// Deliberately duplicated across the seam: the exporter guards against a bad
// config, this guards against a bad decode. They fail for different reasons and
// both failures are silent in a pool.
func (c *Config) Validate() error {
	if c.Game.NumReels != len(c.Game.NumRows) {
		return fmt.Errorf("numReels %d but %d row entries", c.Game.NumReels, len(c.Game.NumRows))
	}
	if len(c.Paylines) == 0 {
		return fmt.Errorf("no paylines")
	}
	for _, l := range c.Paylines {
		if len(l.Rows) != c.Game.NumReels {
			return fmt.Errorf("payline %d covers %d reels, want %d", l.Index, len(l.Rows), c.Game.NumReels)
		}
		for reel, row := range l.Rows {
			if row < 0 || row >= c.Rows(reel) {
				return fmt.Errorf("payline %d: row %d off reel %d", l.Index, row, reel)
			}
		}
	}

	for _, m := range c.BetModes {
		if len(m.Distributions) == 0 {
			return fmt.Errorf("bet mode %s has no distributions", m.Name)
		}
		if m.MaxWin <= 0 {
			return fmt.Errorf("bet mode %s has maxWin %v", m.Name, m.MaxWin)
		}
		for _, d := range m.Distributions {
			if d.Conditions.ReelWeights == nil {
				return fmt.Errorf("%s/%s: no reel weights", m.Name, d.Criteria)
			}
			for gametype, weights := range d.Conditions.ReelWeights {
				for id := range weights {
					if _, ok := c.Strips[id]; !ok {
						return fmt.Errorf("%s/%s/%s: unknown reel strip %q",
							m.Name, d.Criteria, gametype, id)
					}
				}
			}
			for _, st := range d.Conditions.ScatterTriggers {
				if _, ok := c.TierByScatter[st.Scatters]; !ok {
					return fmt.Errorf("%s/%s: %d scatters maps to no tier",
						m.Name, d.Criteria, st.Scatters)
				}
			}
		}
	}
	return nil
}
