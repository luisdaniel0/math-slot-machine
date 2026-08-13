# Starwake — Rules Screen: the beast multiplier

*Math-derived copy for the in-game info screen. The frontend renders this; it does not
get to invent it. Every number below is either read from `game_config.py` or measured
off the converged 1e6 pool, and each one says which.*

Measured Aug 13 2026 by `games/starwake/enumerate_multipliers.py` over all six pools
(5,267,849 act-two rounds). Regenerate with that tool after any change to a star table,
a roam strip, or a tier's feature length.

---

## ⚠ DO NOT WRITE THIS SCREEN FROM `constellation_mult_ladders`

That config field is **dead code**. Act two replaced the climbing ladder with star
collection on Aug 5 2026; `ActTwo()` is true in every tier, so the ladder branch is
unreachable in every mode. The values are still in `game_config.py`, still exported to
`go/config/starwake.json` as `multLadder`, and still validated at load — they just never
run. See the Aug 13 entry at the top of `games/starwake/CLAUDE.md`.

Publishing them would advertise multipliers the engine cannot pay. That is not a
hypothetical: `go/internal/game/starwake/config.go:168` records the same bug already
shipping once — *"rungs were set to featureSpins-1, a depth needing a spin-1 completion,
so ursa and draco advertised multipliers no player could ever be paid."*

---

## 1. The copy

> ### Multiplier Stars
>
> When a constellation completes, its beast wakes and roams the reels. The traced stars
> stop acting as wilds at that moment — from then on **the beast is the only wild on the
> board**.
>
> While the beast is on the board, **multiplier stars** land on reels 2–5. The beast
> collects **every star on the board**, wherever it lands — it does not need to touch
> them. Its multiplier is **1 plus the total of every star it has collected**, and it
> keeps climbing for as long as the beast roams.
>
> The beast multiplies any winning line that passes **through the beast**. Lines that
> miss it pay normally.
>
> Star values are **x2, x3, x5, x10, x25, x50 and x100**. Which values can appear
> depends on the constellation — see the table below.

**Notes for whoever lays this out**

- "Collects every star on the board, wherever it lands" is load-bearing and must not be
  trimmed. Collection is global; only *application* is positional. Players who think they
  need the block to land on a star will misread every roam.
- The two halves — global collection, positional payment — are the mechanic. If layout
  forces a cut, cut elsewhere.
- The wilds-turn-off line matters because it is *visible*: a player watching act one
  build a wild carpet will see it vanish on wake. `constellation.go:470` — under act two
  `WildCells()` returns the beast block alone. Without the sentence it reads as a bug.
- Stars never land on reel 1: both roam strips carry zero star symbols there
  (`FRROAM.csv`, `FRROAMCAP.csv`), because on a left-to-right lines game a blocker on
  reel 1 kills a win outright.

---

## 2. Star values — the enumerable table

**This is the table the "list all obtainable values" requirement is about.** The star is
the special symbol; these are its obtainable values, exactly and completely. Source:
`game_config.constellation_star_values`. Weights sum to 100 per tier, so the percentages
below are exact, not rounded.

| Constellation | x2 | x3 | x5 | x10 | x25 | x50 | x100 |
|---|---|---|---|---|---|---|---|
| **Corvus** (3 scatters) | 55% | 25% | 13% | 6% | 1% | — | — |
| **Ursa** (4 scatters) | 45% | 25% | 17% | 9% | 3% | 1% | — |
| **Draco** (5 scatters) | 16% | 14% | 18% | 18% | 15% | 12% | 7% |
| **Draco Ascendant** (6 scatters) | 32% | 23% | 20% | 14% | 7% | 3% | 1% |

**Corvus Ascension** — a rare Corvus round switches to a richer table:

| | x2 | x3 | x5 | x10 | x25 | x50 |
|---|---|---|---|---|---|---|
| **Corvus, ascended** | 25% | 20% | 20% | 18% | 12% | 5% |

⚠️ **THE PER-MODE SPLIT DIED WITH `buy_corvus` (Aug 13 2026).** That mode's wincap slice
was the only thing setting `forceAscension=True`, which is what made the delivered rate
differ by ~100x between modes. **The "1 in 634" figure described `buy_corvus` alone and is
now meaningless.** With no forced delivery anywhere, ascension runs at its natural
`starDrops.ascension.oneIn` rate everywhere — 1 in 20,000 corvus rounds.

Player copy should call it rare and leave it unnumbered. Re-measure with
`tier_frequency.py` before printing any figure.

⚠️ **THIS MAKES ASCENSION A CANDIDATE FOR DELETION, NOT A FEATURE TO DOCUMENT.** It now
fires effectively never, its `one_in` has no measured effect on anything, and
`constellationAscend` still has no art. Deleting it touches the corvus star table, which
is SHARED by base, ante_starfall, buy_mystery and buy_mystery_spin — so it re-sims four
of six modes. Deferred, not forgotten.

---

## 2b. The seeded multiplier — One Wake only

