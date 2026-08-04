package config

import (
	"bufio"
	"fmt"
	"os"
	"strings"
	"unicode"
)

// ReadStripCSV loads one reel set from the CSV layout the SDK uses.
//
// The file is COLUMN-PER-REEL: each line holds one symbol for every reel, so
// line r of column i is position r on reel i. Returned as Strip[reel][position].
//
// This mirrors Config.read_reels_csv in src/config/config.py exactly, including
// its scrubbing rule -- keep only alphanumeric characters in each cell. That rule
// is what lets the CSVs survive stray whitespace and BOM/CR bytes from being
// edited on Windows, which matters here because these files are edited across the
// WSL boundary. Diverging from it would silently shift symbols on a reel.
func ReadStripCSV(path string, numReels int) (Strip, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	strip := make(Strip, numReels)
	scanner := bufio.NewScanner(f)
	line := 0
	for scanner.Scan() {
		text := strings.TrimRight(scanner.Text(), "\r\n")
		if strings.TrimSpace(text) == "" {
			continue // tolerate a trailing newline
		}
		line++

		cells := strings.Split(text, ",")
		if len(cells) != numReels {
			return nil, fmt.Errorf("%s line %d: %d columns, want %d", path, line, len(cells), numReels)
		}
		for reel, cell := range cells {
			sym := keepAlnum(cell)
			if sym == "" {
				return nil, fmt.Errorf("%s line %d reel %d: empty symbol", path, line, reel)
			}
			strip[reel] = append(strip[reel], sym)
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	if line == 0 {
		return nil, fmt.Errorf("%s: no rows", path)
	}
	return strip, nil
}

// keepAlnum strips everything that is not a letter or digit, matching the
// Python reader's per-cell filter.
func keepAlnum(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// Len returns the number of stops on a reel.
func (s Strip) Len(reel int) int { return len(s[reel]) }

// SymbolCounts tallies every symbol on a reel. Used by tests and by the parity
// harness to confirm Go is reading the same strips Python does.
func (s Strip) SymbolCounts(reel int) map[string]int {
	counts := make(map[string]int)
	for _, sym := range s[reel] {
		counts[sym]++
	}
	return counts
}
