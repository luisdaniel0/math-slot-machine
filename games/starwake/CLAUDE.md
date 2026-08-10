# Starwake — Stake Engine lines slot (in development)

Celestial constellation game, scaffolded from `games/0_0_lines`.
Learner project: build step-by-step, explain decisions, don't bulk-complete.
FULL design doc + rationale for every decision: `docs/ideas/starwake.md` (read it
before proposing design changes — most "open questions" are already resolved there).
Keybearer & knockout_mayhem are SCRATCHED (code remains in games/ as reference only;
`games/0_0_keybearer` has the proven 5x4 paylines set and Vault/global-mult code).

⚠ THIS FILE IS THE GAME'S WORKING MEMORY and it is long because the math has a long
history of decisions that cost a sim run to re-derive. Read order if you are new:
  1. "Design spec" and "Build status" below — what the game IS and what is done
  2. "▶▶ WHERE WE ARE" — the current entry point, always kept at the top of the dated
     sections
  3. "Gotchas" and "Lessons inherited from Keybearer" at the bottom — the traps
  4. Everything between is DATED SESSION HISTORY, newest first. It is reference, not
     instruction. Where an older section disagrees with a newer one, THE NEWER WINS
     and the older one says so explicitly.
Repo-wide rules (remotes, what never to commit) live in the ROOT `CLAUDE.md`.
**`BENCHMARKS.md`** (this directory) holds the competitor-comparison sheet: our measured
numbers, the fixed CrowdSim config that makes session stats comparable, and the traps in
reading them. Use it when comparing Starwake to another game; use THIS file for why the
math is the way it is.

### ▶▶ WHERE WE ARE (Aug 5 2026)
MATH: DONE. Act Two built, converged and gated — see "THE MATH IS DONE" below for
the numbers and the pool location. All seven critical tests pass and 3-Star carries
zero failed classes.
⚠ AMENDED Aug 6, ALL RESOLVED, POOL REBUILT. Four things landed that day and every one is
measured, gated and published — gates never moved off 3-Star 0 failed classes / 2-Star 1:
  1. THE PUBLISH LAYER WAS 36 HOURS STALE. index.json/config.json shipped corvus at cost
     240 and maxWin 10,000 (B1). Root cause was optimize_go.py copying a hand-aged math
     config; stage() now GENERATES it. Corvus also shipped without its consolation bands.
  2. buy_corvus HAS A WINCAP SLICE. Its max-win rate was an optimizer draw ranging 1 in
     2.9M-11.2M with 1 of 8 draws missing the gate; it is now 1 in 2,000,003, every run.
  3. ASCENDANT OWNS THE MAX WIN (1 in 115, was 1 in 939); draco is second at 1 in 642.
  4. URSA IS A 48.2% COIN FLIP (was 34.7%), which makes draco's completion premium over
     it +51.5% instead of +7.5%, and drops ursa from harshest buy to second-kindest.
⚠⚠ AMENDED Aug 8 (LATER): THE CORVUS REBUILD LANDED AND THE POOL IS REPUBLISHED.
Corvus reaches 25,000x via the new ASCENSION mechanic, the buy menu is 200/300/500/600,
and the tier identity finally reads correctly. Every price, ceiling and body figure
dated before Aug 8 is superseded -- read "THE CORVUS REBUILD" below first, and note
its warning that corvus's gentleness is a SELECTED draw, not a structural property.
⚠ AMENDED Aug 8: RTP IS NOW 0.9669, NOT 0.9665, AND IDENTICAL ACROSS ALL SIX MODES to
seven decimal places. Every RTP figure dated Aug 6 or earlier in this file reads 0.9665
and is superseded — see "RTP RAISED TO 0.9669" below for the measurement and for why the
target is not 0.967 exactly. The same entry records the 20-point body variance that a
re-optimize inflicts on buy_corvus at an unchanged RTP.
NEXT IS THE FRONTEND, and it is the larger half of the remaining work. It is also
what decides the STAR RATING, which is a human quality review of art, animation,
sound, performance and depth — the math cannot earn a third star, only fail to lose
one. And the publishing floor rose to 6 points for new games. In rough order:
  (1) wire starsLanded / starsCollected; delete the ladder events
  (2) replay mode — MANDATORY and entirely absent
  (3) six-mode buy menu with the >2x confirmation, info/rules screen
  (4) mobile + popout layouts, sweeps_ language files, the SUPERSPIN remap
  (5) ART, ANIMATION, SOUND — longest lead time, does not block on the math, and
      the single most-cited reason a game is sent back. Start hiring in parallel.
  (6) mystery odds into the frontend copy (the last math-side publishing item;
      ⚠ re-read them off the CURRENT pool, the old 35.161/29.635/25.115/10.055 and
      the 526x price are both stale)
⚠ BEFORE ANY PUBLISH: re-measure buy_corvus's max-win rate on the exact pool being
shipped. It has no wincap slice, so its rate is an optimizer draw — measured across
identical runs at 1 in 3.1M to 6.6M, with one outlier at 1 in 14.5M, against a
1-in-10M gate. This is a permanent per-pool check, not a one-off.
⚠ AND RE-RUN `go/publish_go.py` AFTER ANY game_config.py CHANGE — the Go pipeline does
not publish. See "THE PUBLISH LAYER WENT STALE" (Aug 6) for the 36-hour drift this cost.
⚠ READ "HOW THE FEATURE ACTUALLY PLAYS" (Aug 6) BEFORE ANY FEATURE-ECONOMY CHANGE. Act 2
carries 75-93% of payback in every tier (the design works). It also records that the
84/62/32 completion ladder quoted all over this file is a RAW-POOL number — delivered is
90/35/30 — and the conservation law that decides every "can we have both" question.
⚠ THE DELIVERED LADDER MOVED TWICE ON Aug 6 — the numbers above are the OLD ones. Current
delivered completion is corvus 89.7 / URSA 48.2 / draco 29.9 / mystery 75.3, and ascendant
now owns the max win. Use "URSA IS A COIN FLIP NOW" and "ASCENDANT NOW OWNS THE MAX WIN".

### ▶▶ THE CORVUS REBUILD: ASCENSION, 25,000x, AND A ROUND-NUMBER MENU (Aug 8 2026)
THE POOL IS RE-SIMMED, RE-OPTIMIZED, GATED AND PUBLISHED. All seven CRITICAL tests
pass, 3-Star carries 0 failed classes, cross-mode RTP spread is 0.000%.

  mode              cost      RTP   std/c   <0.25x    beat   median      max win
  base               1.0  0.96690   25.16    73.0%    7.5%   0.000x  1 in 1,250,001
  ante_starfall      1.5  0.96690   22.90    70.3%    3.3%   0.000x    1 in 666,667
  buy_corvus         200  0.96690    1.43    29.7%   31.1%   0.439x     1 in 50,000
  buy_ursa           300  0.96690    1.88    39.6%   37.0%   0.369x      1 in 3,205
  buy_draco          500  0.96690    2.57    38.9%   20.9%   0.317x        1 in 667
  buy_mystery        600  0.96690    2.07    40.2%   20.9%   0.343x      1 in 1,041

THE TIER IDENTITY FINALLY READS CORRECTLY: volatility corvus 1.43 < ursa 1.88 <
mystery 2.07 < draco 2.57; corvus is gentlest (29.7% under-quarter-ticket, highest
median 0.439x); ursa pays back most often (beat 37.0%); corvus's max win is the
rarest in the menu and draco's the most frequent.

⚠ THAT IDENTITY IS SELECTION, NOT STRUCTURE. Corvus's five draws ran 29.7-48.2% on
under-0.25x and ursa's 39.5-46.1%; their MEANS are 41.5% and 42.1%, i.e. identical.
We shipped a corvus draw near the top of its range. BEST-OF-N BEFORE ANY PUBLISH IS
MANDATORY and the property does not re-derive on its own. An earlier single-draw
reading had ursa looking KINDER than corvus -- that was a bad corvus draw, not an
inversion, and both readings were selection effects.

WHAT ASCENSION IS. A rare round switches corvus to a richer star table (values
2/3/5/10/25/50 weighted 25/20/20/18/12/5, mean 9.40 against the ordinary 3.35).
Rolled once at beast wake, sticky for the roam, config-gated per tier.
  - WHY IT EXISTS: corvus tops out at 9,158x on the ordinary roam strip and 18,613x
    on the densest. EIGHT strip density/richness variants were swept at 1e6 and NOT
    ONE reached 25,000x -- the shipped ROAMCAP beat every one of them.
  - READ THE RATE, NOT THE MAX. The tail is nearly vertical: >=10,000x is 1 in
    12,195, >=12,000x 1 in 62,500, >=14,000x 1 in 500,000, >=25,000x extrapolates to
    1 in 25 MILLION. A max-win reading makes the gap look like 1.34x; in RATE terms,
    which is what a forced slice cares about, it is ~2,500x. That is 13 days of
    redrawing -- the documented "hang".
  - WHY 2.5x AND NOT DRACO'S 6x: at 6x corvus's ceiling would reach ~55,000x, so
    natural ascensions would slam into the clamp and the ASCENSION RATE, not the
    slice's rtp share, would set the max-win frequency. MEASURED: at 2.5x natural
    ascensions cap at 1 in 1,000,000, i.e. never, so the slice keeps sole control.
  - forceAscension pins it on for the wincap slice: P(>=25,000x) 1 in 25M -> 1 in
    2,874, so the slice fills its quota in ~2 min. (ForceWincap is declared but has
    NEVER been read by the Go engine; Go redraws until winCriteria matches.)
  - VERIFIED LIVE: 2,053 ascensions in 1e6 corvus books = 2,000 forced + 53 natural,
    a natural rate of 1 in 18,830 against a configured 1 in 20,000.
  - IN BASE IT IS NOT A ROUTE TO THE CAP. 67,000 corvus features, 7 ascensions, top
    ascended payout 1,331x. Base's board wins are too small for a 6x star table to
    reach 25,000x, so base still reaches the cap only via its own wincap slice, and
    base_std moved 24.80 -> 25.16 against a 60.0 limit. Nothing moved.

⚠ hr IS DERIVED, NOT TUNED: hr = 1 / (1 - cap_rate), cap_rate = cap_rtp * cost / cap.
The formula reproduces ursa's and draco's shipped values to 7 places. Leaving corvus's
behind when the ceiling moved put the mode at RTP 0.9673 -- OVER Stake's 0.967 cap,
a CRITICAL failure. EVERY ceiling or price change must re-derive it.

THE MENU IS NOW 200 / 300 / 500 / 600. This SDK treats a price as an OUTPUT
(cost = avg win / rtp), which is how it was 268/520/563 -- but the optimizer reweights
to hit mean = rtp * cost, so COST IS A FREE PARAMETER AND REPRICING NEEDS NO RE-SIM.
The binding constraint is RICHNESS, raw_mean/(rtp*cost); healthy modes sit 1.9-2.6 and
the new ladder lands 2.50/2.29/2.37/1.82. Ceiling-per-stake 125/83/50/42 tracks Rage
Bait's 100/71/50/50. A reprice moves THREE coupled values per mode (cost, cap_rtp, hr)
plus any ticket-relative scaling bands, and a stale one shows up as a wrong RTP rather
than an error.

### ⚠⚠ STRIP THE CAP AND THE VOLATILITY ORDERING INVERTS (Aug 8 2026)
std/cost is squared and tail-driven, so a mode's headline volatility is mostly a
statement about its CAP -- and caps differ in both rate and height across the menu.
Decomposed with payout_curve.py on the shipped pool:

  mode          total std   cap share of E[X^2]   BODY std (cap stripped)
  buy_ursa         1.88            48.5%                 1.167
  buy_corvus       1.43            10.5%                 1.312
  buy_mystery      2.07            31.8%                 1.622
  buy_draco        2.57            49.7%                 1.690

