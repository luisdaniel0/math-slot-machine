package engine

import (
	"math/rand/v2"
	"sort"
)

// RNG is one simulation's random stream.
//
// PARITY BAR: statistical, not bit-exact. Reproducing CPython's Mersenne Twister
// plus the exact semantics of randrange (_randbelow rejection sampling), choices
// (bisect over cumulative weights) and shuffle would be a wide surface of subtle
// failure for zero benefit -- Stake never receives the generator, only the books
// and weights it produced (docs/rgs_docs/data_format.md). What must match is the
// DISTRIBUTION, and that is what the parity harness checks.
//
// PCG is used over the older LCG-based generators because it is measurably
// faster per draw and has better statistical properties; at ~1e9 draws per mode
// both matter.
type RNG struct {
	r *rand.Rand
}

// NewRNG creates a stream for one simulation.
//
// Each simulation gets its own seed so a book is reproducible in isolation --
// that is what lets a single suspicious book be re-run and inspected without
// regenerating the pool.
func NewRNG(seed uint64) *RNG {
	// Two distinct stream constants: PCG takes a state and a sequence selector,
	// and giving every sim the same sequence would correlate their streams.
	return &RNG{r: rand.New(rand.NewPCG(seed, seed^0x9e3779b97f4a7c15))}
}

// IntN returns a uniform value in [0,n). Panics on n <= 0, matching the standard
// library, because a zero-length range is always a caller bug here.
func (g *RNG) IntN(n int) int { return g.r.IntN(n) }

// Float64 returns a uniform value in [0,1).
func (g *RNG) Float64() float64 { return g.r.Float64() }

// Shuffle permutes n elements via the swap callback.
func (g *RNG) Shuffle(n int, swap func(i, j int)) { g.r.Shuffle(n, swap) }

// WeightedStrings picks a string outcome by weight.
//
// ⚠ THE ORDER IS THE POINT. The Python original walks a dict, but Go RANDOMISES
// map iteration order, so picking straight from a map would make the same RNG
// draw select different outcomes between runs -- a non-reproducible pool that
// still looks statistically fine. Keys are sorted once at construction and the
// cumulative weights are frozen, so a given seed always yields a given outcome.
type WeightedStrings struct {
	values []string
	cum    []int
	total  int
}

// NewWeightedStrings builds a stable picker from an outcome -> weight map.
func NewWeightedStrings(weights map[string]int) *WeightedStrings {
	w := &WeightedStrings{}
	keys := make([]string, 0, len(weights))
	for k := range weights {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		if weights[k] <= 0 {
			continue // a zero weight is "not an option", not an error
		}
		w.total += weights[k]
		w.values = append(w.values, k)
		w.cum = append(w.cum, w.total)
	}
	return w
}

// Len is the number of selectable outcomes.
func (w *WeightedStrings) Len() int { return len(w.values) }

// Only returns the single outcome when there is exactly one, which is the common
// case here (most distributions pin one reel strip). Lets callers skip the draw
// entirely and keeps the RNG stream from advancing on a forced choice.
func (w *WeightedStrings) Only() (string, bool) {
	if len(w.values) == 1 {
		return w.values[0], true
	}
	return "", false
}

// Pick selects an outcome. Linear scan: these sets have a handful of entries, so
// a scan beats a binary search's branching.
func (w *WeightedStrings) Pick(g *RNG) string {
	if len(w.values) == 1 {
		return w.values[0]
	}
	target := g.IntN(w.total)
	for i, c := range w.cum {
		if target < c {
			return w.values[i]
		}
	}
	return w.values[len(w.values)-1] // unreachable while total > 0
}

// WeightedInts picks an integer outcome by weight -- scatter counts to force,
// multiplier values to award. Sorted and frozen for the same reason as
// WeightedStrings.
type WeightedInts struct {
	values []int
	cum    []int
	total  int
}

// NewWeightedInts builds a stable picker from a value -> weight map.
func NewWeightedInts(weights map[int]int) *WeightedInts {
	w := &WeightedInts{}
	keys := make([]int, 0, len(weights))
	for k := range weights {
		keys = append(keys, k)
	}
	sort.Ints(keys)
	for _, k := range keys {
		if weights[k] <= 0 {
			continue
		}
		w.total += weights[k]
		w.values = append(w.values, k)
		w.cum = append(w.cum, w.total)
	}
	return w
}

// Len is the number of selectable outcomes.
func (w *WeightedInts) Len() int { return len(w.values) }

// Pick selects an outcome.
func (w *WeightedInts) Pick(g *RNG) int {
	if len(w.values) == 1 {
		return w.values[0]
	}
	target := g.IntN(w.total)
	for i, c := range w.cum {
		if target < c {
			return w.values[i]
		}
	}
	return w.values[len(w.values)-1]
}

// Values exposes the selectable outcomes, for validation and tests.
func (w *WeightedInts) Values() []int { return w.values }
