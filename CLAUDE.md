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
  all values). Guaranteed min roam window (~3 spins). Fixed ~10 feature spins, no
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
      stick), beast roams on-grid climbing 2->10. TWO KNOWN FOLLOW-UPS:
      (a) guaranteed roam window NOT yet implemented — completing on the last spin
      wakes the beast with no spin left to roam (wasted); (b) completion ladder
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
- [ ] Reel strips via re-runnable weight-table script (BR star density → tier
      rates ~1/150 / ~1/2000 / ~1/100k start; FR density = λ; WCAP juiced)
- [ ] 6 bet modes + slice tables; per-mode displayed max wins (Corvus states an
      honest lower ceiling); wincap slice ≥1e-6 in every mode that claims 25,000x
- [ ] Run → measure loop (completion rates vs analytic targets, m2m, hit ≥1/20)
- [ ] Optimize → verify at 1e6/mode; event-ID finder for reviewer scenarios

### ▶ PICK UP HERE (next session)
Feature engine is DONE, unit-tested (13), smoke-verified, and pushed. Resume options
in dependency order:
1. **Guaranteed roam window** — small self-contained `run_freespin` change; closes the
   "complete on the last spin ⇒ beast wakes with no spin to roam" waste (see feature-
   engine note). No dependency on strips — good warm-up.
2. **Reel strips (weight-table script)** — the real unblock. The completion-ladder bug
   (Draco over-completes on scaffold strips) can only be measured/fixed on NATURAL
   (unforced) sims with real strips. This gates the whole measure loop.
Optional first: integration tests for `run_freespin` (a completed book always has
`beastWake`; event ordering; beast on-grid in real books) to lock the wiring.
- Run unit tests:  `./env/bin/python -m pytest tests/starwake/ -v`
- Smoke sim + books: `cd games/starwake && ../../env/bin/python run.py`
- Inspect a book: decompress `library/publish_files/books_bonus.jsonl.zst`, walk `events`.

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