⚠ CORVUS IS NOT THE CALMEST MODE TO PLAY -- URSA IS. Corvus wins the headline only
because its cap is 75x rarer (1 in 50,000 vs ursa's 1 in 3,205), contributing 10.5%
of its E[X^2] against ursa's 48.5%. In the 99.998% of spins that are not a max win,
ursa is the tighter distribution. "Corvus is least volatile" is TRUE OF THE SPEC
SHEET and FALSE OF THE FELT EXPERIENCE. Decide which the tier brief means; if it
means felt, the lever is corvus's CAP RATE, not its body.

⚠ RETRACTED SAME DAY: "draco is an identity mismatch, very-high-vol on paper but the
bottom of the market's buy range". THAT COMPARISON WAS INVALID -- it ranked raw std
across modes with different ceiling-per-stake. Draco has the HIGHEST body volatility
in the menu (1.690) and beats Rage Bait's comparable buy at every threshold it can
reach: 5x+ ticket 3.96% vs 1.37%, 10x+ 0.475% vs 0.356%, session big-win 76.0% vs
65.6%. Rage Bait's higher headline std (2.58) comes from a 100x ceiling-per-stake
against draco's 50x -- four times the variance per unit probability -- which is a
PRICING artifact, not excitement. Draco is behaving exactly as its brief describes.
=> NEVER COMPARE std/cost ACROSS MODES WITH DIFFERENT cap/cost RATIOS. Compare the
   cap-stripped body, or compare P(>=Nx ticket) directly.

### ⚠⚠ THE OPTIMIZER DRAW CHOOSES CORVUS'S PERSONALITY (Aug 8 2026)
THE SELECTION RULE IS A DESIGN DECISION, NOT HOUSEKEEPING. Measured over 2 draws at
each of three ascension rates, on identical books:

  one_in  draw  std/c  <0.25x   median   P(>=10x)   session big-win (1-exp(-300p))
  20000     1    1.68   45.8%   0.302x   1 in 450         48.7%
  20000     2    1.93   51.6%   0.209x   1 in 172         82.5%
  2000      1    1.39   38.3%   0.426x   1 in 2,203       12.7%
  2000      2    1.78   49.6%   0.263x   1 in 318         61.0%
  500       1    1.71   43.6%   0.309x   1 in 361         56.4%
  500       2    1.38   28.8%   0.425x   1 in 1,526       17.8%
  SHIPPED        1.43   29.7%   0.439x   1 in 1,610       17.0%

1. one_in HAS NO DETECTABLE EFFECT. Two draws at an unchanged 20,000 gave session
   big-win 48.7% and 82.5%; the within-variant spread dwarfs everything between.
2. THE DRAW MOVES BIG-WIN FREQUENCY ~10x (1 in 172 to 1 in 2,203) on IDENTICAL books.
3. THE SHIPPED POOL IS ONE OF THE FLATTEST DRAWS OF ITS OWN CONFIG. Corvus is not
   structurally flat -- WE SELECTED FLATNESS. The best-of-N rule was "lowest
   under-0.25x, tie-break lowest std", and sorting the draws by std shows why that is
   self-reinforcing: std 1.38 -> 17.8% session, 1.68 -> 48.7%, 1.93 -> 82.5%.
=> VOLATILITY AND BIG-WIN FREQUENCY ARE THE SAME AXIS. Variance IS excitement. Asking
   for the least volatile mode and then wanting big wins in it is incoherent; the
   conservation law in book_split's output says the same thing.

⚠ "LEAST VOLATILE" AND "KINDEST" ARE ~90% THE SAME MEASUREMENT (Spearman ~0.93 across
these draws) BUT NOT IDENTICAL. std/c is squared and tail-driven, so one 100x outcome
outweighs a thousand near-misses; under-0.25x is purely the LEFT side and ignores the
tail entirely. They cross over: the std 1.39 draw has under-0.25x 38.3% against the
std 1.43 draw's 29.7% -- lower volatility, materially worse to play. Track BOTH: the
left-side number is what a player feels, std is what stakestats and a reviewer read.
For corvus they currently select the same draw, so there is no live conflict; the real
trade is (kind AND low-vol) vs EXCITING, and the shipped pool takes the first.

### ⚠ FOUR THINGS MEASURED AND FOUND NOT TO WORK (Aug 8 2026) -- do not re-derive
1. A DENSER ROAM STRIP CANNOT REACH 25,000x. 8 variants of star density x premium
   richness, 1e6 each. Best 18,196x; the shipped ROAMCAP hit 18,613x. Pushing density
   PAST the optimum makes it worse (x2.5 and x3 both underperformed x2), confirming
   generate_reels.py's own "IT IS NOT SIMPLY MORE STARS" warning.
2. STRIP LAYOUT ALONE SWINGS THE MAX 44%. Same weights, same 130-row length, different
   shuffle seed: 12,957x vs 18,613x. MAX WIN CANNOT RANK STRIPS -- use a tail RATE,
   which counts thousands of books instead of one.
3. THE ASCENSION RATE'S EFFECT ON THE BODY IS NOT ESTABLISHED. A single-draw sweep of
   one_in over 2,000/10,000/20,000/50,000 appeared to rank them; repeating at n=3
   showed the within-variant spread (21.6 points) is WIDER than the gap between
   variants (12.5). one_in sits at 20,000 with no evidence it matters.
4. CORVUS'S BODY INSTABILITY IS UNEXPLAINED. Hypothesis was that its pool being 3.74x
   richer than its price needed gave the optimizer too much freedom. Two fixes tried:
   GAPLESS SCALING BANDS (spread 21.6 -> 17.0, nothing) and REPRICING to cut richness
   to 2.49 (spread 27.7 -> 23.0, nothing). The reprice was KEPT anyway because it
   delivered std/cost 2.00 -> 1.66 and beat 21.6% -> 26.4%, both real at n=8 -- but
   NOT for the reason it was attempted.
⚠ n=8 IS THE MINIMUM SAMPLE for any corvus body question. Its draw-to-draw spread is
~20-27 points on under-0.25x, so n=1 and n=3 answer nothing. ~22 min per arm.

### ▶▶ RTP RAISED TO 0.9669 AND EQUALISED ACROSS ALL SIX MODES (Aug 8 2026)
WHY THIS WAS POSSIBLE ONLY NOW: the buys used to UNDERSHOOT their target — the mode RTP
was right in the optimizer's own report but the delivered LUT came in low, because the
body fence's `hr` was not exhaustive (see game_optimization's feature_cond note). Any
headroom under the 0.967 cap was therefore being eaten by a bug rather than spent on
players. With that fixed, the headroom is real and can be handed back.

MEASURED ON THE SHIPPED LUTs, exact rational arithmetic over id,weight,payout*100:
  mode             exact RTP     vs target     headroom to 0.967
  base             0.96689997    -3.10e-08     +0.000100
  ante_starfall    0.96689997    -2.83e-08     +0.000100
  buy_corvus       0.96689996    -4.37e-08     +0.000100
  buy_ursa         0.96690000    +1.58e-09     +0.000100
  buy_draco        0.96689996    -3.64e-08     +0.000100
  buy_mystery      0.96690000    -4.08e-10     +0.000100
ALL SIX AGREE TO SEVEN DECIMAL PLACES. That is the "same RTP across every mode" property
Meta Gaming ships and it is now a real invariant here, not an approximation.

⚠ WHY NOT 0.967 EXACTLY. buy_ursa lands 1.6e-09 ABOVE its target, so targeting the cap
itself can produce 0.967000002 — over. The RTP band is a CRITICAL test: breaching it
blocks submission outright, unlike a non-critical failure that only costs a bet-level
cap. 0.9669 keeps 1e-04 of margin, ~60,000x the observed overshoot, and costs players
0.01% RTP. 96.69% and 96.70% are indistinguishable in every player-facing surface.

⚠ WHAT THE CHANGE BROKE ON THE WAY: base and ante had HARDCODED catch-all splits
(0.6065 / 0.5415) that silently pinned those modes to 0.9665, so raising game_config.rtp
tripped `verify_optimization_input`. Both now derive the catch-all from `rtp`. Any future
RTP move is a one-line change again — if a split is ever hardcoded back, this breaks.

⚠ RTP BEING RIGHT SAYS NOTHING ABOUT THE BODY. Re-optimizing re-rolls every mode's shape.
The same 0.9669 run that fixed the RTP moved buy_corvus's under-0.25x rate from 32.1% to
53.5% and its beat rate from 28.4% to 13.6% — a full 20 points of body variance at an
identical, correct RTP. ALWAYS MEASURE THE BODY, NOT JUST THE RTP, BEFORE PUBLISHING;
corvus is the mode this bites. Draco, ursa and mystery all came out BETTER on that run,
which is the same coin landing the other way, not evidence the change helped them.

### ▶▶ THE PUBLISH LAYER WENT STALE AND NOTHING NOTICED (Aug 6 2026)
FOUND BY AN OUTSIDE TOOL, not by us: mnemoo/tools (community LUT explorer,
github.com/mnemoo/tools) read the pool and flagged buy_corvus NON-COMPLIANT at RTP
48.32%. THE MATH WAS FINE. The price tag was stale.

THE POOL AND THE PUBLISH LAYER HAD DRIFTED 36 HOURS APART:
  game_config.py             Aug 5 16:34  cost 120, corvus_cap 9000  <- the reprice
  go/config/starwake.json    Aug 5 23:03  cost 120                    correct
  LUTs + books               Aug 5 23:04+ mean payout 115.98x         correct
  index.json                 Aug 4 01:19  cost 240                    STALE
  config.json                Aug 4 01:19  cost 240, maxWin 10,000     STALE
  event_config_*.json        Aug 4 01:19  multiplierClimb, no act two STALE
  books_*.verification.json  Aug 4 01:19  hashes of REPLACED books    STALE
115.98x / 120 = 0.9665 (correct). / 240 = 0.4832 = exactly what the tool reported.

⚠⚠ THE SHIPPED config.json STILL ADVERTISED corvus maxWin 10,000 — that is B1, the
defect recorded below as "THE ONE BLOCKING MATH DEFECT" and fixed in game_config.py on
Aug 5. FIXING THE SOURCE IS NOT FIXING THE ARTIFACT. The publish step is what closes it.

WHY NOTHING CAUGHT IT: the Go pipeline (run_modes.sh / full_run.sh / optimize_go.py)
writes books and LUTs AND NOTHING ELSE. Publishing is a SEPARATE step — go/publish_go.py
— and it had not run since Aug 4. Its own verify() would have caught the stale sha256s
the moment it ran, but it checks mode NAMES and HASHES, not COSTS, so the 240 would
still have shipped. A cost cross-check against game_config.py is a cheap addition.
=> RULE: `env/bin/python go/publish_go.py` after ANY game_config.py change. It takes
   seconds. Editing a price and re-simming is only two thirds of the job.

FIXED Aug 6 by re-running publish_go.py: index 240->120, config 240->120 and maxWin
10,000->9,000, event configs rebuilt, hashes recomputed, verify() clean. GATES
RE-CHECKED on the republished pool, not assumed (several divide by cost, and corvus's
just halved): base_std 25.357, etl40 0.558, p5k 5.01e-03, p10k 2.24e-03, 3-Star 0
failed classes, 2-Star 1 (the known absolute CVaR). Nothing moved.

⚠⚠ AND THE SAME DRIFT REACHED THE MATH ITSELF: **buy_corvus SHIPPED WITHOUT ITS
CONSOLATION BANDS.** optimize_go.py:55 copies math_config.json from the OLD LADDER
GAME'S directory (games/starwake/, Jul 31) and then _sync_bet_modes() overwrites
cost/rtp/max_win from the live GameConfig — so PRICES ARE SAFE and corvus would NOT
revert to 240x. But the sync touches ONLY the bet-mode block. **`dresses` and `fences`
are copied blind.** The docstring at optimize_go.py:81-84 claims fence drift "is checked
below rather than silently tolerated" — THERE IS NO SUCH CHECK. Fences happened to be
identical; dresses were not.

Commit 5e9c59c (Aug 5 21:26) added three consolation bands to buy_corvus — scale 1.4/2.0/
1.5 on win ranges 30-60 / 60-120 / 120-240 — and its own note calls them LOAD-BEARING:
the 240->120 reprice left corvus returning under a quarter of the ticket on 59.1% of buys
at a 0.17x median, and the bands were measured to move that to 42.3% and 0.29x, "larger
than the ~8 points of optimizer run-to-run noise on this mode". It also moved the
maxwin_boost dress from win range [9000,10000] to [8100,9000] to match the corrected cap.
THE Aug 5 23:13 OPTIMIZER RUN NEVER SAW ANY OF IT — the Jul 31 file has 3 corvus dresses,
the live config produces 6.

MEASURED ON THE SHIPPED LUT, and it is unambiguous:
  [8100,9000) shoulder   1 in 19,511,305   <- the band TODAY's dress boosts 4.0x;
                                              4x RARER than the cap. Not applied.
  cap, exactly 9,000x    1 in  4,613,159   <- all cap weight, = the max-win figure
                                              recorded above. The Jul 31 dress's mark.
  under 0.25x ticket             52.2%     vs 42.3% intended (59.1% unbanded + noise)
  weighted median               0.230x     vs 0.29x intended
=> CORVUS IS SHIPPING THE PRE-BAND ECONOMY. Not a compliance failure — every gate still
passes — but the entry-tier buy is harsher than the design that was signed off, and the
17-point improvement recorded in 5e9c59c was never actually delivered.

⚠ WHY THIS WAS INVISIBLE: the shadow math_config reads cost 120 / max_win 9,000, because
the sync wrote those. It LOOKS fresh. Only the dresses are stale, and nothing prints them.
=> FIXED Aug 6 2026 IN optimize_go.py. stage() no longer copies: it calls a new
   write_math_config() which runs make_temp_math_config() against the live GameConfig,
   deriving bet modes, fences and dresses from config.opt_params in one pass.
   _sync_bet_modes() is deleted — generating makes it redundant, and a dead check that
   lies in its own docstring is what caused this. optimize_go.py no longer references
   games/starwake/ at all. VERIFIED: the generated file is BYTE-IDENTICAL to the one
   publish_go.py produces (same generator, same source), corvus now carries all 6
   dresses, and the 30 unit tests pass. Net -18 lines.

POOL REBUILT Aug 6 2026. buy_corvus re-optimized (161s) + republished. RTP 0.9665,
zero-pay 0.00%, max win 9,000x. Gates re-read: UNCHANGED, 3-Star 0 failed classes.

                          pre-band    with bands   design target
  under 0.25x ticket         52.2%         36.5%   42.3%   <- beat it
  weighted median           0.230x        0.325x   0.29x   <- beat it
  beat the ticket           18.64%        15.23%           <- the price, -3.4 pts
  max win               1 in 4.61M    1 in 9.29M   > 1 in 10M
  [8100,9000) shoulder  1 in 19.5M    1 in 7.13M           <- dress now lands
THE BODY FIX WORKED AND OVERSHOT IN THE GOOD DIRECTION. The entry-tier buy now returns
under a quarter ticket on 36.5% of buys rather than 52.2%, better than the 42.3% the
bands were designed for.

⚠⚠ BUT THE TAIL HEADROOM IS NEARLY GONE, AND THIS IS THE LIVE DECISION. Corvus's max
win moved 1 in 4.61M -> 1 in 9.29M against a "typically more frequent than 1 in
10,000,000" gate: headroom fell from 2.2x to 1.08x. Exactly the trade 5e9c59c warned
about -- corvus has no wincap slice, so body weight comes out of an unprotected tail.
⚠ AND THIS MODE'S CAP RATE IS AN OPTIMIZER DRAW WITH KNOWN SPREAD: identical runs have
measured 1 in 3.1M to 6.6M with a 14.5M outlier. Sitting at 9.29M, A ROUTINE RE-RUN CAN
NOW LAND OUTSIDE THE GATE. The permanent per-pool max-win check recorded at the top of
this file has stopped being a formality and become the binding constraint on corvus.
DIALED BACK Aug 6 to 1.25/1.6/1.3 (from 1.4/2.0/1.5), re-optimized and republished.
Gates unchanged, 3-Star 0 failed classes. SHIPPED STATE IS 1.25/1.6/1.3.

  bands            RTP   under .25x   median    beat        max win
  pre-band      0.9665       52.2%    0.230   18.64%   1 in 4.61M
  1.4/2.0/1.5   0.9665       36.5%    0.325   15.23%   1 in 9.29M
  1.25/1.6/1.3  0.9665       34.4%    0.338   19.07%   1 in 8.32M
  design target 0.9665       42.3%    0.290              > 1 in 10M

