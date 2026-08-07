# Starwake — competitor comparison sheet

Our measured numbers, and the protocol for producing the same numbers from another
game so the comparison is like-for-like. Design history and reasoning live in
`CLAUDE.md`; this file is only "what to compare and what we read".

Pool measured: `games/starwake_go/library/publish_files`, 1e6 outcomes/mode, Aug 7 2026.
Re-measure this whole sheet after any pool rebuild — every number below is pool-specific.

---

## How to reproduce these on another game

1. Get the competitor's `publish_files` (index.json + lookUpTable CSVs + books).
2. Point Mnemoo Tools at it (launcher: set `libraryPath`, restart).
3. Read the LUT-derived rows off Overview / Distribution / Mode Comparison.
4. Run **CrowdSim with the exact config below** — the session numbers are meaningless
   across different configs.

⚠ EVERY LUT-DERIVED NUMBER MUST COME FROM THE **OPTIMIZED** TABLE
(`lookUpTable_<mode>_0.csv`), never the raw book pool. The pool is quota-shaped by
construction and a bust rate read off it is meaningless.

⚠ CROWDSIM CONFIG — hold these fixed or nothing is comparable:
    players 2,000 | spins/session 300 | initial balance 100 | bet 1
    big-win threshold 10x | danger threshold 10% | crypto RNG off

---

## 1. Base game — the numbers that decide "does this feel good to play"

  metric                          STARWAKE      market note / source
  RTP                              96.65%       Stake cap is 96.70%
  hit rate (any win)               29.25%       = 1 in 3.42
  zero rate                        70.75%       design doc band 70-83% "OK"
  win frequency >= 1x               8.0%        design doc "~7.4% market norm"
  base std dev                      25.36       design doc expects 35-48; WE ARE UNDER
  RTP above 100x                    31.3%       design doc "40-60% approvable"; UNDER
  median payout                     0.00x
  mean payout                       0.97x
  ordinary-spin ceiling              180x       (i.e. excluding the wincap slice)
  max win                         25,000x       at 1 in 1,250,001

⚠ THE TWO "UNDER" ROWS ARE THE SAME FINDING SEEN TWICE. base std dev 25.36 against a
35-48 expectation, and 31.3% of RTP above 100x against a 40-60% band, both say the same
thing: OUR BASE IS FLATTER AND LESS TOP-HEAVY THAN THE GAMES THE DOC BENCHMARKED.
This is the single most important thing to check against real competitors — those
benchmark bands are second-hand and may simply be stale. If three comparable payline
games come in at 25-30 std dev, the band is wrong and we are fine. If they come in at
40+, we have a real gap and it is a design decision, not a bug.

## 2. Session experience — CrowdSim, base, 2,000 x 300 (see config above)

  metric                          STARWAKE      reading
  probability of profit             36.3%       726 / 2000
  players hitting a 10x+            99.0%       essentially everyone
  average spins to a 10x               63
  never hit a 10x                    1.1%
  median final balance                 49       of a 100 bankroll
  mean final balance               82.94
  busted                            35.5%       sim allows negative balances
  median max drawdown              102.4%
  players below 10% of bankroll     56.9%       averaging 54.5 such moments each
  P5 / P50 / P95 final balance   -97 / 49 / 362

⚠ THE HEADLINE READ: this is NOT "nothing ever happens" — 99% of players see a 10x, one
every ~63 spins. It IS "things happen and you still grind down": median player ends at
half their bankroll. Those are DIFFERENT PROBLEMS. The first would be a math defect; the
second is normal high-volatility behaviour, managed by pacing/anticipation/presentation.
Do not accept a competitor comparison that conflates them.

