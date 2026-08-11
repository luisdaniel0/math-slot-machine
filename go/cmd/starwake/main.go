// Command starwake runs Starwake simulations and writes the published artifacts.
//
//	starwake -mode base -sims 1000000
//
// Writes to go/out/library/ by design -- NEVER into games/starwake/library/,
// which holds the converged production pool.
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"time"

	"starwake/internal/game/starwake"
	"starwake/internal/sdk/config"
	"starwake/internal/sdk/sim"
)

func main() {
	var (
		modeName = flag.String("mode", "base", "bet mode to simulate")
		numSims  = flag.Int("sims", 100000, "number of books")
		workers  = flag.Int("workers", runtime.NumCPU(), "parallel workers")
		outDir   = flag.String("out", "", "output root (default go/out/library)")
		cfgPath  = flag.String("config", "", "config json (default go/config/starwake.json)")
		repoRoot = flag.String("repo", "", "repo root (default: inferred)")
		quiet    = flag.Bool("quiet", false, "suppress the progress summary")
		noWincap = flag.Bool("no-wincap", false,
			"drop forced-wincap slices (measure loop only -- see run())")
	)
	flag.Parse()

	if err := run(*modeName, *numSims, *workers, *outDir, *cfgPath, *repoRoot, *quiet, *noWincap); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}
}

func run(modeName string, numSims, workers int, outDir, cfgPath, repoRoot string, quiet, noWincap bool) error {
	root, err := resolveRoot(repoRoot)
	if err != nil {
		return err
	}
	if cfgPath == "" {
		cfgPath = filepath.Join(root, "go", "config", "starwake.json")
	}
	if outDir == "" {
		outDir = filepath.Join(root, "go", "out", "library")
	}

	cfg, err := config.Load(cfgPath, root)
	if err != nil {
		return err
	}
	feature, err := starwake.LoadFeatureConfig(cfg)
	if err != nil {
		return err
	}
	mode, err := cfg.Mode(modeName)
	if err != nil {
		return err
	}
	// ⚠ MEASURE LOOP ONLY -- a pool built with this flag must never be published.
	//
	// A forced-wincap slice draws until it finds a book paying the mode's ceiling,
	// with no retry cap, so if the ceiling drifts out of structural reach the sim
	// HANGS rather than failing. That is not hypothetical: it is what act two did
	// on its first run, because collected multipliers could not reach 25,000x on
	// first-pass values. Stripping the slice lets a tuning sweep read what the
	// feature pays NATURALLY, which is the number you actually need before deciding
	// whether the ceiling is reachable at all. It also removes the sampling quota
	// that otherwise inflates a mode's raw mean.
	if noWincap {
		kept := mode.Distributions[:0]
		for _, d := range mode.Distributions {
			if d.Criteria != "wincap" {
				kept = append(kept, d)
			}
		}
		if len(kept) == 0 {
			return fmt.Errorf("%s: every distribution is a wincap slice", modeName)
		}
		mode.Distributions = kept
	}
	if workers < 1 {
		workers = 1
	}
	if workers > numSims {
		workers = numSims
	}

	assignment, err := sim.AssignCriteria(mode, numSims, 1)
	if err != nil {
		return err
	}
	layout, err := sim.NewLayout(outDir)
	if err != nil {
		return err
	}

	start := time.Now()

	// Contiguous chunks, one writer per worker. Contiguous rather than striped so
	// each shard file holds a monotonic id range and concatenating the shards in
	// order reproduces a deterministic, id-ordered pool -- which matters because
	// the published artifacts are sha256'd.
	type result struct {
		stats *sim.Stats
		err   error
	}
	results := make([]result, workers)
	shards := make([]string, workers)

	chunk := (numSims + workers - 1) / workers
	var wg sync.WaitGroup
	for w := 0; w < workers; w++ {
		lo := w * chunk
		hi := lo + chunk
		if hi > numSims {
			hi = numSims
		}
		shards[w] = fmt.Sprintf("%s.shard%03d", modeName, w)

		wg.Add(1)
		go func(w, lo, hi int) {
			defer wg.Done()
			st, err := runShard(cfg, feature, mode, layout, shards[w], assignment, lo, hi)
			results[w] = result{stats: st, err: err}
		}(w, lo, hi)
	}
	wg.Wait()

	total := &sim.Stats{Cost: mode.Cost, CriteriaHits: map[string]int{}}
	for w, r := range results {
		if r.err != nil {
			return fmt.Errorf("worker %d: %w", w, r.err)
		}
		total.Merge(r.stats)
	}
	total.Cost = mode.Cost

	if err := sim.MergeShards(layout, modeName, shards); err != nil {
		return fmt.Errorf("merge shards: %w", err)
	}

	elapsed := time.Since(start)
	if !quiet {
		printSummary(modeName, mode, total, elapsed, workers)
	}
	return nil
}