⚠⚠ THE DIAL-BACK DID NOT DO WHAT IT WAS MEANT TO DO, AND THE REASON MATTERS: WEAKER
BANDS PRODUCED A *BETTER* BODY (34.4% vs 36.5%), A BETTER MEDIAN AND A BETTER BEAT RATE.
That is not a monotonic response to a smaller scale factor — IT IS THE OPTIMIZER'S OWN
RUN-TO-RUN NOISE, the exact thing commit 5e9c59c is named for. Every delta BETWEEN the
two band settings (2.1 pts body, 3.8 pts beat, 0.97M cap) sits inside this mode's
documented spread: ~8 points on the body, and cap-rate draws measured from 1 in 3.1M to
1 in 14.5M on IDENTICAL configs. n=1 per setting cannot separate them.
### ▶▶ CORVUS'S TAIL WAS BUILT AND REVERTED (Aug 7 2026). THE CLIFF IS REAL, THE FIX ISN'T
POOL IS BACK TO ITS PRE-CHANGE STATE, verified number-for-number and re-gated (3-Star 0
failed classes, ETL40 0.558). Nothing shipped. Read this before anyone retries it.

THE DEFECT, and it is real and still open: CORVUS PRODUCES NOTHING BETWEEN 2,500x AND ITS
9,000x CEILING. Measured on the shipped pool: 8,295 books in 2,500-5,000, 142 in
5,000-8,100, and **ONE BOOK** in 8,100-9,000 out of 1e6. Consequences:
  - its published max win is delivered at 1 in 2,000,003, against a MARKET NORM OF
    1 in 400-4,000 (Meta Gaming's three titles, see BENCHMARKS.md)
  - the 9,000x max win contributes 0.1% OF CORVUS'S VARIANCE. Strip it entirely and std
    dev moves 250.906 -> 250.825. It is decoration.
  - the maxwin_boost dress on (8100, 9000) is boosting exactly ONE book, i.e. inert
⚠ NO OPTIMIZER DRESS CAN FIX THIS. Weights cannot create books the engine never makes.
Raising corvus_cap_rtp alone would bolt a spike onto a distribution that dies at 2,500x
and CREATE a win-range gap where we currently pass.

THE ATTEMPT: corvus's star table stops at 25x where ursa reaches 50x and draco 100x, so
its collected multiplier cannot get large enough. Swept +50 / +100 / +both
(reels/sweep_star_values.py, now carries these variants and a >=20x/40x/60x TAIL SUPPLY
column). Built corvus+50 at 1e6 across ALL FOUR AFFECTED MODES -- base, ante_starfall,
buy_corvus and buy_mystery all roll corvus-tier features and share the table.

  IT WORKED ON THE TAIL, exactly as swept:
    >=2,500x   1 in 2,417 -> 1 in 888        >=5,000x  1 in 151,016 -> 1 in 11,679
    a real ladder appeared under the ceiling: 2.5-4k 1 in 1,078 | 4-5k 1 in 8,861 |
    5-6.5k 1 in 17,458 | 6.5-8k 1 in 66,279 | 8-9k 1 in 78,396
  AND THE BODY PAID FOR IT:
    under 0.25x ticket  41.6% -> 60.4%       median   0.294x -> 0.166x
    beat the ticket     17.2% -> 14.2%       std/c      2.09 -> 2.56
  Corvus became the HARSHEST AND MOST VOLATILE buy in the menu, at the cheapest price.

⚠⚠ THE TAIL WAS NEVER WHAT COST THE BODY, AND THIS IS THE PART WORTH REMEMBERING.
Everything above 2,500x is 4.0x of a 116x mean = 3.5% of RTP. What actually happened is
that richer supply let the OPTIMIZER move ~15x of RTP into 500x+ (the 500-2,000 band went
1 in 15 -> 1 in 13) and it hollowed out the middle to pay: >=10x fell 86.4% -> 65.1%,
>=25x fell 65.1% -> 44.6%. Rebuilding the body afterwards does not rescue it -- moving 15
points of weight from ~10x books to ~200x books ADDS 28.5x of RTP, a quarter of the whole
budget, which has to come straight back out of the 500-2,000 band.
=> CORVUS CANNOT BE BOTH THE SAFE ENTRY TIER AND CARRY A REAL 9,000x.

=> FIXED Aug 7 2026 BY CUTTING THE CEILING, NOT BY BUILDING TAIL. corvus_cap
9,000x -> 2,500x, which is where corvus's distribution actually lives (P(>=2,500x) was
1 in 2,417 unforced), and corvus_cap_rtp 0.0000375 -> 0.008333 to pin the rate.

  metric              9,000x        2,500x
  max win rate   1 in 2,000,003   1 in 2,501     <- THE POINT
  ceiling/cost           75.0x         20.8x
  median                0.294x        0.256x
  beat                   17.2%         16.8%
  under 0.25x            41.6%         48.9%
  RTP                   0.9665        0.9661
  Gates: 3-Star 0 failed classes, RTP spread 0.151%. Corvus is now BENIGN on risk --
  p5k, p10k and ETL40 all read 0.000 because a 2,500x ceiling is under every threshold.

⚠⚠ THE WHOLE BUY MENU IS NOW MARKET-NORMAL ON MAX-WIN REACHABILITY:
  draco 1 in 642 | mystery 1 in 1,110 | CORVUS 1 in 2,501 | ursa 1 in 3,589
All four inside the 1-in-400-to-4,000 band measured off Meta Gaming (BENCHMARKS.md).
Corvus was the lone outlier at 1 in 2,000,003. It is now THIRD most reachable, not first
-- draco and mystery are more frequent, which suits the expensive tiers.

WHAT IT COST, and it is much less than the tail-build cost: the 5x-25x band funded the
bigger cap slice (>=10x fell 86.4% -> 77.3%, >=25x 65.1% -> 55.9%), some of which is
corvus's own +/-10 point body noise. Corvus sits THIRD of four on harshness (mystery 41.2
< ursa 43.1 < corvus 48.9 < draco 53.1) rather than becoming the worst, which is what the
star-table attempt did. The mid-tail actually IMPROVED: >=500x 6.92% -> 7.53%, >=1,000x
1.88% -> 2.22%.
⚠⚠ RTP LANDED AT 0.9661 AND RE-OPTIMIZING DOES NOT FIX IT -- IT IS STRUCTURAL, NOT A
DRAW. Two runs both returned 0.966114 to six figures. Diagnosed by splitting the delivered
RTP per fence: THE WINCAP FENCE HITS ITS TARGET (0.008330 vs 0.008333) AND THE BODY FENCE
UNDERSHOOTS (0.957784 vs 0.958167, short 0.000383).
=> AND IT IS NOT A CORVUS PROBLEM. THE PATTERN IS FENCE COUNT:
     base / ante / mystery   6 fences each   0.9665 EXACT
     corvus / ursa / draco   2 fences each   0.9661 / 0.9662 / 0.9650
   Every TWO-fence mode undershoots; every multi-fence mode lands exactly. DRACO HAS THE
   SAME DEFECT FOUR TIMES WORSE (0.9650 = 0.15% under) and it has been accepted as normal
   since it was first converged.
⚠ THE OBVIOUS HACK DOES NOT WORK: padding the body fence's target to compensate breaks
verify_optimization_input, which asserts the rtp splits sum to the mode rtp at 5dp.
=> ACCEPTED FOR NOW at 0.9661 -- 0.04%, band spread 0.151% against a 0.5% limit, every
   mode under the 96.70% cap. But UNDERSTANDING THE TWO-FENCE CONVERGENCE BEHAVIOUR IS A
   REAL OPEN ITEM, because the prize is draco's 0.15%, not corvus's 0.04%.

⚠ AND WATCH WHICH DRAW YOU KEEP. The re-optimize returned identical RTP but a WORSE body
(beat 14.64% vs 16.81%, median 0.246x vs 0.256x, under-0.25x 50.5% vs 48.9%) -- corvus's
+/-10 point body variance again. The better draw was restored. Any corvus re-run needs the
body measured before it is published, not just the RTP.

⚠ TWO DRESSES WERE REMOVED WITH THE CEILING and should stay removed:
  tail_scaling("corvus") -- damps (1000,2000) at 0.8 and lifts (3000,4000) at 1.2. Above
    a 2,500x cap the second band CANNOT EXIST, and the first is no longer "mid tail" but
    the shoulder right below the ceiling, which corvus should not be suppressing.
  maxwin_boost("corvus", ...) -- its own docstring says it is ONLY for modes with NO
    forced wincap slice. Corvus gained one on Aug 6, so it had been redundant since then
    and would now fight the slice: a slice sets the rate exactly, a scaling hint only
    biases toward it.

⚠ KEEP THIS LESSON REGARDLESS -- IT GENERALISES TO EVERY FUTURE GAME:
**FREQUENCY BEATS MAGNITUDE WHEN BUILDING A TAIL.** A 50x star rung at weight 1.0 beat a
100x rung at weight 0.4 AND beat both together. The two 100x variants returned a natural
max of exactly 6,247x -- IDENTICAL to shipped, i.e. no effect at all -- because at 0.4%
weight across ~5.5 collected stars you hit one only ~2.2% of the time and still need
lines through the block to cash it. Add a rung you will actually HIT, and concentrate the
weight rather than splitting it across two high rungs.

⚠ METHOD NOTE: the star table is SHARED. base, ante_starfall, buy_corvus and buy_mystery
all roll corvus-tier features, so touching it re-simulates and re-converges FOUR of six
modes. And the revert was cheap ONLY because the engine is deterministic: re-simming with
the old config reproduced byte-identical books, which made the backed-up optimized LUTs
valid again and skipped ~12 minutes of re-optimizing. VERIFY THAT rather than assume it --
compare the restored LUT's payout column against the freshly regenerated raw table.

### ▶▶ HOW THE FEATURE ACTUALLY PLAYS (Aug 6 2026). ACT TWO WORKS. FULL DESIGN AUDIT.
Measured off the SHIPPED pool, LUT-WEIGHTED (not the raw pool -- the two disagree badly,
see below). Harnesses: /tmp/acts_weighted.py, /tmp/mystery_mix.py, /tmp/cap_by_tier.py.

**THE HEADLINE: ACT 2 CARRIES THE GAME, IN EVERY TIER.** The design doc's open risk
("can act 2 carry the money?") is answered yes and it is not close.

  tier      completion   act1      act2     ACT2 SHARE   act2 share (completed only)
  corvus       89.7%    8.29x   107.69x       92.9%              93.3%
  ursa         34.7%   41.02x   216.60x       84.1%              92.5%
  draco        29.9%  121.94x   371.05x       75.3%              88.1%
  mystery      75.3%   87.29x   451.86x       83.8%              90.8%
Per PAYING SPIN act 2 pays 34-63x more than act 1 (corvus 2.34 -> 146.97, ursa 6.39 ->
219.12, draco 17.52 -> 762.05). Forming the constellation pays nearly nothing; the 2x2
roam is the whole economy. NO TIER IS BUILT BACKWARDS.

⚠⚠ THE 84/62/32 COMPLETION LADDER QUOTED THROUGHOUT THIS FILE IS A **RAW POOL** NUMBER.
Players get something different, because the optimizer reweights completed features:
     raw pool   84 / 62 / 32          delivered   90 / 35 / 30  (+ mystery 75)
Ursa is the casualty: 62.4% raw -> 34.7% delivered. Its "coin flip" is a 1 in 3. ALWAYS
say which one you mean; the raw figure is what a sim prints and it is not the product.

**THE PAYOFF LADDER ASCENDS, WHICH IS THE DESIGN INTENT WORKING** (total when completed,
as a multiple of the ticket):   corvus 1.07x -> ursa 2.52x -> draco 2.71x
Rarer completion buys a bigger payoff, exactly as intended. ⚠ BUT THE TOP RUNG IS FLAT:
corvus->ursa is +123% price for +135% payoff, ursa->draco is +94% price for +7.5%.
Draco's premium is really a MAX-WIN play (1 in 642 vs ursa's 1 in 3,589), not a
completion play -- write the buy-menu copy accordingly.

⚠ THE CONSERVATION LAW, and it settles most "can we have both" questions:
      completion_rate * completion_payoff + (1-rate) * consolation == RTP * cost
Everything is pinned except how you split it. You can have OFTEN-BUT-SMALLER or
RARELY-BUT-BIGGER; "often and bigger" does not exist. Worked example: ursa is
0.347*675 + 0.653*37.8 = 259. Forcing 50% completion gives C = 480x, i.e. completing
would pay 1.79x the ticket instead of 2.51x.
=> DONE Aug 6 2026, and the arithmetic above predicted the outcome to within 2%.
   See "URSA IS A COIN FLIP NOW" below. Completion 34.7 -> 48.2%, payoff 2.52 -> 1.83x
   (predicted 1.79x), and DRACO'S UNTOUCHED 2.71x IS NOW A +51.5% PREMIUM over ursa
   (predicted +51%). The flat top rung is fixed by changing ursa; draco was not touched.

### ▶▶ URSA IS A COIN FLIP NOW (Aug 6 2026). 48.2% completion, draco premium +51.5%
NO RE-SIM WAS NEEDED — the raw pool never changed. This is entirely an opt_params reshape,
so each trial was one `optimize_go.py buy_ursa` (~5 min) plus a measurement.

  metric                     before     after     note
  completion (weighted)       34.7%     48.2%    raw pool is 62.6% and did not move
  pays when completed         2.52x     1.83x    of the 268x ticket
  under 0.25x ticket          60.2%     43.1%    was the harshest buy; draco is 53.1%
  beat the ticket             21.4%     32.3%
  carpet (non-completed)     37.8x     45.20x
  RTP                        0.9662    0.9662    gates: 3-Star 0 fails, 2-Star 1 (CVaR)
  ursa p5k                 5.29e-04  4.70e-04    tail improved, not degraded

⚠⚠ THE MECHANISM, because it explains ursa's harshness AND its low completion as ONE
defect. The raw pool is ~2x too rich, so the optimizer must dump half the value, and the
cheapest way to dump value is TO PILE WEIGHT ONTO NEAR-WORTHLESS BOOKS. Measured before:
the 0-50x band held 12.5% of raw books and **49.3% of delivered weight**. Half of ursa's
probability mass paid under 0.19x the ticket. That single fact caused both symptoms, and
the two consolation dresses added earlier were fighting it from the wrong end.

