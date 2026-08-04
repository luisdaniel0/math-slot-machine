package engine

import (
	"fmt"

	"starwake/internal/sdk/config"
)

// Grid bounds. Fixed-size arrays rather than slices so a Board is one flat value
// with NO heap allocation -- a board is drawn once per spin, ~1e7 times per mode,
// and an allocation there would dominate everything else.
const (
	MaxReels = 8
	MaxRows  = 8
)

// Cell is one board position.
//
// Mult is 0 when the cell carries no multiplier, matching Python's `None`. A
// plain wild under Starwake's Option A carries an explicit 1; only the beast
// block stamps anything higher.
type Cell struct {
	Sym  SymID
	Mult uint16
}

// Board is one drawn game board plus the draw metadata the events need.
//
// Reused across spins: Draw overwrites every cell it uses, so a worker allocates
// exactly one Board for its whole run.
type Board struct {
	Cells    [MaxReels][MaxRows]Cell
	NumReels int
	NumRows  [MaxReels]int

	// ReelPositions is each reel's stop index into the strip. Published in the
	// reveal event so the client can render the same stop.
	ReelPositions [MaxReels]int
	// Anticipation drives the client's reel-slowdown effect. Nonzero from the
	// reel after the trigger threshold is met.
	Anticipation [MaxReels]int

	// Scatters holds the positions of scatter symbols on the current board.
	// Backed by a reused array so counting scatters never allocates.
	Scatters   []Cell
	scatterBuf [MaxReels * MaxRows]Cell
	StripID    string

	// Padding symbols: the strip positions just above and just below the visible
	// window. Purely presentational -- they never pay and never count as scatters
	// -- but the reveal event ships them, and their presence is why every CLIENT
	// row is the engine row plus one.
	TopSymbols    [MaxReels]SymID
	BottomSymbols [MaxReels]SymID
}

// fillPadding records the symbols bracketing the visible window on one reel.
func (b *Board) fillPadding(strip Strip, reel, stop int) {
	length := len(strip[reel])
	b.TopSymbols[reel] = strip[reel][((stop-1)%length+length)%length]
	b.BottomSymbols[reel] = strip[reel][(stop+b.NumRows[reel])%length]
}

// NewBoard prepares a board for a given geometry.
func NewBoard(c *config.Config) (*Board, error) {
	if c.Game.NumReels > MaxReels {
		return nil, fmt.Errorf("%d reels exceeds MaxReels=%d", c.Game.NumReels, MaxReels)
	}
	b := &Board{NumReels: c.Game.NumReels}
	for reel := 0; reel < b.NumReels; reel++ {
		rows := c.Rows(reel)
		if rows > MaxRows {
			return nil, fmt.Errorf("reel %d has %d rows, exceeds MaxRows=%d", reel, rows, MaxRows)
		}
		b.NumRows[reel] = rows
	}
	b.Scatters = b.scatterBuf[:0]
	return b, nil
}

// At returns the cell at a position.
func (b *Board) At(reel, row int) Cell { return b.Cells[reel][row] }

// Set overwrites a cell. Used by features that stamp wilds onto a drawn board.
func (b *Board) Set(reel, row int, c Cell) { b.Cells[reel][row] = c }

// ScatterCount is the number of scatters on the current board.
func (b *Board) ScatterCount() int { return len(b.Scatters) }

// ReelSet holds interned strips plus the per-symbol stop positions the forced
// draw needs.
//
// Python recomputes those positions on EVERY forced draw (Board.get_syms_on_reel
// scans the entire strip each time), which for a buy mode -- where every single
// board is forced -- is a full strip scan per spin. Precomputing once at load
// removes that entirely.
type ReelSet struct {
	Strips map[string]Strip
	// scatterStops[stripID][reel] lists positions where a scatter sits.
	scatterStops map[string][][]int
}

