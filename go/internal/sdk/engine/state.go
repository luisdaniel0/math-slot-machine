package engine

import (
	"fmt"

	"starwake/internal/sdk/config"
)

// WinManager is the payout wallet for one simulation.
//
// Port of src/wins/win_manager.py. Wins accumulate into SpinWin for one reveal,
// are folded into the base or free bucket at the end of each spin, and
// RunningBetWin tracks the whole round -- which is what the wincap clamp reads.
type WinManager struct {
	MaxWin        float64
	RunningBetWin float64
	BasegameWins  float64
	FreegameWins  float64
	SpinWin       float64

	// Across the whole worker run, for the RTP summary only.
	TotalCumulative float64
	CumBase         float64
	CumFree         float64
}

// UpdateSpinWin adds a win to the current reveal and the running round total.
func (w *WinManager) UpdateSpinWin(amount float64) {
	w.SpinWin += amount
	w.RunningBetWin += amount
}

// ResetSpinWin clears the per-reveal total.
func (w *WinManager) ResetSpinWin() { w.SpinWin = 0 }

// UpdateGametypeWins folds the reveal's win into the right bucket.
func (w *WinManager) UpdateGametypeWins(gametype, base, free string) error {
	switch gametype {
	case base:
		w.BasegameWins += w.SpinWin
	case free:
		w.FreegameWins += w.SpinWin
	default:
		return fmt.Errorf("unknown gametype %q", gametype)
	}
	return nil
}

// EndRound accumulates the round into the worker totals.
//
// ⚠ Python clamps base and free SEPARATELY here and then sums, so on a capped
// book these two can total slightly above the cap. That feeds only the printed
// RTP summary, never a book payout, but it is the same separate-clamp shape that
// makes the published split fields disagree with payoutMultiplier by up to +5x on
// capped books. Reproduced deliberately so the RTP summaries stay comparable.
func (w *WinManager) EndRound() {
	base, free := min(w.MaxWin, w.BasegameWins), min(w.MaxWin, w.FreegameWins)
	w.TotalCumulative += base + free
	w.CumBase += base
	w.CumFree += free
}

// ResetRound clears the per-simulation wallet.
func (w *WinManager) ResetRound() {
	w.BasegameWins, w.FreegameWins = 0, 0
	w.RunningBetWin, w.SpinWin = 0, 0
}

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

// Book is one simulation's result: the event tape plus its payout.
type Book struct {
	ID               int
	PayoutMultiplier float64
	Criteria         string
	BasegameWins     float64
	FreegameWins     float64
	Events           []Event
}

// Reset clears a book for reuse without releasing its event buffer.
func (b *Book) Reset(id int, criteria string) {
	b.ID = id
	b.Criteria = criteria
	b.PayoutMultiplier = 0
	b.BasegameWins, b.FreegameWins = 0, 0
	b.Events = b.Events[:0]
}

// Add appends an event, stamping its index.
func (b *Book) Add(e Event) {
	e.Index = len(b.Events)
	b.Events = append(b.Events, e)
}

// Spin is one worker's complete engine state.
//
// One Spin per goroutine. Everything mutable lives here and everything immutable
// (symbol table, reel set, paylines) is shared, so workers never contend.
type Spin struct {
	Cfg   *config.Config
	Syms  *SymbolTable
	Reels *ReelSet
	Lines *LineEvaluator
	Board *Board
	Wins  *WinResult
	RNG   *RNG
	WM    WinManager
	Book  Book

	Mode     *config.BetMode
	Dist     *config.Distribution
	Criteria string

	GameType          string
	Fs, TotFs         int
	GlobalMult        int
	WincapTriggered   bool
	TriggeredFreegame bool
	Repeat            bool
	RepeatCount       int
	FinalWin          float64

	padded   bool
	baseType string
	freeType string
	wildSym  SymID

	// PER-BOOK ARENAS. An Event holds SLICES, and a book's events are all
	// serialised together at the end -- so an event may not reference a buffer
	// that a later spin overwrites. Sharing one reveal buffer made every reveal
	// in a book render as the LAST board drawn: a silent bug that leaves every
	// payout correct and every RTP check passing while the replay is wrong.
	//
	// These arenas hand out a fresh region per event and reset once per book, so
	// correctness costs no per-event allocation after the first few books.
	revealArena [][][]RevealSym
	revealUsed  int
	intArena    [][]int
	intUsed     int
	revealRows  int

	// Force-record entries for this book, consumed by the writer.
	Forced []ForceKey
}

// ForceKey is one recorded event description for the force record, which the
// Rust optimizer searches to build its fences.
type ForceKey struct {
	Kind     int
	Symbol   string
	Mult     int
	GameType string
}