⚠ CROWDSIM'S "ACTUAL RTP" WILL LOOK WRONG AND IS NOT. It read 94.31% against a
theoretical 96.65%. Base's per-spin std dev is 25.36, so over 600,000 spins the standard
error on the mean is 25.36/sqrt(600,000) = +/-3.27pp. A 2.33pp deviation is 0.7 sigma.
=> YOU CANNOT MEASURE THIS GAME'S RTP TO BETTER THAN ~3 POINTS IN 600k SPINS, and no
player will ever experience anything near the advertised figure. Expect the same on any
comparably volatile competitor; if a competitor's sim RTP converges tightly, THAT is the
signal — it means their variance is far lower than ours.

⚠ CROWDSIM'S "STREAK" MEANS **payout < cost**, NOT "paid nothing". CONFIRMED by running
base and ante and comparing. Ante has MORE hits than base (34.33% vs 29.25%) but LONGER
losing streaks (avg 87.8 vs 61.4, max 244 vs 192) -- impossible under the dead-spin
reading, immediate under the net-loss one, because ante's BREAK-EVEN rate is 3.2% against
base's 8.0%. Predicted longest run ln(300*p_win)/ln(1/p_loss) is 38.8 (base) vs 69.5
(ante), a 1.79x ratio against 1.43x observed. Right direction, right magnitude.
=> When comparing to a competitor, ALWAYS pair a streak number with that mode's
   break-even rate. A game with a cheaper effective ticket will look "streakier" purely
   because its bar is lower, with no difference in how often symbols land.

## 2b. Session experience — CrowdSim, ANTE_STARFALL, same config

  metric                       BASE      ANTE       intent
  zero rate                   70.75%    65.67%      smoother -- MET
  hit rate                    29.25%    34.33%      more hits -- MET
  cost-adjusted volatility     26.24     22.76      lower vol -- MET
  busted                       35.5%     32.0%      MET
  avg max drawdown            103.8%     99.1%      MET
  players below 10%            56.9%     53.6%      MET
  probability of profit         36.3%     35.5%      ~same
  median final balance          49.07     49.90      ~same
  avg / max losing streak    61.4/192  87.8/244     WORSE
  avg / max winning streak      1.6/5     1.3/3     WORSE
  players hitting a 10x+        99.0%     99.3%
  avg spins to a 10x               63        61
  actual RTP (sim)             94.31%    91.97%     0.71 and 1.59 sigma; both normal

⚠⚠ ANTE IS STATISTICALLY SMOOTHER AND EXPERIENTIALLY STREAKIER AT THE SAME TIME, and this
is the most interesting thing CrowdSim has surfaced. Variance per unit staked genuinely
falls (22.76 vs 26.24 -- the MIKO-style ante works). But the break-even bar rises to 1.5x
while wins do not scale with it, so NET-WINNING SPINS GET RARER: 3.2% vs base's 8.0%.
Players see more symbols land AND longer runs of not getting ahead. No per-spin statistic
shows this; it only appears in session data. Relevant to how ante is presented, and worth
checking on any competitor ante/bonus-buy-lite mode.

## 2c. Session experience — ALL SIX MODES, identical config

  metric                     BASE      ANTE    CORVUS      URSA     DRACO   MYSTERY
  probability of profit     36.3%     35.5%     38.3%     30.3%     34.7%     35.9%
  sim RTP                  94.31%    91.97%    96.61%    96.83%    95.88%    96.59%
  deviation (sigma)          0.71      1.59      0.11      0.75      1.89      0.22
  cost-adjusted volatility  26.24     22.76      2.09      2.16      2.54      2.11
  busted                    35.5%     32.0%      0.5%      0.1%      0.7%      0.1%
  danger zone affected      56.9%     53.6%      1.3%      0.1%      2.0%      0.5%
  median final balance      49.07     49.90     87.98     84.49     82.93     85.29
  mean final balance        82.94     75.92     89.82     90.48     87.63     89.78
  avg max drawdown         103.8%     99.1%     32.8%     29.3%     38.1%     31.6%
  P5 / P95              -97/362   -92/310    33/150    43/169    24/166    36/154
  break-even rate            8.0%      3.2%     17.2%     32.4%     21.7%     22.1%
  avg / max lose streak  61.4/192  87.8/244   23.5/60   12.5/29   19.1/46   18.5/39
  avg / max win streak      1.6/5     1.3/3     3.0/7    4.7/11     3.5/8     3.5/8
  big-win hit rate          99.0%     99.3%     97.0%     74.3%     74.0%     60.9%
  avg spins to a big win       63        61        78       113       122       128
  never hit a big win        1.0%      0.7%      3.0%     25.6%     26.1%     39.1%