// NewReelSet interns every strip and precomputes scatter stop positions.
func NewReelSet(c *config.Config, st *SymbolTable) (*ReelSet, error) {
	strips, err := st.InternStrips(c)
	if err != nil {
		return nil, err
	}
	rs := &ReelSet{Strips: strips, scatterStops: make(map[string][][]int, len(strips))}
	for id, strip := range strips {
		stops := make([][]int, len(strip))
		for reel := range strip {
			for pos, sym := range strip[reel] {
				if st.IsScatter(sym) {
					stops[reel] = append(stops[reel], pos)
				}
			}
		}
		rs.scatterStops[id] = stops
	}
	return rs, nil
}

// Strip returns an interned strip by id.
func (rs *ReelSet) Strip(id string) (Strip, error) {
	s, ok := rs.Strips[id]
	if !ok {
		return nil, fmt.Errorf("unknown reel strip %q", id)
	}
	return s, nil
}

// Draw fills the board from random stop positions on the given strip.
//
// Port of Board.create_board_reelstrips. The window wraps: a stop near the end of
// a strip reads on through position 0, which is what makes a strip a loop.
func (b *Board) Draw(stripID string, strip Strip, st *SymbolTable, anticipationTrigger int, g *RNG) {
	b.StripID = stripID
	b.Scatters = b.scatterBuf[:0]
	firstScatterReel := -1

	for reel := 0; reel < b.NumReels; reel++ {
		length := len(strip[reel])
		stop := g.IntN(length)
		b.ReelPositions[reel] = stop
		b.Anticipation[reel] = 0
		b.fillPadding(strip, reel, stop)

		for row := 0; row < b.NumRows[reel]; row++ {
			sym := strip[reel][(stop+row)%length]
			b.Cells[reel][row] = Cell{Sym: sym}
			if st.IsScatter(sym) {
				b.Scatters = append(b.Scatters, Cell{Sym: SymID(reel), Mult: uint16(row)})
				// Anticipation starts on the reel AFTER the threshold is reached,
				// so the client only teases once a trigger is still possible.
				if len(b.Scatters) >= anticipationTrigger && firstScatterReel == -1 {
					firstScatterReel = reel + 1
				}
			}
		}
	}

	b.applyAnticipation(firstScatterReel)
}

// applyAnticipation ramps 1,2,3... from the first anticipating reel onward.
func (b *Board) applyAnticipation(firstScatterReel int) {
	for reel := 0; reel < b.NumReels; reel++ {
		b.Anticipation[reel] = 0
	}
	if firstScatterReel < 0 || firstScatterReel >= b.NumReels {
		return
	}
	count := 1
	for reel := firstScatterReel; reel < b.NumReels; reel++ {
		b.Anticipation[reel] = count
		count++
	}
}

// ScatterPositions returns the scatter cells as (reel,row) pairs.
//
// Draw packs them into the Cell struct's two fields to avoid a second buffer;
// this unpacks for callers that want real positions.
func (b *Board) ScatterPositions() []config.Cell {
	out := make([]config.Cell, len(b.Scatters))
	for i, s := range b.Scatters {
		out[i] = config.Cell{Reel: int(s.Sym), Row: int(s.Mult)}
	}
	return out
}

// ErrForceFailed reports a forced draw that could not reach its target count.
//
// ⚠ THE PYTHON ORIGINAL CANNOT RETURN THIS. Board.force_special_board is a bare
// `while True` with no retry cap, so a forced count that is out of structural
// reach HANGS FOREVER rather than failing -- which is exactly what CLAUDE.md
// records as the risk of a forced wincap slice whose cap drifts out of reach, and
// why an unsatisfiable slice shows up as a run that never finishes. A bounded
// retry turns a silent hang into a diagnosable error.
type ErrForceFailed struct {
	StripID  string
	Want     int
	Got      int
	Attempts int
}

func (e *ErrForceFailed) Error() string {
	return fmt.Sprintf(
		"could not force %d scatters on strip %s after %d attempts (best %d) -- "+
			"the strip probably cannot show that many; check that at most one scatter "+
			"per reel is reachable and that a reel window can reveal two",
		e.Want, e.StripID, e.Attempts, e.Got)
}