// NewSpin builds a worker engine.
func NewSpin(c *config.Config, st *SymbolTable, rs *ReelSet, le *LineEvaluator) (*Spin, error) {
	b, err := NewBoard(c)
	if err != nil {
		return nil, err
	}
	s := &Spin{
		Cfg: c, Syms: st, Reels: rs, Lines: le,
		Board: b, Wins: NewWinResult(),
		padded:   c.Game.IncludePadding,
		baseType: c.Game.BasegameType,
		freeType: c.Game.FreegameType,
	}
	if wilds := c.SpecialSymbols["wild"]; len(wilds) > 0 {
		s.wildSym = st.MustID(wilds[0])
	}
	s.revealRows = c.Rows(0)
	if s.padded {
		s.revealRows += 2
	}
	return s, nil
}

// nextRevealBoard hands out a reveal buffer owned by the current book.
func (s *Spin) nextRevealBoard() [][]RevealSym {
	if s.revealUsed == len(s.revealArena) {
		board := make([][]RevealSym, s.Board.NumReels)
		for i := range board {
			board[i] = make([]RevealSym, s.revealRows)
		}
		s.revealArena = append(s.revealArena, board)
	}
	b := s.revealArena[s.revealUsed]
	s.revealUsed++
	return b
}

// nextInts hands out an int slice owned by the current book.
func (s *Spin) nextInts(src []int) []int {
	if s.intUsed == len(s.intArena) {
		s.intArena = append(s.intArena, make([]int, MaxReels))
	}
	dst := s.intArena[s.intUsed][:len(src)]
	s.intUsed++
	copy(dst, src)
	return dst
}

// Cap is this mode's ceiling -- both the published max win and the engine clamp.
func (s *Spin) Cap() float64 { return s.Mode.MaxWin }

// ResetBook clears per-simulation state.
func (s *Spin) ResetBook(id int) {
	s.Book.Reset(id, s.Criteria)
	s.WM.ResetRound()
	s.GlobalMult = 1
	s.FinalWin = 0
	s.Fs, s.TotFs = 0, 0
	s.WincapTriggered = false
	s.TriggeredFreegame = false
	s.GameType = s.baseType
	s.Repeat = false
	s.Forced = s.Forced[:0]
	// Hand the arenas back. Safe here and only here: the previous book has been
	// fully serialised by the time the next one starts.
	s.revealUsed, s.intUsed = 0, 0
}

// ---------------------------------------------------------------- board draws

// DrawBoard draws a board for the current distribution and gametype.
//
// Port of Board.draw_board. Three branches, and the middle one is easy to miss:
// in the basegame, a NON-forced distribution REDRAWS until the board shows fewer
// than the minimum trigger count. That is why a base-mode "basegame" or "0" slice
// can never accidentally trigger the feature, and why scatter density on BR0 does
// not set the trigger rate -- the distribution quotas do.
func (s *Spin) DrawBoard(emitReveal bool) error {
	strip, id, err := s.pickStrip()
	if err != nil {
		return err
	}
	trig := s.Cfg.AnticipationTriggers[s.GameType]
	minTrigger := s.minTriggerCount()

	switch {
	case s.Dist.Conditions.ForceFreegame && s.GameType == s.baseType:
		want := s.pickScatterCount()
		if err := s.Board.ForceScatters(s.Reels, id, strip, s.Syms, want, trig, s.RNG); err != nil {
			return err
		}
	case !s.Dist.Conditions.ForceFreegame && s.GameType == s.baseType:
		s.Board.Draw(id, strip, s.Syms, trig, s.RNG)
		for s.Board.ScatterCount() >= minTrigger {
			s.Board.Draw(id, strip, s.Syms, trig, s.RNG)
		}
	default:
		s.Board.Draw(id, strip, s.Syms, trig, s.RNG)
	}

	if emitReveal {
		s.EmitReveal()
	}
	return nil
}

func (s *Spin) pickStrip() (Strip, string, error) {
	weights, ok := s.Dist.Conditions.ReelWeights[s.GameType]
	if !ok {
		return nil, "", fmt.Errorf("%s/%s: no reel weights for gametype %q",
			s.Mode.Name, s.Criteria, s.GameType)
	}
	id := pickWeightedString(weights, s.RNG)
	strip, err := s.Reels.Strip(id)
	return strip, id, err
}

// pickWeightedString selects from a weight map.
//
// ⚠ Sorted keys, not map order: Go randomises map iteration, so picking straight
// from the map would make the same seed produce different strips between runs --
// a non-reproducible pool that still looks statistically fine.
func pickWeightedString(weights map[string]int, g *RNG) string {
	if len(weights) == 1 {
		for k := range weights {
			return k
		}
	}
	return NewWeightedStrings(weights).Pick(g)
}

func (s *Spin) pickScatterCount() int {
	trig := s.Dist.Conditions.ScatterTriggers
	if len(trig) == 1 {
		return trig[0].Scatters
	}
	m := make(map[int]int, len(trig))
	for _, t := range trig {
		m[t.Scatters] = t.Weight
	}
	return NewWeightedInts(m).Pick(s.RNG)
}

