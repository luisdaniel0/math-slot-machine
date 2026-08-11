package sim

import (
	"testing"

	"starwake/internal/sdk/config"
)

func mode(name string, quotas ...float64) *config.BetMode {
	m := &config.BetMode{Name: name, Cost: 1}
	for i, q := range quotas {
		m.Distributions = append(m.Distributions, config.Distribution{
			Criteria: string(rune('a' + i)),
			Quota:    q,
		})
	}
	return m
}

// A run smaller than the distribution count must ERROR, not spin forever.
//
// REGRESSION. Every distribution is seeded with at least one sim and the trim
// loop only ever decrements a count that is above 1, so with fewer sims than
// distributions there is nothing it is allowed to take -- `for total > numSims`
// could never make progress and never exited. `starwake -mode base -sims 3` hung
// indefinitely with no output.
//
// This is the same failure shape the port set out to remove from Python's
// force_special_board: an unbounded loop that cannot reach its own exit
// condition, which presents as a run that simply never finishes.
func TestFewerSimsThanDistributionsErrorsInsteadOfHanging(t *testing.T) {
	m := mode("base", 0.001, 0.007, 0.025, 0.067, 0.5, 0.4)

	for _, n := range []int{1, 3, 5} {
		if _, err := AssignCriteria(m, n, 1); err == nil {
			t.Errorf("AssignCriteria(%d sims, %d distributions) returned no error; "+
				"it cannot satisfy every distribution and must say so",
				n, len(m.Distributions))
		}
	}
}

// The boundary and above must still work, and must hand back exactly numSims
// assignments with every distribution represented.
func TestAssignCriteriaCoversEveryDistribution(t *testing.T) {
	m := mode("base", 0.001, 0.007, 0.025, 0.067, 0.5, 0.4)

	for _, n := range []int{6, 7, 100, 20000} {
		a, err := AssignCriteria(m, n, 1)
		if err != nil {
			t.Fatalf("%d sims: %v", n, err)
		}
		if len(a.Criteria) != n || len(a.Seeds) != n {
			t.Fatalf("%d sims: got %d criteria and %d seeds",
				n, len(a.Criteria), len(a.Seeds))
		}
		seen := map[string]int{}
		for _, c := range a.Criteria {
			seen[c]++
		}
		for _, d := range m.Distributions {
			if seen[d.Criteria] == 0 {
				t.Errorf("%d sims: distribution %q got no books", n, d.Criteria)
			}
		}
	}
}

// Quotas are RELATIVE WEIGHTS, not probabilities: ante_starfall's legitimately
// sum to 0.9615, and treating that as a probability would under-fill the mode.
func TestQuotasSummingUnderOneStillFillTheRun(t *testing.T) {
	m := mode("ante_starfall", 0.0015, 0.0156, 0.0468, 0.1039, 0.5201, 0.2736)

	a, err := AssignCriteria(m, 50000, 1)
	if err != nil {
		t.Fatalf("assign: %v", err)
	}
	if len(a.Criteria) != 50000 {
		t.Fatalf("got %d assignments, want 50000", len(a.Criteria))
	}
}
