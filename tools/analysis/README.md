# tools/analysis — game-agnostic math analysis

Written for Starwake, kept because none of it is Starwake-specific. Everything reads
`index.json` for the mode list and costs, so it runs on any Stake Engine `publish_files`
directory — ours, an older pool, or a competitor's.

⚠ **Every LUT-derived number comes from `lookUpTable_<mode>_0.csv`, the OPTIMIZED table,
never the raw book pool.** The pool is quota-shaped by construction; a bust rate or a
median read off it is meaningless. Two of these tools read books as well, but always
weighted by the optimized LUT.

    env/bin/python tools/analysis/<script> <publish_files_dir> [args]

| script | what it answers |
|---|---|
| `pool_audit.py` | one table, every mode: RTP, zero rate, median, beat rate, under-0.25x, ceiling/cost, std dev, max-win rate |
| `payout_curve.py` | chance-of-multiplier-or-better + **variance decomposition by payout band**, one mode |
| `book_split.py` | split books on an event (default `beastWake`) — reach rate, payout each side, payoff when reached |
| `tier_mix.py` | delivered sub-outcome mix inside a mode, with per-outcome payback share, completion and max-win rate |
| `event_budget.py` | outcomes / events / file size per mode against the RGS publish limits |
| `competitor_pull.py` | any published rival's full per-mode stats from the stakestats API |

## The four things these were built to catch

**Raw-pool and delivered numbers disagree, often badly.** Starwake's raw pool showed
tier completion 84/62/32; weighted by the shipped LUT it was 90/35/30. A sim printout
gives the first, players experience the second. `book_split.py` and `tier_mix.py` both
report the weighted figure. Always say which one you mean.

**A headline std dev can be one outcome.** `payout_curve.py`'s decomposition found 77.7%
of Starwake base's E[X²] sitting in the single 25,000x cap — strip it and std dev falls
25.36 → 11.96. A competitor at a similar headline number had only 35% in its cap and a
genuinely populated tail. Run the decomposition before concluding anything about
volatility.

**Conservation pins the design.** `reach_rate × payoff + (1 − reach_rate) × consolation
= RTP × cost`. Everything is fixed except the split, so a feature can be *often but
smaller* or *rarely but bigger* — never both. `book_split.py` prints all three terms so
the trade is explicit before anyone tunes.

**An advertised mix must be the delivered mix.** The optimizer reweights books, so inner
odds correct in the raw pool can drift. `tier_mix.py` is the pre-publish check.

## Competitor workflow

1. `competitor_pull.py <slug>` — every mode's RTP, std dev, bust, outcomes, volatility
   rank, and their **buy prices** (recovered via `cost = base_cap / maxMultiplier`;
   published nowhere else).
2. For max-win chance, median win, top-heavy RTP and dry streaks, open
   `stakecruncher.com/slots-tracker/stats/<slug>/<ver>/<mode>` — client-rendered, so it
   needs a browser rather than curl.
3. `payout_curve.py` on our matching mode reproduces StakeCruncher's
   chance-of-multiplier-or-better table exactly, giving a like-for-like diff.

Measured comparisons and what they concluded live in `games/starwake/BENCHMARKS.md`.

## Not promoted

The optimizer-variance and draw-selection harnesses stayed in scratch. They shell out to
`go/optimize_go.py`, so they are pipeline-specific rather than analysis, and they belong
with whatever pipeline the next game uses.
