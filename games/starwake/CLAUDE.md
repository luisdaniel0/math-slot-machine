# Starwake — working notes

Celestial constellation slot, 5x4 / 20 paylines. **The math is done, gated and
published.** Current phase is the frontend and art.

This file holds only what you CANNOT get from the code. Everything else lives at its
source, and the source wins:

| what | where |
|---|---|
| design + full rationale | `docs/ideas/starwake.md` |
| what the game IS (paytable, cells, prices, ladders, modes) | `game_config.py`, `go/config/starwake.json` |
| what is built | the tree + `tests/starwake/` |
| competitor comparison sheet | `BENCHMARKS.md` |
| **how every number was arrived at** | **`DECISIONS.md`** (dated sessions, newest first) |
| repo rules, remotes, Go engine, commands | root `CLAUDE.md` |

⚠ **Before changing any paytable value, strip, cell map, price, ladder, band or
optimizer setting, grep `DECISIONS.md` for the knob name.** Nearly every one was
measured at least once, most cost a 1e6 sim run, and several were measured, found not
to work, and reverted. The list under "Measured, does not work" below is the index.

## Where it stands

Six modes, all at RTP 0.96690 to seven decimal places. **Menu 200 / 300 / 400 / 500.**
Mystery mix 35 / 35 / 20 / 10 (corvus / ursa / draco / ascendant), delivered and
verified off the LUT, not just designed. All seven CRITICAL tests pass; 3-Star carries
zero failed classes, 2-Star one (absolute CVaR, structural to any 25,000x game, free).

⚠ **`buy_corvus` WAS REPLACED BY `buy_mystery_spin` ON Aug 13 2026** (branch
`mystery-spin`). The deciding number was that cost-adjusted volatility read **corvus
1.85 against ursa 1.88** — the two cheapest products were the same product at two
prices. **The corvus TIER is untouched** and still rolls in base, ante_starfall,
buy_mystery and buy_mystery_spin; only the 200x buy is gone. The new mode is ONE spin
with the set dealt complete and the beast already up, 150x, mix 15/25/60
corvus/ursa/draco. Full measurement record in `DECISIONS.md`.

⚠ **`buy_mystery_spin` IS THE ONLY MODE THAT DOES NOT PUBLISH 25,000x.** Its ceiling is
**15,000x** and that is structural. One spin cannot ACCUMULATE, and accumulation is how
the 15-spin modes reach the cap. Measured organic max, unforced: **19,778x unseeded,
23,072x seeded** — both under the cap, and flat across roam densities ROAMCAP 10 → 2000.
At a 200x ticket 15,000x is 75x cost, still ahead of Rage Spins' 71.4x and nearly double
Miko Spin's 40x.

⚠⚠ **CAP-SLICE COST IS EXPONENTIAL IN HOW FAR THE TARGET SITS ABOVE THE ORGANIC MAX.**
Measured on the wake spin with the seed floor ON (100 sims, one cap book each):

    cap        redraws/book   books/s   est 1e6
    25,000        29,102          9     ~31 hours
    22,000        13,843         18     ~15 hours
    20,000         6,575         38     ~7 hours
    18,000         3,871         66     ~4 hours
    15,000           237        808     ~21 min

A **16x cliff** between 18,000 and 15,000. **No amount of forcing rescues an
above-record target** — the seed floor bought 3x against the ~1000x that was needed.
This is the general form of the loop-forever warning: it does not hang, it just becomes
unaffordable, and the failure looks like a run that never finishes.

⚠ **THE SEED BOUGHT RICHNESS, NOT CEILING** — the opposite of why it was added. Raw mean
330.24x → 423.92x, which is what makes a 200x ticket land at richness 2.19. At 150x it
would sit at 2.92, above the healthy band, generating value only to discard two thirds.
**The cheaper ticket does not make a mode punchier; the optimizer needs room to discard,
and that room IS the volatility.**

⚠ **The live pool is `games/starwake_go/library/`.** `games/starwake/library/` is the
stale Jul 31 Python-era pool — measuring it reads buy_draco at RTP 1.0036 and looks
entirely plausible. `check_risk_gates.py` still DEFAULTS to the stale path; pass the
shadow dir explicitly.

Open, in rough priority:
- **Delete the dead multiplier ladder** (see below). Deferred on purpose, not forgotten.
- **Two-fence modes undershoot RTP.** Every 2-fence mode lands low (corvus 0.9661,
  draco 0.9650), every multi-fence mode lands exact. Padding the body fence breaks
  `verify_optimization_input`. The prize is draco's 0.15%.