// maxForceAttempts bounds the retry loop. Forcing 6 scatters on the ASC strip
// succeeds ~92% of the time, so a few hundred attempts is astronomically more
// than any legitimate draw needs while still terminating on an impossible ask.
const maxForceAttempts = 500

// ForceScatters draws a board showing exactly `want` scatter symbols.
//
// Port of Board.force_special_board / _force_special_board. The selection places
// AT MOST ONE scatter per reel (each chosen reel's probability is zeroed), so on a
// 5-reel grid a 6th scatter can only come from a reel whose window happens to
// reveal two -- which is precisely why Starwake needs the dedicated ASC strip to
// deal its 6-scatter Ascendant.
func (b *Board) ForceScatters(
	rs *ReelSet, stripID string, strip Strip, st *SymbolTable,
	want, anticipationTrigger int, g *RNG,
) error {
	stops := rs.scatterStops[stripID]
	best := -1

	for attempt := 1; attempt <= maxForceAttempts; attempt++ {
		b.forceOnce(stops, stripID, strip, st, want, anticipationTrigger, g)
		got := len(b.Scatters)
		if got == want {
			return nil
		}
		if got > best {
			best = got
		}
	}
	return &ErrForceFailed{StripID: stripID, Want: want, Got: best, Attempts: maxForceAttempts}
}

// forceOnce is one attempt at a forced draw.
func (b *Board) forceOnce(
	stops [][]int, stripID string, strip Strip, st *SymbolTable,
	want, anticipationTrigger int, g *RNG,
) {
	// Weight each reel by how densely it carries the symbol, matching the
	// Python selection, then zero a reel once chosen so no reel is picked twice.
	var weights [MaxReels]float64
	var total float64
	for reel := 0; reel < b.NumReels; reel++ {
		if len(stops[reel]) == 0 {
			continue
		}
		weights[reel] = float64(len(stops[reel])) / float64(len(strip[reel]))
		total += weights[reel]
	}

	var forced [MaxReels]int
	for reel := range forced {
		forced[reel] = -1
	}

	for picked := 0; picked < want && total > 0; picked++ {
		target := g.Float64() * total
		chosen := -1
		var acc float64
		for reel := 0; reel < b.NumReels; reel++ {
			if weights[reel] == 0 {
				continue
			}
			acc += weights[reel]
			if target < acc {
				chosen = reel
				break
			}
		}
		if chosen == -1 {
			break
		}
		// The scatter lands at a random row of the visible window, so the stop
		// is offset back from the symbol's own position.
		symPos := stops[chosen][g.IntN(len(stops[chosen]))]
		forced[chosen] = symPos - g.IntN(b.NumRows[chosen])
		total -= weights[chosen]
		weights[chosen] = 0
	}

	b.fillFromStops(stripID, strip, st, forced, anticipationTrigger, g)
}

// fillFromStops fills the board, using a forced stop where one is set and a
// random stop everywhere else. Port of force_board_from_reelstrips.
func (b *Board) fillFromStops(
	stripID string, strip Strip, st *SymbolTable,
	forced [MaxReels]int, anticipationTrigger int, g *RNG,
) {
	b.StripID = stripID
	b.Scatters = b.scatterBuf[:0]
	firstScatterReel := -1

	for reel := 0; reel < b.NumReels; reel++ {
		length := len(strip[reel])
		stop := forced[reel]
		if stop < 0 {
			stop = g.IntN(length)
		}
		// Python's negative index wraps; Go's % keeps the sign, so normalise.
		stop = ((stop % length) + length) % length
		b.ReelPositions[reel] = stop
		b.fillPadding(strip, reel, stop)

		for row := 0; row < b.NumRows[reel]; row++ {
			sym := strip[reel][(stop+row)%length]
			b.Cells[reel][row] = Cell{Sym: sym}
			if st.IsScatter(sym) {
				b.Scatters = append(b.Scatters, Cell{Sym: SymID(reel), Mult: uint16(row)})
				if len(b.Scatters) >= anticipationTrigger && firstScatterReel == -1 {
					firstScatterReel = reel + 1
				}
			}
		}
	}

	b.applyAnticipation(firstScatterReel)
}
