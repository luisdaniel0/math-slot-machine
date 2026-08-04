package sim

import (
	"fmt"
	"math/rand/v2"
	"sort"

	"starwake/internal/sdk/config"
)

// Assignment maps every simulation index to the distribution criteria it must
// satisfy, and to its RNG seed.
type Assignment struct {
	Criteria []string
	Seeds    []uint64
}

// AssignCriteria allocates sims across a mode's distributions.
//
// Port of get_sim_splits + assign_sim_criteria (src/state/run_sims.py).
//
// ⚠ QUOTAS ARE RELATIVE WEIGHTS, NOT PROBABILITIES. Python seeds each criteria
// with int(num_sims * quota) and then tops up or trims by weighted random choice
// until the total matches exactly -- so a quota set summing to anything positive
// is normalised. ante_starfall legitimately sums to 0.9615, and treating that as
// a probability would silently under-fill the mode.
func AssignCriteria(mode *config.BetMode, numSims int, seed uint64) (*Assignment, error) {
	for _, d := range mode.Distributions {
		if d.FixedAmt != nil {
			return nil, fmt.Errorf("%s/%s: fixedAmt distributions are not supported yet",
				mode.Name, d.Criteria)
		}
	}

	// Every distribution is seeded with at least one sim, so a run smaller than the
	// distribution count can never be trimmed down to numSims -- the trim loop
	// below would spin forever looking for a count it is allowed to decrement.
	// Fail loudly instead: a bare unbounded loop that cannot make progress is the
	// exact shape this port set out to remove from force_special_board.
	if numSims < len(mode.Distributions) {
		return nil, fmt.Errorf(
			"%s: %d sims for %d distributions -- each distribution needs at least one book",
			mode.Name, numSims, len(mode.Distributions))
	}

	counts := make(map[string]int, len(mode.Distributions))
	names := make([]string, 0, len(mode.Distributions))
	weights := make([]float64, 0, len(mode.Distributions))
	total := 0
	for _, d := range mode.Distributions {
		n := int(float64(numSims) * d.Quota)
		if n < 1 {
			n = 1
		}
		counts[d.Criteria] = n
		total += n
		names = append(names, d.Criteria)
		weights = append(weights, d.Quota)
	}

	// Deterministic top-up/trim. Python seeds this at 0; we use our own stream but
	// the same weighted-choice shape, since only the resulting proportions matter.
	g := rand.New(rand.NewPCG(seed, 0x5851f42d4c957f2d))
	pick := func() string {
		var sum float64
		for _, w := range weights {
			sum += w
		}
		t := g.Float64() * sum
		var acc float64
		for i, w := range weights {
			acc += w
			if t < acc {
				return names[i]
			}
		}
		return names[len(names)-1]
	}
	for total > numSims {
		c := pick()
		if counts[c] > 1 {
			counts[c]--
			total--
		}
	}
	for total < numSims {
		counts[pick()]++
		total++
	}

	// Build and shuffle the assignment so criteria are interleaved rather than
	// blocked -- workers then see a representative mix, which keeps their
	// runtimes even.
	list := make([]string, 0, numSims)
	ordered := append([]string(nil), names...)
	sort.Strings(ordered)
	for _, c := range ordered {
		for i := 0; i < counts[c]; i++ {
			list = append(list, c)
		}
	}
	g.Shuffle(len(list), func(i, j int) { list[i], list[j] = list[j], list[i] })

	// One seed per simulation, so any single book is reproducible in isolation --
	// that is what lets a suspicious book be re-run without regenerating the pool.
	seeds := make([]uint64, numSims)
	for i := range seeds {
		seeds[i] = uint64(i) + 1
	}
	return &Assignment{Criteria: list, Seeds: seeds}, nil
}