- **The points rubric is unknown** — what the scale is out of, how points split across
  art / depth / performance. Worth asking Stake; it is the actual grading sheet.
- Frontend: replay mode is mandatory and entirely absent; `constellationAscend` has no
  art and is the moment corvus's whole ceiling depends on.

## Traps — where the code validates, runs, and lies

Every entry here is a case where the config loads, the sim completes, the numbers look
plausible, and the thing you changed did nothing. This is the failure family that has
cost the most time on this game.

- ⚠⚠ **THE MULTIPLIER LADDER IS DEAD CODE.** `constellation_mult_ladders` /
  `constellation_ladder_rungs` never run — Act Two replaced the climbing ladder with
  star collection, `ActTwo() = drops != nil` (constellation.go:262), every tier carries
  `starDrops`, so the ladder branch (constellation.go:335) is unreachable in every mode.
  The values are still in game_config, still exported, still validated by
  config.go:171-179. **A ladder edit is a silent no-op.** Kept loadable on purpose:
  config.go:242-244 records that the A/B sweep needs the path with no roam weights.
- **The multiplier is DERIVED, not authored**: `multiplier = 1 + collected`
  (constellation.go:412). x2 is unobtainable (smallest star is 2, so the set is x1 then
  resumes at x3 — zero occurrences in 5.27M rounds); no gaps from x3 up. Neither ceiling
  the enumerator prints is publishable — the combinatorial bound is fiction, the observed
  max is a sample that moved with sample size. **The honest bound is the 25,000x win cap.**
  The multiplier gets a rule; the win gets a cap.
- **Sweep harnesses overwrite the production pool.** `create_books` writes to the
  standard paths, destroying that mode's books, LUTs, segmented LUT, force record,
  verification file and event config. Move them aside first. The optimized
  `lookUpTable_<mode>_0.csv` is not rewritten but goes STALE (its book ids stop
  existing), so protect it too. Backups have been incomplete before — force records and
  verification files are the ones that get forgotten.
- **go/out books are HARD LINKED to the published pool** (link count 2). A 20k smoke run
  truncated both — a 1.5 GB shipped file became a 30 MB stub. Back up before any
  small-count run.
- **`batching_size` is a memory knob, not a speed knob.** Batch count is
  `round(sims/threads/batching_size)`, so at 1e5/14/5000 it rounds to ONE batch and every
  thread holds 7,142 books — more than at 1e6. That was ~15 GB live and it took the WSL
  VM down. Keep it at 1000. **Lowering a sim count can make memory worse.**
- **Publishing is a SEPARATE step.** The Go pipeline writes books and LUTs and nothing
  else. Run `go/publish_go.py` after ANY game_config.py change — the pool and the publish
  layer once drifted 36 hours apart and shipped a stale price that an outside tool caught
  before we did. Fixing the source is not fixing the artifact.
- **The fence-config family — three members, all silent, all invisible to
  `verify_optimization_input`** (it only checks that splits sum and criteria match):
  (a) fence ORDER — tier fences searching `{"symbol":"scatter"}` with no `kind`, so the
  first swallows every feature book; (b) fence ORDER — the basegame catch-all before the
  `"0"` fence, skewing the weight denominator, uniform 1.019x overshoot; (c) fence
  PROPORTION — `hr` wrong, uniform 4.0x undershoot. **A uniform factor on every slice
  means look at the fence bookkeeping, never at the game math.** `hr` is a "1 in N"
  frequency, and the shares must be EXHAUSTIVE: `sum(1/hr) + wincap weight == 1`.
- **`hr` is DERIVED, not tuned**: `hr = 1/(1-cap_rate)`, `cap_rate = cap_rtp*cost/cap`.
  Leaving it behind when a ceiling moved put a mode at 0.9673 — over Stake's 0.967 cap, a
  CRITICAL failure that blocks submission. **Every ceiling or price change re-derives it.**
- **A reprice moves THREE coupled values per mode** — cost, cap_rtp, hr — plus any
  ticket-relative bands. A stale one shows up as a wrong RTP, never as an error.
- **Derive scaling bands from the ticket, never hardcode them.** Every hardcoded band in
  this game has gone stale on a reprice at least once: corvus's 30/60/120/240 were
  written for a 240x ticket and were boosting the dump zone by the time it cost 120x.
- **A forced wincap slice LOOPS FOREVER if its cap is out of structural reach.** That is
  what a "hang" means here — not a crash. Both sweep harnesses strip the slice for this
  reason, and they also lift `BetMode._wincap` to the design cap first, or the published
  ceiling clamps the draw and hands last session's decision back as a natural limit.
