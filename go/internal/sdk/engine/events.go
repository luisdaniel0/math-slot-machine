package engine

// Event is one entry on a book's event tape.
//
// ⚠ THIS STRUCT IS A PUBLISHED INTERFACE. The events array ships inside
// books_<mode>.jsonl.zst and drives the web-sdk frontend's animations, so the key
// names and value shapes must match src/events/events.py and
// games/starwake/game_events.py exactly. A Go engine can produce math-perfect
// books that pass every RGS check and still render wrong if a key is renamed.
//
// One flat struct with omitempty rather than a map[string]any: a map allocates
// and hashes per event, and there are tens of events per book across ~1e7 books.
// Fields that can legitimately be zero use pointers so omitempty does not silently
// drop a real 0 (a setWin of 0, a litCount of 0, a multiplier of 0).
type Event struct {
	Index int    `json:"index"`
	Type  string `json:"type"`

	// --- reveal ---
	Board            [][]RevealSym `json:"board,omitempty"`
	PaddingPositions []int         `json:"paddingPositions,omitempty"`
	GameType         string        `json:"gameType,omitempty"`
	Anticipation     []int         `json:"anticipation,omitempty"`

	// --- wins ---
	TotalWin *int64    `json:"totalWin,omitempty"`
	Wins     []WinJSON `json:"wins,omitempty"`
	Amount   *int64    `json:"amount,omitempty"`
	WinLevel int       `json:"winLevel,omitempty"`

	// --- freespins ---
	TotalFs   int   `json:"totalFs,omitempty"`
	Positions []Pos `json:"positions,omitempty"`
	Total     *int  `json:"total,omitempty"`

	// --- constellation (game-local, but carried on the shared tape) ---
	Tier       string `json:"tier,omitempty"`
	Beast      string `json:"beast,omitempty"`
	Cells      []Pos  `json:"cells,omitempty"`
	TotalCells int    `json:"totalCells,omitempty"`
	// Prelit is a POINTER so an EMPTY set still serialises as []. Python emits
	// "prelit" on every constellationDealt event, and a frontend reading
	// event.prelit.length would break on an omitted key -- omitempty drops an
	// empty slice but keeps a non-nil pointer to one.
	Prelit     *[]Pos `json:"prelit,omitempty"`
	LitCount   *int   `json:"litCount,omitempty"`
	NewlyLit   []Pos  `json:"newlyLit,omitempty"`
	Complete   *bool  `json:"complete,omitempty"`
	BeastShape *Shape `json:"beastShape,omitempty"`
	// Beasts is one top-left origin per block, and is emitted ONLY when a tier
	// wakes more than one. With a single block `cells` is unambiguous, but two
	// 2x2s produce eight cells that can be paired up several ways, so a replay
	// starting from this event could not reconstruct the board without it.
	// ⚠ OMITTED FOR SINGLE-BLOCK TIERS ON PURPOSE: their books stay byte-identical,
	// which is what keeps five of six modes off the re-sim list.
	Beasts     []Pos `json:"beasts,omitempty"`
	BeastCount *int  `json:"beastCount,omitempty"`
	Multiplier *int  `json:"multiplier,omitempty"`

	// --- act two: multiplier stars ---
	Stars  []StarJSON `json:"stars,omitempty"`
	Gained *int       `json:"gained,omitempty"`
}

// StarJSON is one multiplier star as the client sees it: where it landed and what
// it was worth. Carried on BOTH starsLanded and starsCollected so the frontend can
// animate the land and the fly-to-beast without holding state between events -- the
// tape is a projection, and an event that only makes sense relative to an earlier
// one breaks replay from an arbitrary point.
type StarJSON struct {
	Reel  int `json:"reel"`
	Row   int `json:"row"`
	Value int `json:"value"`
}

// Pos is a client-coordinate board position.
//
// ⚠ CLIENT COORDINATES ARE PADDED. With include_padding the reveal prepends a top
// symbol to every reel, so client row 0 is the padding symbol and every engine row
// is emitted as row+1. Getting this wrong shifts every animation by one cell while
// leaving the math untouched -- invisible to any RTP check.
type Pos struct {
	Reel int `json:"reel"`
	Row  int `json:"row"`
}

// Shape is a beast block's footprint.
type Shape struct {
	Reels int `json:"reels"`
	Rows  int `json:"rows"`
}

// RevealSym is one symbol as the client sees it.
type RevealSym struct {
	Name       string `json:"name"`
	Wild       bool   `json:"wild,omitempty"`
	Scatter    bool   `json:"scatter,omitempty"`
	Multiplier int    `json:"multiplier,omitempty"`
}

// WinJSON is one paying line in client form.
type WinJSON struct {
	Symbol    string  `json:"symbol"`
	Kind      int     `json:"kind"`
	Win       int64   `json:"win"`
	Positions []Pos   `json:"positions"`
	Meta      WinMeta `json:"meta"`
}

// WinMeta carries the presentation detail for one line win.
type WinMeta struct {
	LineIndex      int   `json:"lineIndex"`
	Multiplier     int   `json:"multiplier"`
	WinWithoutMult int64 `json:"winWithoutMult"`
	GlobalMult     int   `json:"globalMult"`
	LineMultiplier int   `json:"lineMultiplier"`
}

// Event type constants, mirroring src/events/event_constants.py.
const (
	EvReveal          = "reveal"
	EvWinInfo         = "winInfo"
	EvFinalWin        = "finalWin"
	EvSetWin          = "setWin"
	EvSetTotalWin     = "setTotalWin"
	EvWincap          = "wincap"
	EvUpdateFreeSpin  = "updateFreeSpin"
	EvFreeSpinTrigger = "freeSpinTrigger"
	EvFreeSpinEnd     = "freeSpinEnd"
)

// helpers for the pointer fields
func i64(v int64) *int64 { return &v }
func ip(v int) *int      { return &v }
func bp(v bool) *bool    { return &v }

// cents converts a payout multiplier to the integer hundredths the client and
// the lookup table both use, clamped at the mode ceiling.
func cents(v, cap float64) int64 {
	if v > cap {
		v = cap
	}
	return int64(roundCents(v)*100 + 0.5)
}

// PadRow shifts an engine row into client coordinates.
func PadRow(row int, padded bool) int {
	if padded {
		return row + 1
	}
	return row
}
