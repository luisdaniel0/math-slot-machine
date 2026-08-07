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

⚠ DO NOT QUOTE CROWDSIM'S STREAK NUMBERS UNTIL THE DEFINITION IS CONFIRMED. It reported
average lose streak 61.4 and maximum 192. Under the obvious reading (consecutive spins
paying nothing) that is impossible: at a 29.25% hit rate the expected longest dead run in
300 spins is ~13, and across 2,000 players it would top out near 30. The likely
definition is "spins paying less than the bet" (92.2% of spins, predicting ~39), or
possibly "time spent below the starting balance". These are the most quotable and most
misreadable numbers on the page.

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