⚠ "BIG WIN 10x" IS RELATIVE TO COST, so these are different events per mode: base 10x
absolute, corvus 1,200x, ursa 2,680x, draco 5,200x, mystery 5,630x. The buy columns are
NOT comparable to the base ones and barely to each other -- mystery's "worst" hit rate is
against the highest bar in the game. What IS readable, and is a real product fact:
39.1% OF MYSTERY PLAYERS AND ~26% OF URSA/DRACO PLAYERS NEVER SEE 10x THEIR TICKET in 300
buys, against 3% on corvus.

⚠⚠ THE STREAK-vs-BREAK-EVEN RELATIONSHIP IS CONFIRMED ACROSS ALL SIX MODES AND IS
PERFECTLY MONOTONIC. This settles what CrowdSim's "streak" counts: SPINS THAT DID NOT PUT
YOU AHEAD, not spins that paid nothing.
    B/E   3.2%   8.0%  17.2%  21.7%  22.1%  32.4%
    lose  87.8   61.4   23.5   19.1   18.5   12.5  (ante, base, corvus, draco, mystery, ursa)
Predicted longest run ln(300*p_win)/ln(1/p_loss) fits the buys almost exactly (ursa 11.7
predicted vs 12.5 observed, mystery 16.8 vs 18.5, draco 17.1 vs 19.1, corvus 20.9 vs 23.5)
and runs ~1.3-1.6x loose on base/ante, whose large zero mass changes the shape.
=> NEVER COMPARE A STREAK NUMBER WITHOUT THE BREAK-EVEN RATE BESIDE IT.

⚠⚠ URSA HAS THE LOWEST PROBABILITY OF PROFIT OF ANY MODE (30.3%) DESPITE HAVING THE
HIGHEST BREAK-EVEN RATE (32.4%). That is not a contradiction, it is the SIGNATURE OF THE
Aug 6 RESHAPE. Ursa now clusters hard just below break-even: 27.6% of players end in
50-75 and 32.6% in 75-100, so 60.2% FINISH BETWEEN HALF AND ALL OF THEIR BANKROLL. It has
the shortest losing streaks, the longest winning streaks (avg 4.7, max 11), the lowest
bust rate (0.1%) and the smallest drawdown (29.3%) -- and the fewest players who actually
end ahead. The trade was "rare and big" for "often and nearly", and over a long session
"nearly" resolves as a small reliable loss.
=> THIS IS THE COST OF THE 48.2% COMPLETION CHANGE and it was not visible in any per-spin
   statistic. Whether it is the right trade is a design call, not a defect: ursa is now
   the smoothest, safest, least-frustrating buy AND the least likely to send anyone home
   up. Check what competitors' mid-tier buys do here before deciding.

⚠ SIM RTP TRACKED VOLATILITY EXACTLY AS PREDICTED, across a 12x range of it: standard
error is (cost-adj std dev)/sqrt(600,000), giving +/-3.27pp on base and +/-0.27pp on
corvus. Every mode landed inside 1.9 sigma. THE TOOL IS SAMPLING OUR LUTS CORRECTLY.