⚠ IT IS NOT THE m2m BAND. Ursa sat at m2m 5.67 inside a (3,10) band, so the constraint
was NOT BINDING and moving it would have done nothing. This was checked before acting on
it; the completion/m2m correlation across tiers (corvus 1.5-5 -> 89.7%, draco 5-20 ->
29.9%) is real but it is a symptom, not the lever.

THE LEVER IS DRESSES, and the payout split makes them targetable: ABOVE 268x THE
SEPARATION IS CLEAN — non-completed ursa books essentially never pay a full ticket, so a
win_range dress can address completions specifically. Final set added to the ursa scaling:
    (0, 50)         x0.5    kill the dump zone
    (268, 800)      x2.2    50% completion at this RTP needs completions to average
                            ~484x; that is this band. Measured result 489.12x.
    (1200, 25000)   x0.5    the extreme tail was eating the budget that band needed
⚠ FIRST ATTEMPT USED (1, 50) AND LEAKED — books paying under 1x base bet fell outside the
range, the optimizer dumped displaced weight there instead (0-25x went 29.93% -> 39.49%),
and completion moved only 34.7% -> 37.9%. RANGE SUPPRESSIONS FROM 0, or it is a funnel.

⚠ URSA IS NO LONGER THE HARSHEST BUY. 43.1% under a quarter ticket against draco's 53.1%
restores the intended identity (draco is the lottery, ursa the coin flip) that the
wincap-0.030 note further down was written about. Ordering by harshness is now
mystery 32.7 < ursa 43.1 < corvus ~41.6 < draco 53.1.

⚠ A TIER IS NOT THE SAME PRODUCT IN EVERY MODE. Completion inside buy_mystery vs bought
standalone, RE-MEASURED Aug 8 2026 on the rebuilt pool: corvus 99.5 vs 92.3, ursa 42.8
vs 53.5, DRACO 53.0 vs 28.7 (+24 POINTS), ascendant 98.9. Ursa's inner completion FELL
63.7 -> 42.8 and draco's ROSE 45.6 -> 53.0 across the rebuild; unlike the roll odds,
these DO move. Max-win rate per roll: ascendant 1 in 108, draco 1 in 11,128, and corvus
and ursa rolls NEVER reach 25,000x -- so mystery's ceiling lives entirely in 35% of its
rolls. Mystery's economics (563x ticket, ascendant carrying ~50% of payback)
let it spend its tier budgets as "often but smaller" where the standalone buys spend the
same tiers as "rarely but bigger". FRONTEND MUST NOT IMPLY ROLLING URSA == BUYING URSA.

⚠ RETRACTED: "the mystery odds are stale". THEY WERE NEVER STALE. Measured delivered mix
35.144 / 29.622 / 25.105 / 10.129 against a published 35.16 / 29.64 / 25.15 / 10.06 --
every tier within 0.07pp.
⚠⚠ RE-CONFIRMED Aug 8 2026 ON THE FULLY REBUILT POOL (reprice to 200/300/500/600,
corvus to 25,000x, ascension live): 35.142 / 29.620 / 25.104 / 10.134. THE ODDS DID NOT
MOVE -- they come from generation-time roll quotas that none of the rebuild touched, so
a reprice or a ceiling change cannot shift them. The published figures stand.
⚠ THE CLAIM WAS MADE AGAIN ANYWAY on Aug 8, four times, without reading this entry.
That is what this file is for. Read it before calling anything stale. Payback split 14.28 / 13.52 / 22.34 / 49.86 against a
14.9/14.1/23.2/47.8 design. These numbers are VERIFIED against the shipped pool and can
go straight into the frontend copy. That closes the last math-side publishing item.

⚠ ETL40'S WORST CASE IS **base** (0.558), NOT A BUY. The per-mode table reads base 0.558
/ ante 0.529 / corvus 0.000 / ursa 0.027 / draco 0.079 / mystery 0.043. So buy-mode
changes do NOT threaten the tightest 3-Star gate -- an earlier note in this file implying
they do was wrong. What buy changes DO threaten is Tail Probability: p5k/p10k worst case
is draco (5.01e-03 / 2.24e-03), and a second failed class costs the $50 bet template.

### ▶▶ ASCENDANT NOW OWNS THE MAX WIN (Aug 6 2026)
MEASURED FIRST, and it was backwards: max-win rate per roll INSIDE buy_mystery was draco
1 in 317, ascendant 1 in 939. Every forced cap book in the mode used
draco_wincap_condition, so draco got all the help and ascendant kept only organic
leftovers -- on the tier that cannot be bought and carries ~50% of the mode's payback.

FIX: mystery's wincap Distribution now uses a new ascendant_wincap_condition (scatter 6,
ASC basegame strip -- NOT _wincap_condition(6), which draws BR0 where six scatters land
~20% of the time against ~92% on ASC). Quota, mystery_cap_rtp and total cap weight are
ALL UNCHANGED; no opt_params edit was needed, because the single "wincap" fence searches
payout == 25,000 and still matches, and fence order still puts it ahead of the kind=6
ascendant body fence.

  RESULT      ascendant  1 in 939 -> **1 in 115**      draco-in-mystery  317 -> 11,860
  ORDERING    ascendant 1 in 115 > buy_draco 1 in 642 > buy_ursa 1 in 3,589
              > draco-in-mystery 1 in 11,860 > buy_corvus 1 in 2,000,003
  Forcing is CHEAP: 1.02 redraws/book (draco's ~117, corvus's 2.74). No hang risk.
  Gates: 3-Star 0 failed classes, 2-Star 1 (absolute CVaR). Unchanged.

⚠ IT WAS NOT THE PURE RELABELLING IT WAS PREDICTED TO BE. Every cap book still pays
exactly 25,000x, but the optimizer re-solved the whole mode and mystery's tail IMPROVED:
p5k 4.67e-03 -> 3.45e-03, p10k 2.10e-03 -> 1.81e-03, ETL10k 0.073 -> 0.065. Draco's
payback share inside mystery fell 25.89% -> 22.34% and ascendant's rose 46.31% -> 49.86%
(closer to the 10%-of-rolls / ~52%-of-payback Rage Bait shape this mode is modelled on).
Displayed mix moved <0.08pp and still rounds to the published figures.

### ▶▶ CORVUS HAS A WINCAP SLICE (Aug 6 2026). RATE CONTROL WORKS; BODY COST UNRESOLVED
BUILT: corvus_wincap_condition = _wincap_condition(3, {"ROAM":1,"ROAMCAP":40}) + a
Distribution(criteria="wincap", quota=0.002, win_criteria=corvus_cap) on buy_corvus, and
a wincap fence in game_optimization.py at corvus_cap_rtp = 0.0000375.
⚠ win_criteria MUST be corvus_cap (9,000), NOT the global 25,000 cap — this mode clamps
at 9,000 via BetMode.max_win, so a slice hunting 25,000 would loop forever.

THE RATE FORMULA IS EXACT, not approximate: rate = slice_rtp * cost / cap reproduces
every mode's measured cap frequency to ~1 part in 1e6 (base 0.02 -> 1 in 1,250,000 vs
measured 1,250,001; ursa 0.026 -> 3,588 vs 3,589; draco 0.075 -> 641 vs 642). Corvus
targeted 1 in 2,000,000 and LANDED ON 1 IN 2,000,003. Cap RTP share 0.0039% vs 0.00375%
predicted. USE THIS FORMULA TO SET ANY CAP RATE — it is a dial, not a hope.

  FEARED: a forced slice hangs when its cap is near the top of organic reach.
  MEASURED: 2.74 redraws/book at 1e6 vs draco's ~117. ROAMCAP 40 made it cheap.
  Sim 1e6 in 23.5s, 2,000 wincap books, zero-pay 0.00%, completion 83.80% unchanged.
  Gates after: 3-Star 0 failed classes, 2-Star 1 (the known absolute CVaR). No change.

SETTLED BY n=8 WITH THE SLICE IN (Aug 6). Same harness, same pool:

                     UNSLICED n=8        SLICED n=8
  cap rate        1 in 2.9M .. 11.2M   1 in 2,000,003 ON ALL EIGHT RUNS
                  1 OF 8 FAILED gate   zero spread, gate failure impossible
  body mean              41.78%             46.20%
  body sd                  9.98               6.10
  body range           28.05-54.31        39.94-59.04  (26.3 pts -> 19.1 pts)

⚠ THE CAP RESULT IS NOT STATISTICAL, IT IS STRUCTURAL. Every run returned the identical
figure because the rate is now set by slice_rtp rather than drawn. This is the entire
point of the change and it worked completely.

⚠ THE BODY COST IS REAL-LOOKING BUT NOT ESTABLISHED. +4.4 points of mean is roughly
t=1.1 on ~12 df (p~0.3) — suggestive, NOT significant at n=8 each. The ~40% drop in sd
is likewise directionally right (the slice removes a free variable, which is what it
should do) but F=2.67 against a ~3.79 critical value, so also not formally significant.
DO NOT RECORD EITHER AS FACT. What IS certain: the slice's RTP cost is 0.0039%, far too
small to fund 4 points of body, so if the shift is real its cause is the SECOND FENCE
consuming the >=9,000x books, not the payback it spends.

⚠ THE SHIPPED DRAW IS AN UNLUCKY ONE: 55.8% under a quarter ticket against a sliced mean
of 46.2%, second-worst of the nine sliced measurements taken. Since the cap rate is now
fixed by construction, RE-DRAWING ONLY VARIES THE BODY, and players experience the
SHIPPED pool rather than the distribution of possible pools — so re-optimizing a few
times and shipping the best-balanced draw is defensible product work, not p-hacking, PROVIDED
the chosen draw is gated in full and the selection stops there.

DONE Aug 6. Six fresh draws, criteria FIXED BEFORE RUNNING (primary: lowest under-0.25x;
guards: median must rise inversely, beat >= ~16%, RTP/cap/max-win invariants, full gates
on the winner). Draw 6 won outright — best on the primary AND on both guards, so no
fallback was needed and the selection stopped there.

  draw   under.25x   median   beat        cap
    1       47.90%    0.264  20.70%   1 in 2,000,003
    2       62.46%    0.165  18.05%   1 in 2,000,003
    3       65.59%    0.120  19.66%   1 in 2,000,003
    4       46.43%    0.268  12.72%   1 in 2,000,003
    5       46.66%    0.273  18.84%   1 in 2,000,003
    6       41.62%    0.294  17.20%   1 in 2,000,003   <- SHIPPED
  (old)     55.80%    0.206  13.56%   1 in 2,000,003

SHIPPED CORVUS IS NOW 41.62% / 0.294x / 17.20% — better than the pool it replaced on all
three. Gates re-read on the winner: 3-Star 0 failed classes, 2-Star 1 (absolute CVaR),
base_std 25.357, etl40 0.558, p5k 5.01e-03, p10k 2.24e-03. Unchanged.
⚠ CAP RATE WAS 1 IN 2,000,003 ON ALL SIX, as on the previous eight — FOURTEEN CONSECUTIVE
RUNS at the identical figure. The slice is deterministic; this is settled, stop testing it.
⚠ THE BODY SPREAD IS STILL 41.6-65.6% ACROSS DRAWS. Selection fixed THIS pool, not the
config. Any future re-optimize of corvus re-rolls the body and needs re-measuring — the
same permanent per-pool discipline the max-win check used to need before the slice.

⚠ THE 20k SMOKE TEST DESTROYED THE SHIPPED BOOKS, and this will happen again. go/out's
books_buy_corvus.jsonl.zst is HARD LINKED (link count 2) to the published pool's copy, so
the engine truncating one truncated BOTH — a 1.5 GB shipped file became a 30 MB stub.
The 1e6 re-sim + publish repaired it. BACK UP go/out/library/{publish_files/books_,
forces/force_record_,lookup_tables/lookUpTable_}<mode> BEFORE ANY SMALL-COUNT RUN.

### ▶▶ CORVUS VARIANCE MEASURED, n=8 (Aug 6 2026). THE NOISE IS BIGGER THAN EVERY EFFECT
Harness: /tmp/corvus_variance/run_variance.sh — 8 optimizer runs on the SHIPPED config
(bands 1.25/1.6/1.3), same pool, ~25 min, restoring the published LUT byte-for-byte at
the end (verified: config.json's sha256 still matches).

  metric            min       max     median   spread
  RTP            0.9665    0.9665     0.9665   ZERO — converges perfectly every time
  under 0.25x     28.05%    54.31%    38.84%   26 POINTS
  median          0.215x    0.370x    0.310x
  beat            12.76%    18.94%    17.5%    6 points
  cap rate      1 in 2.9M 1 in 11.2M 1 in 5.2M  4x

⚠⚠ RETRACTION — "THE BANDS WORK" (recorded above, same day) IS NOT SUPPORTED. The
unbanded measurement of 52.2% sits INSIDE the banded distribution: runs 2, 5 and 8 came
in at 53.85 / 54.31 / 50.80 with the bands ON. n=1 unbanded against n=8 banded cannot
establish a difference, and 52.2% lands around the 75th percentile of the banded spread.
The bands MAY help — banded mean is 41.8% — but IT IS UNPROVEN AND WAS ASSERTED TOO EARLY.
The same applies to "the bands push the tail rarer": unbanded drew 1 in 4.61M against a
banded median of 1 in 5.24M. Noise.

⚠⚠ THE ANSWER WE ACTUALLY WENT LOOKING FOR: **1 OF 8 DRAWS FAILS THE 1-IN-10M GATE**
(run 1, 1 in 11.18M). A ~12% failure rate per re-optimize — point estimate only, the
95% interval on 1/8 is wide. The SHIPPED pool sits at 1 in 8.32M, i.e. in the unlucky
end of its own distribution, and passes.
=> THE PERMANENT PER-POOL MAX-WIN CHECK IS NOT OPTIONAL AND NOW HAS A NUMBER ON IT.
   Roughly one in eight rebuilds ships an unpublishable corvus. Never re-optimize this
   mode without re-measuring, and never assume a passing draw survives a re-run.

⚠ WHY SO NOISY, mechanically: RTP converges to 0.9665 EVERY time, so the optimizer is
not struggling — it is UNDER-CONSTRAINED. Corvus's raw pool implies ~3.75x its configured
price, so ~73% of the value is discarded, and there are many shapes that discard it while
hitting the same RTP. No wincap slice means the tail is one of the free variables.
=> DO NOT TUNE THE BANDS FURTHER OFF SINGLE DRAWS. Any change smaller than ~26 points of
body or ~4x of cap rate is unmeasurable at n=1, which is every change anyone would want.
=> THE STRUCTURAL FIX NOW HAS THE STRONGER CASE: give corvus a wincap slice, which turns
the cap rate from a 12%-failure lottery into a design parameter — what ursa, draco and
mystery already do. Rejected earlier because it "trades away the best body in the game";
that judgement was made against a single-draw body measurement which we now know carries
a 26-point spread, so THE EVIDENCE IT RESTED ON WAS NEVER SOLID. Re-ask it properly,
with replicates on both sides. NOT YET DECIDED.

⚠ event_config_<mode>.json IS AUTO-DISCOVERED FROM THE BOOKS (publish_go.py:153), NOT
from game_events.py. The published event vocabulary therefore SELF-HEALS on republish:
multiplierClimb vanished from all six modes with no code change. game_events.py is still
act-one-shaped and that did not matter here. CONFIRMED NAMES for frontend item (1):
**starsLanded** and **starsCollected** (14-15 types/mode; buy_corvus alone has no
`wincap` event — correct, it carries no wincap slice).

⚠ THE TOOL'S COMPLIANCE TAB IS NOT OUR RUBRIC. mnemoo hardcodes global limits (p5k
0.005, p10k 0.001, ETL40 2.0, CVaR 50,000) that its own source calls "tentative
defaults", and they disagree with the docs-derived per-rating limits in
check_risk_gates.py — p5k/p10k are 10x stricter there, so it reports tail failures we
pass with 10x headroom. Its star-tier table also differs (std-dev max 35/40/50, exposure
100k/5M/10M vs our $15M). USE IT TO FIND DISCREPANCIES, NOT TO DECIDE COMPLIANCE;
check_risk_gates.py remains the authority. What it is genuinely good for: CrowdSim
(session-level PoP / drawdown / streaks, which nothing of ours measures) and the
LGS + force-outcome + replay harness for the frontend phase.