- **Never price a mode off the raw pool mean.** The wincap slice is a sampling QUOTA, not
  a probability — 0.5% of books forced to 25,000x adds ~125x to the mean.
- **`force.json` is APPEND-ONLY** (write_data.py:219-227). A stale mode survives every
  future run; deleting the force record does not clear it, force.json itself must go.
  `make_force_json` looks like the rebuild helper, is dead code, and is doubly broken.
- **`event_config_<mode>.json` is auto-discovered FROM THE BOOKS** (publish_go.py:153),
  not from game_events.py. The published vocabulary self-heals on republish.
- **`config_fe_<game>.json` is not byte-reproducible** — symbols come from an unordered
  collection, so every `generate_configs` reshuffles them. A changed fe hash is not a
  math change.
- **The star table is SHARED.** base, ante_starfall, buy_mystery and buy_mystery_spin all
  roll corvus-tier features, so touching it re-sims and re-converges FOUR of six modes.
- ⚠⚠ **A NEW TIER VARIANT CANNOT BE KEYED BY SCATTER COUNT ABOVE 6.** `ascendant` at 6 is
  the ceiling of that trick, not a pattern to extend. `_force_special_board` places **at
  most one scatter per reel**, so on five reels a 6th already needs a reel window
  revealing two — which is the entire reason the ASC strip exists, and it only succeeds
  ~92% of the time there. A 7th needs two such reels; 8/9/10 are unreachable. **In Python
  an unreachable forced count does not error — `force_special_board` is a bare
  `while True`, so it hangs forever.** The wake spin rides a `wake` flag on the
  DISTRIBUTION instead (the `forceAscension` path), leaving the trigger board ordinary.
- ⚠ **THE PYTHON ENGINE CANNOT RUN A WAKE SLICE, AND NOW REFUSES TO.**
  `constellation.py` predates act two — no star drops, no collection — so it would
  silently write a full-length ladder feature with entirely plausible numbers.
  `game_override.update_freespin_amount` raises NotImplementedError on a wake condition.
  **The Go engine is the sim engine for buy_mystery_spin.** This also means the Python
  sweep harnesses (`sweep_beast.py`, `measure_tiers.py`) cannot measure it.
- **A repeated max win is a SAMPLE, not a structural bound.** The wake spin read exactly
  17,496x across four roam densities at 500k, which looked like a hard combinatorial
  ceiling; at 3e6 it moved to 19,778x. Same trap as draco reading x1,126 at 5k and
  x1,841 at 1e6. Raise the sim count before concluding anything is a limit.
- **Enrichment cannot buy a ceiling.** ROAMCAP 10 → 2000 moves the wake spin's mean +5%
  and its natural max not at all, and it makes the CAP SLICE MORE expensive, not less
  (1,153 → 1,287 redraws/book at 15,000x). The cap TARGET is the only lever on slice cost.
- **Reel-3 constellation cells are a gate AND A KEY.** Never "harden" a tier by adding
  them. ⚠ This does NOT transfer to PRE-LIT cells, where the reel-4 pair is
  transformative and the reel-3 neck nearly worthless — opposite problems.
- **`optimization_program/src/setup.toml` is generated by every optimizer run.** Tracked,
  never commit it.

## Measured, does not work — do not re-derive

Each of these cost real sim time. Details and tables in `DECISIONS.md`.

- **A denser roam strip cannot reach 25,000x.** 8 density x richness variants at 1e6;
  best 18,196x against the shipped strip's 18,613x. Pushing density past the optimum
  makes it WORSE.
- **Max win cannot rank strips.** Same weights, same length, different shuffle seed:
  12,957x vs 18,613x — a 44% swing. Use a tail RATE, which counts thousands of books.
- **The ascension rate `one_in` has no detectable effect.** Within-variant spread (21.6
  points) is wider than the gap between variants (12.5). It sits at 20,000 on no evidence.
- **Corvus's body instability is unexplained.** Gapless scaling bands and a reprice to cut
  richness were both tried; neither moved the spread. The reprice was kept for other
  reasons.
- **Corvus cannot be both the safe entry tier and carry a real 9,000x.** Building the tail
  via a richer star table worked exactly as swept and made corvus the harshest and most
  volatile buy in the menu. Reverted. Fixed instead by CUTTING THE CEILING to where the
  distribution actually lives.
- **Cutting the constellation is rejected.** Cells are FUEL, not difficulty — easy cells
  are the engine that manufactures the long wins needed to reach the hard ones. Every cut
  variant broke the tier ladder. Keep 4 / 7 / 11.
