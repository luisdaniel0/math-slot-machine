package starwake

import (
	"fmt"

	"starwake/internal/sdk/config"
	"starwake/internal/sdk/engine"
)

// Game is one worker's Starwake engine: the shared SDK spin state plus this
// game's feature state.
type Game struct {
	*engine.Spin
	Feature *FeatureConfig
	Con     *Constellation
	Tier    string
	wild    engine.SymID
	padded  bool
}

// NewGame builds a worker.
func NewGame(c *config.Config, fc *FeatureConfig) (*Game, error) {
	st, err := engine.NewSymbolTable(c)
	if err != nil {
		return nil, err
	}
	rs, err := engine.NewReelSet(c, st)
	if err != nil {
		return nil, err
	}
	// max_symbol, not the SDK default: the beast is a BLOCK wild stamping one
	// multiplier across every cell it covers, and summing would pay a line
	// crossing two of them twice the advertised rung.
	le, err := engine.NewLineEvaluator(c, st, engine.MultMaxSymbol)
	if err != nil {
		return nil, err
	}
	sp, err := engine.NewSpin(c, st, rs, le)
	if err != nil {
		return nil, err
	}
	return &Game{
		Spin: sp, Feature: fc,
		wild:   st.MustID("W"),
		padded: c.Game.IncludePadding,
	}, nil
}

// RunSpin simulates one book, redrawing until it satisfies its distribution.
//
// Port of gamestate.run_spin.
func (g *Game) RunSpin(sim int, seed uint64) error {
	g.RNG = engine.NewRNG(seed)
	g.Repeat = true
	g.RepeatCount = 0

	for g.Repeat {
		g.ResetBook(sim)
		g.Con, g.Tier = nil, ""

		if err := g.DrawBoard(true); err != nil {
			return err
		}
		g.EvaluateLines()
		if err := g.WM.UpdateGametypeWins(g.GameType, g.Cfg.Game.BasegameType, g.Cfg.Game.FreegameType); err != nil {
			return err
		}

		if g.CheckFsCondition() {
			if err := g.runFeature(); err != nil {
				return err
			}
		}

		g.UpdateFinalWin()
		g.checkRepeat()
	}
	return nil
}

// FeatureOutcome reports what the accepted book's feature did, for the
// measure-loop summary.
//
// Valid after RunSpin returns: the redraw loop clears g.Con at the top of each
// attempt, so what survives is the constellation of the book that was KEPT.
//
// roamSpins is rung+1, not rung: the beast shows rung 0 on the spin it first
// appears (a roam spin that pays but does not climb), and each later roam takes
// the next rung. That is the same count Python's measure harness gets from
// counting beastRoam events.
func (g *Game) FeatureOutcome() (dealt, completed bool, roamSpins, topRung int) {
	if g.Con == nil {
		return false, false, 0, 0
	}
	if g.Con.Phase() != PhaseRoam {
		return true, false, 0, 0
	}
	return true, true, g.Con.Rung() + 1, g.Con.Multiplier()
}

// checkRepeat is Starwake's redraw rule on top of the SDK's.
//
// Port of game_override.check_repeat. ⚠ THE EXTRA RULE IS LOAD-BEARING AND EASY
// TO MISS: a distribution with NO win_criteria rejects any book paying ZERO.
//
// That single line is what actually delivers "buy modes bust 0.00%" -- it is a
// REDRAW, not a structural property of the feature. A cold-start feature that
// never lands a win really does exist (roughly 1 in 40 corvus deals: a ~32%
// per-spin hit rate over 10 spins leaves ~2.4% with no win at all), and Python
// simply throws those books away and draws again. Omitting this leaves the math
// looking plausible while every buy mode busts a few percent of the time and its
// RTP sits low by exactly that share.
//
// The "0" slices in base/ante are unaffected: they set win_criteria = 0.0, so
// win_criteria is non-nil and a zero payout is exactly what they want.
func (g *Game) checkRepeat() {
	g.Spin.CheckRepeat()
	if g.Repeat {
		return
	}
	if g.Dist.WinCriteria == nil && g.FinalWin == 0 {
		g.Repeat = true
	}
}

// runFeature records the trigger, awards the spins and runs the feature.
func (g *Game) runFeature() error {
	count := g.Board.ScatterCount()
	g.RecordTrigger(count)

	// 6+ scatters clamp to the top tier. Defensive: draw_board redraws away every
	// unforced board with >=3 scatters and the forced branch pins an exact count,
	// so a 6 only exists where 6 was asked for. Kept because exact-count indexing
	// is what KeyError'd on Keybearer's scatter-rich strips.
	maxCount := 0
	for c := range g.Cfg.SpinsByScatter[g.GameType] {
		if c > maxCount {
			maxCount = c
		}
	}
	if count > maxCount {
		count = maxCount
	}

	spins, ok := g.Cfg.SpinsByScatter[g.GameType][count]
	if !ok {
		return fmt.Errorf("%d scatters awards no spins in %s", count, g.GameType)
	}
	tier, ok := g.Cfg.TierByScatter[count]
	if !ok {
		return fmt.Errorf("%d scatters deals no tier", count)
	}
	g.TotFs = spins
	g.Tier = tier
	g.EmitFsTrigger()

	return g.RunFreespin()
}

