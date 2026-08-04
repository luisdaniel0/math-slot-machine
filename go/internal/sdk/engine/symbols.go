// Package engine is the game-agnostic hot loop: symbols, board draws, line
// evaluation and per-spin state. Nothing here knows about any specific game.
//
// EVERYTHING IN THIS PACKAGE IS BUILT AROUND ONE FACT: this code runs billions of
// times. A 1e6-book pool of 15-spin features evaluates 20 paylines x 5 reels on
// every spin, so a per-cell operation happens on the order of 1e9 times per mode.
// The Python original spends most of its time there, doing a getattr plus a set
// lookup per cell (Symbol.check_attribute in src/calculations/symbol.py) and a
// tuple-keyed dict hash per paytable probe.
//
// So symbols are INTERNED TO A uint8 ID at config load, and every per-symbol
// question becomes an array index:
//
//	name lookup   map[string]Symbol   ->  []string indexed by SymID
//	is it wild?   getattr + set probe ->  []bool indexed by SymID
//	paytable      map[(kind,name)]    ->  [kind][symID] float64
//
// That trade -- do the string work once at load, never in the loop -- is the
// single largest source of the speedup, ahead of concurrency.
package engine

import (
	"fmt"

	"starwake/internal/sdk/config"
)

// SymID is a symbol interned to a small integer. Valid IDs start at 1; 0 is
// reserved so a zero-valued Cell is recognisably empty rather than silently
// being the first symbol in the table.
type SymID uint8

// NoSym is the zero value: an unset board cell.
const NoSym SymID = 0

// maxSymbols bounds the interning table. uint8 IDs cap it at 255 anyway; slot 0
// is reserved.
const maxSymbols = 256

// SymbolTable interns every symbol name and answers per-symbol questions by
// array index. Built once at load, then read-only -- so it is safe to share
// across every worker goroutine without copying or locking.
type SymbolTable struct {
	names   []string         // SymID -> name; names[0] is ""
	ids     map[string]SymID // name -> SymID. LOAD TIME ONLY, never in the loop.
	wild    []bool
	scatter []bool

	// pay[kind][sym] is the per-line payout, 0 when that combination does not
	// pay. Indexed rather than hashed: the line evaluator probes it twice per
	// payline per spin.
	pay     [][]float64
	maxKind int
}

// NewSymbolTable interns every symbol named anywhere in the config: on a reel
// strip, in the paytable, or in the special-symbol lists.
//
// It deliberately gathers from all three rather than trusting one. A symbol that
// appears on a strip but not in the paytable is legal (it simply never pays), and
// one in special_symbols but on no strip is a config error worth surfacing early
// rather than as a mysteriously absent wild.
func NewSymbolTable(c *config.Config) (*SymbolTable, error) {
	st := &SymbolTable{
		names:   []string{""},
		ids:     make(map[string]SymID),
		wild:    make([]bool, 1),
		scatter: make([]bool, 1),
	}

	intern := func(name string) (SymID, error) {
		if name == "" {
			return NoSym, fmt.Errorf("empty symbol name")
		}
		if id, ok := st.ids[name]; ok {
			return id, nil
		}
		if len(st.names) >= maxSymbols {
			return NoSym, fmt.Errorf("more than %d distinct symbols", maxSymbols-1)
		}
		id := SymID(len(st.names))
		st.names = append(st.names, name)
		st.wild = append(st.wild, false)
		st.scatter = append(st.scatter, false)
		st.ids[name] = id
		return id, nil
	}

	// Strips first, so the common symbols land on the lowest IDs.
	for _, strip := range c.Strips {
		for reel := range strip {
			for _, name := range strip[reel] {
				if _, err := intern(name); err != nil {
					return nil, err
				}
			}
		}
	}
	for _, p := range c.Paytable {
		if _, err := intern(p.Symbol); err != nil {
			return nil, err
		}
		if p.Kind > st.maxKind {
			st.maxKind = p.Kind
		}
	}
	for _, names := range c.SpecialSymbols {
		for _, name := range names {
			if _, err := intern(name); err != nil {
				return nil, err
			}
		}
	}

	for _, name := range c.SpecialSymbols["wild"] {
		st.wild[st.ids[name]] = true
	}
	for _, name := range c.SpecialSymbols["scatter"] {
		st.scatter[st.ids[name]] = true
	}

	st.pay = make([][]float64, st.maxKind+1)
	for kind := range st.pay {
		st.pay[kind] = make([]float64, len(st.names))
	}
	for _, p := range c.Paytable {
		st.pay[p.Kind][st.ids[p.Symbol]] = p.Value
	}

	return st, nil
}

// ID resolves a symbol name. Load-time only -- the hot loop already holds IDs.
func (st *SymbolTable) ID(name string) (SymID, error) {
	id, ok := st.ids[name]
	if !ok {
		return NoSym, fmt.Errorf("symbol %q is not registered", name)
	}
	return id, nil
}

// MustID is ID for setup paths where an unknown symbol is a programming error.
func (st *SymbolTable) MustID(name string) SymID {
	id, err := st.ID(name)
	if err != nil {
		panic(err)
	}
	return id
}

// Name returns a symbol's display name (events, force records, debugging).
func (st *SymbolTable) Name(id SymID) string { return st.names[id] }

// Count is the number of interned symbols, excluding the reserved zero slot.
func (st *SymbolTable) Count() int { return len(st.names) - 1 }

// IsWild reports whether a symbol substitutes. Single array index.
func (st *SymbolTable) IsWild(id SymID) bool { return st.wild[id] }

// IsScatter reports whether a symbol counts toward a trigger. Single array index.
func (st *SymbolTable) IsScatter(id SymID) bool { return st.scatter[id] }

// Pay returns the per-line payout for `kind` of `id`, or 0 if that does not pay.
//
// Out-of-range kinds return 0 rather than panicking: the line evaluator counts
// matches before it knows whether the run is payable, and a 1- or 2-of-a-kind is
// an ordinary non-win, not an error.
func (st *SymbolTable) Pay(kind int, id SymID) float64 {
	if kind < 0 || kind > st.maxKind {
		return 0
	}
	return st.pay[kind][id]
}

// MaxKind is the longest paying combination in the paytable.
func (st *SymbolTable) MaxKind() int { return st.maxKind }

// Strip is a reel set with symbols already interned to IDs.
//
// Interning the strips once at load is what keeps the draw free of string work:
// a board draw copies uint8s out of these slices.
type Strip [][]SymID

// InternStrips converts every configured reel strip into ID form.
func (st *SymbolTable) InternStrips(c *config.Config) (map[string]Strip, error) {
	out := make(map[string]Strip, len(c.Strips))
	for id, strip := range c.Strips {
		interned := make(Strip, len(strip))
		for reel := range strip {
			interned[reel] = make([]SymID, len(strip[reel]))
			for pos, name := range strip[reel] {
				symID, err := st.ID(name)
				if err != nil {
					return nil, fmt.Errorf("strip %s reel %d pos %d: %w", id, reel, pos, err)
				}
				interned[reel][pos] = symID
			}
		}
		out[id] = interned
	}
	return out, nil
}