⚠ THE DANGER ZONE PANEL IS VARIANCE, NOT A DEFECT, and corvus proves it: 1.3% affected
against base's 56.9% on the identical config, because corvus's cost-adjusted volatility
is 2.09 against 26.24 and it never pays zero.
⚠⚠ AND ITS "TOTAL EVENTS" / "AVG PER PLAYER" FIGURES ARE INFLATED AND SHOULD NOT BE
QUOTED. The sim does NOT stop at zero (base min balance -149.89), so a player who runs out
at spin 150 contributes another 150 danger events. Base's 108,902 events are dominated by
post-ruin spins. "Avg per player 54.5" is also divided by ALL 2,000 players, not the 1,137
affected. ONLY "PLAYERS AFFECTED" IS READABLE.
=> Base's 56.9% is the arithmetically expected result of a thin bankroll, not harshness:
   per-spin std dev 25.36 over 300 spins gives a session std dev of 25.36*sqrt(300) = 439
   against a 100-unit bankroll. THE NOISE IS 4.4x THE BANKROLL, so where you finish is
   almost independent of where you started. Expected loss over the session is only ~10.

⚠ SIM RTP CONVERGENCE IS A VARIANCE DIAGNOSTIC — USE IT ON COMPETITORS. Standard error is
(per-spin std dev)/sqrt(spins), so base lands +/-3.27pp and corvus +/-0.27pp on the same
600k spins. Base read 0.71 sigma, ante 1.59, corvus 0.11 — all normal. IF A COMPETITOR'S
SIM RTP CONVERGES TIGHTLY, THEIR VARIANCE IS FAR BELOW OURS. That is the single fastest
read available on whether their game is genuinely comparable to ours.

⚠ TWO THINGS THAT ARE NOT COMPARABLE ACROSS MODES:
  (a) "BIG WIN 10x" IS RELATIVE TO COST. For corvus that is 1,200x absolute, for base 10x.
      Corvus's 97.0% hit rate is a vastly bigger event than base's 99.0%. Never put those
      two columns side by side without saying so.
  (b) 300 SPINS OF A BUY IS NOT A SESSION. 300 corvus buys is 36,000x of turnover. Buy-mode
      session stats are for CROSS-GAME COMPARISON at a fixed config, not for predicting
      real player behaviour.

## 3. Buy menu — structure, and where we are unusual

  mode        cost   RTP      max win   ceil/cost  median/c  beat    <0.25x tkt  max-win rate
  buy_corvus   120x  96.65%     9,000x      75.0x     0.294   17.2%      41.6%   1 in 2,000,003
  buy_ursa     268x  96.62%    25,000x      93.3x     0.298   32.3%      43.1%   1 in 3,589
  buy_draco    520x  96.50%    25,000x      48.1x     0.235   21.8%      53.1%   1 in 642
  buy_mystery  563x  96.65%    25,000x      44.4x     0.327   22.1%      32.7%   1 in 1,110

  feature completion (delivered, LUT-weighted -- NOT the raw-pool figure):
    corvus 89.7%  |  ursa 48.2%  |  draco 29.9%  |  mystery 75.3%
  payoff when the feature completes, as a multiple of the ticket:
    corvus 1.07x  |  ursa 1.83x  |  draco 2.76x  |  mystery ~1.17x

⚠ THINGS TO ASK OF A COMPETITOR'S BUY MENU, because these are where we made real choices:
  (a) CEILING-PER-COST FALLS WITH PRICE for anyone using a shared max win, since it is
      just cap/price. Ours: 75 / 93 / 48 / 44. If a competitor's RISES with price, they
      are using PER-MODE CAPS — worth knowing, we have that machinery (corvus is 9,000x).
  (b) DOES THE EXPENSIVE TIER PAY BIGGER *WHEN IT LANDS*? Ours does: 1.07 -> 1.83 -> 2.76.
      This is the ladder that matters, not the ceiling.
  (c) HOW OFTEN DOES A BUY REACH ITS FEATURE CLIMAX? Ours: 90 / 48 / 30 / 75%.
  (d) MAX-WIN RATE PER MODE. Ours spans 1 in 642 (draco) to 1 in 2M (corvus).

## 3b. COMPETITOR: Rage Bait (Meta Gaming, v11) — measured Aug 7 2026