- **Longer features do not fix corvus's pricing**, and cost completion separation, book
  size and price at once.
- **Base volatility: three routes, all closed.** Raising the cap share makes the cheapest
  bet the best max-win play; raising the feature's payout spread collapses the tier ladder
  (the feature's RTP share is fixed, so making each feature pay more makes it happen less);
  base-boost is real but parked until a playtest with a controller in hand. Do not reopen
  without new information.
- **The base-game meter needs cascades** and was reverted. Rage Bait's collect → cascade →
  collect chain does not transfer for the same reason — do not design assuming it.
- **3x3 beasts break the roam** (6 positions on a 5x4 vs 2x2's 12) and cost a second sprite
  rig. Twin dragons is two 2x2s for this reason.
- **The 2-scatter dud is dropped** — ours triggers at 3, so a 2-scatter roll is a plain
  base spin, and a dud slice buys tail, not fun.
- **A tier-upgrade gamble is rejected** — Stake permits no gamble features.

## Why the numbers are what they are

- **Max win 25,000x, and it is coupled.** Absolute CVaR IS the max win whenever a mode's
  cap lands more often than 1 in 1,000 (CVaR is measured over the worst 0.1%, so the whole
  window becomes cap books). **Absolute CVaR is therefore a cap on the cap** — 50,000 at
  3-Star. Going to a 50,000x max win would land exactly ON the limit AND force every cap
  rate below 1 in 1,000, draining the cap's RTP contribution. Two coupled re-derivations
  for a bigger number on the tin.
- **RTP 0.9669, not 0.967.** buy_ursa can land 1.6e-09 ABOVE target, and the RTP band is a
  CRITICAL test — breaching it blocks submission outright. 0.9669 keeps ~60,000x the
  observed overshoot in margin and costs players 0.01%.
- **The conservation law**, which settles most "can we have both" questions:
  `completion_rate * completion_payoff + (1-rate) * consolation == RTP * cost`.
  Often-but-smaller or rarely-but-bigger. "Often and bigger" does not exist.
- **Cap rate is a dial, not a hope**: `rate = slice_rtp * cost / cap`, exact to ~1 part in
  1e6. `slice_rtp` is literally cap-value-per-stake, which makes it the right number to
  compare across modes at different prices. The slice QUOTA is a separate thing entirely.
- **Cost is a FREE PARAMETER — repricing needs no re-sim.** The optimizer reweights to hit
  `mean = rtp * cost`. The binding constraint is RICHNESS, `raw_mean/(rtp*cost)`; healthy
  modes sit 1.9–2.6.
- **Variance IS excitement.** Volatility and big-win frequency are the same axis; asking
  for the least volatile mode and then wanting big wins in it is incoherent. "Least
  volatile" and "kindest" are ~90% the same measurement (Spearman ~0.93) but cross over —
  std is tail-driven and squared, under-0.25x ignores the tail entirely. Track both.
- **Never compare std/cost across modes with different cap/cost ratios.** A higher headline
  std can be pure pricing artifact. Compare the cap-stripped body, or P(>=Nx ticket).
- **To move a distribution's bottom, scale the band JUST ABOVE it, not the middle.** The
  optimizer takes weight from the nearest band. And **range suppressions must start from
  0**, or displaced weight funnels into the gap below your range.
- **Frequency beats magnitude when building a tail.** A 50x rung at weight 1.0 beat a 100x
  rung at weight 0.4 and beat both together. Add a rung you will actually hit.
- **Beat rate is bought with concentration, not with dresses.** A fence whose own mean is
  half a ticket cannot pay a full one often — Markov caps it at the mean. Three dress cuts
  moved the body 10 points and the beat rate not at all.
- **n=8 is the minimum sample for any corvus body question** (~20-27 point draw-to-draw
  spread on under-0.25x, ~22 min per arm). n=1 and n=3 answer nothing.
- ⚠ **Corvus's gentleness is SELECTION, not structure.** Its draws and ursa's have
  effectively identical means; we shipped a favourable one. **Best-of-n before any publish
  is mandatory** and the property does not re-derive on its own. Same for its max-win rate:
  roughly 1 in 8 rebuilds ships an unpublishable corvus.
- **A tier is not the same product in every mode.** Completion inside buy_mystery differs
  sharply from the standalone buy, and unlike the roll odds these DO move on a rebuild.
  Frontend must not imply rolling ursa == buying ursa.
- **The roll odds CANNOT move on a reprice or a ceiling change** — they are generation-time
  quotas. Only a mix change moves them. This has been wrongly called stale at least five
  times.

## External facts — not in this repo at any length

- **The star rating is a HUMAN QUALITY REVIEW, not a math tier.** The math already passes
  every 3-Star risk limit with zero failed classes and **that is all it can contribute**.
  The third star is won on art, animation, sound, performance, bundle size and depth of
  play. Named failure: "players typically place only 1-2 bets before losing interest."
  Generic AI-generated assets are the single most-cited reason a game is sent back.
- **The publishing floor rose from 4.5 to 6 points** (announced week of Jul 28 2026,
  effective immediately for new games — Starwake is subject to the new one). Stake said
  they are monitoring whether 6 is right, **so it may move again**; the only insulation is
  to sit well above it. 1-Star is not published at all.
- **The 10,000,000 limit is OUTCOMES, not events** — confirmed by the RGS team, not
  inferred. At 1e6 per mode we use 10% of the cap. The doc's "events" wording cost a day;
  the tell was that the same page recommends 100k–1M sims, which under the literal reading
  would breach its own cap for essentially every slot ever made. **When a spec contradicts
  itself in adjacent sections, the reading is wrong, not the spec.**
- **The binding size constraint is FILE SIZE, and it is tighter than the docs.** Docs say
  4.2 GB, the RGS team says 3.14 GB — use the stricter. buy_draco is at 86% of it. That is
  the real reason to care about events per book.
- **ETL is `ETL(>=40x COST) <= 0.8`** — a win-SIZE measure, not top-tier share. At a 500x
  mystery, 40x cost = 20,000x, so only the sliver under the cap counts: **ETL cannot bind
  for our buys at any tier mix.** Do not use top-tier share as a proxy; that conflation
  only holds on a 100,000x-cap game. Worst case is **base** (0.558), not a buy.
- **CVaR's percentile convention is 0.1%** — confirmed from the RGS team's own platform
  code and `utils/analysis/distribution_functions.py` (cutoff 0.999, accumulate from the
  smallest payout up, conditional mean of the tail). Base reads 233.8 against 700. This
  closes what this file long recorded as the one gate resting on an assumption.
- **Non-critical failures do not block — they reduce exposure and bet caps, and the first
  one is free.** 0 and 1 failed classes both keep the full template. The question is never
  "do we pass everything", it is "are we at 2 or more". The class closest to flipping is
  Tail Probability (p5k/p10k), worst case draco.
- **`p5k`/`p10k` are NOT scaled by cost multiplier** — the docs are explicit, and an old
  leniency factor understated every buy mode.
- **mnemoo/tools is not our rubric.** It hardcodes global limits its own source calls
  "tentative defaults" that disagree with the docs-derived per-rating limits.
  `check_risk_gates.py` is the authority. Use mnemoo to find discrepancies and for
  CrowdSim session stats, which nothing of ours measures.
- **Stake compliance:** no gamble features; statelessness means stateful features inside
  one book are fine; **post-approval is a total math lock** — all six modes ship finished
  or not at all. Buy cost is capped at 1000x.
- **stake.us is social:** route ALL UI copy through lang files with `sweeps_` variants from
  day one (bet→play, buy→get).
- **Thumbnail/tile art must be BRIGHT** — no dark edges, despite the night-sky theme. An
  art-direction constraint from day one. Provider/studio name and logo are still undecided
  and are needed before submission.
- **Market norms** (measured, stakestats.net — full table in `BENCHMARKS.md`): max-win
  reachability 1 in 400–4,000; base bust 70–83%; win freq ≥1x ~7.4%; base std dev under 50.

## Lessons inherited from Keybearer — do not relearn these

- **Two-stage pipeline**: game_config generates outcomes, the optimizer only RE-WEIGHTS.
  It cannot invent outcomes — a convergence failure means fix strips/paytable/feature,
  never optimizer config.
- **The basegame hit-rate is the global RTP dial and it is SIM-COUNT DEPENDENT.** Tune at
  production count, never trust quick-run tuning.
- **Fixed-length features kill runaway loops AND volatility.** Keybearer fell to m2m ~2.2.
  Starwake's volatility must come from completion-time x tier tail, not feature length.
- **Persistent state is where silent bugs live** — Keybearer's global mult multiplied
  NOTHING until the lines strategy was switched. Unit-test the feature engine in isolation
  before full runs.
- **Buy-mode books should never pay zero** (market norm: buys bust 0.00%). Ours is
  structural — any lit star pays. Verify it stays true.
- **Replays are public and shareable, so the wincap book must be watchable.** Bounded
  feature length guarantees it; worst case here is 17 spins. Keybearer's 60-spin cap book
  took ~10 min to watch. Any future length increase is a REPLAY decision too.
