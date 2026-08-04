package starwake

import (
	"fmt"

	"starwake/internal/sdk/config"
	"starwake/internal/sdk/engine"
)

// Phase is where a constellation is in its life.
type Phase uint8

const (
	// PhaseCharge is filling cells via win-lines; the beast is asleep.
	PhaseCharge Phase = iota
	// PhaseRoam is set complete; the beast is awake and roaming.
	PhaseRoam
)

// CellMask is a bitset over grid positions.
//
// Starwake's 5x4 grid is 20 cells, so the whole "which cells are lit" question --
// asked on every feature spin, ~1e7 times per mode -- becomes a single 64-bit OR
// and a popcount instead of Python's set-of-tuples. Completion is then just
// `lit == targets`.
type CellMask uint64

// Bit returns the mask bit for one position.
func Bit(reel, row int) CellMask { return 1 << uint(reel*engine.MaxRows+row) }

// Has reports whether a position is set.
func (m CellMask) Has(reel, row int) bool { return m&Bit(reel, row) != 0 }

// Count is the number of set positions.
func (m CellMask) Count() int {
	n := 0
	for v := m; v != 0; v &= v - 1 {
		n++
	}
	return n
}

// Constellation is the persistent state of one dealt constellation across one
// feature.
//
// Port of games/starwake/constellation.py. It holds everything that must survive
// the feature loop: which cells are lit (sticky wilds), the phase, where the
// beast block sits and its climbing multiplier. Kept free of any engine state so
// it can be unit-tested on its own -- the Keybearer lesson that persistent state
// is where silent bugs live.
type Constellation struct {
	Tier      string
	BeastName string

	targets    CellMask
	targetList []config.Cell
	numTargets int
	prelit     CellMask
	lit        CellMask

	phase      Phase
	multiplier int
	rung       int
	ladder     []int

	beastW, beastH int
	origins        []config.Cell
	beastOrigin    config.Cell
	beastPlaced    bool

	// Per-spin scratch, consumed by the event emitters. Backed by a reusable
	// array so a spin never allocates to report newly lit cells.
	newlyLit     []config.Cell
	newlyLitBuf  [engine.MaxReels * engine.MaxRows]config.Cell
	WokeThisSpin bool
}

// NewConstellation deals a tier.
func NewConstellation(tier Tier, tierName string, c *config.Config) (*Constellation, error) {
	if len(tier.MultLadder) == 0 {
		return nil, fmt.Errorf("%s: the beast needs at least one multiplier rung", tierName)
	}

	con := &Constellation{
		Tier:       tierName,
		BeastName:  tier.BeastName,
		targetList: tier.Cells,
		numTargets: len(tier.Cells),
		ladder:     tier.MultLadder,
		beastW:     tier.BeastShape[0],
		beastH:     tier.BeastShape[1],
		origins:    tier.RoamOrigins(c),
		phase:      PhaseCharge,
		multiplier: 1,
		rung:       -1,
	}
	con.newlyLit = con.newlyLitBuf[:0]

	for _, cell := range tier.Cells {
		con.targets |= Bit(cell.Reel, cell.Row)
	}
	for _, cell := range tier.PrelitCells {
		bit := Bit(cell.Reel, cell.Row)
		if con.targets&bit == 0 {
			return nil, fmt.Errorf("%s: pre-lit cell (%d,%d) is not part of the shape",
				tierName, cell.Reel, cell.Row)
		}
		con.prelit |= bit
	}
	// A fully pre-lit deal would wake the beast before a single spin and hand out
	// the top of the ladder for free. Loud here rather than silent in a pool,
	// where the payout would look plausible right up to the ceiling.
	if con.prelit.Count() >= con.numTargets {
		return nil, fmt.Errorf("%s: pre-lit on every cell -- would complete before spin 1", tierName)
	}
	if len(con.origins) == 0 {
		return nil, fmt.Errorf("%s: beast %dx%d does not fit the grid", tierName, con.beastW, con.beastH)
	}
	con.lit = con.prelit
	return con, nil
}

// Phase reports the current phase.
func (con *Constellation) Phase() Phase { return con.phase }

// Multiplier is the beast's current multiplier (1 while asleep).
func (con *Constellation) Multiplier() int { return con.multiplier }

// Rung is the current ladder index, or -1 before the beast wakes.
func (con *Constellation) Rung() int { return con.rung }

// Lit exposes the lit-cell mask.
func (con *Constellation) Lit() CellMask { return con.lit }

// Targets exposes the full constellation shape.
func (con *Constellation) Targets() CellMask { return con.targets }

