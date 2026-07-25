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
  cells light). Complete the set → beast wakes: oversized block wild (Corvus 2x2 /
  Ursa 2x3 / Draco 3x3) that ROAMS to a random position each spin (C&C/MIKO style;
  fine because the fat tail depends on how LONG it stays, not the path — it never
  exits), multiplier climbs +1/spin (enumerable ladder — compliance requires listing
  all values). Guaranteed min roam window (5 spins; a late completion extends the
  feature to honor it, worst case 15 spins). Fixed ~10 feature spins, no
  retrigger. Completion rates are now SIM-DERIVED (coupon-collector model retired);
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
- [x] Trigger table: fixed 10 spins ALL tiers (config.num_feature_spins), no
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
- [x] Guaranteed roam window (config.min_roam_spins = 5). A late completion (fewer
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
- [ ] Optimize → verify at 1e6/mode; event-ID finder for reviewer scenarios

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
- [ ] Set per-mode displayed ceilings + mystery odds (below); event-ID finder

### ▶ PICK UP HERE (next session)
PHASE B IS CONVERGED at 1e6. Costs 1 / 1.5 / 224 / 283 / 651 / 285x. Remaining:
1. DISPLAYED CEILINGS: corvus and ursa still publish max_win=25000 they cannot reach.
   Measured 1e6 ceilings are corvus 1,515x (P=7.3e-06) and ursa 4,774x (P=7.5e-07).
   Setting BetMode.max_win also sets the ENGINE CLAMP (run_sims.py:48 assigns
   config.wincap = bm.get_wincap()), so change it and re-run those two modes to
   confirm; the clamped tail is below measurement resolution but should be verified.
2. MYSTERY ODDS: measured post-opt mix is 25.74 / 63.20 / 11.06% against the intended
   60/30/10. Compliance requires the UI to display the TRUE odds, so either publish
   26/63/11 or give buy_mystery per-tier fences (kind=3/4/5, like base) so the mix
   becomes a designed quantity instead of whatever hits RTP. Design call.
3. Still open: the two STRUCTURAL feel levers (feature length 10 spins, and beast
   block sizes -- both FEEL calls, doc L255/L259, worth a playtest first). They are
   the only levers left for corvus, whose raw pre-multiplier cost is 89x -- i.e. the
   feature's base payout is already its whole budget and every multiplier is over it.
   Changing either invalidates this whole Phase B run.
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
- Full detached pool: `cd games/starwake && ./run_modes.sh`   (log in library/logs/)
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
- Replays are public + shareable: the wincap book must be watchable (~10 fixed
  spins guarantees this; Keybearer's 60-spin cap book took ~10min — never again).

## Gotchas
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