// RunFreespin is the fixed-length Charge -> Bloom -> Roam feature.
//
// Port of gamestate.run_freespin. ⚠ THE ORDER IS LOAD-BEARING:
//
//	draw (reveal held) -> stamp wilds + beast -> reveal -> evaluate -> light -> wake
//
// Stamping BEFORE evaluation is the snowball: existing sticky wilds inflate this
// spin's wins, which light more cells, which are wilds next spin. Holding the
// reveal until after stamping is what makes the board the player sees actually
// show its wilds. Lighting AFTER evaluation is why the completing spin cannot
// also carry the beast -- it appears the spin after.
func (g *Game) RunFreespin() error {
	g.ResetFsSpin()

	tier, err := g.Feature.Tier(g.Tier)
	if err != nil {
		return err
	}
	con, err := NewConstellation(tier, g.Tier, g.Cfg)
	if err != nil {
		return err
	}
	g.Con = con
	g.emitConstellationDealt()

	beastHasAppeared := false

	for g.Fs < g.TotFs {
		g.UpdateFreespin()
		if err := g.DrawBoard(false); err != nil {
			return err
		}

		// An awake beast rides onto THIS board before evaluation. On its first
		// appearance it sits where it woke; after that it roams and climbs.
		if con.Phase() == PhaseRoam {
			if beastHasAppeared {
				if err := con.Roam(g.RNG); err != nil {
					return err
				}
				g.emitBeastRoam()
				g.emitMultiplierClimb()
			} else {
				beastHasAppeared = true
				g.emitBeastRoam()
			}
		}

		con.ApplyWilds(g.Board, g.wild)
		g.EmitReveal()
		g.EvaluateLines()

		// This spin's winning lines trace the constellation.
		var crossed CellMask
		g.Wins.WinningCells(func(reel, row int) {
			crossed |= Bit(reel, row)
		})
		if newly := con.LightFromWins(crossed); len(newly) > 0 {
			g.emitStarLit(newly)
		}

		// Just completed? Wake the beast; it appears next spin.
		if con.Phase() == PhaseCharge && con.IsComplete() {
			if err := con.Wake(g.RNG); err != nil {
				return err
			}
			g.emitBeastWake()
			// Guarantee the roam window. An early completion already has the
			// spins (tot_fs untouched -- "finish early = longer roam", the fat
			// tail); only a LATE completion extends the feature, so "even a
			// last-spin completion still pays". Same mid-feature mutation shape
			// as a retrigger.
			if want := g.Fs + g.Feature.MinRoamSpins; want > g.TotFs {
				g.TotFs = want
			}
		}

		if err := g.WM.UpdateGametypeWins(g.GameType, g.Cfg.Game.BasegameType, g.Cfg.Game.FreegameType); err != nil {
			return err
		}
	}

	g.EndFreespin()
	return nil
}

// ---------------------------------------------------------------- game events
//
// Mirrors games/starwake/game_events.py. All positions are CLIENT coordinates
// (row+1 when padded), matching reveal and winInfo.

func (g *Game) clientCells(cells []config.Cell) []engine.Pos {
	out := make([]engine.Pos, len(cells))
	for i, c := range cells {
		out[i] = engine.Pos{Reel: c.Reel, Row: engine.PadRow(c.Row, g.padded)}
	}
	return out
}

func (g *Game) maskCells(m CellMask) []engine.Pos {
	var out []engine.Pos
	for reel := 0; reel < g.Board.NumReels; reel++ {
		for row := 0; row < g.Board.NumRows[reel]; row++ {
			if m.Has(reel, row) {
				out = append(out, engine.Pos{Reel: reel, Row: engine.PadRow(row, g.padded)})
			}
		}
	}
	return out
}

func (g *Game) emitConstellationDealt() {
	con := g.Con
	prelit := g.maskCells(con.Lit())
	if prelit == nil {
		// Non-nil empty, so the key still ships as [] for every normal tier.
		prelit = []engine.Pos{}
	}
	litCount := len(prelit)
	g.AddEvent(engine.Event{
		Type:       "constellationDealt",
		Tier:       con.Tier,
		Beast:      con.BeastName,
		Cells:      g.clientCells(con.TargetCells()),
		TotalCells: len(con.TargetCells()),
		Prelit:     &prelit,
		LitCount:   &litCount,
	})
}

func (g *Game) emitStarLit(newly []config.Cell) {
	con := g.Con
	litCount := con.Lit().Count()
	complete := con.IsComplete()
	g.AddEvent(engine.Event{
		Type:       "starLit",
		NewlyLit:   g.clientCells(newly),
		LitCount:   &litCount,
		TotalCells: len(con.TargetCells()),
		Complete:   &complete,
	})
}

func (g *Game) emitBeastWake() {
	con := g.Con
	tier, _ := g.Feature.Tier(con.Tier)
	g.AddEvent(engine.Event{
		Type:       "beastWake",
		Tier:       con.Tier,
		Beast:      con.BeastName,
		BeastShape: &engine.Shape{Reels: tier.BeastShape[0], Rows: tier.BeastShape[1]},
	})
}

func (g *Game) emitBeastRoam() {
	con := g.Con
	mult := con.Multiplier()
	g.AddEvent(engine.Event{
		Type:       "beastRoam",
		Cells:      g.maskCells(con.BeastCells()),
		Multiplier: &mult,
	})
}

func (g *Game) emitMultiplierClimb() {
	mult := g.Con.Multiplier()
	g.AddEvent(engine.Event{Type: "multiplierClimb", Multiplier: &mult})
}