func (s *Spin) minTriggerCount() int {
	best := -1
	for count := range s.Cfg.SpinsByScatter[s.GameType] {
		if best == -1 || count < best {
			best = count
		}
	}
	return best
}

// ------------------------------------------------------------------ win logic

// EvaluateLines scores the board, banks the win and emits the win events.
func (s *Spin) EvaluateLines() {
	s.Lines.Evaluate(s.Board, s.GlobalMult, s.Wins)
	s.recordLineWins()
	s.WM.UpdateSpinWin(s.Wins.TotalWin)
	if s.WM.SpinWin > 0 {
		s.EmitWinInfo()
		s.EvaluateWincap()
		s.EmitSetWin()
	}
	s.EmitSetTotal()
}

// recordLineWins builds the force-record entries the optimizer fences on.
func (s *Spin) recordLineWins() {
	for i := range s.Wins.Wins {
		w := &s.Wins.Wins[i]
		s.Forced = append(s.Forced, ForceKey{
			Kind: w.Kind, Symbol: s.Syms.Name(w.Symbol),
			Mult: w.Mult, GameType: s.GameType,
		})
	}
}

// EvaluateWincap stops the book once the mode ceiling is reached.
func (s *Spin) EvaluateWincap() bool {
	if s.WM.RunningBetWin >= s.Cap() && !s.WincapTriggered {
		s.WincapTriggered = true
		s.Book.Add(Event{Type: EvWincap, Amount: i64(cents(s.WM.RunningBetWin, s.Cap()))})
		return true
	}
	return false
}

// UpdateFinalWin clamps and records the round's payout.
//
// state.py:192 clamps the TOTAL, which is what becomes payoutMultiplier -- so no
// book ever pays above its ceiling. The base and free split fields are clamped
// SEPARATELY on the next two lines, which is why on a capped book they can sum to
// slightly more than the payout. Reproduced as-is: the SDK's own assert permits
// it and the published payout is correct either way.
func (s *Spin) UpdateFinalWin() {
	cap := s.Cap()
	s.FinalWin = roundCents(min(s.WM.RunningBetWin, cap))
	s.Book.PayoutMultiplier = s.FinalWin
	s.Book.BasegameWins = roundCents(min(s.WM.BasegameWins, cap))
	s.Book.FreegameWins = roundCents(min(s.WM.FreegameWins, cap))
	s.Book.Add(Event{Type: EvFinalWin, Amount: i64(cents(s.FinalWin, cap))})
}

// CheckRepeat decides whether this simulation must be redrawn.
//
// A distribution with a win_criteria only accepts books paying exactly that --
// the mechanism behind the forced wincap slices. A force_freegame distribution
// that never reached the feature is likewise rejected.
func (s *Spin) CheckRepeat() {
	if !s.Repeat {
		if s.Dist.WinCriteria != nil && s.FinalWin != *s.Dist.WinCriteria {
			s.Repeat = true
		} else if s.Dist.Conditions.ForceFreegame && !s.TriggeredFreegame {
			s.Repeat = true
		}
	}
	s.RepeatCount++
}

// ------------------------------------------------------------------- freespins

// CheckFsCondition reports whether the board triggers the feature.
func (s *Spin) CheckFsCondition() bool {
	return s.Board.ScatterCount() >= s.minTriggerCount() && !s.Repeat
}

// ResetFsSpin prepares the feature loop.
func (s *Spin) ResetFsSpin() {
	s.TriggeredFreegame = true
	s.Fs = 0
	s.GameType = s.freeType
	s.WM.ResetSpinWin()
}

// UpdateFreespin advances the spin counter and emits the counter event.
func (s *Spin) UpdateFreespin() {
	s.Book.Add(Event{Type: EvUpdateFreeSpin, Amount: i64(int64(s.Fs)), Total: ip(s.TotFs)})
	s.Fs++
	s.WM.ResetSpinWin()
}

// EndFreespin emits the feature's closing total.
func (s *Spin) EndFreespin() {
	s.Book.Add(Event{
		Type:     EvFreeSpinEnd,
		Amount:   i64(cents(s.WM.FreegameWins, s.Cap())),
		WinLevel: s.winLevel(s.WM.FreegameWins, true),
	})
}

// RecordTrigger adds the feature-trigger force key the optimizer fences on.
//
// ⚠ Kind is the SCATTER COUNT. Base and ante search {"symbol":"scatter"} for
// three different tiers, and without the count all three fences match the same
// books -- the first one swallows every feature book and the rest match zero.
func (s *Spin) RecordTrigger(count int) {
	s.Forced = append(s.Forced, ForceKey{
		Kind: count, Symbol: "scatter", GameType: s.GameType,
	})
}