// runShard simulates a contiguous id range on one goroutine.
func runShard(
	cfg *config.Config, feature *starwake.FeatureConfig, mode *config.BetMode,
	layout *sim.Layout, shard string, a *sim.Assignment, lo, hi int,
) (*sim.Stats, error) {
	game, err := starwake.NewGame(cfg, feature)
	if err != nil {
		return nil, err
	}
	writer, err := sim.NewWriter(layout, shard)
	if err != nil {
		return nil, err
	}
	defer writer.Close()

	game.Mode = mode
	stats := &sim.Stats{Cost: mode.Cost, CriteriaHits: map[string]int{}}

	for i := lo; i < hi; i++ {
		criteria := a.Criteria[i]
		dist, err := findDistribution(mode, criteria)
		if err != nil {
			return nil, err
		}
		game.Criteria = criteria
		game.Dist = dist

		if err := game.RunSpin(i, a.Seeds[i]); err != nil {
			return nil, fmt.Errorf("sim %d (%s): %w", i, criteria, err)
		}

		// 0-based, matching Python: make_lookup_tables writes the book's own id
		// field, which is the simulation number.
		if err := writer.Write(i, &game.Book, game.Forced, mode.MaxWin); err != nil {
			return nil, err
		}

		payout := game.Book.PayoutMultiplier
		stats.Books++
		stats.TotalWin += payout
		stats.BaseWin += game.Book.BasegameWins
		stats.FreeWin += game.Book.FreegameWins
		stats.Repeats += game.RepeatCount
		stats.CriteriaHits[criteria]++
		if payout == 0 {
			stats.ZeroBooks++
		}
		if payout >= mode.MaxWin {
			stats.CapHits++
		}
		if payout > stats.MaxPayout {
			stats.MaxPayout = payout
		}

		// The measure columns EXCLUDE the forced wincap slice -- it is a
		// generation quota, not a probability, and including it prices a mode off
		// a pool the optimizer is about to re-weight.
		if criteria != "wincap" {
			stats.MeasureBooks++
			stats.MeasureWin += payout
			stats.Payouts = append(stats.Payouts, payout)
			if payout > mode.Cost {
				stats.OverCost++
			}
			if dealt, completed, roam, rung := game.FeatureOutcome(); dealt {
				stats.Features++
				if completed {
					stats.Completed++
					stats.RoamTotal += roam
					if rung > stats.TopRung {
						stats.TopRung = rung
					}
				}
			}
		}
	}
	return stats, writer.Close()
}

func findDistribution(mode *config.BetMode, criteria string) (*config.Distribution, error) {
	for i := range mode.Distributions {
		if mode.Distributions[i].Criteria == criteria {
			return &mode.Distributions[i], nil
		}
	}
	return nil, fmt.Errorf("mode %s has no distribution %q", mode.Name, criteria)
}

// printSummary prints the measure-loop table.
//
// ⚠ THE RAW-POOL RTP IS NOT THE GAME'S RTP and is deliberately not headlined. A
// mode's pool is QUOTA-shaped: base is 40% forced-zero books by construction and
// every mode with a wincap slice carries a fixed lump of max-win books, so the
// raw mean reads wildly high. The player-facing RTP comes from the OPTIMIZED
// lookup table, after `sw optimize`.
func printSummary(name string, mode *config.BetMode, s *sim.Stats, elapsed time.Duration, workers int) {
	fmt.Printf("\n%-14s %s books in %s   (%s books/s, %d workers)\n",
		name, commas(s.Books), elapsed.Round(time.Millisecond),
		commas(int(float64(s.Books)/elapsed.Seconds())), workers)
	note := ""
	if n := s.Stripped(); n > 0 {
		note = fmt.Sprintf("   [measure columns exclude %s wincap-slice books]", commas(n))
	}
	fmt.Printf("  cost %.0fx   ceiling %.0fx%s\n", mode.Cost, mode.MaxWin, note)

	// The tuning columns, matching what measure_tiers.py printed.
	if s.Features > 0 {
		fmt.Printf("  completion  %6.2f%%      mean roam %5.2f      top rung %.0fx\n",
			s.Completion(), s.MeanRoam(), float64(s.TopRung))
	}
	fmt.Printf("  mean        %8.2fx    median %8.2fx   (%.3fx / %.3fx of cost)\n",
		s.Mean(), s.Median(), s.Mean()/mode.Cost, s.Median()/mode.Cost)
	fmt.Printf("  > cost      %6.2f%%      zero pay %6.2f%%     max win %.0fx\n",
		s.OverCostRate(), s.ZeroRate()*100, s.MaxPayout)
	if s.CapHits > 0 {
		fmt.Printf("  at ceiling  %6.4f%%     (1 in %s)\n",
			100*float64(s.CapHits)/float64(s.Books), commas(s.Books/s.CapHits))
	}
	// Implied price, the number buy tuning actually targets: cost = mean / rtp.
	if mode.IsBuyBonus {
		fmt.Printf("  implied price %6.0fx    (mean / rtp; configured %.0fx)\n",
			s.Mean()/mode.RTP, mode.Cost)
	}
	fmt.Printf("  raw pool    RTP %.4f  redraws %.2f/book   (raw pool is quota-shaped -- "+
		"real RTP comes from the optimizer)\n",
		s.RTP(), float64(s.Repeats)/float64(maxi(s.Books, 1)))
	fmt.Printf("  criteria   ")
	for _, d := range mode.Distributions {
		fmt.Printf(" %s=%s", d.Criteria, commas(s.CriteriaHits[d.Criteria]))
	}
	fmt.Println()
}

// commas formats an integer with thousands separators.
func commas(n int) string {
	s := fmt.Sprintf("%d", n)
	if len(s) <= 3 {
		return s
	}
	var out []byte
	for i, c := range []byte(s) {
		if i > 0 && (len(s)-i)%3 == 0 {
			out = append(out, ',')
		}
		out = append(out, c)
	}
	return string(out)
}

func maxi(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// resolveRoot finds the repo root by walking up for go.mod's parent.
func resolveRoot(override string) (string, error) {
	if override != "" {
		return filepath.Abs(override)
	}
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for i := 0; i < 8; i++ {
		if _, err := os.Stat(filepath.Join(dir, "go", "config", "starwake.json")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "", fmt.Errorf("could not locate repo root (pass -repo)")
}