### ▶▶ THE MATH IS DONE (Aug 5 2026). Clean 1e6 x 6, 23 min, all gates green.
POOL: `games/starwake_go/library/publish_files` (optimized LUTs) and
`go/out/library` (books, segmented LUTs). Every mode from ONE config state in one
pass. `games/starwake/library/` still holds the OLD LADDER POOL -- do not read it.

  mode              cost   median  med/c    beat  ceiling  ceil/c        max win  gaps
  base                1x       0x   0.00    8.0%  25,000x  25000x 1 in 1,250,001  none
  ante_starfall     1.5x       0x   0.00    3.2%  25,000x  16667x   1 in 666,667  none
  buy_corvus        120x      28x   0.23   18.6%   9,000x   75.0x 1 in 4,613,159  none
  buy_ursa          268x      46x   0.17   21.4%  25,000x   93.3x     1 in 3,589  none
  buy_draco         520x     122x   0.24   21.8%  25,000x   48.1x       1 in 642  none
  buy_mystery       563x     184x   0.33   18.7%  25,000x   44.4x     1 in 1,110  none

COMPLIANT: all seven critical tests pass; 3-Star has ZERO failed classes -> the
$500 bet template. 2-Star still shows one (absolute CVaR) and it is still free.
  base std        25.36    limit 60 (critical floor 0.6)
  CVaR/stake        245    limit 700
  CVaR absolute  25,000    limit 50,000
  P(>=5,000x)  5.01e-03    limit 0.050
  P(>=10,000x) 2.24e-03    limit 0.010
  ETL(>40x)       0.558    limit 0.9      <- moved 0.377 -> 0.558; the stacked base
  ETL sum         0.580    limit 1.5         pushes RTP into heavy-tail wins, as designed
NO WIN-RANGE GAPS in any mode. Largest books file 2.82 GB vs the 4.2 GB cap.

BASE DRYNESS FIXED, and it was the defect players would actually feel:
  ordinary base spin ceiling   22x -> 180x
  base RTP above 100x        0.229 -> 0.311
Hit rate, bust rate and the basegame RTP share are UNCHANGED at 29.25 / 70.75 /
62.8% -- opt_params pins all three, so the ceiling was not bought with any of them.
Same money, same hit rate, redistributed: the typical paying spin gives a little
less and the occasional one gives a lot more.

CORVUS'S MAX WIN LANDED AT 1 IN 4.61M, a mid draw of the measured 1-in-3.1M to
6.6M range and comfortably inside the 1-in-10M gate. ⚠ THAT CHECK IS PERMANENT:
corvus has no wincap slice, so its rate is set by the optimizer's draw and must be
re-measured on every pool that ships. One earlier draw landed at 1 in 14.5M.

⚠ WHAT IS **NOT** FIXED, deliberately: base std 25.36 against a 35-48 market band.
Stacking moved it only 24.51 -> 25.36 because base variance is dominated by the
wincap slice's 25,000x at 1 in 1.25M -- a 180x ordinary ceiling barely registers.
It was never a compliance issue (critical floor 0.6, non-critical ceiling 50/60);
the band is a competitor observation. Chasing it means changing what the CAP
contributes, which is far more invasive than anything done here. ACCEPTED.

NEXT IS NOT MATH. Replay mode (mandatory) does not exist; starsLanded/
starsCollected are not wired and the ladder events need removing; no buy menu,
info screen, mobile/popout, sweeps_ language files; no art, animation or sound.
That is what decides the star rating and the 6-point publishing threshold.

### ▶▶ CORVUS IS A PRICING PROBLEM, NOT A CEILING PROBLEM (Aug 5 2026)
Measured on the converged act two pool, buy_corvus has no reason to exist:

    mode         cost   median  med/cost   beat   ceiling  ceil/cost
    buy_corvus    240      59x    0.24    22.4%    9,158x     38.2x
    buy_ursa      268      33x    0.12    21.1%   25,000x     93.3x
    buy_draco     520     140x    0.27    21.7%   25,000x     48.1x
    buy_mystery   563     177x    0.31    22.0%   25,000x     44.4x

LAST on ceiling-per-cost, second-worst on median, and its beat rate is inside the
noise of the other three. Ursa costs 12% more and offers 2.7x the ceiling, because
ursa reaches the global 25,000x cap and corvus's ceiling is organic. Publishing
7,500x or 10,000x does not change any of this -- even at 10,000x corvus is 41.7x
cost, still last.

LONGER FEATURES DO NOT FIX IT (reels/sweep_feature_spins.py). Only corvus's ceiling
is organic, so extra spins raise its number while leaving ursa/draco/mystery's
forced 25,000x untouched -- the asymmetry that made the idea worth testing. It
works mechanically (corvus reaches 10,000x at 14-15 spins) and costs too much:
  completion 83.9/62.6/32.4 -> 89.4/75.4/44.5 (+20%) -> 93.1/84.5/55.1 (+40%),
    where corvus and ursa stop being distinguishable and draco is no longer rare
  implied price reaches 4.9x (corvus) and 6.8x (draco) of configured, so ~85% of
    the value would have to be optimized away, thinning the very tail it creates
  draco events/book 85 -> 120 = 120M per mode against the open 10M question, and
    its books file 2.82 -> ~4.0 GB against a 4.2 GB cap
And corvus is STILL last on ceiling-per-cost afterwards.

RE-PRICING DOES FIX IT. Same 1e6 pool, re-optimized per price:

    cost      RTP    median  med/cost   beat   ceil/cost   max win 1 in
    240x   0.9665       49x     0.20   23.9%      38.2x      3,115,983
    150x   0.9665       36x     0.24   18.3%      61.1x      4,350,921
    120x   0.9665       21x     0.17   20.7%      76.3x      4,732,641

At 120x corvus clears draco's 48.1x and approaches ursa's 93.3x, and THE MAX WIN
STAYS OBTAINABLE at 1 in 4.7M against the 1-in-10M guideline. It survives because
the ceiling contributes almost nothing to RTP (9,158x at 1 in 3.1M is ~0.001% of a
232x mean), so the optimizer hits a lower target by reweighting the BODY and has no
reason to touch the tail. beat/median wobble is optimizer variance, not a trend.
Menu becomes 120 / 268 / 520 / 563 -- a real ladder instead of 240 and 268 sitting
on top of each other.

⚠⚠ TWO HARNESS TRAPS FOUND THE HARD WAY HERE, BOTH SILENT:
 1. THE SWEEPS WRITE TO go/out/library/, THE SAME TREE THE CONVERGED POOL LIVES IN.
    sweep_feature_spins left corvus/ursa/draco as 20k books from its last variant
    (48-56 MB against 1.5-2.8 GB) and the next optimizer run happily consumed them,
    reporting RTP 1.9330 and a 10,000x ceiling the real pool cannot reach. Re-sim
    those modes after ANY sweep: `go/run_modes.sh 1000000 <modes>`. The engine is
    deterministic, so a re-sim restores byte-identical books.
 2. optimize_go.py COPIES math_config.json FROM games/starwake/library/configs/ --
    the OLD LADDER GAME'S directory -- and that file, not game_config.py, is where
    the optimizer reads bet_modes[].cost. Editing game_config.py to test a price
    changes only what the report divides by, so every run targets the same RTP and
    the output looks like a cost effect while being optimizer noise. Patch the math
    config to test a price. It also means the Go pipeline silently uses whatever
    fences and costs that file was last generated with -- currently Jul 31, still
    correct only because opt_params and the costs have not moved since.

### ▶▶ ACT TWO CONVERGED + FULL AUDIT (Aug 5 2026). 1e6 x 6 modes, 23 min end to end
POOL LIVES IN `games/starwake_go/library/` (optimized LUTs) and `go/out/library/`
(books, segmented LUTs). `games/starwake/library/` still holds the OLD LADDER POOL.
Read gates with: `check_risk_gates.py games/starwake_go/library/publish_files`.

COMPLIANT: YES. All seven critical tests pass. 3-Star shows ZERO failed classes ->
the $500 bet template. 2-Star still shows one (absolute CVaR 25,000 vs 20,000) and it
is still free. NOTHING REGRESSED vs the ladder pool -- tail probability improved:

  check              ladder    act two   3* limit   headroom
  base std dev        24.16      24.77       60       2.4x
  CVaR per-stake        234        229      700       3.1x
  CVaR absolute      25,000     25,000   50,000       2.0x
  P(>=5,000x)      6.57e-03   4.46e-03    0.050      11.2x
  P(>=10,000x)     1.79e-03   2.16e-03    0.010       4.6x
  ETL(>40x)           0.385      0.377      0.9       2.4x
  ETL(>10,000x)       0.085      0.094      0.8       8.5x
  ETL sum             0.411      0.404      1.5       3.7x
WIN-RANGE GAPS: NONE, in any mode (re-read because act two reshaped every
distribution). Largest books file 2.82 GB vs the 4.2 GB cap. Events per book
86.8 on ursa vs 87.0 before -- act two's two new events replaced multiplierClimb.

WHAT ACT TWO DELIVERED, measured:
  - the tier ladder HOLDS at 1e6: implied 450 < 561 < 934x, ratios to configured
    price 1.88 / 2.09 / 1.80 / 1.72. Tight enough that the optimizer converged every
    mode AT THE EXISTING MENU PRICES -- no repricing needed, which kills an open item.
  - beat-the-ticket is now uniform and market-normal (~22%): corvus 22.45, ursa
    21.09, draco 21.73, mystery 21.97. Draco was the worst offender at 18.9%.
  - mystery's payback split restored: 16.7/16.8/24.6/41.9 against the
    14.9/14.1/23.2/47.8 design (the first star tables gave a near-flat 27/27/19/26).
  - draco mean/median 1.17 -> 3.34 against the ladder's 1.72.
  - ursa, draco and mystery reach 25,000x ORGANICALLY, not only via the forced slice.

⚠⚠ B1, THE ONE BLOCKING MATH DEFECT: buy_corvus CANNOT PAY ITS PUBLISHED MAX WIN.
Across a full 1e6 its top payout is 9,158x against a published 10,000x. The
guidelines require "the maximum win amount matches the description in the game rules
for each mode", so the published figure is simply wrong. Corvus has NO wincap slice
(deliberately -- one was measured to trade away the best body in the game) and act
two removed the fully-wild-board route that used to reach the ceiling. Cannot be
tuned away. Tail curve, for choosing a replacement number:
     >=5,000x  1 in    70,144      >=8,000x  1 in 1,450,177
     >=7,500x  1 in   962,206      >=9,000x  1 in 2,476,458
Guideline is "typically more frequent than 1 in 10,000,000", so anything here passes
OBTAINABILITY -- the defect is the advertised number, not the odds.

⚠ Q1, BASE DRYNESS IS UNTOUCHED AND SLIGHTLY WORSE. Act two only changed the
feature. An ordinary base spin still tops out at 22x and carries 62.8% of base RTP,
with 70.75% of spins paying nothing. And the share of base RTP arriving as a win
above 100x fell 0.271 -> 0.226, because an act two feature can complete and still pay
small where the ladder's fully-wild board always paid big.
⚠ CORRECTION TO THE RECORD: the 0.372 figure quoted elsewhere in this file for
"share of RTP above 100x" is the FEATURE + CAP RTP SHARE, an upper bound, not the
measured >100x share. Measured like-for-like it is 0.271 (ladder) and 0.226 (act two).
This is the "1-2 bets before losing interest" shape the ratings page names.

