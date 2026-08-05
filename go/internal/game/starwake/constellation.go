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

	// ACT TWO. nil drops means this tier runs the original climbing ladder.
	drops     *StarDrops
	collected int
	fallen    []Star
	fallenBuf [engine.MaxReels * engine.MaxRows]Star

	// Per-spin scratch, consumed by the event emitters. Backed by a reusable
	// array so a spin never allocates to report newly lit cells.
	newlyLit     []config.Cell
	newlyLitBuf  [engine.MaxReels * engine.MaxRows]config.Cell
	WokeThisSpin bool
}

// Star is one multiplier star sitting on the board for a single roam spin.
type Star struct {
	Cell  config.Cell
	Value int
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
		drops:      tier.StarDrops,
		beastW:     tier.BeastShape[0],
		beastH:     tier.BeastShape[1],
		origins:    tier.RoamOrigins(c),
		phase:      PhaseCharge,
		multiplier: 1,
		rung:       -1,
	}
	con.newlyLit = con.newlyLitBuf[:0]
	con.fallen = con.fallenBuf[:0]

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

// ActTwo reports whether this tier runs the star-collect mechanic rather than
// the original climbing ladder.
func (con *Constellation) ActTwo() bool { return con.drops != nil }

// Wake enters the roam phase, places the block and sets the first multiplier.
//
// ⚠ ACT TWO CONSUMES THE STICKY WILDS HERE. `lit` is deliberately NOT cleared --
// it stays as the record of which stars were traced, which the star chart and the
// deal/starLit events still read. What changes is that WildCells stops counting
// it, so the board goes back to normal symbols and the block is the only wild
// left. Keeping the record and dropping the wildness is what lets act one's
// completion ladder (84/63/32%) stay measurable after the change.
func (con *Constellation) Wake(g *engine.RNG) error {
	if !con.IsComplete() {
		return fmt.Errorf("%s: beast cannot wake before the set is complete", con.Tier)
	}
	if con.phase != PhaseCharge {
		return fmt.Errorf("%s: beast already awake", con.Tier)
	}
	con.phase = PhaseRoam
	if con.ActTwo() {
		// Starts bare. Every point of multiplier from here is collected, so there
		// is no dead x1 rung to sit through -- the first star IS the climb.
		con.rung = -1
		con.multiplier = 1
	} else {
		con.rung = 0
		con.multiplier = con.ladder[0]
	}
	con.beastOrigin = con.origins[g.IntN(len(con.origins))]
	con.beastPlaced = true
	con.WokeThisSpin = true
	return nil
}

// Roam moves the block to a new valid origin.
//
// Under the ladder it also climbs one rung. The rung CLAMPS at the top: clamping
// means a feature-length change can never index off the end, but it also means a
// ladder that is too short silently caps that tier's ceiling with no error, which
// is what the rung-count invariant in config.go guards against.
//
// Under act two it climbs nothing -- the multiplier moves only in Collect.
func (con *Constellation) Roam(g *engine.RNG) error {
	if con.phase != PhaseRoam {
		return fmt.Errorf("%s: roam before the beast woke", con.Tier)
	}
	con.beastOrigin = con.origins[g.IntN(len(con.origins))]
	if !con.ActTwo() {
		if con.rung+1 < len(con.ladder) {
			con.rung++
		}
		con.multiplier = con.ladder[con.rung]
	}
	con.WokeThisSpin = false
	return nil
}

// RollStarValues finds the multiplier stars the reels just dealt and gives each
// one a value.
//
// ⚠ STARS ARE REAL REEL SYMBOLS, NOT AN OVERLAY. Their POSITION comes from the
// strip -- act two draws a roam-only strip carrying the star symbol -- and only
// their VALUE is rolled here. Splitting it that way keeps the two knobs
// independent: density is tuned on the strip (per reel, the same machinery the FR0
// drying used) and the value table is tuned in config, which matters because the
// two trade against each other.
//
// A star is a non-paying symbol, so it BREAKS a payline the way a scatter does.
// That cost is real and is why density belongs on the right-hand reels: on a
// left-to-right lines game a blocker on reel 0 kills a win outright, while one on
// reel 4 only shortens a 5-kind to a 4-kind.
//
// The value is stashed in the cell's own Mult field rather than a parallel map.
// Safe because applyMult only reads cells INSIDE a winning run and a star never
// matches, so it is never in one.
func (con *Constellation) RollStarValues(b *engine.Board, star engine.SymID, g *engine.RNG) []Star {
	con.fallen = con.fallenBuf[:0]
	if !con.ActTwo() || con.phase != PhaseRoam {
		return con.fallen
	}
	for reel := 0; reel < b.NumReels; reel++ {
		for row := 0; row < b.NumRows[reel]; row++ {
			if b.At(reel, row).Sym != star {
				continue
			}
			value := pickWeighted(con.drops.Values, g.IntN)
			b.Set(reel, row, engine.Cell{Sym: star, Mult: uint16(value)})
			con.fallen = append(con.fallen, Star{
				Cell:  config.Cell{Reel: reel, Row: row},
				Value: value,
			})
		}
	}
	return con.fallen
}

// Collect takes every star the board dealt and adds it to the beast's multiplier.
//
// ⚠ COLLECTION IS GLOBAL, APPLICATION IS POSITIONAL -- copied from Rage Bait's own
// rules ("whenever a Wild is on the board it collects every Fish... any winning
// line passing through the Wild is multiplied that much more"). The block does not
// have to land on a star to take it, so there is no positional lottery; but the
// multiplier still only reaches lines that cross the block, so WHERE it roamed
// decides which wins get paid at the new value.
//
// Returns the amount added this spin and the new total.
func (con *Constellation) Collect() (gained, total int) {
	for _, s := range con.fallen {
		gained += s.Value
	}
	con.collected += gained
	con.multiplier = 1 + con.collected
	return gained, con.multiplier
}

// Fallen lists the stars currently on the board (this spin's drops).
func (con *Constellation) Fallen() []Star { return con.fallen }

// RoamStrip is the reel set act two draws while the beast is awake.
func (con *Constellation) RoamStrip() string {
	if con.drops == nil {
		return ""
	}
	return con.drops.RoamStrip
}

// StarSymbol is the symbol name the beast collects.
func (con *Constellation) StarSymbol() string {
	if con.drops == nil {
		return ""
	}
	return con.drops.StarSymbol
}

// Collected is the running sum of every star value taken so far.
func (con *Constellation) Collected() int { return con.collected }

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

// WildCells is every cell that should read as wild this spin.
//
// ⚠ THIS IS WHERE ACT TWO ACTUALLY HAPPENS. Under the ladder it is the sticky lit
// stars plus the block, for the whole feature -- which is how draco ended up with
// 11.2 of 20 cells wild, a board that looks like a jackpot and pays a third of the
// ticket. Under act two the lit stars stop being wild the moment the beast wakes,
// so the roam runs on a normal board with the block as the only wild. The payout
// moves off the wild carpet and onto the collected multiplier, and there is room
// for paying symbols again.
func (con *Constellation) WildCells() CellMask {
	if con.ActTwo() && con.phase == PhaseRoam {
		return con.BeastCells()
	}
	return con.lit | con.BeastCells()
}

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