SOURCES, and they are cheap to re-pull:
  stakestats.net/api/games/<slug>  -- ONE GET, returns every mode as JSON (rtp, std dev,
    hit, bust, maxMultiplier, events, volatility rank vs 26,470 modes). No screenshots,
    no clicking "Load Stats". curl it from WSL and parse.
  stakecruncher.com/slots-tracker/stats/<slug>/<ver>/<mode> -- per-mode page carrying the
    numbers stakestats does NOT have: MAX WIN CHANCE, median win, top-heavy RTP,
    money-back-on-a-win, dry-streak percentiles.

⚠ THE TWO SITES DEFINE "HIT" DIFFERENTLY AND BOTH ARE INTERNALLY CONSISTENT:
    StakeCruncher HIT = P(any win)      -- base 37.5%, and HIT + BUST = 100
    stakestats hitFrequency = P(>= 1x)  -- base 16.08%
    BUST agrees on both (62.5%). Always state which one a number is.

  mode                    cost      RTP   std dev   bust   any win   >=1x    max win   MAX-WIN RATE
  base                      1x   96.70%    33.435  62.5%    37.5%   16.08%   25,000x   (not shown)
  ante                      3x   96.70%    20.020  58.0%    42.0%   10.47%    8,333x   1 in 319,430
  bonus_fs_super          250x   96.70%     2.576   0.0%   100.0%   27.94%      100x   1 in 3,998
  rage_spins              350x   96.70%     3.963   5.9%    94.1%   14.72%     71.4x   1 in 1,377
  bonus_fs_mystery        500x   96.70%     2.684   0.0%   100.0%   23.35%       50x   1 in 981
  bonus_fs_mystery_ante   500x   96.70%     3.323  46.5%    53.5%   20.11%       50x   1 in 395
  events/mode 1.23M-1.98M. maxMultiplier is COST-NORMALISED, so cost = 25,000/maxMult --
  that is how the prices above were derived, and it confirms every mode reaches 25,000x.

### THE FINDINGS THAT MATTER

⚠⚠ 1. OUR BASE IS FLATTER AND DRIER, AND THE 35-48 BENCHMARK BAND WAS ROUGHLY RIGHT.
  std dev      Rage Bait 33.435   Starwake 25.357   (we are 24% below; their base ranks
                                                     1483/26,470 = 94.4th percentile)
  pays nothing         62.5%              70.75%
  any win              37.5%              29.25%
  pays >= 1x          16.08%               8.00%
  partial (0-1x)      21.42%              21.25%   <- IDENTICAL to 0.2 points
=> THE PARTIAL BAND IS THE SAME IN BOTH GAMES. THE ENTIRE DIFFERENCE IS THAT RAGE BAIT
   CONVERTS 8 POINTS OF DEAD SPINS INTO MONEY-BACK-OR-BETTER. And it does that while
   being 32% MORE volatile on the same 25,000x cap and the same RTP -- more frequent
   break-evens AND a heavier tail, which is the hard combination.

⚠⚠ 2. CORVUS'S MAX-WIN RATE IS A 500x OUTLIER AGAINST THE MARKET.
  Rage Bait's buys:  1 in 395 / 981 / 1,377 / 3,998
  Starwake's buys:   draco 1 in 642, mystery 1 in 1,110, ursa 1 in 3,589  <- all normal
                     CORVUS 1 in 2,000,003                               <- 500x rarer
  Set Aug 6 for a 5x margin under the 1-in-10M obtainability gate. Legal, and nothing
  like how a competitor prices a buy's headline: a Rage Bait buyer reaches their ceiling
  every few hundred to few thousand buys; a corvus buyer effectively never does.
  TO FIX: corvus_cap_rtp 0.0000375 -> ~0.019 gives ~1 in 4,000. Corvus caps at 9,000x so
  p10k is untouched; p5k goes to ~2.5e-4 against a 0.010 limit. Legal but it costs ~1.9%
  of the mode's RTP out of the body, where the current setting costs 0.004%. NOT DECIDED.