STILL OPEN AFTER THIS RUN: corvus's ceiling (B1, below), base dryness (Q1), base std
24.77 vs a 35-48 market band, the whole frontend, and the 10M-events question.
[Aug 7: the 10M question is CLOSED — it counts OUTCOMES, we use 10% of the cap. See
"THE 10,000,000 LIMIT IS OUTCOMES" below. B1 and corvus's ceiling are closed too.]

### ▶▶ DECIDED Aug 4 2026: TARGET 3-STAR, HOLD THE MAX WIN AT 25,000x
TARGET RATING IS 3-STAR. Measured on the converged pool, Starwake ALREADY passes every
3-Star non-critical test with ZERO failed classes (and all seven critical tests). So
compliance is not a problem to solve — the retune's only compliance job is to not break
something that already works. Every other decision goes to whether the game is GOOD.
⚠ THE 2-STAR COLUMN IS NOISE FOR US. The absolute-CVaR "failure" recorded above is a
2-Star failure only (limit 20,000, ours 25,000); the 3-Star limit is 50,000. Do not
spend anything fixing it. Do not re-derive draco's cap rate to chase it.
⚠⚠ CORRECTION (same day): THE STAR RATING IS A HUMAN QUALITY REVIEW, NOT A MATH TIER.
This was recorded as an open question and then answered by
stake-engine.com/docs/approval-guidelines/game-quality-rankings. 3-Star is "awarded only
to studio-quality games showing exceptional creativity, uniqueness and attention to
detail", judged on: tested across a range of devices, renders at all screen sizes, no
laggy or low-quality sounds, optimised bundle size, clean animations and cohesive art,
and GAMEPLAY DEPTH (the named failure is "players typically place only 1-2 bets before
losing interest"). The named reasons games are sent back are generic AI-generated assets
("standard fonts, gradients, emoji icons, and border effects are not sufficient"),
mismatched art styles, poor animation, and missing engaging features.
=> THE MATH CANNOT EARN A THIRD STAR. It already passes every 3-Star risk limit with
zero failed classes and that is ALL it can contribute; the rating a reviewer gives then
decides which exposure caps apply. The third star is won on the FRONTEND — art,
animation, sound, performance, bundle size — plus depth of play.
=> 1-Star IS NOT PUBLISHED AT ALL ("the developer will be asked to resubmit"). 2-Star is
the publishing floor; 3-Star is what earns Burst Games / Stake Exclusives / featured
New Releases placement.

⚠ THE PUBLISHING FLOOR JUST ROSE, AND STARWAKE IS SUBJECT TO THE NEW ONE. Per the Stake
Engine team (announced the week of Jul 28 2026): the minimum quality threshold went from
4.5 points to 6 POINTS, "equivalent to a 2-star game before rounding", IN EFFECT
IMMEDIATELY FOR NEW GAMES — only games already in the queue keep 4.5. Stated cause is AI
tooling lowering the barrier and flooding the review queue with low-effort submissions;
the team explicitly wants developers "who invest real time and money into art, design
and gameplay" not to be drowned out. They also said review times are currently well past
their 24-hour goal, and that the 6-point threshold is being personally monitored "over
the coming weeks to see whether 6 points is the right threshold" — SO IT MAY MOVE AGAIN,
and the only insulation is to sit well above the floor rather than on it.
⚠ UNKNOWN: the points rubric itself (what the scale is out of, how points are allocated
across art / depth / performance). Worth asking — it is the actual grading sheet.

=> CONSEQUENCES FOR THE PLAN, and they reorder it:
  1. ART AND ANIMATION ARE NOW CRITICAL PATH, not "eventually". Placeholder and generic
     AI assets are the single most-cited reason for a sub-threshold rating, and hiring
     has the longest lead time of anything left. It does NOT block on the math, so it
     should run in PARALLEL with Act Two rather than after it.
  2. BASE-GAME DRYNESS IS NOW A RATING RISK, not just a feel question. Ordinary base
     spins cap at 21x and carry 62.8% of base RTP, with ~70% of spins paying nothing --
     which is exactly the "1-2 bets before losing interest" shape the reviewers name.
     See BASE VOLATILITY below; the doc parked base-boost until first playtest, and the
     playtest has now happened.
  3. Act Two still counts -- depth is on their list -- but it is no longer sufficient on
     its own, and it cannot substitute for art.

MAX WIN STAYS AT 25,000x. It could have gone to 50,000x (2-Star now permits 50,000 and
3-Star 100,000 — our 25,000 is a leftover from when 25,000 WAS the 2-Star ceiling, and
the design doc still says so). Rejected because of the coupling below.
⚠⚠ ABSOLUTE CVaR *IS* THE MAX WIN whenever a mode's cap lands more often than 1 in
1,000. CVaR is measured over the worst 0.1% of outcomes, so if cap books alone exceed
0.1% the whole window is cap books and CVaR equals the cap exactly. That is why
buy_draco reads 25,000 (cap rate 1 in 642 = 0.156%) and buy_mystery 24,845 (1 in 1,110).
CONSEQUENCE: absolute CVaR is a CAP ON THE CAP — 50,000 at 3-Star. Going to a 50,000x
max win would land absolute CVaR exactly ON the 3-Star limit, so it would ALSO require
pushing every mode's cap rate below ~1 in 1,000, which drains the cap's RTP contribution
and forces buy_draco's value to be rebuilt out of the body. Two coupled re-derivations
for a bigger number on the tin. Not worth it.
HEADROOM AT 3-STAR, tightest first: CVaR absolute 2.0x | ETL40 2.3x | base std 2.5x |
CVaR per-stake 3.0x | max cost 3.6x | ETL sum 3.6x | max payout 4.0x | p10k 5.6x |
p5k 7.6x | ETL10k 9.4x. So at 3-Star the number to watch during the retune is absolute
CVaR, and it only moves if the max win or a cap rate moves. p5k -- the tight one at
2-Star (1.52x) -- has 7.6x here and is not a constraint.

### ▶▶ COMPLIANCE UNDER THE NEW REGIME (Aug 4 2026) — measured, 1 failing class
Stake replaced "any failing statistical test blocks the game" with critical vs
non-critical (stake-engine.com/docs/approval-guidelines/math-verification). Critical
tests block submission; NON-CRITICAL failures instead reduce maximum exposure and
maximum bet cost, and those two caps pick the bet-level template.

ALL SEVEN CRITICAL TESTS PASS with margin (base 1.0x and cheapest; base std 24.16 vs
>=0.6; RTP 96.50-96.65% inside 90-96.7; spread 0.151% vs 0.5%; max payout 25,000x vs
500,000x; max cost 563x vs 2,000x; hit rate 1 in 3.4 vs 1 in 50).

⚠⚠ THE PENALTY IS A STEP FUNCTION AND THE FIRST FAILURE IS FREE. At 2-Star, 0 AND 1
failed classes both keep the full $15M exposure / $100k bet cost. So the question is
never "do we pass everything", it is "are we at 2 or more".
MEASURED ON THE SHIPPED POOL — 2-Star: 1 failed class, 3-Star: 0.
  FAIL  CVaR absolute   25,000  limit 20,000   <- the only failure
        buy_draco's cap rate is 1 in 642 = 0.156%, MORE FREQUENT than the 0.1% tail
        cutoff, so its entire tail is cap books and its absolute CVaR IS the 25,000x
        cap. buy_mystery 24,845 for the same reason. This is new in the Aug 2026
        rollout and it is what stops an expensive buy passing trivially — the
        per-stake CVaR (234 vs 700) divides by cost and hides it.
  Result: $100 bet template = the US/EU maximum. Nothing is lost to this failure.
  One more failure -> $50 template. THAT is the thing to protect.

⚠ THE CLASS CLOSEST TO FLIPPING IS TAIL PROBABILITY: p5k worst 6.57e-03 (buy_mystery)
against a 0.010 limit = 1.52x headroom. Act Two reshapes exactly that tail, so p5k on
buy_mystery is the live constraint on the retune — watch it every sweep.

⚠ TWO ERRORS IN THE OLD NOTES, BOTH CORRECTED IN check_risk_gates.py:
  1. p5k/p10k are NOT scaled by cost multiplier. The docs are explicit — "raw
     probabilities... not scaled by cost multiplier" — so the old get_prob_scale()
     leniency factor (0.2/0.5/0.8 by cost band) was UNDERSTATING every buy mode. The
     recorded "p5k 3.28e-03, headroom 3x" was really 6.57e-03 and 1.52x.
  2. p10k's limit is 0.005, not the 8e-2 recorded here — 16x tighter. We measure
     1.79e-03, so still OK, but the recorded headroom was fiction.
Re-measure any time: `env/bin/python games/starwake/check_risk_gates.py [lut_dir]`
It now prints critical tests, both ratings, the failed-class tally and the resulting
bet template, and takes a directory argument so the Go pool can be checked identically.

### ▶▶ CLOSED Aug 7 2026: THE 10,000,000 LIMIT IS **OUTCOMES**, NOT EVENTS. WE ARE FINE.
ANSWERED BY THE STAKE ENGINE TEAM, not inferred. Happle (RGS), in a thread titled
"10 mil outcomes per mode limit" (Jul 16 2026): "We have a new cap on outcomes per mode,
modes must not exceed 10 million outcomes. If you have existing games on the platform
they will need to be updated." Taylor (RGS) separately: "10m each mode / still has to be
less than 3.14gb per file", alongside "1M on all base atleast / and then like 250k on
bonuses" — a recommendation that is only coherent if the cap counts OUTCOMES.

=> AT 1,000,000 OUTCOMES PER MODE WE USE 10% OF THE CAP. No rebuild, no sim-count change,
   and the pool resolution every measurement in this file depends on is safe.

⚠ THE DOC WORDING IS A TRAP AND IT COST A DAY OF ANALYSIS. The page says "No game mode
can contain more than 10,000,000 events", and the SDK genuinely has a separate `events`
concept (the array inside each book). Measured events per book here: base 10.7 | ante
15.4 | corvus 61.1 | ursa 86.8 | draco 85.4 | mystery 78.0 — so read literally, every
mode was 1.1x-8.7x "over" and the fix looked like an 8x cut to sim counts.
THE TELL, AND IT WAS AVAILABLE THE WHOLE TIME: the same page recommends running
"100,000-1,000,000 simulations". Base alone is 10.7 events/book, so the literal reading
makes the doc's own recommended MAXIMUM breach the doc's own cap — for essentially every
slot ever made. When a spec contradicts itself in adjacent sections, the reading is wrong,
not the spec. "Events file" also refers to books_<mode>.jsonl.zst, whose LINES are books.

⚠ THE CONSTRAINT THAT ACTUALLY BINDS IS FILE SIZE, and it is tighter than the docs say.
Docs: 4.2 GB/file. Taylor: 3.14 GB. Use the stricter one. Current largest files:
  buy_draco 2.7 GB (86% of 3.14) | buy_ursa 2.5 GB (80%) | buy_mystery 2.2 GB (70%)
DRACO IS AT 86% OF THE CAP. Anything that adds events per book — a longer feature, a
richer roam, another per-spin event — pushes it over, and THAT is the real reason to
care about events per book. It is a file-size input, not a compliance limit.

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
- [x] event-ID finder for reviewer scenarios (games/starwake/find_books.py) + the stale
      `bonus` publish purge -- both Jul 30 2026, see "REVIEWER SCENARIOS + PUBLISH PURGE"

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
      So a ceiling is honest ALMOST by construction once set.
      ⚠⚠ THE "OVERSHOOT" WAS A MISREADING -- RETRACTED Jul 30 2026. It was recorded here
      as "base tops out at 25,005x against a published 25,000x", and as a product call
      needing four modes re-simmed. NO BOOK PAYS ABOVE ITS CEILING. state.py:192 sets
      book.payout_multiplier = round(min(running_bet_win, wincap), 2) off the TOTAL, so
      the payout is clamped correctly; state.py:193-194 then clamp basegame and freegame
      SEPARATELY for the book's own split fields, and it is only those two that can sum
      past the cap. Verified over all 999,964 base books: max payoutMultiplier is exactly
      25,000.00, while max(baseGameWins + freeGameWins) is 25,005.00 (id 255217, base 5.00
      + free 25,000.00). The optimized LUT -- the authority on what is actually paid --
      reads 2500000 for that id. Every mode's max equals its published maxWin exactly.
      WHAT IS REAL, and it is much smaller: on capped books the two split fields do not
      reconcile with the payout (up to +5x, ~1,000 books per 1e6 in base). They ship
      inside books_<mode>.jsonl.zst, so a validator that cross-checks base+free against
      payout would flag them. The SDK's own assert at state.py:200 deliberately permits
      it (it compares min(base+free, wincap) to min(total, wincap)). Not worth a re-sim.
      win_manager.py:55-57 has the same separate-clamp-then-sum shape, but it feeds only
      total_cumulative_wins, i.e. the sim's PRINTED RTP summary -- never a book payout.
      The buy modes with NO basegame win on the trigger spin land
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
- [ ] Write those odds into the frontend copy (the LAST publishing item; lives outside
      this repo -- the math SDK owns no lang/copy files)

### ▶▶ ACT TWO -- DESIGNED, NOT BUILT (Aug 3 2026).  PARKED behind the Go port.
STATUS: design decided in conversation, ZERO code written, math unchanged and still the
converged Jul-31 pool. Resume here after the Go SDK port (go/) lands.

THE PROBLEM, MEASURED. Draco ends a feature with 9.9 of 20 cells lit as sticky wilds,
11.2 of 20 once the beast is out -- over half the board, ~70% during the roam. Almost
everything is wild, so every line wins, so no individual win means anything: 15 winning
lines that look like a jackpot and pay 0.5x the ticket. Meanwhile THE LADDER IS BARELY
RUNNING -- mean roam depth is 1.3 rungs of 12 on draco, 3.2 of 13 on ursa. The multiplier
is a rounding error and the wild carpet is the whole mode. That is the "x1 ladder feels
bad" complaint and the "too packed but not paying" complaint; they are one defect.

THE DESIGN. Split the feature into two acts and CONSUME THE STICKY WILDS AT WAKE.
  Act 1 CHARGE  unchanged -- cells light when a winning line crosses, lit = sticky wild,
                snowball builds. Ends at its most crowded, which is fine: that is the
                climax of act one and it is over.
  Act 2 ROAM    the stars pour into the beast and THE BOARD CLEARS. Normal symbols
                return; the 2x2 is the ONLY wild left. Multiplier stars drop each spin,
                the block collects them, its multiplier accumulates, and lines crossing
                it pay symbol wins at a real multiplier.
This replaces constellation_mult_ladders / constellation_ladder_rungs and the two guard
tests. Losing the Jul-30 dead-top-rungs work is acceptable -- it was tuning a mechanism
that climbs 1.3 rungs.
WHY IT IS THE RIGHT FIX: it moves the payout OFF the carpet (the actual ask), it leaves
room on the board for paying symbols, the two acts finally look different, and the
completion ladder 84/63/32 SURVIVES UNTOUCHED because act 1 is unchanged.

RAGE BAIT'S ACTUAL RULES (read off the in-game paytable, not inferred):
  "Fish carry a multiplier value. Whenever a Wild is on the board it collects every Fish
   and adds each Fish's value to that Wild's multiplier -- so any winning line passing
   through the Wild is multiplied that much more. Each collected Fish is then cleared and
   the symbols above cascade down, with new symbols dropping in -- which can land more
   Fish to collect."  Values 2/3/5/10/25/50/100x.
⚠ COLLECTION IS GLOBAL, APPLICATION IS POSITIONAL. The wild does NOT have to land on the
fish. Copy that split: the block collects everything on the board each spin (simple, no
lottery), but the multiplier only applies to lines crossing the block -- so WHERE it roams
still decides which wins get multiplied. That is also our Option A, confirmed by market.
⚠ THEIR CHAIN DOES NOT TRANSFER. collect -> cascade -> new fish -> collect again is the
engine of their feature and WE HAVE NO CASCADES (the base-game meter idea was already
reverted for this reason). Without them it is one beat per spin, not a chain. Do not
design assuming the chain.
⚠ EXPIRE vs PERSIST is moot under global collection -- nothing is ever left uncollected.
An earlier plan had drop -> roam -> collect-what-it-covers, which invents a positional
lottery Rage Bait does not have. Dropped.

THE ONE RISK TO MEASURE FIRST: can act 2 carry the money? The paytable is deliberately
dusty (lows 0.2-0.5, H1 3/6/12), so on a normal board with no wild carpet the raw wins
are small and the multipliers must be big and accumulate fast. If act 2 comes in thin,
draco's price collapses and the whole menu re-derives. MEASURE BEFORE COMMITTING.
SECOND RISK: only 32% of dracos complete, and after this change act 2 is where both the
money and the fun live -- two thirds of a 520x ticket would never reach it. Today the
carpet pays the whole way, so this gate gets much sharper. IF it needs help, the levers
are (a) move draco's gate cells to CENTRE rows -- its gates are currently the full reel-4
column including rows 0 and 3, which few paylines cross -- or (b) a pre-lit floor, machinery
we already have from Draco Ascendant. NOT fewer cells; see below.

### ▶▶ CELL-COUNT SWEEP -- CUTTING THE CONSTELLATION IS REJECTED (Aug 3 2026)
Harness: `games/starwake/reels/sweep_cell_counts.py` (n=20k/tier/variant, wincap slice
stripped, ~5 min for all 12 runs). Tested cutting draco 11 -> 6/8/9 and ursa 7 -> 5/6.

  variant         tier   cells  e/g  complete   lit  wild/20  roam    cost      max  beat tkt
  current 4/7/11  corvus     4  4/0     83.7%   3.5      6.9   4.1    239x  10,000x    25.1%
                  ursa       7  5/2     63.2%   6.4      9.0   3.2    269x  25,000x    20.4%
                  draco     11  6/5     32.1%   9.9     11.2   1.3    523x  25,000x    18.9%
  A  4/5/6        ursa       5  3/2     10.2%   3.4      3.8   0.4     55x   7,752x    24.6%
                  draco      6  3/3     40.0%   4.8      6.4   1.6    221x  25,000x    16.2%
  B  4/6/8        ursa       6  4/2     34.8%   5.0      6.4   1.6    136x  22,808x    18.6%
                  draco      8  4/4     15.9%   6.1      6.8   0.5    103x  11,675x    22.6%
  C  4/6/9        ursa       6  4/2     34.8%   5.0      6.4   1.6    136x  22,808x    18.6%
                  draco      9  5/4     40.3%   7.9      9.5   1.5    308x  25,000x    21.6%

⚠⚠ CELLS ARE FUEL, NOT DIFFICULTY. This is the headline and it is the opposite of the
assumption the cut was proposed on. A lit cell becomes a sticky wild, and the EASY cells
(reels 0-2) are the engine that manufactures the long wins needed to reach the HARD cells
(reels 3-4). Remove easy cells and you do not remove work, you remove the engine.
TWO CLEAN CONTROLS, both accidental, both ~2.5x off ONE cell:
  ursa 6-cell (34.8%) vs current 7-cell (63.2%) -- identical but for one easy cell (2,0)
  draco B 8-cell (15.9%) vs draco C 9-cell (40.3%) -- IDENTICAL GATES, one easy cell (1,2)
SECOND EFFECT: once fuel is short, gate ROW beats gate COUNT. Variant A's draco has THREE
gates and completes 40%; variant A's ursa has TWO and completes 10.2% -- because A-draco's
gates sit in rows 1-2 (centre, high payline traffic) and A-ursa's (3,0) is an edge row.
EVERY CUT VARIANT BREAKS THE TIER LADDER: A inverts it (draco 40.0% EASIER than ursa
10.2% at a quarter of the price), B inverts price (draco 103x < ursa 136x), C still
inverts completion (draco 40.3% > ursa 34.8%).
AND SATURATION IS THE PAYOUT: draco's wild/20 falls 11.2 -> 9.5 -> 6.4 and its price falls
523 -> 308 -> 221 -> 103x in lockstep. "Less packed AND pays more" is NOT reachable by
cutting cells -- it needs a payout source that is not the carpet, i.e. Act Two.
=> KEEP 4 / 7 / 11. The clutter motive is answered by consuming wilds at wake; the cost
(a broken tier ladder) would remain. Change ONE thing at a time: build act 2 against the
current shapes, measure, and only then revisit completion.

⚠ POOL DAMAGE FROM THIS SWEEP, NOT YET REPAIRED. Books, publish LUTs, lookup_tables and
segmented LUTs for buy_corvus/buy_ursa/buy_draco were backed up and RESTORED correctly.
NOT backed up, and therefore now 20k-sweep vintage: library/forces/force_record_buy_*.json,
library/configs/books_buy_*.verification.json and event_config_buy_*.json for those three
modes. The gotcha below DOES name force records and verification files -- the backup was
incomplete, not the documentation. Math and books are intact; this only breaks the reviewer
force artifacts and config.json's sha256 for them. Fixed by the re-sim that any retune
needs anyway -- do NOT ship the current library/ without re-running those three modes.

### ▶▶ REVIEWER SCENARIOS + PUBLISH PURGE (Jul 30 2026)
TWO SHIPPED. Neither touches the math: the pool, the LUTs and every RTP are byte-identical
(library/ is gitignored, so the purge is a publish-artifact fix, not a code change).

1. STALE `bonus` PURGED FROM THE PUBLISHED SET. The Jul 20-22 scaffold left seven
   `*bonus*` files in library/, and one of them leaked into a REVIEWER-FACING artifact:
   force.json advertised SEVEN modes while index.json/config.json had six.
   ROOT CAUSE, worth not re-deriving: force.json is APPEND-ONLY. write_data.py:219-227
   reads the existing file, sets `data[<current mode>]`, writes it back -- it never drops
   a mode. So a stale entry survives every future run, and deleting only the force record
   does NOT clear it; force.json itself must go too. Both were deleted and force.json was
   rebuilt from the six surviving records, then generate_configs refreshed the hashes.
   VERIFIED: force.json / index.json / config.json now name the same six modes, and every
   sha256 in config.json matches its file on disk (books, LUTs, force records, fe config).
   ⚠ `make_force_json` (write_data.py:31) LOOKS like the rebuild helper and is NOT -- it
   is dead code, called from nowhere, and doubly broken: it reads gamestate.config.
   force_path (force_path lives on OutputFiles, not GameConfig) and treats item["search"]
   as a dict when the record stores a list of {"name","value"} pairs. Do not reach for it.
   ⚠ config_fe_<game>.json IS NOT BYTE-REPRODUCIBLE: symbols come out of an unordered
   collection, so every generate_configs call reshuffles them and changes the published
   frontendConfig sha256 with ZERO math change. Confirmed semantically identical here
   (same 11 symbols, same paytables, everything else equal). Do not read a changed fe
   hash as a math change.

2. EVENT-ID FINDER -- `games/starwake/find_books.py`. Turns a scenario description into
   book ids. `--scenarios [mode]` emits the curated reviewer pack; ad-hoc queries combine
   --criteria / --min-payout / --key / --tier / --woke / --no-woke / --top-rung /
   --min-roam / --prelit. Full pack for all six modes: `find_books.py --scenarios --json
   reviewer_scenarios.json` (~5 min, 68 of 72 scenarios resolved; output committed as
   games/starwake/reviewer_scenarios.json).
   WHY NOT utils/search_tool/forcetool_ids.py alone -- it covers force-record key matching
   but (a) the force record only indexes LINE-WIN keys, so our constellation events are
   invisible to it, (b) its find_payout_range_ids MIN branch filters `line_val <
   min_payout`, returning payouts BELOW the minimum -- an SDK bug, left unfixed and worked
   around, (c) it defaults to the UNWEIGHTED pre-optimizer LUT, and (d) it json.loads a
   603 MB force record. find_books.py streams records entry-by-entry and rejects
   non-candidate book lines on a regex over the id prefix before parsing.
   ⚠ TWO DIFFERENT QUESTIONS, do not conflate: "the beast REACHED rung N" is an EVENT
   question (beastRoam carries the multiplier every spin); "a win was PAID at rung N" is
   `--key mult=N` against the force record, which only logs a mult on a WINNING line. Ursa
   reaches 500x outside the wincap fence but only ever PAYS at 500x inside it.

3. FINDING -- TOP LADDER RUNGS ARE NOT REACHED IN EVERY MODE THAT LISTS THEM. Measured
   across all six modes on the shipped pool:
     corvus 200x  reached NATURALLY (criteria=corvus, roam 9/9) in every mode with corvus
     ursa   500x  reached ONLY in buy_ursa, and only via the forced wincap slice --
                  NEVER in base, ante_starfall or buy_mystery
     draco  600x  reached in every mode with draco, but ONLY via the wincap slice
     ascend 600x  NEVER REACHED ANYWHERE. Ascendant's deepest roam is 13 of 14 (rung 315
                  fires, 600 does not), because it inherits draco's 14-rung ladder but has
                  no forced-wincap slice of its own to manufacture a spin-1 completion.
   MATTERS because compliance requires listing all obtainable multiplier values, and
   ascendant's ladder currently advertises a rung the mode cannot deliver. Not proven
   impossible -- only unobserved at 1e6 -- but ascendant is dealt 2 of 11 cells pre-lit,
   so a spin-1 completion needs one spin to trace the other 9. Either verify it is truly
   unreachable and trim/annotate ascendant's published ladder, or accept it as <1e-6.
   Corvus is the only tier whose ceiling is a normal outcome rather than a forced one.

### ▶▶ THE DEAD TOP RUNGS -- FOUND, FIXED, RE-CONVERGED (Jul 30 2026)
⚠ THIS SUPERSEDES EVERY LADDER AND PRICE NUMBER BELOW. Ladders are now
corvus 9 / ursa 13 / draco 12 rungs, and buy_mystery costs 563x.

THE BUG. Rung count was set to num_feature_spins[tier]-1 -- the THEORETICALLY longest
roam. That is not the achievable one: the top rung needs a completion on SPIN 1, i.e.
the whole constellation lit in a single spin. 4 cells manage it; 7 and 11 do not. So
the ladders advertised multipliers that could not be won. Measured organically on the
old 1e6 pool (forced wincap books excluded -- a forced cap book manufactures the
spin-1 completion and makes a dead rung look alive):
    corvus 200x  organic 1 in 466            HEALTHY
    ursa   500x  organic 1 in 3,978,063 in buy_ursa; NEVER in base/ante/mystery
    draco  600x  FORCED CAP BOOKS ONLY, never organic in any mode
    ascend 600x  NEVER REACHED ANYWHERE (no cap slice of its own to borrow from)
Both guard tests were green throughout: one asserted len(ladder) >= longest_roam
(catches only too-SHORT) and the other equality against the same wrong number.
game_config's own comment already NAMED the failure mode -- "too long advertises rungs
no player can ever be paid" -- and the invariant simply did not encode it.

THE FIX. Re-sweep each ladder to the depth its tier actually reaches, holding the top
VALUE and the shipped price. Rung count is now config.constellation_ladder_rungs, a
MEASURED number, and both tests assert equality against it.
    corvus  9 rungs 1:200:2.5  [1,1,1,2,3,5,13,44,200]              unchanged
    ursa   13 rungs 1:500:2.4  [1,1,1,1,2,2,3,5,10,23,55,155,500]
    draco  12 rungs 2:600:2.0  [2,2,2,3,4,6,11,20,41,91,223,600]    ascendant shares it
Draco took 12 not 13 because ascendant shares the list: at 13 ascendant's top read
1 in 29,658 but draco's 1 in 2.5M. 12 serves both.
⚠ THE LADDER IS PAYOUT-ONLY AND CANNOT MOVE COMPLETION -- 63.2% ursa / 32.1% draco
reproduced EXACTLY across every swept variant. That is what made this predictable:
the roam-depth distribution is invariant, so shortening the ladder only re-labels
which rung sits at which depth.

RESULT AT 1e6 x 6 MODES -- EVERY TOP RUNG NOW ORGANIC IN EVERY MODE:
  tier / mode      buy mode        mystery        base          ante
  corvus 200x      1 in 366        1 in 442       1 in 12,414   1 in 14,255
  ursa   500x      1 in 30,121     1 in 31,957    1 in 239,648  1 in 108,143
  draco  600x      1 in 60,166     --             1 in 661,846  1 in 1,042,004
  ascend 600x      --              1 in 1,846     --            --
Ascendant went from NEVER to 1 in 1,846, and those books average 24,983x -- it can
reach 25,000x for the first time. reviewer_scenarios.json now resolves 72/72 (was
68/72), and the finder runs in 30s instead of 4m47s because the rungs are findable.

  mode           cost  maxWin     RTP   std  zero%   hit%  >=1x  ETL40x  >100x  cap rate
  base            1.0  25,000  0.9665 24.16  70.75  29.25 11.58   0.322  0.271  1 in 1.25M
  ante_starfall   1.5  25,000  0.9665 21.93  65.67  34.33  8.97   0.385  0.245  1 in 671k
  buy_corvus      240  10,000  0.9665  1.53   0.00 100.00 28.28   0.000  0.000  1 in 11.7M
  buy_ursa        268  25,000  0.9663  2.16   0.00 100.00 25.25   0.024  0.000  1 in 4,340
  buy_draco       520  25,000  0.9655  2.07   0.00 100.00 26.25   0.053  0.000  1 in 963
  buy_mystery     563  25,000  0.9665  1.81   0.00 100.00 23.88   0.023  0.000  1 in 2,231
BAND SPREAD 0.1011% (limit 0.5%), all <= the 0.9670 ceiling, every published maxWin
exactly equal to that mode's true maximum, zero-pay 0.00% on all four buys.
WIN-RANGE HOLES TIGHTENED: base 1.27 -> 1.11x, ante 1.40 -> 1.07x, ursa 1.13 -> 1.02x,
draco 1.03 -> 1.00x. Shorter ladders fill the upper range more densely.

TWO THINGS THAT CAME FREE:
1. THE FORCED WINCAP SLICES GOT MUCH CHEAPER. Draco's NATURAL at-cap rate went 0.004%
   -> 0.065% (1 in 1,818) because 600x now sits at roam 12 instead of 14. buy_ursa's
   sim -- flagged here as "the single most likely thing to hang the next run" and
   costing 24:47 last time -- came in at 13:52. Whole sim phase 74 -> 53 min.
2. base >=1x rose 9.71 -> 11.58% and >100x share 0.252 -> 0.271, untouched by design.

BUY_MYSTERY RE-PRICED 526 -> 563x, and it is a CONSEQUENCE, not a choice. Ascendant
shares draco's ladder, and a shorter ladder rewards exactly what ascendant does best
(complete early, ride the top), so its mean went 2,249 -> 2,598x with no change to its
cells, pre-lit set or mix. Its only independent lever is the pre-lit cell set, and the
neighbouring sets bracket the target badly (~956x vs ~2,249x), so 526 was not
reachable. Holding it would have cost either the "ascendant IS a draco" shared-ladder
invariant or the "1 in 10 rolls wakes something you cannot buy" story. Took the price:
the menu stays ordered (240/268/520/563), stays under the 1,000x buy cap, and
ascendant's payback share moved 43.4% -> 47.2%, TOWARD the Rage Bait shape this mode
is modelled on (10% of rolls / 52% of payback). Delivered mix 35.161/29.635/25.115/
10.055 + 0.034 wincap = 100.000%; tier means 226.1/253.9/493.6/2,554.5x, correctly
ordered.
⚠ THE RISK THAT DID NOT LAND. Ascendant now caps ORGANICALLY on ~1.5% of its features,
which implied a mystery cap rate near 1 in 670 -- more often than buy_draco's 1 in 963,
inverting "draco is the cap play". The wincap slice was deliberately HELD at 0.0199
rather than re-derived to the 0.074 the new rates imply, on the theory that the
optimizer could weight the organic cap books down. IT COULD: measured cap-value-per-
stake is base 0.0200 / ante 0.0250 / ursa 0.0215 / DRACO 0.0499 / mystery 0.0199.
Draco keeps the cap crown by 2.3x. Do not re-derive that slice from natural rates.

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

### ▶▶ CAP-SHARE LADDER + CORVUS MAX-WIN + CVaR CLOSED (Jul 31 2026)
Optimizer-only pass on FOUR modes (no re-sim, ~20 min). Three things landed.

1. CVaR IS RESOLVED AND WAS NEVER CLOSE. The percentile convention -- the one gate
   this file said "rests on an assumption" -- is 0.1%, confirmed from the RGS team's
   own platform code and from utils/analysis/distribution_functions.py: cutoff 0.999,
   accumulate from the smallest payout up, then take the conditional mean of the tail.
   So the 0.01% (673) and 0.001% (3,071) readings were never the ones being checked.
   MEASURED: base 233.8 against the 700 limit = 3.0x headroom. Every mode passes.
   ⚠ The frontend divides CVaR by bet cost before checking, which makes buy modes
   pass trivially -- ETL and the tail-probability checks are what constrain buys.
2. buy_corvus's PUBLISHED MAX WIN WAS NOT LEGALLY OBTAINABLE. 10,000x sat at
   P = 8.52e-08 = 1 in 11.7M against the docs' "typically more frequent than 1 in
   10,000,000". Not on any prior deficiency list, and it is a HARD gate (the RGS team
   confirmed submission is BLOCKED while any analysis check is out of range; that
   becomes a penalty rather than a block in a coming update). Fixed with a scaling
   boost on the 9,000-10,000x band -- corvus has no wincap Distribution, so its
   ceiling is organic and there is no slice to turn. NOW 1.50e-07 = 1 in 6.66M. PASSES.
   Cost in RTP: 0.00036% of the mode. ⚠ Only 16 at-cap corvus books exist (vs
   thousands in the forced-slice modes), so re-measure this after ANY corvus re-run.