// TargetCells lists the constellation's cells in config order (for the deal event).
func (con *Constellation) TargetCells() []config.Cell { return con.targetList }

// NewlyLit lists the cells lit on the most recent spin.
func (con *Constellation) NewlyLit() []config.Cell { return con.newlyLit }

// IsComplete reports whether every constellation cell is lit.
func (con *Constellation) IsComplete() bool { return con.lit == con.targets }

// LightFromWins lights any still-dark target cell that a winning line crossed.
//
// Idempotent and monotonic: already-lit cells are never re-lit and `lit` only
// grows, which is what makes a lit star STICKY -- and the stickiness is the
// snowball (a lit cell is a wild, which makes the next spin win more, which
// lights more cells).
func (con *Constellation) LightFromWins(crossed CellMask) []config.Cell {
	con.newlyLit = con.newlyLitBuf[:0]
	fresh := crossed & con.targets &^ con.lit
	if fresh == 0 {
		return con.newlyLit
	}
	// Report in the constellation's own cell order so events are stable.
	for _, cell := range con.targetList {
		if fresh.Has(cell.Reel, cell.Row) {
			con.newlyLit = append(con.newlyLit, cell)
		}
	}
	con.lit |= fresh
	return con.newlyLit
}

// Wake enters the roam phase, places the block and sets the first multiplier.
func (con *Constellation) Wake(g *engine.RNG) error {
	if !con.IsComplete() {
		return fmt.Errorf("%s: beast cannot wake before the set is complete", con.Tier)
	}
	if con.phase != PhaseCharge {
		return fmt.Errorf("%s: beast already awake", con.Tier)
	}
	con.phase = PhaseRoam
	con.rung = 0
	con.multiplier = con.ladder[0]
	con.beastOrigin = con.origins[g.IntN(len(con.origins))]
	con.beastPlaced = true
	con.WokeThisSpin = true
	return nil
}

// Roam moves the block to a new valid origin and climbs one ladder rung.
//
// The rung CLAMPS at the top. Clamping means a feature-length change can never
// index off the end -- but it also means a ladder that is too short silently caps
// that tier's ceiling with no error, which is exactly the failure the rung-count
// invariant in config.go guards against.
func (con *Constellation) Roam(g *engine.RNG) error {
	if con.phase != PhaseRoam {
		return fmt.Errorf("%s: roam before the beast woke", con.Tier)
	}
	con.beastOrigin = con.origins[g.IntN(len(con.origins))]
	if con.rung+1 < len(con.ladder) {
		con.rung++
	}
	con.multiplier = con.ladder[con.rung]
	con.WokeThisSpin = false
	return nil
}

// BeastOrigin returns the block's top-left cell and whether it is on the board.
func (con *Constellation) BeastOrigin() (config.Cell, bool) {
	return con.beastOrigin, con.beastPlaced
}

// BeastCells is the mask of cells the block currently covers (0 while asleep).
func (con *Constellation) BeastCells() CellMask {
	if !con.beastPlaced {
		return 0
	}
	var m CellMask
	for dr := 0; dr < con.beastW; dr++ {
		for drow := 0; drow < con.beastH; drow++ {
			m |= Bit(con.beastOrigin.Reel+dr, con.beastOrigin.Row+drow)
		}
	}
	return m
}

// WildCells is every cell that should read as wild this spin: the sticky lit
// stars plus the beast block.
func (con *Constellation) WildCells() CellMask { return con.lit | con.BeastCells() }

// ApplyWilds stamps wilds onto a freshly drawn board.
//
// Called once per feature spin AFTER the draw and BEFORE line evaluation -- that
// ordering IS the snowball, because existing wilds inflate this spin's wins,
// which then light more cells. Beast cells additionally carry the climbing
// multiplier, which is what "the multiplier lives on the beast" means in board
// terms.
func (con *Constellation) ApplyWilds(b *engine.Board, wild engine.SymID) {
	beast := con.BeastCells()
	wilds := con.WildCells()
	if wilds == 0 {
		return
	}
	for reel := 0; reel < b.NumReels; reel++ {
		for row := 0; row < b.NumRows[reel]; row++ {
			if !wilds.Has(reel, row) {
				continue
			}
			// Plain wilds carry x1 under Option A; only the beast stamps higher.
			mult := uint16(1)
			if beast.Has(reel, row) {
				mult = uint16(con.multiplier)
			}
			b.Set(reel, row, engine.Cell{Sym: wild, Mult: mult})
		}
	}
}