⚠ 3. WE ARE MORE GENEROUS ON MEDIAN, THEY ARE FAR MORE TOP-HEAVY.
  median win / ticket   theirs 0.05-0.22x     ours 0.235-0.327x   WE WIN
  RTP from 100x+ wins   theirs 62% (ante), 92-99% (bonuses)   ours 31.3% (base)
  StakeCruncher labels EVERY Rage Bait mode "Psychotic -- most of the RTP is locked
  behind the tail, dry for ages, then you either hit big or go home." We are the
  opposite shape: more middle, less tail.

⚠ 4. THEIR SIX MODES ARE ALL EXACTLY 96.7000%. Zero spread. We run 96.50-96.65% and
  buy_draco is 0.20 points under the cap -- free player-facing RTP we are not giving.

⚠ 5. CEILING-PER-COST FALLS WITH PRICE FOR THEM TOO: 100x (250 cost) -> 71.4x (350) ->
  50x (500). CONFIRMS this is structural under a shared cap and NOT a defect of ours.
  Ours is only non-monotonic because corvus carries a 9,000x cap instead of 25,000x.

⚠ 6. REPLAY URL FORMAT, useful for the mandatory replay work:
  https://fair.stake-engine.com/replay/<publisher>/<game>/<version>/<mode>/{event}

## 3c. COMPETITOR: Coins and Cauldrons (Meta Gaming, v13) — measured Aug 7 2026

⚠ THE stakestats API RETURNS EVERY VERSION. Filter to activeVersion or you will read a
retired build. C&C carries v10/v11/v13; v11's base std dev is 29.155 and v13's is 59.870
-- THEY ROUGHLY DOUBLED THE VOLATILITY OF A LIVE GAME BETWEEN VERSIONS. A published
game's variance is not fixed, and studios do retune it upward.

  mode              cost      RTP   std dev    bust   any win   >=1x    maxMult     events
  base                1x   96.01%    59.870  69.82%    30.18%   8.53%   50,000x  1,903,275
  bonus2x             2x   96.01%    34.472  93.00%     7.00%   6.78%   25,000x    938,743
  bonus_wild_coin     8x   96.01%    16.259  48.13%    51.87%  16.19%    6,250x    859,365
  bonus_fs          100x   96.01%     4.474   0.00%   100.00%  22.18%      500x  1,000,001
  bonus_fs_4sc      200x   96.01%     3.754   0.00%   100.00%  22.25%      250x  1,000,001
  bonus_fs_wild     500x   96.01%     3.957   0.00%   100.00%  14.56%      100x  1,999,687
  RTP is 96.01%, NOT the 96.70% cap -- sitting on the cap is not universal. Max win is
  50,000x (2x ours). Buy ladder 2x/8x/100x/200x/500x: cheap feature buys next to
  expensive ones, where our cheapest is 120x.

⚠⚠ THE DRYNESS FINDING FROM RAGE BAIT DOES NOT SURVIVE A SECOND DATA POINT.
  base            RAGE BAIT   COINS & CAULDRONS   STARWAKE
  pays nothing        62.5%              69.82%     70.75%
  any win             37.5%              30.18%     29.25%
  pays >= 1x         16.08%               8.53%      8.00%
WE MATCH C&C TO WITHIN A POINT ON ALL THREE. Rage Bait is the outlier on hit frequency,
not us. An earlier note here concluded from Rage Bait alone that our base pays >=1x half
as often as the market; that was n=1 and it was wrong.

⚠⚠ WHAT *DOES* SURVIVE: OUR TAIL IS LIGHT. And the full curve locates it exactly.

  CHANCE OF MULTIPLIER OR BETTER, base game, per spin:
    >= mult      STARWAKE          C&C              who
      0.5x       1 in 4.4          1 in 6.2         us 1.4x
      1x         1 in 12.5         1 in 11.7        equal
      2x         1 in 43.1         1 in 16.6        THEM 2.6x
      5x         1 in 51.2         1 in 76.7        us 1.5x
      10x        1 in 67.7         1 in 112.1       us 1.7x
      50x        1 in 238          1 in 593         us 2.5x
      100x       1 in 667          1 in 1,319       us 2.0x
      250x       1 in 4,390        1 in 3,850       equal   <- CROSSOVER
      500x       1 in 31,493       1 in 8,306       THEM 3.8x
      1,000x     1 in 70,561       1 in 17,902      THEM 3.9x
      2,500x     1 in 332,709      1 in 40,981      THEM 8.1x
      5,000x     1 in 930,862      1 in 94,452      THEM 9.9x
      25,000x    1 in 1,250,001    1 in 901,583     THEM 1.4x
      (their 50,000x max win: 1 in 1,983,481)