// Stats summarises a completed run.
//
// Carries the MEASURE-LOOP numbers (completion rate, median, >cost, mean roam,
// top rung) as well as the totals, so tuning needs exactly one command and no
// second pass over the compressed books. These are the columns the Python
// measure_tiers.py harness printed.
type Stats struct {
	Books        int
	TotalWin     float64
	BaseWin      float64
	FreeWin      float64
	Cost         float64
	MaxPayout    float64
	ZeroBooks    int
	Repeats      int
	CriteriaHits map[string]int

	// ---- MEASURE-LOOP metrics, over books EXCLUDING the forced wincap slice ----
	//
	// ⚠ THE WINCAP SLICE IS A SAMPLING QUOTA, NOT A PROBABILITY. It plants a fixed
	// lump of max-win books in the pool so the optimizer has some to weight; it
	// does NOT describe how often the cap is hit. Leaving it in the mean prices a
	// mode off a pool that is about to be re-weighted -- buy_draco reads 742x
	// with it and 495x without, and 495x is the real number. Every Python
	// measure/sweep harness strips it for the same reason.
	MeasureBooks int
	Features     int
	Completed    int
	RoamTotal    int
	TopRung      int
	OverCost     int
	MeasureWin   float64
	Payouts      []float64 // for the median; ~8 MB at 1e6, worth it

	// CapHits is over ALL books, since "how often does this pool sit at the
	// ceiling" is a property of the pool as generated.
	CapHits int
}

// RTP is the measured return to player.
func (s *Stats) RTP() float64 {
	if s.Books == 0 || s.Cost == 0 {
		return 0
	}
	return s.TotalWin / (float64(s.Books) * s.Cost)
}

// ZeroRate is the share of books paying nothing.
func (s *Stats) ZeroRate() float64 {
	if s.Books == 0 {
		return 0
	}
	return float64(s.ZeroBooks) / float64(s.Books)
}

// Merge folds a worker's stats into the total.
func (s *Stats) Merge(o *Stats) {
	s.Books += o.Books
	s.TotalWin += o.TotalWin
	s.BaseWin += o.BaseWin
	s.FreeWin += o.FreeWin
	s.ZeroBooks += o.ZeroBooks
	s.Repeats += o.Repeats
	s.MeasureBooks += o.MeasureBooks
	s.MeasureWin += o.MeasureWin
	s.Features += o.Features
	s.Completed += o.Completed
	s.RoamTotal += o.RoamTotal
	s.OverCost += o.OverCost
	s.CapHits += o.CapHits
	s.Payouts = append(s.Payouts, o.Payouts...)
	if o.MaxPayout > s.MaxPayout {
		s.MaxPayout = o.MaxPayout
	}
	if o.TopRung > s.TopRung {
		s.TopRung = o.TopRung
	}
	if s.CriteriaHits == nil {
		s.CriteriaHits = map[string]int{}
	}
	for k, v := range o.CriteriaHits {
		s.CriteriaHits[k] += v
	}
}

// Completion is the share of dealt constellations that woke their beast.
func (s *Stats) Completion() float64 {
	if s.Features == 0 {
		return 0
	}
	return 100 * float64(s.Completed) / float64(s.Features)
}

// MeanRoam is the average number of roam spins on a completed feature.
func (s *Stats) MeanRoam() float64 {
	if s.Completed == 0 {
		return 0
	}
	return float64(s.RoamTotal) / float64(s.Completed)
}

// OverCostRate is the share of books returning more than the ticket price,
// excluding the wincap slice.
func (s *Stats) OverCostRate() float64 {
	if s.MeasureBooks == 0 {
		return 0
	}
	return 100 * float64(s.OverCost) / float64(s.MeasureBooks)
}

// Median payout, excluding the wincap slice. Sorts in place -- called once.
func (s *Stats) Median() float64 {
	if len(s.Payouts) == 0 {
		return 0
	}
	sort.Float64s(s.Payouts)
	return s.Payouts[len(s.Payouts)/2]
}

// Mean payout, excluding the wincap slice. THIS is the number a buy's price is
// derived from (cost = mean / rtp), never the raw pool mean.
func (s *Stats) Mean() float64 {
	if s.MeasureBooks == 0 {
		return 0
	}
	return s.MeasureWin / float64(s.MeasureBooks)
}

// Stripped reports whether a wincap slice was excluded from the measure columns.
func (s *Stats) Stripped() int { return s.Books - s.MeasureBooks }
