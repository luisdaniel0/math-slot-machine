package engine

// Event emitters. Each mirrors one function in src/events/events.py; the key
// names and shapes are a published interface (see events.go).

// EmitReveal publishes the drawn board.
//
// The board ships in CLIENT form: padded reels, so each reel is
// [topPadding, ...visible rows..., bottomPadding] and every other event's row
// index is shifted by one to match.
func (s *Spin) EmitReveal() {
	b := s.Board
	board := s.nextRevealBoard()
	for reel := 0; reel < b.NumReels; reel++ {
		row := 0
		if s.padded {
			board[reel][row] = s.revealSym(b.TopSymbols[reel], 0)
			row++
		}
		for r := 0; r < b.NumRows[reel]; r++ {
			cell := b.Cells[reel][r]
			board[reel][row] = s.revealSym(cell.Sym, cell.Mult)
			row++
		}
		if s.padded {
			board[reel][row] = s.revealSym(b.BottomSymbols[reel], 0)
		}
	}
	s.Book.Add(Event{
		Type:             EvReveal,
		Board:            board,
		PaddingPositions: s.nextInts(b.ReelPositions[:b.NumReels]),
		GameType:         s.GameType,
		Anticipation:     s.nextInts(b.Anticipation[:b.NumReels]),
	})
}

func (s *Spin) revealSym(id SymID, mult uint16) RevealSym {
	rs := RevealSym{Name: s.Syms.Name(id)}
	if s.Syms.IsWild(id) {
		rs.Wild = true
	}
	if s.Syms.IsScatter(id) {
		rs.Scatter = true
	}
	// Python emits the multiplier attribute only when it is set and truthy.
	if mult > 0 {
		rs.Multiplier = int(mult)
	}
	return rs
}

// EmitWinInfo publishes this reveal's line wins.
func (s *Spin) EmitWinInfo() {
	cap := s.Cap()
	wins := make([]WinJSON, 0, len(s.Wins.Wins))
	for i := range s.Wins.Wins {
		w := &s.Wins.Wins[i]
		positions := make([]Pos, w.Kind)
		for reel := 0; reel < w.Kind; reel++ {
			positions[reel] = Pos{Reel: reel, Row: PadRow(int(w.Rows[reel]), s.padded)}
		}
		wins = append(wins, WinJSON{
			Symbol:    s.Syms.Name(w.Symbol),
			Kind:      w.Kind,
			Win:       cents(w.Win, cap),
			Positions: positions,
			Meta: WinMeta{
				LineIndex:      w.LineIndex,
				Multiplier:     w.Mult,
				WinWithoutMult: cents(w.WinNoMult, cap),
				GlobalMult:     s.GlobalMult,
				LineMultiplier: w.Mult / maxInt(s.GlobalMult, 1),
			},
		})
	}
	s.Book.Add(Event{
		Type:     EvWinInfo,
		TotalWin: i64(cents(s.Wins.TotalWin, cap)),
		Wins:     wins,
	})
}

// EmitSetWin updates the win ticker for one reveal.
//
// Suppressed once the wincap has fired: past that point the round is over and
// the client should not tick further.
func (s *Spin) EmitSetWin() {
	if s.WincapTriggered {
		return
	}
	s.Book.Add(Event{
		Type:     EvSetWin,
		Amount:   i64(cents(s.WM.SpinWin, s.Cap())),
		WinLevel: s.winLevel(s.WM.SpinWin, false),
	})
}

// EmitSetTotal updates the round's cumulative total.
func (s *Spin) EmitSetTotal() {
	s.Book.Add(Event{
		Type:   EvSetTotalWin,
		Amount: i64(cents(s.WM.RunningBetWin, s.Cap())),
	})
}

// EmitFsTrigger announces the feature and the spins awarded.
func (s *Spin) EmitFsTrigger() {
	positions := make([]Pos, 0, s.Board.ScatterCount())
	for _, sc := range s.Board.Scatters {
		positions = append(positions, Pos{
			Reel: int(sc.Sym),
			Row:  PadRow(int(sc.Mult), s.padded),
		})
	}
	s.Book.Add(Event{
		Type:      EvFreeSpinTrigger,
		TotalFs:   s.TotFs,
		Positions: positions,
	})
}

// AddEvent lets a game append its own event to the tape.
func (s *Spin) AddEvent(e Event) { s.Book.Add(e) }

// winLevel buckets a win for the client's celebration tier.
//
// Port of Config.get_win_level. The bands are relative to the MODE ceiling, so a
// buy_corvus book is bucketed against 10,000x rather than the global 25,000x.
func (s *Spin) winLevel(amount float64, endFeature bool) int {
	cap := s.Cap()
	var bounds [10]float64
	if endFeature {
		bounds = [10]float64{0, 1, 5, 10, 20, 50, 100, 500, 2000, cap}
	} else {
		bounds = [10]float64{0, 0.1, 1, 2, 5, 15, 30, 50, 100, cap}
	}
	for i := 0; i < len(bounds); i++ {
		lo := bounds[i]
		hi := cap
		if i+1 < len(bounds) {
			hi = bounds[i+1]
		}
		if i == len(bounds)-1 {
			if amount >= lo {
				return 10
			}
			break
		}
		if amount >= lo && amount < hi {
			return i + 1
		}
	}
	return 10
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