=> WE ARE UP TO 2.5x MORE GENEROUS FROM 5x TO 100x AND 4-10x LESS GENEROUS FROM 500x TO
   5,000x. That single fact IS the std-dev gap (25.4 vs 59.9) and IS the top-heavy-RTP
   gap (31.3% vs 41%). Variance lives in the far tail, so their advantage above 500x
   buys 2.4x our standard deviation while their base pays LESS often than ours below 100x.
=> THEREFORE THE LEVER IS NOT "ADD MORE WINS". Our base is generous in the body and thin
   in the tail. Market-normal volatility means moving RTP from the 5x-100x shoulder into
   500x+, which is the OPPOSITE of what the dryness framing implied.

⚠ AN ANOMALY THIS EXPOSED IN OUR OWN CURVE: the 2x-5x band is a DIP. Odds by band run
1 in 18 (1-2x) -> 1 in 273 (2-5x) -> 1 in 211 (5-10x) -> 1 in 182 (10-20x). A 15x rarity
jump and then back down. C&C runs 1 in 21 smoothly through the same band. It passes the
win-range-gap check (no zero-weight range) but it is a visible pothole in an otherwise
smooth curve, and it is exactly what a reviewer eyeballing a hit-rate table would query.

STAKECRUNCHER'S QUALITATIVE LABELS, worth knowing since a reviewer may think this way:
  C&C base       "Swingy -- long dry streaks punctuated by meaningful hits. Needs bankroll."
  Rage Bait ALL  "Psychotic -- most of the RTP is locked behind the tail, dry for ages,
                  then you either hit big or go home."
  C&C base dry streaks: median 2, bad day 4, rough 8, nightmare 13 consecutive 0x spins.

## 4. Compliance position (for context, not comparison)

3-Star: 0 failed classes -> $500 bet template. 2-Star: 1 (absolute CVaR 25,000 vs 20,000).
All seven critical tests pass. Tightest 3-Star headroom is ETL40 at 1.61x (0.558 vs 0.9),
and its worst case is BASE, not a buy.
Authority is `check_risk_gates.py`, verified line-by-line against
stake-engine.com/docs/approval-guidelines/math-verification including the penalty schedule.

⚠ MNEMOO'S COMPLIANCE TAB IS NOT THE RUBRIC. Its hardcoded limits (p5k 0.005, p10k 0.001)
are 5-10x stricter than the real spec (2-Star 0.010/0.005, 3-Star 0.050/0.010) and its
own source calls them "tentative defaults". It also invents a 1-Star tier that does not
exist in the spec, which is why buy_corvus displays "1-STAR". Use Mnemoo for Distribution,
CrowdSim, LGS and the Event Finder. Ignore its verdicts.

## 5. Limits (settled Aug 7 2026)

  outcomes per mode   10,000,000   we use 1,000,000 = 10% of cap. NOT events; confirmed
                                   by Happle (Stake Engine) in "10 mil outcomes per mode
                                   limit". The docs say "events" and it is a trap.
  file size per mode        3.14GB Taylor (Stake Engine); the docs say 4.2GB. Use 3.14.
                                   buy_draco is 2.7GB = 86% OF THE CAP -- this is the
                                   constraint that actually binds, and the real reason
                                   events-per-book matters (86.8 on ursa).
  practitioner norm                "1M on all base atleast, and then like 250k on
                                   bonuses" (Taylor). We run 1M everywhere.