3. THE CAP-SHARE LADDER WAS INVERTED and is now fixed. slice_rtp IS
   cap-value-per-stake, so it ranks "best max-win bet per dollar" -- and ante (0.025)
   was beating buy_ursa (0.0215) and buy_mystery (0.0199). Backwards from every
   audited game (Rage Bait: base 0.045, super 0.056, mystery 0.064 -- buys highest).
   DELIVERED, exactly on target: corvus 0.0000 / base 0.0200 / ante 0.0250 /
   ursa 0.0300 / mystery 0.0400 / draco 0.0749. Draco rose WITH the others so its
   crown strengthened: draco/ursa 2.33x -> 2.50x, still far past the 1.94x price-ratio
   break-even. Cap rates now ursa 1 in 3,110 / mystery 1 in 1,110 / draco 1 in 642.

WHAT IT COST, measured before/after off the LUTs (backup in library/lut_backup_precapshare):
  >=1x cost   corvus 28.28->28.57  ursa 25.25->23.59  draco 26.25->24.05  myst 23.88->21.30
  >=10x cost  corvus 0.095->0.085  ursa 0.203->0.518  draco 0.180->0.245  myst 0.189->0.445
  median/cost corvus 0.239->0.318  ursa 0.226->0.118  draco 0.322->0.329  myst 0.381->0.388
  std         corvus 1.53->1.46    ursa 2.16->2.49    draco 2.07->2.31    myst 1.81->2.13
