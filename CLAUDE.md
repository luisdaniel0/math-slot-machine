# Starwake — Stake Engine lines slot (in development)

Celestial constellation game, scaffolded from `games/0_0_lines`.
Learner project: build step-by-step, explain decisions, don't bulk-complete.
FULL design doc + rationale for every decision: `docs/ideas/starwake.md` (read it
before proposing design changes — most "open questions" are already resolved there).
Keybearer & knockout_mayhem are SCRATCHED (code remains in games/ as reference only;
`games/0_0_keybearer` has the proven 5x4 paylines set and Vault/global-mult code).

## Design spec (the blueprint — build to this)

- **Identity:** Lines, 5x4, 20 paylines (4-row set, done), high volatility,
  wincap 25,000x (= the 2-star cap exactly; zero headroom).
- **RTP:** converge every mode to ~0.9665–0.9669 → displays 96.7%, always ≤ 0.967
  Stake cap. All 6 modes must sit within a 0.5% band (market bar is ±0.02%).
- **Signature mechanic (feature-only): Charge → Bloom → Roam.**
  Star scatters ("S") trigger by count: 3/4/5 → Corvus (4-star) / Ursa Major (7-star)
  / Draco (11-star). The dealt constellation appears as dim outlines on specific grid
  cells; a cell LIGHTS when a WINNING PAYLINE CROSSES IT (the win "traces" the
  constellation). NOTE: this replaced the earlier star-landing / λ / fly-to-cell
  fill rule — no star-landing rate anymore; fill is driven by wins. Each lit cell =
  STICKY WILD for the rest of the feature → SNOWBALL (lit wild → more wins → more
  cells light). Complete the set → beast wakes: a 2x2 block wild (ALL THREE tiers —
  a 3x3 has only 6 roam positions on a 5x4, which breaks the roam on the showpiece
  tier; tier identity rides the 4/7/11 sticky cells instead) that ROAMS to a random
  position each spin (C&C/MIKO style; fine because the fat tail depends on how LONG
  it stays, not the path — it never exits), multiplier climbs one GEOMETRIC LADDER
  rung per roam spin (enumerable — compliance requires listing all values).
  Guaranteed min roam window (2 spins; a late completion extends the feature to honor
  it). Feature length is FIXED PER TIER — Corvus 10, Ursa/Draco 15 — with no
  retrigger; the split is a PRICE lever (spins move completion, completion is what a
  buy's economy rides on), not a volatility one.
  Completion rates are now SIM-DERIVED (coupon-collector model retired);
  tier ladder still holds (more cells = harder) BUT constellation SHAPE now matters
  (cells on more paylines light faster). Cold-start risk: no early wins → snowball
  never ignites → near-bust; may need a fill floor.
- **Tier volatility identity:** Corvus = reliable beast hunt; Ursa = coin flip
  (the streamable one); Draco = wild carpet + dragon lottery. Wincap path = big
  constellation completed EARLY (falls out structurally; slice weight ≥ ~1e-6).
- **Draco can't be pure nothing-or-jackpot (compliance):** ETL ≤ 0.8 (≤80% of a
  mode's RTP from big wins) + "no win-range gaps" REQUIRE intermediate wins, so
  partial progress (the carpet) MUST pay ~20%+ of each mode's RTP. The win-line
  snowball produces this spread naturally (fizzle→warm carpet→dragon continuum) —
  it's better-suited to ETL than a binary fill would be — but the COLD end must not
  bust too hard (watch buy-mode bust rate; add a fill floor if needed).
- **6 bet modes:** `base` (1x) | `ante_starfall` (~1.5–3x, denser stars: more
  triggers AND richer tier mix, LOWER vol — classic MIKO-style ante, NOT C&C's
  lottery type) | `buy_corvus` | `buy_ursa` | `buy_draco` | `buy_mystery`
  ("Let the Sky Decide", weighted random tier, probabilities must display
  accurately). Buy prices are OUTPUTS (avg win ÷ rtp), never inputs.
- **Symbols:** W (wild), S (Star: scatter + constellation filler, one symbol both
  contexts), H1–H4 (constellation beasts: Leo/Cygnus/Aquila/Lupus), L1–L5 (card
  ranks as constellation line-art). Paytable NOT YET DESIGNED (next step).
- **Base game:** standard scatter hunt (meter idea was tried & reverted — needs
  cascades). Base-boost question deliberately parked until first playtest.
- **Benchmarks (measured, stakestats.net):** base bust 70–83% OK, win-freq ≥1x
  ~7.4% market norm, base std dev < 50 (2-star cap; expect ~35–48), ~40–60% of RTP
  above 100x is approvable. Full table in the design doc.

## Build status
- [x] Concept + design doc complete (docs/ideas/starwake.md) — mechanic, tiers,
      modes, compliance gates, benchmarks all locked with rationale.
- [x] Fork → `games/starwake`: 5x4, 20 four-row paylines (keybearer set), wincap
      25000, rtp 0.9665, scatter S=Star. Smoke-verified: 6k books both modes ~7s;
      25,000x wincap forces even on sample math (>1000-repeat warnings expected
      until WCAP strips exist). run.py pinned to sims-only smoke settings.
- [x] Paytable: W 5-kind-only 60x (override fix + carpet economy control), H1
      3/12/50 steep ladders, low 3-kinds dust 0.2-0.5 (crumb texture funds hit
      floor cheaply, budget stays in tail). Values = total-bet multiples PER LINE,
      stacking (verified in src/calculations/lines.py). Smoke-verified. First-pass
      numbers — the measure loop will re-tune.
- [x] Trigger table [SPIN COUNT SUPERSEDED Jul 28 -> per-tier 10/15/15; the rest
      stands]: fixed 10 spins ALL tiers (config.num_feature_spins), no
      retriggers (removed from run_freespin), 6+ scatters clamp to draco
      (update_freespin_amount override), count→tier mapping stored as
      gamestate.constellation_tier (config.scatter_tiers). Book-verified:
      every feature book both modes awards exactly totalFs=10, zero retriggers.
- [x] Feature engine: constellation state machine (deal/charge/sticky/bloom/roam)
      + events constellationDealt/starLit/beastWake/beastRoam/multiplierClimb.
      Built as a PURE object (games/starwake/constellation.py) unit-tested in
      isolation FIRST (tests/starwake/test_constellation.py, 13 tests: lit->wild,
      snowball via real Lines, beast never exits, enumerable ladder) — Vault lesson
      honored. Wired into run_freespin (draw noreveal->apply_wilds->reveal->eval->
      light->wake/roam). Events game-local (game_events.py; auto-discovered by the
      event_config generator). Option A chosen: BEAST is the ONLY multiplier
      (sticky stars x1); inherited freegame wild-mult neutralized in game_override.
      Smoke-verified: book tape correct, snowball visible (wins escalate as wilds
      stick), beast roams on-grid climbing 2->10. ONE KNOWN FOLLOW-UP REMAINS:
      completion ladder
      INVERTED on scaffold strips (Draco ~59% > Ursa ~52%; Draco should be rarest)
      — the snowball makes 5-kind wins common, and 5-kinds span all reels so they
      cross the "hard" reels-3-4 cells anyway, collapsing reel-position difficulty.
      Fix is TUNING (drier FR strips / harder Draco shape / dampen snowball), needs
      real strips + natural (unforced) sims. Engine is correct; rates are a knob.
- [x] Constellation cell-maps in config.constellation_cells (reel,row per tier).
      First-pass shapes with difficulty from REEL POSITION (left 3 reels light easily,
      reels 3-4 need long wins): hard-cell ladder Corvus 0 / Ursa 2 / Draco 5 = the
      tier ladder. Validated (counts 4/7/11, on-grid, no dupes). Exact rates
      sim-derived — nudge cells in the measure loop. Cell-map figure shown in chat.
- [x] Guaranteed roam window [FLOOR SUPERSEDED Jul 27 -> 2, because at 5 it was
      carrying ~70% of buy_draco's value and CREATING the win-range gap; the
      extend-to-honor-the-floor MECHANISM below is unchanged and still tested].
      (config.min_roam_spins = 5). A late completion (fewer
      than 5 spins left) EXTENDS tot_fs to fs+min_roam so the woken beast always gets
      ≥5 on-board/paying spins ("even a last-spin completion still pays"); early
      completions are untouched, keeping "finish early = longer roam" (the fat tail).
      It is a FLOOR, not a flat +5: roam = max(10-K, 5); worst-case length 15 (complete
      on spin 10). Same mid-feature tot_fs mutation as a retrigger; update_fs events
      report the extended total. Integration-tested — tests/starwake/test_run_freespin.py
      drives the real run_freespin loop with scripted completion timing (7 tests);
      verified in real books too (187/1000 smoke books extended past 10).
- [x] Reel strips via re-runnable weight-table script
      (games/starwake/reels/generate_reels.py — "edit a weight, re-run", seeded).
      CORRECTED MENTAL MODEL: trigger RATE + TIER MIX are DISTRIBUTION-driven (betmode
      quotas + scatter_triggers), NOT strip star density — draw_board redraws away
      >=3-scatter boards in the non-forced branch and forces the count in the forced
      branches (verified: bonus tier mix 67/25/8% tracks freegame {3:50,4:20,5:5}).
      So strips = WIN composition only: BR0 lows-heavy (hit-rate = RTP dial) + wilds
      rare + ~5 stars/reel just to seed forced triggers/anticipation; FR0 wild-rich
      (~8%, NO stars) = the snowball → completion+roam; FRWCAP juiced (~20% W + H1
      boost, NO stars). First-pass UNIFORM weights, sim-tunable. Baseline on new
      strips (1k bonus books): completion corvus 96.9% / ursa 69.8% / draco 64.5% —
      the scaffold INVERSION is FIXED (draco now < ursa; the scaffold's reel-4-densest
      wilds were the accident). REMAINING = measure-loop tuning: separate + lower
      ursa/draco (target ~50% / rare) via FR wild density (lever 1), then per-reel
      reels-3-4 FR drying (lever 2, machinery not built yet) or harder Draco shape
      (lever 3, game_config.constellation_cells).
- [x] 6 bet modes STRUCTURAL pass (game_config.bet_modes): base | ante_starfall |
      buy_corvus | buy_ursa | buy_draco | buy_mystery. Tier forced by scatter_triggers
      (a _tier_condition(count) helper; {3/4/5:1} pin corvus/ursa/draco), mystery =
      weighted {3:60,4:30,5:10}. Only Draco reaches 25k so every wincap slice forces
      {5:1}+WCAP; buy_corvus/buy_ursa carry NO wincap slice (unreachable cap would
      loop). Smoke-verified all 6 (run.py sims all 6): tiers force correctly (buys
      100% their tier), buys 0% zero, base mix 67/25/8, ante richer 62/27/10 + more
      triggers (16.5%) + fewer zeros (smoother), mystery 62/26/11 (wincap nudges
      draco). Measured ceilings: corvus 9965x / ursa 15581x (HONEST lower ceilings,
      confirmed <25k) / draco+mystery+base+ante 25000x. MEASURE-LOOP PENDING:
      (a) costs are placeholders -> set cost = avg win/rtp; (b) config.json currently
      writes maxWin 25000 for ALL modes -> set BetMode.max_win for corvus/ursa to
      their real 1e6 ceilings (smoke 9965/15581 understate the tail); (c) quotas +
      RTP convergence to ~0.9665 all 6 modes; (d) mystery DISPLAYED odds = measured
      post-opt proportions.
- [x] Optimization opt_params rewritten for all 6 modes (game_optimization.py).
      Per-criteria RTP splits sum to 0.9665 (verify_optimization_input PASSES), small
      DRY builders (wincap_cond/feature_cond/base_cond), per-mode m2m bands encoding
      the vol identity (buy_draco 5-20 highest, buy_corvus 1.5-5 lowest, ante 2-6).
      Note ConstructConditions needs rtp PLUS an hr/av_win hint (rtp alone trips its
      guard). FIRST-PASS targets (rtp splits, hr hints, m2m, scaling) -- the measure
      loop tunes them against 1e6 reality. Optimizer binary (PigFarmRust) is BUILT.
      NOT yet run: convergence on smoke-count pools is ambiguous, validate at 1e6.
- [x] Run → measure loop PHASE A (completion ladder) DONE. FR drying via per-reel
      generate_reels.py (base + per_reel overrides): FR0 wet left / dry right (reels
      0-2 W=12, reel 3 W=3, reel 4 W=0). Ladder 97/70/66 -> 95/54/28 (corvus/ursa/
      draco, buy-mode books). Draco RESHAPED to fix the ~46% plateau: KEY FINDING
      (sim-derived, no analytic rate) -- completion is driven overwhelmingly by how
      many hard cells sit on reel 4, the DRIEST strip (W=0), NOT by payline traffic
      or adjacency (my first traffic-based reshape went the WRONG way, 46->57%). New
      draco hard cells = FULL reel-4 column (4,0..4,3) + one easy reel-3 neck (3,2);
      full column alone ~11-15%, the neck lifts to ~28% (the ~30% dragon-lottery
      target; neck row 1 -> ~36% is the finer knob). Corvus/ursa unchanged (separate
      cell-maps). VERIFIED: all 3 buys still bust 0.00% (carpet pays structurally
      despite 72% draco non-completion), buy_draco still reaches 25000x wincap.
      Sweep harness: scratchpad/sweep_draco.py (patches cells in-process, regens
      one mode, counts beastWake books). PHASE B (RTP convergence + costs/ceilings
      at 1e6) NOT started.
- [x] Optimize → verify at 1e6/mode — DONE Jul 29 2026, ALL SIX MODES CONVERGED on the
      post-rebuild config. See "▶▶ FULL 1e6 RE-CONVERGE (Jul 29 2026)" below for the
      table, the two optimizer bugs it exposed, and the base-volatility investigation.
- [ ] event-ID finder for reviewer scenarios

- [x] ECONOMY RE-TUNE (the buy prices were ~10x too high; cost = avg win/rtp, and
      Stake caps buy cost at 1000x). Buy cost 2208/2907/7258x -> **224/283/651x**,
      correctly ordered, all under the gate, 0.00% zero-pay throughout. Four changes:
      (1) MULTIPLIER BUG -- the beast stamps its multiplier on EVERY block cell and
      the SDK's "symbol" strategy SUMS multipliers along a line, so a payline crossing
      2 block cells paid 2*M (3*M for the 3-wide blocks). 87% of buy_corvus's payout
      came from double-crossings, and the enumerable ladder was really {M,2M,3M}.
      Fixed with a new `max_symbol` strategy (src/wins/multiplier_strategy.py, also
      made apply_mult dispatch lazily instead of building all strategies per line win);
      game_executables opts in. (2) PAYTABLE asymmetric rescale 5-kinds /4, 4-kinds /2,
      3-kinds HELD -- feature takes 61% of its money from 5-kinds vs base's 13%, so
      this drains the feature x2.49 for only x1.29 off the base. (3) PER-TIER MULT
      LADDERS replacing beast_start_mult/beast_climb: explicit lists, rung per roam
      spin, clamped at the top (config.constellation_mult_ladders). (4) FR0 dried
      12->4 on reels 0-2.
- [x] PHASE B RUN AT 1e6/MODE + OPTIMIZER CONVERGED. All six modes land on
      RTP 0.9665/0.9665/0.9665/0.9665/0.9652/0.9661, band spread 0.126% (limit 0.5%),
      every mode <= the 0.9670 Stake ceiling. Base hit rate 29.25% (1 in 3.4, gate is
      1 in 20). Two optimizer-config bugs found and fixed, BOTH about fence ORDER --
      fences are assigned in sequence and CONSUME the books they match:
      (a) base/ante had three tier fences all searching {"symbol":"scatter"}, so draco
      swallowed all ~100k feature books and the run died with "ursa matched 0 books".
      Fixed by adding kind=5/4/3 (the scatter count the engine already records at
      trigger) -- exactly what keybearer's game_optimization.py:40 already did.
      (b) basegame is the ONLY fence with no identity condition (a catch-all) and it
      sat BEFORE the "0" fence, absorbing the zero-win books that "0" should hold.
      That skewed the weight denominator and every slice overshot by a UNIFORM 1.019x
      (base 0.9850, ante 0.9781 -- both over the ceiling). Moving "0" ahead of the
      catch-all made every slice hit its target to 4dp. NOTE verify_optimization_input
      catches NEITHER: it only checks the rtp splits sum and that criteria match.
- [x] PER-MODE DISPLAYED CEILINGS. corvus/ursa published maxWin 25000 they cannot
      reach; now 1500x and 4750x, rounded DOWN from the measured natural maxima
      (1,515.35x / 4,773.80x) so only the sliver above clamps -- RTP untouched to 5dp,
      band spread still 0.126%, buys still 0.00% zero. KEY MECHANIC: BetMode.max_win is
      BOTH the published maxWin (write_configs.py:356 -> config.json bookShelfConfig)
      AND the engine clamp (run_sims.py:48 -> config.wincap; state.py:256 rebuilds
      WinManager per thread from it; executables.evaluate_wincap ends the book at it).
      So a ceiling is honest ALMOST by construction once set -- ⚠ CORRECTED Jul 29 2026,
      "a deeper future sample can never exceed it" IS FALSE. win_manager.py:55-57 clamps
      basegame and freegame wins SEPARATELY and then SUMS them, so a book's true maximum
      is published maxWin + the trigger spin's own line win. Measured on the 1e6 pool:
      base tops out at 25,005x and ante at 25,004x against a published 25,000x (205 and
      307 books per 1e6; every one has freegame pinned to exactly 25000.00 with the base
      win added on top). Pre-existing -- the shipped Phase B pool did the same at
      25,005.5x -- and it is upstream SDK behaviour, not something Starwake introduced.
      Magnitude 0.02%, RTP cost of fixing it ~4e-6. MATTERS BECAUSE 25,000x IS THE 2-STAR
      TIER CAP WITH ZERO HEADROOM, so this pokes above the tier, not merely above our own
      config. One-line fix if wanted: `total_cumulative_wins += min(max_allowed_win,
      base + free)` -- but it is a shared SDK file and needs base/ante/buy_draco/
      buy_mystery re-simmed. The buy modes with NO basegame win on the trigger spin land
      exactly ON their cap (old corvus/ursa pools: 1 and 2 books at cap, zero above).
      Capped books
      are KEPT, not redrawn: check_repeat repeats only on a win_criteria mismatch or a
      missing freegame, and corvus/ursa set neither (verified -- if they had, the
      published ceiling would have been silently redrawn away and unreachable).
      Re-ran ONLY those two modes at 1e6 + optimizer (~30 min); the other four lookup
      tables were confirmed untouched by mtime. VERIFIED: both now top out at EXACTLY
      their cap, RTP 0.9665 both. Ceiling frequency on the NEW pool reads 1 in 428k
      (corvus) / 1 in 1.78M (ursa) vs 1 in 137k / 672k on the old one -- pure tail
      sampling noise at 1e6, where such an event is seen only 2-3 times; do not treat
      the top-bucket probability as a stable measurement.
- [x] ECONOMY REBUILD APPLIED + CONFIRMED AT 100k/TIER (Jul 28 2026). Per-tier
      feature length (corvus 10 / ursa 15 / draco 15), all beasts 2x2, roam floor 2,
      and the three swept ladders are now IN game_config.py; tests derive from config
      and guard the rung count (23 passing); the design doc's open questions on
      length / beast size / multiplier scale are struck through as resolved.
      Confirmation run reproduced the 20k sweep to within 4x on price (240 / 268 /
      520x) and CLOSED THE DRACO CLIFF on every tier -- cheapest completion now lands
      BELOW carpet max, widest hole <=1.24x and only in the >9,000x tail. Zero-pay
      still 0.00% on all three buys. Full table + the four things the deeper sample
      changed: "CONFIRMATION RUN @ 100k/TIER" below.
- [x] MYSTERY ODDS MEASURED on the converged 1e6 pool (Jul 29 2026): corvus 35.16% /
      ursa 29.64% / draco 25.15% / ASCENDANT 10.05%, summing to exactly 100%. Draco's
      figure INCLUDES the 0.04% forced-wincap slice, which uses draco_wincap_condition
      (5 scatters), so those books are Draco rolls and must be attributed to Draco, not
      shown as a fifth outcome. Ascendant carries 43.4% of the mode's payback on 10% of
      rolls -- the Rage Bait shape, now measured at 1e6 rather than swept at 20k.
      STILL TO DO: write these into the frontend copy. Display rounding to 35/29.6/25.2/
      10.0 is fine; the gate is that the displayed mix is the DELIVERED mix.
- [ ] event-ID finder

### ▶ THE ECONOMY REBUILD -- RATIONALE (Jul 27 2026; EXECUTED Jul 28, see below)
⚠ READ ORDER: this section and the two ladder sweeps under it are the WHY. They are
kept because every argument still holds, but the live numbers are in "CONFIRMATION
RUN @ 100k/TIER" and the live to-do list is "▶▶ NEXT SESSION STARTS HERE" -- both
further down. Where a number here disagrees with those, THEY win.

PHASE B WAS CONVERGED at 1e6 (costs 1 / 1.5 / 224 / 283 / 651 / 285x, ceilings
25000 / 25000 / 1500 / 4750 / 25000 / 25000) and is SUPERSEDED. The Jul 27 2026
session RESOLVED THE WHOLE ECONOMY DESIGN; what remains is execution. It is a full
Phase B re-converge (base/ante/mystery all contain Draco features).

TARGET STRUCTURE (decided Jul 27 2026):
  buy_corvus 200x | buy_ursa 300x | buy_draco 500x | buy_mystery 500x
  num_feature_spins 10 -> 15 | ALL beasts 2x2 | min_roam_spins 5 -> 2
  every tier gets a REAL ceiling (25,000x wherever structurally clean)
  buy_mystery = 35% corvus / 30% ursa / 25% draco / 10% DRACO ASCENDANT
  ⚠ MEASURED OUTCOME (Jul 28): prices came in at 240 / 268 / 520x -- draco on target,
  corvus 20% over, and the corvus-ursa gap nearly closed. "Every tier reaches
  25,000x" is DISPROVEN for corvus (natural max 11,438x, zero cap hits in 100k) and
  CONFIRMED for ursa. The 15-spin length also had to become per-tier: corvus reverted
  to 10 because at 15 no ladder could price it under ~375x.

WHY ALL-2x2 (measured this session):
- THE ROAM BARELY WORKS AT 3x3. Roam positions on a 5x4: 2x2=12, 2x3=8, 3x3=6,
  2x4=4. The 3x3 dragon shuffles between six spots covering 45% of the board --
  the signature "beast roams each spin" mechanic is undermined on the showpiece
  tier. Only 2x2 actually moves around a board.
- ONE beast size = one frontend sprite rig + one roam animation instead of three
  (the doc calls the frontend ~half the remaining work).
- 2x2 is the readable market block-wild idiom; 2x3 is not a shape seen on Stake
  Engine games.
- TIER IDENTITY SURVIVES VIA STICKY CELLS, not beast footprint. At wake the board
  is 8 / 11 / 15 of 20 cells wild (4/7/11 lit + a 2x2 beast). The constellation
  covers the sky; the beast prowls over it -- arguably the better story.

COST OF THE CHANGE (both are ladder work; measured, not estimated):
- TIER SPREAD COLLAPSES to roughly 224 / ~230 / 363x (from 224/283/651). Flat tier
  spread is the exact thing that makes buy_mystery undesignable (see below), so the
  spread must be rebuilt in the per-tier ladders.
- 2x2 draco's natural max is 9,968x against the 25,000x cap. Draco's ladder top
  must go 165 -> ~400+ or EVERY forced-wincap slice (base/ante/buy_draco/
  buy_mystery) hangs forever.
1. WHY A MYSTERY CANNOT COST 500x AS A MIX OF 200/300/500 TIERS. A mystery's price
   is the probability-weighted average of the outcomes it can roll, so it is ALWAYS
   CHEAPER THAN ITS MOST EXPENSIVE TIER -- it reaches 500x only at 100% draco, which
   is buy_draco with a worse name. Arithmetic, not tuning. Rage Bait solves this by
   making its top tier NOT PURCHASABLE (10% of rolls, 52% of payback => ~2,500x per
   hit => a ~2,600x standalone price, over the 1,000x Stake buy cap). We made every
   tier a buy, so the buy cap became our mystery cap.
   FIX = a FOURTH, MYSTERY-EXCLUSIVE outcome: "DRACO ASCENDANT", a Draco dealt with
   some cells ALREADY LIT. Pre-lighting raises completion AND makes it EARLY (early
   completion = long roam = top rungs = where all the value is), so it reuses every
   asset and nearly all the code -- a different initial state, not a new feature.
   Its required value is a RESIDUAL of the mix; frequency/value trade inversely:
   5% <-> ~3,800x | 10% <-> ~2,150x | 15% <-> ~1,600x | 20% <-> ~1,200x.
   CHOSE 10% / ~2,150x (matches both audited games; "1 in 10 mystery rolls wakes
   something you cannot buy").
   FEASIBILITY CONFIRMED WITHOUT A SIM: a COMPLETED draco already averages 5,114x
   (measured off the shipped LUT), so ~2,150x needs only ~40% completion -- a PARTIAL
   pre-light, not a full one. Re-priced to a 500x draco it scales to ~3,900x, so ~55%
   completion. Comfortable either way; the RATIO is what survives the rebuild.

2. 15 SPINS (10 -> 15) -- fixes the metric no ladder can touch. buy_draco's >cost
   rate EQUALS its completion rate exactly (you beat the ticket iff you complete --
   the carpet tops out at 336x), and it is 7.7% against a ~22% market norm.
   Completion is a function of how many spins you get to light cells, and more spins
   helps DRACO enormously while barely touching CORVUS (already 95%). Expect draco
   ~12% -> ~25-30%, which also populates the 400-3,000x cliff band with cheap
   completions. SECOND EFFECT: the ladder gains rungs (9 -> 14), and more rungs =
   gentler growth per rung for the SAME top, so a tall ceiling costs less in the
   body (corvus to top 250 needs x2.0/rung over 9 rungs, only x1.53 over 14).
   DIVISION OF LABOUR: spins fix the SHAPE, ladders fix the PRICE, cell maps fix
   tier SEPARATION.
   COSTS: books ~50% larger (KEEP batching_size 1000 -- see the memory gotcha); and
   "fixed 10 spins, no retrigger" is written into the design doc -> doc revision.

3. CORVUS/URSA HAVE CHEAP, UNBOUGHT CEILINGS; DRACO'S IS ALREADY SPENT. Share of
   each tier's mean held in its top 0.1% of outcomes (measured, shipped LUTs):
     corvus 0.6%  -> x10 on that slice: price 224->235x, ceiling 1,500->~15,000x
     ursa   1.0%  -> x10: price 283->308x, ceiling 4,750->~23,000x
     draco  5.2%  -> ALREADY AT the 25,000x cap; it cannot buy more ceiling
   CAVEAT: that model multiplies only the extreme tail. A REAL ladder is geometric,
   so raising the top drags the MIDDLE rungs up too, and the middle is where the
   common (late) completion lives -- the true price cost is higher than +5%. 15
   spins is what makes it affordable (see 2).

4. PER-TIER FEEL, MEASURED (ticket multiples, shipped pools):
              median  >ticket  2-5x   5-10x  10x+   99th   best
     corvus    0.68x   30.2%   15.7%  0.09%  0.00%  4.15x   6.7x
     ursa      0.41x   29.5%   14.7%  1.39%  0.03%  5.38x  16.8x
     draco     0.41x    7.7%    0.1%  7.16%  0.49%  9.08x  38.5x
   CORVUS HAS THE BEST BODY AND THE WORST DREAM -- the most generous buy to play
   (highest median, most likely to beat its ticket) but NOTHING has ever exceeded
   10x and only 0.09% reach 5x, so a hundred corvus buys show a best of ~4x. That is
   the flat feel, and it is market watch-item (b) seen from the player side.
   URSA READS CORRECTLY (genuinely bimodal, real tail) -- leave its shape alone.
   FIX CORVUS'S TAIL ONLY, and do NOT spike the last rung: that builds a CORVUS
   CLIFF (dense body to 5x, then a jump), the identical gate we are fixing on draco.
   Stretch the ladder GEOMETRICALLY so the range stays continuous.

5. CORVUS MAY NOT REACH 25,000x CLEANLY -- treat its ceiling as a SWEEP OUTPUT, not
   an assumption. Its max/mean is 6.9x (ursa 17.4x, draco 39.8x): the tightest of the
   three, so there is no natural long tail to stretch. Fork: a cheap ceiling = a
   disconnected spike (win-range gap); a continuous ceiling = fill the middle = price
   above 200x. It may only get two of {cap, no gaps, 200x}.
   SEPARATE THE GOAL FROM THE NUMBER: the aim is "a corvus buy can dream", and
   10,000x on a 200x ticket is 50x return-on-stake -- inside the market band and
   enough. Publishing 10,000x would be the HONEST answer, not a compromise.
   ALSO: to publish 25,000x a mode needs a FORCED WINCAP SLICE, which needs the cap
   reachable at roughly >=1e-6..1e-7 or the sim hangs hunting a book that
   effectively never occurs.

NEXT CONCRETE STEPS, IN ORDER (order matters -- 15 spins moves draco's completion
rate, which moves prices/ceilings/the cliff at once; sweeping first wastes runs):
  (1) config: num_feature_spins 15, all beast shapes (2,2), min_roam_spins 2, and
      ladders re-parameterised to 14 rungs (geometric from (start, top)) -- a 9-rung
      ladder would CLAMP EARLY at 15 spins and silently cap every ceiling.
  (2) back up library/ (13G; 930G free), then BASELINE all three tiers at the new
      structure: new completion rates, prices, ceilings, did the cliff close.
  (3) ladder sweep against the per-tier targets above.
  (4) Draco Ascendant tier + buy_mystery per-tier fences (see BUY_MYSTERY #1).
  (5) full Phase B re-converge at 1e6 x 6 modes.

### BASELINE MEASURED (Jul 27 2026) -- steps (1) and (2) DONE
Config now 15 spins / ALL beasts 2x2 / roam floor 2 / 14-rung ladders holding the
OLD (start, top) endpoints. Harness: `reels/measure_tiers.py` (n=40k/tier, forced
wincap slice stripped, and it LIFTS BetMode._wincap to the design cap first --
otherwise the published per-mode ceilings clamp the draw and hand back last
session's decision as if it were a natural limit; corvus read exactly 1500x until
that was fixed, its true natural max is 1,776x). Pool backed up to
games/starwake/library_phaseB_backup/ (13G).
                  corvus      ursa     draco   | target
  completion      94.36%    63.06%    32.26%   | draco ~25-30% ACHIEVED
  price             406x      278x      600x   | 200 / 300 / 500
  median            353x      141x      284x
  natural max     1,776x    5,404x   20,028x   | 25,000x
  at cap          0.000%    0.000%    0.000%   | NOTHING REACHES IT
  max/cost            4x       19x       33x   | 50-100x
  >cost           43.96%    28.46%    19.74%   | ~22% market norm
  widest hole      1.05x     1.28x     1.19x   | was 7.73x on draco
  mean roam        8.81      5.02      4.05    | of 14 possible
  zero pay         0.00%     0.00%     0.00%   | buys still never bust

THE 15-SPIN CHANGE DID BOTH JOBS IT WAS CHOSEN FOR:
- THE DRACO CLIFF IS CLOSED. 7.73x -> 1.19x, and the residual hole is up at
  16,783->20,028x = tail sparsity at 40k, not structure. Cheapest completion is now
  160x against a carpet topping at 476x, so the completion band OVERLAPS the carpet
  instead of floating above it. Compliance gate cleared.
- DRACO COMPLETION 12% -> 32.3%, >cost 7.7% -> 19.7% (market norm ~22%). >cost is
  now BELOW completion instead of equal to it -- that decoupling IS what a closed
  cliff looks like (cheap completions exist that do not beat the ticket).

TWO NEW PROBLEMS IT CREATED:
- NOTHING REACHES 25,000x ANY MORE (draco natural max 20,028x, at cap 0.000%).
  Every forced-wincap slice (base/ante/buy_draco/buy_mystery) would HANG. Draco's
  ladder top must rise from 165, far enough that the cap is FORCEABLE (~1e-6), not
  merely touched.
- THE TIER PRICE ORDER IS INVERTED: corvus 406x > ursa 278x. Corvus completes 94%
  with a mean roam of 8.81 of a possible 14, so it rides the TOP of its own ladder
  on nearly every buy; ursa completes 63% at mean roam 5.02. More spins do not add
  completions to a tier that already completes -- they just lengthen every roam,
  lifting the body while the ceiling stands still (corvus max/cost got WORSE,
  6.7x -> 4x, and it still has NOTHING above 5x its ticket, p99 2.74x).
=> CORVUS NEEDS THE OPPOSITE LADDER TREATMENT FROM THE OTHER TWO: a flat cheap
   bottom to halve the price, an explosive top to finally give it a dream. A plain
   geometric ladder cannot do that for corvus -- at mean roam 8.8/14 its body sits
   two-thirds up the curve in log space, so body and ceiling are welded together.
   Hence the sweep's CURVE parameter: ladder[i] = start*(top/start)^((i/(n-1))^curve),
   curve>1 = convex = stays low then explodes. curve=1 reproduces today's geometric.
SWEEP JOBS:  corvus 406->200x price, ceiling as high as continuity allows
             ursa   hold ~300x (it landed there free), ceiling 5,404 -> ~25,000x
             draco  600->500x, ceiling past 25,000x WITH measurable at-cap frequency

### LADDER SWEEP -- CORVUS SETTLED (Jul 27 2026).  reels/sweep_ladder.py
A ladder is THREE numbers, not fourteen:
  ladder[i] = start * (top/start) ** ((i/(n-1)) ** curve)
start prices the common (late-completion) case = the cliff floor; top prices the
rare early completion = the ceiling; CURVE decouples them (curve=1 is the plain
geometric ladder we shipped, curve>1 is convex = stays low then explodes).

**DECIDED: corvus = 10 SPINS, ladder [1, 1, 1, 2, 3, 5, 13, 44, 200] (1:200:2.5).**
  price 239x | median 94x (0.39x ticket) | ceiling 10,661x = 45x return-on-stake
  >cost 25.1% (above the ~22% norm) | widest hole 1.29x | completion 83.7%
  vs SHIPPED corvus: ceiling 6.7x -> 45x, >cost 30.3% -> 25.1%, median 0.68 -> 0.39x.

FINDING 1 -- PER-TIER FEATURE LENGTH IS REQUIRED, and it is a PRICE lever, not the
volatility lever the doc ruled out. At 15 spins NO ladder gets corvus under ~375x
(the sweep tried curve up to 5.5): corvus completes 94% and mean-roams 8.81 of 14,
so its typical buy sits high on the ladder no matter how convex the curve. At 10
spins the same ladder family prices at 202-274x. 12 spins reads 327x -- too dear.
So corvus 10 / ursa+draco 15 (ursa at 12 under test). This REVISES the documented
"count scales the TIER, never the spin count" choice; "more scatters = more spins"
is standard market design and the original rationale was about volatility, not price.

FINDING 2 -- THE CEILING IS NEARLY FREE IN PRICE; IT COSTS BODY. Corvus frontier at
10 spins (completion 83.7% throughout -- the ladder is payout-only, it cannot move
completion):
  ladder       price  median  med/price      max  max/cost   >cost   hole
  1:1:1          76x     75x      0.99x     231x        3x   49.2%  1.03x  <- RAW feature
  1:40:1.5      202x    112x      0.55x   2,444x       12x   34.1%  1.07x
  1:100:2       219x     94x      0.43x   5,562x       25x   28.7%  1.21x
  1:200:2.5     239x     94x      0.39x  10,661x       45x   25.1%  1.29x  <- CHOSEN
  1:400:3.5     223x     80x      0.36x  20,666x       93x   19.5%  1.38x
  1:800:4       274x     80x      0.29x  25,000x       91x   14.5%  1.12x
A ten-fold ceiling swing (2,444 -> 25,000x) moves the price only 202->274x, while
med/price falls 0.55->0.29 and >cost falls 34.1->14.5%. So the question is never
"can we afford the dream" -- it is "how much grind do you trade for it".

FINDING 3 -- THE RAW UNMULTIPLIED FEATURE IS ONLY 76x at 10 spins (the 1:1:1 row).
The LADDER carries corvus's economy, not the wild carpet. (An earlier estimate of
~360x for the raw feature was wrong -- at 15 spins the typical roam reaches rung
8-9, so even an all-1s-at-the-bottom ladder was paying real multipliers.)

FINDING 4 -- NO CORVUS CLIFF. Widest hole stays <= 1.38x across every variant up to
curve 5.5, so the convex ladder does NOT gap the way the old min_roam floor did.
The worry that a cheap ceiling must be a disconnected spike is DISPROVEN.

FINDING 5 -- CORVUS CAN REACH 25,000x (top 800 -> at cap 0.030-0.040%, ~1 in 2,500 =
easily forceable). Its ceiling is a free choice, not a structural limit.

⚠ PRICE NOISE AT 20k SIMS: one 20,000x outcome moves the mean by 1x, so the price
column carries ~+/-20x (that is why 1:200:2.5 reads dearer than 1:400:3.5). Trends
are solid; exact prices need the 1e6 run.
⚠ UX WATCH-ITEM: very convex ladders read as a flat multiplier for the first half of
the feature ([1,1,1,1,2,3,9,43,400] barely climbs until rung 6) while the pitch is
"the multiplier climbs each spin". 1:200:2.5 was chosen partly because it starts
moving by rung 3.

### LADDER SWEEP -- URSA + DRACO (Jul 27 2026).  n=20k/variant
URSA @ 15 spins (completion 63.2%)      DRACO @ 15 spins (completion 32.1%)
 ladder      price  median     max mx/cst >cost  hole | ladder     price median    max  at cap mx/cst >cost hole
 1:38:1 base  277x    140x  4,238x   15x 28.5% 1.23x | 2:165:1 base 602x  283x 20,028x 0.000%  33x 19.8% 1.34x
 1:180:1.5    281x    135x 10,339x   37x 23.6% 1.45x | 2:400:1.3    545x  282x 25,000x 0.005%  46x 18.8% 1.35x
 1:300:1.7    284x    135x 13,708x   48x 23.4% 1.47x | 2:400:1.5    502x  282x 22,851x 0.000%  46x 21.1% 1.46x
 1:500:2      266x    133x 17,220x   65x 22.5% 1.50x | 2:600:1.5    524x  282x 25,000x 0.005%  48x 20.0% 1.22x

- URSA MUST STAY AT 15 SPINS. At 12 it prices 170-177x on EVERY ladder (completion
  collapses 63.2% -> 46.1%) -- barely half its 300x target. So feature length is
  CORVUS 10 / URSA 15 / DRACO 15, not the tidier 10/12/15.
- PRICE ORDER IS FIXED: 239 < 284 < 524 (was corvus 406 > ursa 278).
- "CEILING IS NEARLY FREE" REPLICATED ON URSA: price sits at 266-284x across
  ceilings from 4,238x to 17,220x.
- DRACO REACHES THE CAP AGAIN at 2:600:1.5 -- at cap 0.005% (~1 in 20,000, well
  above the ~1e-6 forceable gate), price 524x, hole 1.22x, >cost 20.0%.
- DRACO'S max/cost IS ARITHMETICALLY CAPPED AT 50x (25,000 / 500), so its 48x is
  the maximum available, not a tuning miss. Do not chase the 50-100x band here.

**RECOMMENDED (NOT YET APPLIED): ursa 1:300:1.7, draco 2:600:1.5.**
PROPOSAL -- ASCENDING PUBLISHED CEILINGS 10,000 / 15,000 / 25,000 instead of pushing
every tier to the cap. Corvus landed at 10,661x and ursa ~13,700x, so the published
maxWin column becomes a visible tier ladder rather than three identical numbers.
This REVERSES the earlier "make every tier reach 25,000x" argument -- that was made
when corvus's ceiling was 1,500x and the cap was its only route to a dream; at
10,661x it already has one.

### ▶▶ STATE OF THE TREE AT END OF Jul 29 2026 SESSION
COMMITTED AND CLEAN. Four commits on claude/starwake-feature-engine, in order:
  1. per-tier feature length + swept multiplier ladders   (pushed to `mine`)
  2. ursa joins draco at the 25,000x cap                  (local)
  3. Draco Ascendant + buy_mystery restructure            (local)
  4. buy_mystery hr fix + 1e6 re-converge notes           (local)
Only unrelated paths remain untracked (.claude/, four other game design docs,
games/knockout_mayhem/) plus games/starwake/library_phaseB_backup/ (13G, gitignored)
and optimization_program/src/setup.toml (generated optimizer state -- never commit it).
⚠ REMOTES: `origin` is StakeEngine/math-sdk, the PUBLIC upstream SDK. `mine` is the
fork. The branch tracks `mine`, so a bare `git push` is correct -- never push starwake
to origin.
POOL: library/ is now a CONVERGED PRODUCTION POOL -- all six modes at 1e6 on the
current config. See "POOL STATE" further down.

### ▶▶ NEXT SESSION STARTS HERE (as of Jul 29 2026)
The math is converged and shippable. What remains is publishing work plus two open
product calls.
 1. WRITE MYSTERY'S ODDS INTO THE FRONTEND: corvus 35.16 / ursa 29.64 / draco 25.15 /
    ascendant 10.05%. Draco's number INCLUDES the 0.04% cap slice (it forces 5
    scatters, so those are Draco rolls). Display rounding is fine; the gate is that the
    displayed mix is the delivered mix.
 2. EVENT-ID FINDER for reviewer scenarios -- the last unstarted engineering item.
 3. PRODUCT CALL -- the maxWin overshoot (books pay up to 25,005x against a published
    25,000x). Diagnosis and the one-line fix are in the PER-MODE DISPLAYED CEILINGS
    section. Costs a re-sim of base/ante/buy_draco/buy_mystery.
 4. PRODUCT CALL -- base-boost, i.e. whether ordinary base spins should be able to pay
    more than 21x. This is the ONLY remaining route to higher base volatility and to a
    >100x share above 0.372 (see BASE VOLATILITY). The doc parks it until first
    playtest and that is still the right call.
 5. NOT A TODO: base std dev 24.08 and >100x share 0.372. Both investigated at length
    on Jul 29 and deliberately left. Read BASE VOLATILITY before reopening.

EVERYTHING DECIDED ON Jul 27 IS NOW WRITTEN INTO game_config.py:
  num_feature_spins = {"corvus": 10, "ursa": 15, "draco": 15}   <- PER TIER
  freespin_triggers is DERIVED from it, never hand-written, so a length change is a
    one-line edit and the count-indexed ENGINE view cannot drift from the
    tier-indexed DESIGN view.
  all beasts (2,2) | min_roam_spins 2
  corvus [1,1,1,2,3,5,13,44,200]                    ( 9 rungs, 1:200:2.5)
  ursa   [1,1,1,1,2,3,4,6,11,20,40,86,199,500]      (14 rungs, 1:500:2)
  draco  [2,2,3,4,5,8,12,19,31,53,94,169,315,600]   (14 rungs, 2:600:1.5)
URSA TOOK 1:500:2, NOT the recommended 1:300:1.7. The taller ceiling (13,708 ->
  17,220x at 20k) cost ~1% of >cost and almost nothing in price -- ursa's price sits
  at 266-284x across EVERY ceiling from 4,238x up -- so the cheap dream was taken.
TESTS: 29 passing (23 after the ladder work, +6 for pre-lit deals). Rewritten to
  DERIVE from config instead of hard-coding 5/10/15,
  because an economy re-tune must not break tests that assert a RULE. Plus a new
  guard that each ladder has EXACTLY its tier's rung count: too short clamps early
  and silently caps that tier's ceiling (the trap the 10->15 change set), too long
  advertises rungs no player can ever be paid. Both failure modes are silent --
  roam() clamps rather than raising.
DOC: docs/ideas/starwake.md now records per-tier length, all-2x2, the ladder formula
  and roam floor 2 as RESOLVED (struck through), not open questions.

### CONFIRMATION RUN @ 100k/TIER (Jul 28 2026) -- THE 20k SWEEP HELD
n=99,960/tier, forced wincap slice stripped, BetMode._wincap lifted to the design cap.
                  corvus      ursa     draco  | sweep predicted at 20k
  completion      83.76%    62.60%    32.01%  | 83.7 / 63.2 / 32.1
  price             240x      268x      520x  | 239 / 266 / 524
  median             94x      132x      281x  |  94 / 133 / 282
  natural max    11,438x   25,000x   25,000x  | 10,661 / 17,220 / 25,000
  at cap          0.000%    0.001%    0.004%  | -- / -- / 0.005%
  max/cost           48x       93x       48x
  >cost           25.05%    22.08%    19.84%  | 25.1 / 22.5 / 20.0
  zero pay         0.00%     0.00%     0.00%  | the sweep does not print it
  widest hole      1.07x     1.24x     1.09x  | 1.29 / 1.50 / 1.22
  mean roam         4.89      5.00      4.04
  max roam             9        14        12  | ladder length 9 / 14 / 14

PRICES LANDED WITHIN 4x OF THE 20k SWEEP -- the +/-20x noise warning was
conservative. The three-number ladder model (start:top:curve) predicts price, median,
completion and >cost well enough to SWEEP AT 20k AND TRUST IT; only the ceiling needs
depth, because a natural max is a sampling floor until the tail is actually reached.

THE CLIFF IS DEAD ON ALL THREE TIERS. Cheapest completion now lands BELOW carpet max
everywhere (0.5x / 0.1x / 0.3x -- it was 9.0x on draco), so the completion band
OVERLAPS the carpet instead of floating above it. Every surviving hole sits ABOVE
9,000x (corvus 9,001->9,655, ursa 17,220->21,285, draco 18,749->20,437) = tail
sparsity at 100k, not structure. The compliance gate is cleared.

ZERO-PAY 0.00% ON ALL THREE BUYS -- the explicit check this run was for. BUT the FEEL
table's "zero" bucket is <0.001x TICKET, not zero: corvus 1.07% / ursa 0.15% / draco
0.24% of buys pay under a thousandth of their cost. Not a bust by the market gate,
but corvus's 1-in-93 READS like one, and it is NEW -- an artifact of dropping corvus
to 10 spins. Watch it at 1e6.

FOUR THINGS THE DEEPER SAMPLE CHANGED:
1. URSA REACHES 25,000x (at cap 0.001%, ~1 in 100k). The sweep's 17,220x was a
   sampling floor, not a structural limit. So ursa CAN carry a forced wincap slice
   (1e-5 clears the ~1e-6 gate by 10x) and its max/cost 93x is the BEST IN THE GAME.
   The ascending-ceiling proposal is now a CHOICE for ursa, not a constraint -- see
   OPEN DECISION 1.
2. CORVUS CANNOT. 11,438x natural max and ZERO cap hits in 100k, so no forced wincap
   slice is possible for it (an unsatisfiable forced slice hangs forever, it does not
   error). Its published ceiling must be its natural max rounded down: ~10,000x.
3. DRACO'S TOP TWO RUNGS NEVER FIRED. Max roam 12 of a possible 14 -- draco never
   completed before spin 3 in 100k books, so rungs 315 and 600 sit in the compliance
   "all obtainable values" table doing nothing. They ARE obtainable, just <1-in-100k,
   and shortening the ladder would lower the ceiling (a 25,000x book rides the top
   rung). A note, not a defect -- and DRACO ASCENDANT is what finally puts them to
   work, since pre-lit cells are exactly what makes an EARLY completion possible.
4. THE PRICE LADDER IS COMPRESSED: 240 / 268 / 520 against the 200/300/500 target.
   Corvus and ursa are 28x APART -- near-identical on a buy menu while being very
   different products (corvus 84% completion, best body, 48x dream; ursa 63%,
   genuinely bimodal, 93x dream). See OPEN DECISION 2.

### CEILINGS + CAP FREQUENCIES -- SETTLED Jul 28 2026 (applied, tests green)
DECISION: ursa and draco SHARE the 25,000x cap; corvus publishes an honest 10,000x;
the tier story is carried by CAP FREQUENCY instead of by ceiling.

  mode           cost    maxWin  capRTP        cap rate   maxWin/cost
  base            1.0    25,000  0.0200  1 in 1,250,000            --
  ante_starfall   1.5    25,000  0.0250  1 in   666,667            --
  buy_corvus      240    10,000      --            never           42x
  buy_ursa        268    25,000  0.0215  1 in     4,339           93x
  buy_draco       520    25,000  0.0500  1 in       962           48x
  buy_mystery     276    25,000  0.0157  1 in     5,769           91x

WHY SHARED CEILINGS ARE FINE. Market precedent is explicit: Rage Bait's buys cost
250-500x and ALL of them reach the 25,000x cap. Multiple buys at one ceiling is the
norm, not a defect. It is also free -- publishing ursa at 15,000x instead would have
clipped 5 books in 100,000 and moved its mean 0.077%. The earlier "ascending
ceilings" proposal is therefore RETIRED.

WHY DRACO IS STILL WORTH 1.94x URSA'S PRICE. Cap-value-per-stake is rate*cap/cost,
so the two break even when draco's cap rate is exactly its price ratio (520/268 =
1.94x ursa's). BELOW THAT, DRACO IS A STRICTLY WORSE CAP PLAY AND COSTS MORE -- the
one failure mode this arrangement has to avoid. Set to ~4.5x, giving draco ~2.3x the
cap value per stake. THAT RATIO IS THE TIER STORY: re-check it on the 1e6 pool, do
not assume it survived re-convergence.

WHY CORVUS STAYS AT 10,000x -- it is a CHOICE, not a limit. The sweep showed corvus
can reach the cap (ladder top 800, ~1 in 2,500, easily forceable). Buying it costs
>cost 25.1% -> 14.5% (under the ~22% norm, and the best body in the game) and
flattens the ladder for five of nine rungs against a pitch that says the multiplier
climbs every spin. Corvus is the deliberate non-lottery grind tier; a menu where
every tier is a lottery has no entry point.

WHY THE 240/268 CORVUS-URSA PRICE GAP STAYS. It is structural, not a tuning miss:
the sweep priced corvus at 202-274x across EVERY ladder at 10 spins and ursa at
266-284x at 15, so neither can move far. Reaching 200x means the 1:40:1.5 ladder,
which drops corvus's ceiling to 2,444x and max/cost to 12x -- undoing the rebuild.
The menu differentiates on the CEILING column (10,000 vs 25,000) instead. The only
untried lever is a corvus feature shorter than 10 spins; not worth it for cosmetics.

⚠ FIRST-RUN WATCH-ITEM: buy_ursa now carries a FORCED wincap slice where it never had
one. A forced slice LOOPS FOREVER if its cap is out of structural reach. Ursa reached
25,000x naturally (once in 99,960) and the slice draws on the juiced WCAP strips, so
this should be safe -- but it is the single most likely thing to hang the next run.

### DRACO ASCENDANT -- BUILT Jul 28 2026 (29 tests green, end-to-end verified)
The mystery-exclusive 4th outcome ships as a fourth TIER, not a special case: it is
a Draco (same 11 cells, 2x2 beast, 14-rung ladder, 15 spins, all DERIVED from draco
in config so they cannot drift) dealt with some cells ALREADY LIT.

TRIGGER = 6 STARS, a real scatter count, so tier selection stays uniform (count ->
tier) with no engine special case. Measured on buy_mystery at n=20k: shares land
35.0 / 29.5 / 25.5 / 10.0, zero-pay 0.00% on every tier, 25,000x reachable.
              corvus     ursa    draco  ascendant
  mean          234x     273x     956x*    2,286x     *incl. forced wincap slice
  completion   83.6%    63.0%    32.4%      89.2%
  mean roam     4.91     5.10     4.46       6.13

WHY 6 CANNOT LEAK, and why it needs its own strip -- BOTH sides of this were got
wrong first and are worth not re-deriving:
- THERE WAS NEVER A LEAK. draw_board redraws away EVERY unforced board with >=3
  scatters, and the forced branch enforces an exact count, so a 6-scatter board only
  exists where 6 was explicitly forced. The "6+ clamp to draco" line in game_config
  is dead defensive code. No strip constraint was needed.
- THE TIGHT SCATTER PAIR ON BR0 IS NOT A HAZARD, IT IS THE ENABLER.
  _force_special_board places at most ONE scatter per reel (it zeroes each reel's
  probability after picking it), so on 5 reels a 6th can only come from a reel whose
  4-row window happens to show two -- and force_special_board is a bare `while True`
  with NO retry cap. Removing BR0's pair (the "fix" that was nearly applied) would
  have turned the ascendant force into a silent infinite hang.
- HENCE ASC.csv: reel 2's scatters are laid down as one step-3 run so a stop there
  always reveals two -> 1+1+2+1+1 = 6 on 91.6% of attempts (BR0 manages 20%, ~5
  retries). It also ISOLATES ascendant from BR0, which is the base-game tuning
  surface -- any future BR0 weight edit reshuffles it and could delete the pair.
  This is the one place the SDK's "ensure the reels do not have stacked scatter
  symbols" is deliberately violated, because it is the only route to 6 on 5 reels.

PRE-LIT CELL SWEEP (reels/sweep_ascendant.py, n=20k, judged on implied mystery cost)
  pre-lit            mean  complete  at cap   -> cost
  (none)             510x     32.2%   0.00%     346x
  (3,2) neck         589x     34.9%   0.01%     354x
  (3,2)(4,0)         956x     45.2%   0.05%     392x
  (4,0)(4,1)       2,249x     89.6%   0.09%     526x   <- CHOSEN
  (3,2)(4,0)(4,1)  2,742x     90.7%   0.36%     577x
  3 body cells     1,339x     49.3%   0.09%     431x

FINDING 1 -- PRE-LIGHTING AND SHAPE ARE OPPOSITE PROBLEMS. The documented shape rule
("a reel-3 cell is a gate AND A KEY, never harden a tier by adding reel-3 cells")
does NOT transfer. Pre-lit, the neck is nearly worthless (510 -> 589x) while an
adjacent REEL-4 PAIR is transformative (510 -> 2,249x, completion 32% -> 90%) -- same
cell count, 2.4x the payout. Reel 3 already carries wilds (FR0 W=3) so it is not the
binding constraint; reel 4 is BONE DRY (W=0), so two permanent wilds there are the
only thing that makes the column reachable, and any win crossing it lights the rest.
FINDING 2 -- PRE-LIGHTING PAYS THROUGH TWO CHANNELS AND THE SECOND DOMINATES: fewer
cells to trace (earlier completion -> higher rungs), and wilds on the board from spin
one (every win richer, no cold start). A roam-length model sees only the first and
underestimates badly -- the chosen set completes at mean roam 6.06 where the draco
roam table predicts ~1,350x, and it pays 2,249x. It is also why the body-cell control
still reached 1,339x on barely-improved completion.

BUY_MYSTERY RESTRUCTURED at the same time, since it needed the same change: the single
blended "mystery" distribution became ONE PER TIER (corvus/ursa/draco/ascendant +
wincap) with kind=3/4/5/6 fences. That also fixes the long-standing INVERTED TIER
LADDER (BUY_MYSTERY #1) -- one undifferentiated fence let the optimizer reshape each
tier freely, so rolling Draco averaged LESS than rolling Corvus while the UI sold
Draco as the prize. Cost 285 -> 526x (mean/rtp on natural tier means); ascendant
carries 44% of the mode's payback on 10% of rolls, the Rage Bait shape (10% -> 52%).

⚠ READING THE MODE MEAN: a straight mean over the shipped pool reads ~657x because
the wincap slice is a SAMPLING QUOTA, not a probability -- 0.5% of books forced to
25,000x adds ~125x. Strip it and it is 510x -> 528x, matching the 526x derived from
natural tier means. Never price a mode off the raw pool mean.

### ▶▶ FULL 1e6 RE-CONVERGE (Jul 29 2026) -- ALL SIX MODES CONVERGED
Sims 74 min (one process per mode via run_modes.sh, detached with setsid) + optimizer
~32 min = 106 min total. 999,964 books per mode, no warnings, no repeat-limit trips.
Both flagged hang risks CLEARED: buy_ursa's new forced wincap slice and buy_mystery's
ascendant slice both resolved. ⚠ URSA'S SLICE IS EXPENSIVE -- 24:47 vs ~10-18 min for
the other buys, because it hunts a ~1-in-100k book. That is the price of giving ursa a
cap slice, not a symptom.

  mode           cost  maxWin     RTP   std  zero%   hit%  >=1x  ETL40x  >100x  cap rate
  base            1.0  25,000  0.9665 24.08  70.75  29.25  9.71   0.333  0.252  1 in 1.25M
  ante_starfall   1.5  25,000  0.9665 21.81  65.67  34.33  8.79   0.381  0.327  1 in 667k
  buy_corvus      240  10,000  0.9665  1.45   0.00 100.00 26.64   0.000  0.893  never
  buy_ursa        268  25,000  0.9663  2.27   0.00 100.00 23.57   0.023  0.928  1 in 4,340
  buy_draco       520  25,000  0.9655  2.10   0.00 100.00 26.85   0.052  0.955  1 in 963
  buy_mystery     526  25,000  0.9665  1.74   0.00 100.00 21.67   0.022  0.983  1 in 2,388
BAND SPREAD 0.1004% (limit 0.5%), every mode <= the 0.9670 ceiling. Zero-pay 0.00% on
all four buys. PRICES CONFIRMED AS OUTPUTS to 0.1%: 240.0 / 267.9 / 519.5 / 526.0x
implied vs 240 / 268 / 520 / 526 configured -- the 100k confirmation run held at 1e6.
DRACO-VS-URSA CAP VALUE HELD at 2.32x (0.0499 vs 0.0215) against the ~2.3x design
target and the 1.94x break-even -- the thing the ceilings section said not to assume.
⚠ ante_starfall's cap-value-per-stake (0.0250) EXCEEDS buy_ursa's (0.0215) and
buy_mystery's (0.0199), so grinding ante is a marginally better max-win bet per dollar
than buying those two. Pre-existing, and buy_draco still dominates everything at
0.0499, so the TOP of the menu holds -- but it is the same ordering failure mode that
rules out raising base's cap share (see the volatility section below).

### ▶▶ THE hr BUG -- THIRD MEMBER OF THE FENCE-CONFIG FAMILY (Jul 29 2026)
buy_mystery came out of the first 1e6 optimizer run at RTP 0.2416 -- a UNIFORM factor
of exactly 4.0004 under target, with all four tier fences at exactly 25.00% weight.
`hr` IS A "1 IN N" FREQUENCY, verified against base, whose configured hr 220/600/1900/
3.5 reproduce EXACTLY as its measured trigger rates. So hr=1 declares "this fence
occurs on every book". That is harmless for buy_corvus/buy_ursa/buy_draco where one
tier fence really does own ~100% of the mode -- and it was copied from them. With FOUR
fences each claiming 100%, the optimizer split them evenly, and because each fence
still hit its own rtp_k as a sub-pool mean, the mode landed on sum(rtp_k)/4.
FIX: hr = 1 / intended share. Cross-check that the config is self-consistent:
rtp_k * cost * hr_k is the fence mean the optimizer must produce, and it lands within
3% of every measured natural tier mean, so the tiers keep their swept shape.
⚠ SECOND BUG, FOUND WHILE FIXING THE FIRST: THE SHARES MUST BE EXHAUSTIVE --
sum(1/hr) + wincap weight == 1. The clean design mix (35/29.5/25/10) sums to 0.995
because 0.5% was left for the cap slice, but 0.5% is the cap's GENERATION QUOTA and
its actual WEIGHT is rtp*cost/cap = 0.0199*526/25000 = 0.000419 (0.042%). The
optimizer filled the 0.46% shortfall by scaling every tier up, scaling RTP with it:
0.9665 * 1.004604 = 0.9709, over the ceiling. Same quota-vs-frequency trap already
recorded in the gotchas, met from the other side. Shares renormalised to 1 - 0.000419.
NEITHER BUG IS CAUGHT BY verify_optimization_input -- it only checks that the splits
sum and that criteria match, and the splits were correct throughout both failures.
THE FAMILY: (a) fence ORDER, three tier fences searching {"symbol":"scatter"} with no
kind -> the first swallowed all feature books; (b) fence ORDER, the basegame catch-all
before "0" -> skewed the weight denominator, uniform 1.019x overshoot; (c) fence
PROPORTION, hr wrong -> uniform 4.0x undershoot. All three: identity right, bookkeeping
wrong, silent, and visible only as a UNIFORM multiple on the measured RTP. A uniform
factor on every slice means look at the fence bookkeeping, never at the game math.

### ▶▶ BASE VOLATILITY -- INVESTIGATED AND DELIBERATELY LEFT ALONE (Jul 29 2026)
base std dev is 24.08 against the doc's "expect ~35-48". THE GATE IS "< 50" AND WE PASS
IT; 35-48 is an observation about comparable games, not a requirement. Investigated
properly and every route costs more than it buys. DO NOT REOPEN without new information.
WHERE std ACTUALLY COMES FROM -- decomposition of E[p^2] (std = sqrt(E[p^2] - mean^2)):
  wincap 500.0 (86.1%) | draco 42.7 | ursa 17.9 | corvus 15.3 | basegame 4.9
  closed form: std ~= sqrt(slice_rtp * cost * cap + 81). base std is 86% ONE NUMBER:
  the wincap slice's rtp share. 0.02 -> 24.1 | 0.05 -> 36.5 | 0.06 -> 39.8 | 0.08 -> 45.6
ROUTE 1 -- RAISE THE CAP SHARE. REJECTED: cap-value-per-stake IS slice_rtp, so base at
  0.06 exceeds buy_draco's 0.05 and the CHEAPEST bet on the menu becomes the best
  max-win play. Concretely: 520 base spins would beat one draco buy by 20% on cap odds.
  Every buy button becomes worse value than ignoring it. Base is effectively ceilinged
  at slice 0.05 / std ~36 by draco's share, and closer to 0.04 to keep real separation.
ROUTE 2 -- RAISE THE FEATURE'S PAYOUT SPREAD (reweight feature books toward the tail,
  cap rate untouched). REJECTED, and this one looked clean until measured: the feature's
  RTP share is FIXED at 35.2%, so making each feature pay more makes it happen less.
    tilt   std   feature rate      corvus / ursa / draco
    none  24.08  1 in    148   1 in   220 /   600 / 1,900
    1.2   35.70  1 in    803   1 in 2,326 / 2,166 / 2,823
    1.4   39.92  1 in  1,165   1 in 3,701 / 3,501 / 3,307
  std 36 costs the feature 5.4x in frequency -- and THE TIER LADDER COLLAPSES: the
  three tiers converge to ~1 in 3,000 and the ORDER INVERTS (corvus becomes rarest).
  Three constellations that are meant to feel different become one thing. Bust rate and
  win frequency barely move, which is why a metrics table alone HIDES this -- the
  damage is entirely in the trigger rate and the tier separation. Always print the
  trigger rate when reshaping a fence.
ROUTE 3 -- LET BASE SPINS THEMSELVES PAY BIG. The real fix, and still open: ordinary
  non-feature spins max out at 21x, so 63% of base's payback is structurally incapable
  of being a big win. That is also why "share of RTP above 100x" is stuck -- it plateaus
  at 0.372 (= the feature's 35.2% + the cap's 2.1%), i.e. at the plateau literally 100%
  of feature money arrives as a >100x win and there is nothing left to convert. Getting
  past 0.40 needs base's own ceiling raised (base-boost / richer paytable), which is a
  full re-sim and re-price -- and the doc already parks base-boost until first playtest.
  Do it with a controller in hand, not from a spreadsheet.
WHY THIS IS FINE: frequency, generosity and volatility trade against each other, and
base is deliberately tuned to the first two -- win freq >=1x 9.71% vs the 7.4% norm,
bust 70.75% at the friendly end of 70-83%, a feature every 148 spins. The volatility
lives in the buys, where draco caps 1 in 963 and ursa's max/cost is 93x.

POOL STATE -- CLEAN FOR THE FIRST TIME SINCE THE REBUILD:
  ALL SIX MODES are 999,964 books on the CURRENT config, optimizer-converged, with
  fresh optimized LUTs. config.json is internally consistent -- real costs, real
  ceilings, real std, and bookLength finally matches the books (it reads std and
  bookLength from the optimized LUT, so those two lag whenever a sim runs without the
  optimizer; that is how it silently mixed vintages before).
  library_phaseB_backup/ (13G) still holds the pre-rebuild shipped set.
  ⚠ optimization_program/src/setup.toml is REWRITTEN BY EVERY OPTIMIZER RUN (it records
  the last bet_type and m2m bounds). It is tracked in git but it is generated state --
  do not commit it.

### THE DRACO CLIFF -- ✅ CLOSED Jul 28 2026 (kept for the diagnosis + the levers)
FIXED. Widest hole is now 1.09x on draco (1.07 / 1.24 / 1.09 across the three tiers)
and every surviving hole sits above 9,000x = tail sparsity at 100k, not structure.
Three changes did it, in order of contribution: min_roam_spins 5 -> 2 (the floor was
the cause, see below), 10 -> 15 feature spins (cheap completions became common), and
the convex ladders (a late completion no longer jumps straight to a big multiplier).
The diagnosis below is kept because the FAILURE MODE is general -- any feature where
several step-changes fire on one trigger will gap the same way -- and because the
sweep table is the evidence for which lever actually mattered.
--- as originally found: ---
buy_draco has a structural win-range gap: **no book pays between 400x and 3,000x**
(raw pool: 0 distinct payouts in 400-2,000, 3 in 2,000-3,000, then 44,298 in
3,000-6,000). Doc L300-301 lists "no win-range gaps between small pays and the max"
as a hard gate, and the hole sits right across buy_draco's own 651x cost. Corvus
and Ursa are smooth across that range -- Draco alone has it.

CAUSE = three step-changes fire together at completion: the board goes near-fully
wild, the multiplier switches on for the FIRST time (non-completions have NO
multiplier -- sticky stars are x1 under Option A), and min_roam_spins=5 guarantees
five spins of it. Cheapest possible completion ~3,016x; carpet can never exceed 336x.

MEASURED (`reels/sweep_beast.py`, 40k sims/variant, wincap slice stripped):
- BEAST SIZE ALONE NARROWS BUT NEVER CLOSES IT. Cliff (cheapest completion /
  carpet max): 3x3 9.0x -> 2x4 6.9x -> 2x3 4.1x -> 2x2 3.0x. The carpet always
  tops out at 336x because it happens BEFORE the wake -- beast size cannot touch it.
- min_roam_spins IS THE REAL LEVER:
    3x3 roam>=5  cost 651x  cheapest completion 3,016x  cliff 9.0x  >cost 11.9%  max/cost 30x
    3x3 roam>=3  cost 285x  833x  cliff 2.5x  >cost 11.9%  max/cost 69x
    3x3 roam>=2  cost 229x  371x  cliff 1.1x  >cost 13.6%  max/cost 86x  <- GAP CLOSED
    2x3 roam>=2  cost 185x  209x  cliff 0.6x  >cost 20.9%  max/cost 67x
- Closing it fixes THREE documented problems at once: the gate, buy_draco's
  return>cost (11.9% -> 20.9%, market norm ~22%), and max/cost (30x -> 67-86x,
  watch-item (b)'s 50-100x target band).
- LOWERING THE FLOOR SERVES THE DOC'S OWN GOAL. "Finish early = longer roam" spans
  5->9 spins at floor 5 (1.8x) but 2->9 at floor 2 (4.5x): the floor was flattening
  the very tail the design is built on. "Even a last-spin completion pays" survives
  -- 2 roam spins at rungs 2,3 pays ~371x, above anything the carpet can produce.
- Cost collapses because min_roam=5 was carrying ~70% of buy_draco's value.
  Restore the price in the LADDER TOPS, not by putting the floor back.

### BUY_MYSTERY -- measured state (do AFTER the beast/ladder rebuild)
NOTE Jul 27 2026: #1 (the fence defect) is STILL LIVE and must be fixed. #3's mix
table and #4's "Rage Bait's shape is not available" are SUPERSEDED by the DRACO
ASCENDANT decision in PICK UP HERE -- a fourth, non-purchasable outcome is exactly
what makes that shape available. #5 (no 2-scatter dud) and #6 (publish true odds,
do not overlap ursa's price) still stand.
1. THE PUBLISHED TIER LADDER IS INVERTED. In today's buy_mystery, rolling Draco
   pays 213x on average -- LESS than rolling Corvus (331x) -- against 628x when
   Draco is bought directly (median 49x vs buy_draco's 269x). CAUSE: buy_mystery has
   a single undifferentiated "mystery" fence (game_optimization.py:155), so the
   optimizer reshaped each tier freely to hit RTP at 285x. FIX = kind=3/4/5 fences
   like base/ante. A real defect, independent of any mix decision.
2. NATURAL per-tier avg wins (the coherent targets): corvus 216.5 / ursa 273.5 /
   draco 628.4x. Mystery's RAW draco reads 1,793x only because 5,001 of its 104,166
   draco books are the forced wincap slice; strip them and it is 622.9x, matching
   buy_draco's 628.4x.
3. A MYSTERY'S PRICE IS THE PROBABILITY-WEIGHTED AVERAGE OF ITS TIER PRICES. So it
   is structurally bounded to (224x, 651x), and picking a price IS picking a Draco
   frequency -- at 500x, Draco is >=59% of rolls however corvus/ursa split.
   mix -> cost / draco RTP share / return>cost:
     45/45/10 293x 22.2% 26.3% | 40/40/20 333x 39.1% 20.6% | 38/38/25 353x 46.1% 18.8%
     35/35/30 372x 52.4% 17.4% | 25/25/50 452x 71.9% 12.8% | 20/20/60 491x 79.4% 11.1%
   Concentration and fun move in OPPOSITE directions here, because our dragon is a
   tail-carried feature (see the cliff). Fixing the cliff should change this table.
4. RAGE BAIT'S SHAPE IS NOT AVAILABLE TODAY. Back out doc L352: its top tier is 10%
   of rolls carrying 52% of payback at 500x -> ~2,500x per hit, 5x its own ticket.
   Ours pays 1.4x its ticket. ~2,500x implies a ~2,600x standalone price, over the
   1,000x Stake buy cap -- so Rage Bait's top mystery tier is almost certainly NOT
   purchasable. We made every tier a buy, so the buy cap also caps our top tier.
   Faking it from our pool needs either 7.7% of the draco slice on wincap books (a
   25,000x hit 1 in 130 buys) or an ~8x up-weight of the extreme tail (44% at
   ~5,000x / 56% at ~350x -- gappy). Neither ships.
5. THE 2-SCATTER DUD IDEA IS DROPPED. Captain Death's 60.9% 2-scatter tier (doc
   L353) PAYS -- the same audit says its buys bust 0.00%, so its feature triggers at
   2. Ours triggers at 3, so a 2-scatter roll is a plain base spin (1.0x avg,
   literally 0 about 71% of the time), and no cheap scatter prize fixes it (2
   scatters land often enough in base that even 0.5x eats ~4% of the RTP budget).
   Measured, a dud slice buys TAIL not FUN: at matched price it trades return>cost
   20.6% -> 15.5% for more concentration plus a 10-14% bust.
6. STILL TRUE: the UI must display the ACTUAL post-opt mix (both audited games show
   true odds), and mystery must not overlap a tier buy's price. That constraint got
   TIGHTER after the rebuild, not looser -- the tier prices compressed to 240 / 268 /
   520x, so a mystery has to clear 520x to sit above the ladder and only the DRACO
   ASCENDANT slice can lift it there (see NEXT SESSION #3).

### RESOLVED PLAYTEST WATCH-ITEM (was: FEEL call; CLOSED by the ladder rebuild)
   (b) CORVUS/URSA CEILINGS TOO CONSERVATIVE -- FIXED Jul 28 2026. Return-on-stake
       (maxWin/cost) WAS corvus 1500/224 = 6.7x, ursa 4750/283 = 16.8x, draco
       25000/651 = 38x, against a market band of 50-100x (Rage Bait's buys 50-100x,
       Waylanders' capped bonus3 = 80x) -- corvus at 6.7x was the MOST-capped buy in
       the survey. The predicted lever (raise the per-tier multiplier ladders, which
       lifts ceilings with RTP untouched) WORKED AS PREDICTED: now corvus 48x, ursa
       93x, draco 48x. All three are in or at the band, and ursa is the best in the
       game. Draco's 48x is its ARITHMETIC MAXIMUM (25,000 cap / 520x cost), not a
       tuning miss -- at a 500x ticket the cap alone forbids more, so do not chase
       50-100x there. (Reading note: stakestats "Max Multiplier" for a buy is
       COST-NORMALIZED = maxWin/cost; our published maxWin column is base-bet, so
       divide by cost to compare.)
- A WINCAP SLICE'S rtp SHARE IS ITS FREQUENCY -- the only dial that sets how often a
  mode pays its max win, and it is exact, not a tuning knob:
      rate = slice_rtp * cost / cap        (slice_rtp = rate * cap / cost)
  So slice_rtp is literally the share of that mode's RTP delivered by cap books, which
  also makes it the cap-value-per-stake -- the right number to compare ACROSS modes at
  different prices. Verified: base at slice_rtp 0.02, cost 1.0 measured P=8.0e-07,
  exactly 0.02*1.0/25000. The slice QUOTA in game_config is a separate thing entirely
  (a sampling quota: how many cap books get generated for the optimizer to weight), and
  confusing the two is easy -- the quota does not set the frequency.
- base wincap slice sits at P=8.0e-07: clears the doc's ">= ~1e-7 / better than 1 in
  10M" gate, marginally under the stricter 1e-6 written elsewhere in this file.
- ⚠ ANY forced-wincap slice LOOPS FOREVER if the cap drifts out of structural reach
  (base/ante/buy_draco/buy_mystery all carry one). That is what a "hang" means here,
  not a crash. Both sweep harnesses strip the slice for exactly this reason.
- Regenerate strips: `./env/bin/python games/starwake/reels/generate_reels.py`
- Run unit tests:  `./env/bin/python -m pytest tests/starwake/ -v`
- Measure loop (~15s/mode): `cd games/starwake && ../../env/bin/python run.py buy_corvus 20000`
- FR0 density sweep: `./env/bin/python games/starwake/reels/sweep_fr0.py 4 3 0 40000`
- Draco shape sweep: `./env/bin/python games/starwake/reels/sweep_draco_cells.py 40000`
- Beast size / roam floor sweep: `./env/bin/python games/starwake/reels/sweep_beast.py 40000`
  (⚠ back up the buy_draco pool first -- see the sweep gotcha above)
- Full detached pool: `cd games/starwake && ./run_modes.sh`   (log in library/logs/)
  ⚠ LAUNCH IT WITH `setsid nohup ./run_modes.sh >launch.out 2>&1 </dev/null &`, NOT as an
  agent background job. A 106-min run must outlive the session; setsid gives it its own
  session id so it is reparented to init instead of dying with the process tree. Verify
  with `ps -o pid,ppid,sid` -- its sid must differ from the shell's. The sims and the
  optimizer are 100% local compute, so a run costs no model tokens once launched.
- Optimizer for ONE mode (~5 min, no re-sim): `../../env/bin/python run.py optimize buy_mystery`
  This is the whole loop for any change that lives in game_optimization.py -- rtp
  splits, hr, scaling, fence order. Re-simming for those is wasted time.
- Read the player-facing distribution, NOT the raw pool: every benchmark (bust rate,
  win frequency, std dev, ETL, >100x share) must be computed from the OPTIMIZED LUT as
  sum(weight*payout)/sum(weight) over `publish_files/lookUpTable_<mode>_0.csv`, joined
  to `lookup_tables/lookUpTableSegmented_<mode>.csv` for per-criteria splits. The raw
  book pool is QUOTA-shaped: base has exactly 40% zero-win and 50% basegame books by
  construction, so reading a bust rate off it is meaningless. LUT format is
  `id,weight,payout*100`; segmented is `id,criteria,basegame_payout,freegame_payout`.
- Inspect a book: decompress `library/publish_files/books_buy_draco.jsonl.zst`, walk `events`.

## Lessons inherited from Keybearer (do not relearn these)
- Two-stage pipeline: game_config generates outcomes; optimizer only RE-WEIGHTS
  to hit RTP. It cannot invent outcomes — convergence failures = fix strips/
  paytable/feature, not optimizer config.
- The basegame hit-rate is the global RTP dial and it is SIM-COUNT DEPENDENT —
  tune at production count (1e6), never trust quick-run tuning.
- Fixed-length features kill runaway loops AND volatility: Keybearer fell to
  m2m ~2.2. Starwake's vol must come from the completion-time × tier tail, not
  feature length. If vol is low, fatten the beast ladder / tier spread.
- Persistent state (sticky wilds, climbing mult) is where silent bugs live —
  Keybearer's global mult multiplied NOTHING until the lines strategy was switched
  symbol→combined. Unit-test the feature engine before full runs.
- Tier-based spin awards, not count-indexed (key-rich strips show 6+ scatters;
  exact-count indexing KeyErrors).
- Buy-mode books should never pay zero (market norm: buys bust 0.00%) — ours is
  structural (any lit star pays), verify it stays true.
- Replays are public + shareable: the wincap book must be watchable. Bounded feature
  length guarantees it — now 10 (corvus) / 15 (ursa, draco), worst case 17: a
  last-spin completion sets tot_fs = max(tot_fs, fs + min_roam_spins) = 15 + 2. Keybearer's 60-spin cap book took
  ~10min — never again. Any future length increase is a REPLAY decision too.

## Gotchas
- ETL IS NOT WHAT THE DOC'S TAKEAWAY SAYS. The gate is **ETL(>=40x COST) <= 0.8**
  (doc L302) -- a win-SIZE measure, not top-tier share. Measured: base 0.341, ante
  0.387, buy_corvus/ursa/draco 0.000, buy_mystery 0.041. At a 500x mystery, 40x cost
  = 20,000x, so only the sliver under the cap counts -- ETL CANNOT BIND for our buys
  at any tier mix. Doc L356 conflates it with Captain Death's 80% top-tier share;
  those coincide only on a 100,000x-cap game. Do not use top-tier share as an ETL
  proxy. (CVaR <= 700 normalized, the other tail gate, is still UNVERIFIED.)
- COMPLETION RATES, CURRENT (100k/tier, Jul 28): corvus 83.8 / ursa 62.6 / draco
  32.0%. Earlier figures scattered through this file are all SUPERSEDED -- the Phase A
  note's 95/54/28 predates the economy re-tune's FR0 drying, and the ~11.9% draco it
  corrected predates the 10->15 spin change that nearly tripled it back. Draco is
  finally AT the "~30% dragon lottery" target it was designed for. Corvus FELL 95 ->
  83.8% because it went the other way, to 10 spins.
- `>cost` NO LONGER EQUALS COMPLETION. It used to on draco (7.7% both) -- you beat the
  ticket iff you complete, because the carpet topped out below the cost. That equality
  WAS the cliff. Now: corvus 25.1 / ursa 22.1 / draco 19.8% >cost against 83.8 / 62.6 /
  32.0% completion, i.e. cheap completions that do not beat the ticket now exist on
  every tier. Watching those two numbers decouple is how you see a cliff close.
- ⚠ THE SWEEP HARNESSES OVERWRITE THE PRODUCTION POOL. `create_books` writes to the
  standard library/ paths, so any sweep destroys that mode's converged books, LUTs,
  segmented LUT, force record and verification file. Move them aside first and move
  them back after (instant on the same filesystem; a buy_draco set is ~2.4 GB).
  The optimized `lookUpTable_<mode>_0.csv` is not rewritten by sims but goes STALE
  (its book ids stop existing), so protect it too.
- MEASURE/SWEEP HARNESSES ONLY PRINT AFTER THE LAST TIER FINISHES, so a session that
  dies during a multi-tier run loses the WHOLE report even though every tier
  succeeded. IT IS RECOVERABLE WITHOUT RE-SIMULATING: `read_books` / `summarise` /
  `report` in measure_tiers.py are pure readers over
  `library/publish_files/books_<mode>.jsonl.zst`, so import them, chdir to the game
  dir, and re-run just the analysis (~1 min for 300k books vs ~8 min to re-sim).
  This is how the Jul 28 confirmation table above was recovered. The catch: it only
  works until the next sweep overwrites those tapes -- WRITE THE NUMBERS DOWN.
- MEMORY: `batching_size` is a memory knob, not a speed knob. The SDK derives batch
  count as round(sims/threads/batching_size), so at 1e5/14/5000 it rounds to ONE batch
  and every thread holds 7,142 books at once -- MORE than at 1e6. A buy book is ~34 KB
  of JSON vs ~4.6 KB for a base book, so that was ~15 GB live and it took the whole WSL
  VM down mid-buy_corvus. 1000 pins the in-flight set to ~14k books at any sim count.
  Lowering a sim count can make memory WORSE.
- Drying FR0 moves the COMPLETION RATE, not the payout per completion (draco's
  completed-feature mean held 6451 -> 6074 -> 5945x across W=12/4/2). So density is
  the lever for Draco's rarity and the WRONG lever for Corvus's price.
- A ladder is the only knob that lowers the mean and raises the ceiling at once. A
  paytable cut scales body and tail together, so it can never widen max-vs-typical --
  and cutting it far enough to fix the price put the 25,000x cap out of reach.
- Reel-3 constellation cells are a gate AND A KEY -- see the shape sweep in
  game_config.constellation_cells. Never "harden" a tier by adding reel-3 cells.
- Fill rule = WIN-LINE crosses cell (NOT star-landing; λ/fly-to-cell retired). This
  couples completion to win-rate + paytable + strips + shape simultaneously — no clean
  analytic completion rate, derive by sim, expect slower convergence (interdependent
  knobs). Constellation SHAPE is now load-bearing (paylines-per-cell = difficulty).
- Cold-start / ETL: partial progress MUST pay (ETL ≤ 0.8, no win-gaps). The snowball
  spreads outcomes naturally, but features with no early wins never ignite → near-bust.
  Watch buy-mode bust rate; a fill floor (guaranteed 1-2 cells, or star-drop backstop,
  or wetter early reels) is the lever if it busts too often.
- Stake compliance: no gamble features (tier-upgrade gamble was rejected for
  this), statelessness = stateful features inside one book are fine, post-approval
  = total math lock (all 6 modes ship finished or not at all).
- stake.us social language: route ALL UI copy through lang files with sweeps_
  variants from day one (bet→play, buy→get, etc.).
- Thumbnail/tile art must be BRIGHT (no dark edges) despite the night-sky theme —
  constraint art direction from day one, plus provider/studio name + logo needed
  before submission (undecided).