> ### The beast wakes ready
>
> In **One Wake**, the beast is already roaming when the spin begins, and it arrives
> **already carrying a multiplier**. Every star it collects on that spin adds to it.

| Seed | x2 | x5 | x10 | x25 | x50 | x100 |
|---|---|---|---|---|---|---|
| **One Wake** | 30% | 25% | 20% | 15% | 7% | 3% |

Source: `game_config.wake_seed_values`. Weights sum to 100, so these are exact.

⚠️ **THE SEED APPLIES ONLY TO One Wake.** Everywhere else the beast wakes bare at x1 and
climbs purely by collecting — `multiplier = seed + collected` with seed 1 is exactly the
old rule. Copy must not imply the beast is ever pre-loaded in the ordinary feature.

⚠️ **DO NOT PUBLISH THE WINCAP SEED FLOOR.** `wake_seed_wincap_floor` guarantees seed ≥25
inside the max-win slice; it is a GENERATION device that makes cap books affordable to
manufacture, and it does not change the odds a player faces. The delivered max-win rate
is set by the slice's RTP share (1 in 1,500), not by the floor. Printing it would
advertise a mechanic nobody experiences.

---

## 3. The beast multiplier itself — publish the rule, not a ceiling

`multiplier = 1 + collected` (`constellation.go:412`). The obtainable set is therefore
*derived*, and it has two properties worth stating precisely:

**x2 is unobtainable.** It would need exactly 1 collected, and the smallest star is x2.
The multiplier is **x1** before any star is taken, then resumes at **x3**. Confirmed
against all 5.27M act-two rounds — x2 appeared zero times.

**From x3 up there are no gaps.** Every tier's table contains both a 2 and a 3, and
`{2,3}` generates every integer ≥ 2 as a sum. So the obtainable set is a **range**, not a
list — which is why this screen does not carry a 1,800-row table.

### What NOT to publish

Two numbers are available and **both are wrong to print as a maximum**:

| | corvus | corvus asc. | ursa | draco | ascendant |
|---|---|---|---|---|---|
| Highest **observed**, 1e6 pools | x125 | x729 | x543 | **x1,841** | x848 |
| **Combinatorial bound** from config | x3,151 | — | x9,801 | x19,601 | x19,601 |

- The **bound** (densest 4-row window per reel × collecting spins × top star value) needs
  every window packed *and* every star rolling its top value. Printing x19,601 repeats
  the exact sin quoted at the top of this document.
- The **observation** is a sample, not a limit. It moved with sample size — draco read
  x1,126 at 5k books/pool and x1,841 at 1e6 — so it is not a ceiling and must never be
  presented as one.

### The number that *is* a limit

**Maximum win: 25,000x total bet**, enforced by the engine, identical in every mode. That
is the honest, exact, player-facing bound, and it is what the screen should state. The
beast multiplier gets a rule; the win gets a cap.

---

## 4. Facts the rest of the screen needs

Source: `go/config/starwake.json`. All modes share one RTP by design.

| Mode | Cost | RTP | Max win |
|---|---|---|---|
| Base | 1x | 96.69% | 25,000x |
| Ante (Starfall) | 1.5x | 96.69% | 25,000x |
| **One Wake** (mystery spin) | **200x** | 96.69% | **15,000x** |
| Buy Ursa | 300x | 96.69% | 25,000x |
| Buy Draco | 400x | 96.69% | 25,000x |
| Buy Mystery | 500x | 96.69% | 25,000x |

⚠️ **BUY CORVUS NO LONGER EXISTS** (removed Aug 13 2026). Any screen still listing it is
stale. The corvus *constellation* is unchanged and still appears in base, ante, Buy
Mystery and One Wake — only the 200x buy is gone.

⚠️ **ONE WAKE IS THE ONE MODE WITH A DIFFERENT MAX WIN, AND THE COPY MUST NOT ROUND IT
UP TO 25,000x.** One spin cannot accumulate a multiplier the way a 15-spin feature does;
the measured organic maximum is 23,072x, so 15,000x is the honest, reachable figure. It
is delivered at 1 in 1,500, the most frequent max win in the game.

Feature length: Corvus **10** spins, Ursa / Draco / Draco Ascendant **15**. A beast that
completes late still gets a guaranteed minimum roam of **2** spins.

Scatter → constellation: **3** Corvus, **4** Ursa, **5** Draco, **6** Draco Ascendant.
Draco Ascendant cannot be bought directly — only Buy Mystery can reach it.

**Buy Mystery tier mix**, measured off the optimized LUT (`tier_frequency.py`), not the
pool quota:

| Tier | Delivered | Share of mode RTP |
|---|---|---|
| Corvus | 34.97% | 13.7% |
| Ursa | 34.97% | 20.6% |
| Draco | 19.99% | 15.8% |
| **Draco Ascendant** | **10.07%** (1 in 9.9) | **49.9%** |

The headline "1 in 10 wakes something you cannot buy" is accurate as delivered, not just
as designed. Ascendant is a tenth of the rolls and **half the mode's payback**.