THE TRADE IS THE ONE WE WANTED: ~2pp fewer break-even returns for 2.4-2.6x more
>=10x outcomes on ursa/mystery, and buy std moved toward the market's 2.6-4.0 band.
All four buys still bust 0.00%, every >=1x rate still at or above the market's 13-28%.
⚠ URSA OVERSHOT AT 0.030 AND WAS RE-TUNED TO 0.026 (same day, two extra optimizer
passes). At 0.030 the optimizer funded the bigger cap slice by packing the consolation
band down: buys returning <=0.25x cost went 53.4% -> 67.7% and the median halved
0.226 -> 0.118x, making URSA THE HARSHEST BUY IN THE GAME and inverting its "coin
flip" identity. Two things fixed it, and the SECOND one is the lesson:
  v1  0.026 + scaling on 134-536x (0.5-2x cost)  -> >=1x recovered to 26.8% but
      <=0.25x only fell to 62.8% and the median got WORSE (0.099x). Lifting the
      1-2x band pulled mass out of 0.25-0.5x rather than out of the bottom.
  v2  + scaling on 67-134x (0.25-0.5x cost)      -> the actual fix. That shoulder
      band had collapsed 16.4% -> 5.3%, and rebuilding it to 26.0% is what drained
      the bottom.
FINAL vs the ORIGINAL 0.0215 state -- v2 is better on EVERY metric except >=1x:
  <=0.25x 53.4 -> 47.4%   0.25-0.5x 16.4 -> 26.0%   median 0.226 -> 0.269x
  >=5x 3.51 -> 4.36%      >=10x 0.203 -> 0.500%     std 2.16 -> 2.36
  >=1x 25.3 -> 22.3%  (the one regression; still mid-market, Rage Bait mystery 23.4%)
⚠ TO MOVE A DISTRIBUTION'S BOTTOM, SCALE THE BAND JUST ABOVE IT, NOT THE MIDDLE.
Boosting 1-2x pulled from 0.25-0.5x; boosting 0.25-0.5x pulled from <=0.25x. The
optimizer takes weight from the NEAREST band, so aim one step above the problem.
NOT A BUG -- ursa (47.4%) still has a harsher floor than draco (38.6%) and mystery
(33.2%). That is STRUCTURAL: draco lights 11 cells to ursa's 7, so its partial-progress
carpet is worth more even though it completes far less often. Fewer cells = weaker floor.
WIN-RANGE HOLES DID NOT MOVE: 1.00-1.02x on all four, and every surviving hole sits
above 9,000x (tail sparsity, not structure). The worry that draco's body would hollow
out did not materialise.
RISK GATES AFTER: worst p5k 3.28e-03 vs 1e-02 (headroom 9x -> 3x, the one number this
spent), p10k 8.97e-04 vs 8e-02, ETL40 0.385 vs 0.8, ETL10k 0.085 vs 0.6, CVaR 233.8
vs 700. RTP band 0.9650-0.9665 = 0.15% spread (limit 0.5%).
RE-MEASURE ANY TIME WITH: `env/bin/python games/starwake/check_risk_gates.py` (new;
mirrors the platform's own checks including the cost-scaling on p5k/p10k).

ALSO DONE Jul 31:
- UPSTREAM MERGED (dfb9f39). origin/main had the CVaR-normalisation and prob-scaling
  fixes; the upstream-only diff was ONE file (utils/analysis/distribution_functions.py,
  +13/-1) touching nothing we modified. Zero conflicts.
- SCAFFOLD PLACEHOLDERS FIXED. game_config never set provider_name/game_name, so both
  silently inherited src/config/config.py's "sample_provider"/"sample_lines" all the
  way into the published config_fe_starwake.json. Now **Uptown Games** / **Starwake**.
  ⚠ Regenerating configs is a SEPARATE step from optimizing -- the optimizer process
  holds the config it loaded at start, so a name change made mid-run does not reach
  the published file until generate_configs runs again.

### ▶▶ NEXT SESSION STARTS HERE (as of Jul 30 2026)
⚠ SUPERSEDED AS THE ENTRY POINT (Aug 3 2026). Current order of work is:
  1. the Go port of the SDK (go/) -- IN PROGRESS, everything below is parked behind it
  2. then "ACT TWO -- DESIGNED, NOT BUILT" near the top of this file
  3. then the publishing items in this section, which are still valid and still pending
The math below is converged and correct; it is just no longer the next thing to touch.

The math is converged and shippable. ONE publishing item remains, plus product calls.
 0. ⚠ THE TABLE BELOW AND IN "THE DEAD TOP RUNGS" PREDATE the Jul 31 cap-share pass --
    ursa/draco/mystery std, ETL and cap rates all moved. See the Jul 31 section above.
 1. WRITE MYSTERY'S ODDS INTO THE FRONTEND: corvus 35.16 / ursa 29.64 / draco 25.15 /
    ascendant 10.05%. Draco's number INCLUDES the 0.04% cap slice (it forces 5
    scatters, so those are Draco rolls). Display rounding is fine; the gate is that the
    displayed mix is the delivered mix. ⚠ USE THE POST-LADDER-FIX FIGURES, measured on
    the Jul 30 RE-CONVERGED pool: corvus 35.161 / ursa 29.635 / draco 25.115 + 0.034
    wincap / ascendant 10.055, summing to 100.000%. The mode also costs 563x now, not
    526x -- see "THE DEAD TOP RUNGS" for why the price moved.
 2. ✅ DONE Jul 30 -- event-ID finder + the stale `bonus` purge. See "REVIEWER SCENARIOS
    + PUBLISH PURGE" near the top.
 3. ✅ RETRACTED Jul 30 -- there is NO maxWin overshoot. Books are clamped correctly at
    state.py:192; only the basegame/freegame SPLIT FIELDS can sum past the cap. No
    re-sim needed. Full retraction in PER-MODE DISPLAYED CEILINGS.
 3b. ✅ DONE Jul 30 -- the dead top rungs are fixed and re-converged at 1e6 x 6 modes.
    Every tier's top rung is now reached ORGANICALLY in every mode it appears in.
    See "THE DEAD TOP RUNGS" near the top for the ladders, the table and the two
    things that came free.
 3c. ⚠ CARRY-OVER: buy_mystery is now 563x, so the frontend price and any copy quoting
    526x must follow. Mystery's delivered mix barely moved (35.161/29.635/25.115/
    10.055) but re-read it off the new pool before publishing rather than reusing the
    Jul 29 figures.
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

### BUY_MYSTERY -- historical diagnosis (✅ ALL RESOLVED; kept for the reasoning)
⚠ READ AS HISTORY, NOT STATE. Every number below is pre-rebuild. Current state is in
"FULL 1e6 RE-CONVERGE" and "THE hr BUG". Status of each item:
  #1 the inverted tier ladder -- ✅ CLOSED. Per-tier kind fences landed Jul 28, and the
     hr fix on Jul 29 made the mix itself correct. Draco now averages 490x against
     corvus's 226x, i.e. the ladder points the right way for the first time.
  #3 mix table / #4 "Rage Bait's shape is not available" -- SUPERSEDED by DRACO
     ASCENDANT: a fourth, non-purchasable outcome is exactly what makes that shape
     available, and it now measures 43.4% of payback on 10.05% of rolls at 1e6.
  #5 (no 2-scatter dud) and #6 (publish true odds, do not overlap ursa's price) STAND.
     #6 is satisfied: mystery costs 526x against ursa's 268x, and the true odds are
     recorded in the MYSTERY ODDS MEASURED item near the top.
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
  proxy. CVaR <= 700 normalized, the other tail gate, was MEASURED Jul 30 2026 off the
  optimized LUTs (mean payout given you are in the top q, ticket-normalized):
              CVaR 1%   CVaR 0.1%   CVaR 0.01%   CVaR 0.001%
    base         45.5       228.9        673.1       3,070.9
    ante         46.1       197.2        532.2       3,356.0
    all buys    <12.3       <48.1        <93.3         <93.3
  THE VERDICT DEPENDS ON THE PERCENTILE CONVENTION, which we do not have in writing: at
  the 0.01% tail base reads 673.1 and PASSES with only 4% headroom; at 0.001% it is
  3,071 and fails. Every buy passes at every percentile by a wide margin. CONFIRM WHICH
  q STAKE MEANS before treating this gate as cleared -- it is the one compliance number
  still resting on an assumption, and base is the mode sitting near the line.
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
