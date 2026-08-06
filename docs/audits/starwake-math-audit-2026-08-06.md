# Starwake math audit — Aug 6 2026

Full audit of the committed math, run against a **freshly regenerated pool** rather than
against recorded numbers: `library/` is gitignored, so nothing here is inherited from an
earlier session's measurements. Everything below was re-derived in this session.

    engine       go/cmd/starwake, 1,000,000 books x 6 modes   (10 min, 4 workers)
    optimizer    unchanged Rust PigFarmRust, all six modes    (46 min)
    pools        go/out/library, games/starwake_go/library    (shadow game, per optimize_go.py)
    reference    a Python buy_corvus pool at 20k, for engine parity

Read all numbers below off the **optimized LUTs**, per the house rule. The raw book pool
is quota-shaped and its statistics are meaningless.

---

## Verdict

The math is internally sound and the engine is correct. **One compliance gate that was
recorded as passing now fails**, and it costs the bet-level template. Everything else is
documentation drift, publish-artifact accuracy, or an open question that is still open.

| | |
|---|---|
| Critical tests (all 7) | **PASS**, with margin |
| 2-Star non-critical | **2 failed classes** (was 1) → **$50 bet template**, not $100 |
| 3-Star non-critical | 0 failed classes |
| Engine correctness | Go and Python statistically indistinguishable; event tapes identical |
| Config drift | none — `go/config/starwake.json` and the reel strips regenerate byte-identical |
| Publish set | self-consistent; every sha256 matches |

---

## 1. BLOCKING — buy_mystery fails the tail-probability gate, and the $100 template with it

    p5k   buy_mystery   1.71e-02   limit 1.00e-02   OVER by 1.7x
    p10k  buy_mystery   1.86e-03   limit 5.00e-03   ok

`games/starwake/CLAUDE.md` names this exact class as the one closest to flipping
("p5k worst 6.57e-03 … 1.52x headroom"). On this pool it flipped. Two failed classes at
2-Star (Tail Probability joins the structural CVaR-absolute failure), which steps the caps
down from $15M/$100k to $10M/$50k and the template from **$100 to $50**.

**Where it comes from — 94% of it is one fence:**

| criteria | P(≥5,000x) | share of rolls | mean | x ticket |
|---|---|---|---|---|
| **ascendant** | **1.60e-02** | 10.061% | 2,527x | 4.49x |
| wincap | 6.87e-04 | 0.069% | 25,000x | 44.4x |
| draco | 2.43e-04 | 25.104% | 483x | 0.86x |
| ursa | 1.04e-04 | 29.622% | 249x | 0.44x |
| corvus | 6.58e-05 | 35.144% | 221x | 0.39x |

Mystery costs 563x, so 5,000x is only **8.9x its ticket** — and Draco Ascendant is designed
to average 4.5x its ticket on 10% of rolls. About 16% of ascendant rolls land above 5,000x.
The mode's whole p5k budget is 1.0e-02; ascendant alone is spending 1.6e-02.

**Nothing in `game_optimization.py` constrains this.** The RTP split fixes ascendant's
*mean* (46.7% of payback on 10% of rolls) and leaves the optimizer free to choose how that
mean is spread across 5,000–25,000x. The shipped pool happened to land at 6.57e-03 and this
one at 1.71e-02 — same config, 2.6x apart. The gate is not pinned, so it will keep landing
on either side of the line at random until something pins it.

**Levers, cheapest first** (all optimizer-only, ~12 min for the one mode, no re-sim):

1. Add a `ConstructScaling` entry that damps ascendant's 5,000–25,000x band and lifts
   2,000–5,000x. Ascendant must hold ≤ ~9.3e-3 of the mode's p5k, i.e. ≤ ~9% of ascendant
   rolls above 5,000x rather than 16%. Note the existing `tail_scaling("ascendant")` already
   pushes toward 3,000–4,000x — this extends the same idea with the gate as the target.
2. Cut `mystery_cap_rtp` 0.040 → lower. Worth only 6.9e-04 of the 1.71e-02, and it would
   break the cap-share ladder — do not lead with this.
3. Re-shape ascendant itself (fewer pre-lit cells → lower mean). Changes the price and the
   published mix; it is a re-sim and a re-price. Last resort.
4. Accept the $50 template. That is a product call, not a math one — it halves the maximum
   bet, which is exactly what the CLAUDE.md note says to protect.

Whatever is chosen, **p5k on buy_mystery must be measured on every future pool**, the same
way RTP is.

---

## 2. Published per-mode RTP is the target, not the delivered value

`config.json` writes `"rtp": bet.get_rtp()` — the configured 0.9665 for every mode — while
`std` and `bookLength` in the same record are measured off the LUT. Delivered:

| mode | published rtp | delivered rtp |
|---|---|---|
| base | 0.9665 | 0.9665 |
| ante_starfall | 0.9665 | 0.9665 |
| buy_corvus | 0.9665 | 0.9665 |
| buy_ursa | 0.9665 | 0.9662 |
| **buy_draco** | **0.9665** | **0.9650** |
| buy_mystery | 0.9665 | 0.9665 |

buy_draco advertises 0.15pp more than it pays, and it under-converges the same way on every
recorded run (0.9655, 0.9650, and 0.9650 here) — so this is systematic, not noise. The
mechanism is upstream (`src/write_data/write_configs.py:350`). Either converge draco onto
its target or publish the measured number.

---

## 3. The 10,000,000-event limit is still open, and every mode is over it at 1e6 books

Re-measured on this pool (events per book x 1e6 books):

    base 10.7M | ante 15.5M | corvus 61.2M | ursa 86.8M | draco 85.3M | mystery 78.0M

Identical to the figures recorded on Aug 4, so nothing has drifted — the question simply has
not been answered. It sets the sim count for every future run and the two readings differ by
a factor of a million. At 100k books only ursa (8.7M) and draco (8.5M) would sit under a
literal limit; base and ante would be fine at 1e6 and the buys would not. **Ask the RGS
team.** This is the cheapest open item on the list and it blocks planning the retune above.

---

## 4. Ladder-obtainability figures do not reproduce — they are 4–19x pessimistic

`game_config.constellation_ladder_rungs` carries a measured table justifying the rung counts.
Re-measured here, on both engines, counting `beastRoam` multiplier values with forced-wincap
books excluded:

| tier / top rung | recorded | measured now | ratio |
|---|---|---|---|
| corvus 200x (buy_corvus) | 1 in 466 | **1 in 122** | 3.8x |
| ursa 500x (buy_ursa) | 1 in 17,995 | **1 in 1,695** | 10.6x |
| draco roam 12 (buy_draco) | 1 in 75,112 | **1 in ~4,000** | 19x |

The Python engine reproduces the new numbers too (corvus top rung 0.815% at 20k books vs
Go's 0.735%), so this is not a Go-port artifact — the recorded table is wrong. The most
likely cause is the very distinction CLAUDE.md itself documents: *"the beast REACHED rung N"*
is an event question, *"a win was PAID at rung N"* is a force-record question, and the second
is far rarer.

**The rung-count decisions survive** — measured roam-depth distributions confirm them:

    ursa    depth >=13  1 in 1,869    depth 14  NEVER in 200k   -> 13 rungs is exactly right
    draco   depth 12    1 in 4,000    depth 13  NEVER in 200k   -> 12 rungs is exactly right
    corvus  depth 9     1 in 122                                -> 9 rungs, comfortably organic

So no ladder advertises an unwinnable multiplier — the compliance requirement holds. But the
one number that decided draco stops at 12 rather than 13 ("roam 13 at 1 in 2.5M") is from the
unreliable table, so if a 13th rung is ever wanted again, re-derive it rather than trusting it.

---

## 5. Capped base books still ship with split fields that do not reconcile

Measured over all 1,000,000 base books: **214 books (0.0214%)** where
`baseGameWins + freeGameWins` exceeds `payoutMultiplier`, worst case **+5.50x**. Zero books
pay above their ceiling — the payout itself is clamped correctly at
`src/state/state.py:192`; it is the two split fields, clamped separately at 193–194, that can
sum past the cap. The SDK's own assert deliberately permits it.

This matches what was recorded and retracted-as-cosmetic in July. It remains true, it ships
inside `books_base.jsonl.zst`, and a validator that cross-checks the split against the payout
would flag it. Still not worth a re-sim on its own; worth fixing whenever base is next
re-simmed.

---

## 6. Documentation and hygiene

| | |
|---|---|
| `game_optimization.py` module docstring | cap-share table says `buy_ursa 0.030`; the code settled at **0.026**. The criteria list says `buy_mystery: wincap, mystery` — it has been four tier fences plus wincap since Jul 28. |
| `game_optimization.py:102` | `feature_cond` docstring says *"buy_mystery MUST omit [kind]"*; the code 250 lines below passes `kind=3/4/5/6`. Directly contradicts itself, and the fence-order bug family it warns about is exactly what a reader would get wrong. |
| `check_risk_gates.py:36` | `COSTS` is hardcoded. A price change in `game_config.py` silently mis-scales every per-stake gate. Read it from the config. |
| `go/cmd/starwake/main.go:236` | prints `cost %.0fx`, so ante_starfall's 1.5x displays as **"cost 2x"**. Ratio math is unaffected (it uses `mode.Cost`). |
| `ante_starfall` quotas | sum to 0.9615, not 1.0. Both engines normalise, so the pool composition is proportional and the optimizer re-weights anyway — harmless, but it is not what the numbers look like. |
| `constellation.py` docstring | still says *"Corvus 2x2 / Ursa 2x3 / Draco 3x3"*. All three have been 2x2 since Jul 27. |
| Python version | `utils/get_file_hash.py:36` uses a nested-quote f-string, so the repo needs **Python ≥ 3.12**. Undocumented; a 3.11 venv fails at import of `write_configs`. |

**Test gaps**

- No Python test for `apply_max_symbol_mult` — the strategy that fixed the block-wild
  double-crossing bug worth 87% of buy_corvus's payout. Go has one
  (`internal/sdk/engine/lines_test.go:174`); the reference engine does not.
- No test for `game_override.check_repeat`'s zero-win redraw. That single line is what
  delivers "buys bust 0.00%", and its own Go port carries a warning saying so.
- `go/internal/sdk/sim` (runner, writer, merge) has no tests. The shard-merge step is where
  book ids and LUT rows could desynchronise silently. Verified correct by hand here
  (below), but nothing guards it.

---

## What was verified clean

**Config integrity**

- `go/config/starwake.json` is **byte-identical** to a fresh `export_go_config.py` — the one
  documented footgun (Go running old math silently) is not present.
- `reels/*.csv` regenerate byte-identical from `generate_reels.py`.
- Reel composition matches the design notes exactly: BR0 lows-heavy W=2/S=5 per reel, FR0
  wet-left/dry-right (W = 4/4/4/3/0, no scatters), FRWCAP W=16 + H1 boost, ASC with the
  reel-2 step-3 scatter run that makes a 6-scatter force succeed.

**Engine correctness**

- 43 Python tests and 36 Go tests pass.
- Go vs Python on buy_corvus, same config, 20k books each:
  KS distance **0.0062** against a 0.0136 critical value — statistically indistinguishable.
  Means 231.10 vs 229.16, completion 83.67% vs 83.77%, mean roam 4.89 vs 4.89, and the roam
  depth histogram matches bucket by bucket.
- `schema_diff.py`: Go and Python event tapes are structurally identical, key for key.
- Roam depth never shows a depth of 1 — `min_roam_spins = 2` is doing its job, on both engines.

**Pool and artifact integrity**

- LUT ↔ books ↔ segmented LUT: 1,000,000 rows, ids unique and contiguous from 0, all raw
  weights 1, **zero** payout mismatches and **zero** segmented-sum mismatches over 200k books.
- **No book pays above its published ceiling in any mode.**
- `publish_go.py` verification passes: index.json, force.json and config.json name the same
  six modes, every sha256 matches its file, no stale optimized LUT.
- `config_fe_starwake.json` carries the real names (Starwake / Uptown Games), not the
  scaffold defaults.

**Economy**

    mode            cost     RTP    std   zero%   hit%  >=1x%  med/c    max     pub  >pub    P(cap)      1 in  cap/stake
    base             1.0  0.9665  24.35   70.75  29.25  12.43  0.000  25,000  25,000    0  8.00e-07 1,250,000     0.0200
    ante_starfall    1.5  0.9665  22.07   65.67  34.33   7.87  0.000  25,000  25,000    0  1.50e-06   666,667     0.0250
    buy_corvus     240.0  0.9665   1.55    0.00 100.00  27.19  0.271  10,000  10,000    0  4.53e-07 2,207,561     0.0000
    buy_ursa       268.0  0.9662   2.13    0.00 100.00  26.78  0.327  25,000  25,000    0  2.79e-04     3,589     0.0260
    buy_draco      520.0  0.9650   2.32    0.00 100.00  26.43  0.198  25,000  25,000    0  1.56e-03       642     0.0749
    buy_mystery    563.0  0.9665   2.24    0.00 100.00  17.08  0.453  25,000  25,000    0  9.01e-04     1,110     0.0400

- RTP band 0.9650–0.9665, **spread 0.151%** against a 0.5% limit; every mode ≤ the 0.9670 ceiling.
- Zero-pay **0.00%** on all four buys.
- Win-range holes: base 1.13x, ante 1.07x, corvus 1.01x, ursa 1.02x, draco 1.01x, mystery
  1.00x — **the Draco cliff is dead and no new gap has opened**. Every surviving hole sits
  above 18,000x, i.e. tail sparsity, not structure.
- **buy_corvus's 10,000x is legally obtainable**: P = 4.53e-07 = 1 in 2.21M, clearing the
  "typically better than 1 in 10,000,000" gate by 4.5x. The `maxwin_boost` scaling works, and
  it works better on this pool than the 1.50e-07 recorded on the shipped one.
- **The cap-share ladder is delivered exactly as designed**, and the identity
  `slice_rtp = rate * cap / cost` holds to four significant figures on every mode:

      corvus 0.0000 < base 0.0200 < ante 0.0250 < ursa 0.0260 < mystery 0.0400 < draco 0.0749

  draco/ursa = **2.88x**, far past the 1.94x price-ratio break-even, so "draco is the cap play"
  holds. The worry that organic ascendant cap books would drift mystery's delivered share above
  its 0.040 target did **not** materialise — the wincap fence absorbs them and lands on 0.0400.
- **buy_mystery's delivered mix is its published mix**, which is the compliance requirement:

      delivered  corvus 35.144  ursa 29.622  draco 25.104  ascendant 10.061  (+0.069 wincap)
      published  corvus 35.161  ursa 29.635  draco 25.115  ascendant 10.055

  Ascendant carries **46.7% of payback on 10.1% of rolls** — the Rage Bait shape it was
  modelled on. Tier means are correctly ordered: 221 / 249 / 483 / 2,527x.
- Base fence rates land exactly on their `hr` hints: corvus 1 in 220, ursa 1 in 600, draco
  1 in 1,900, and the payback splits reproduce the configured RTP splits to 3 decimal places.
- Base: bust 70.75% (market 70–83%), win frequency ≥1x 12.43% (market norm ~7.4%), std 24.35
  against the <50 gate. Share of RTP above 100x is 0.224 on this solve, below the 0.252–0.271
  previously recorded — the base-boost product call parked in CLAUDE.md is still the only
  lever that moves it.

---

## Recommended order of work

1. **Answer the 10M-event question with the RGS team.** It gates the sim count for the retune
   below, and it is free to ask.
2. **Pin buy_mystery's p5k** with an ascendant scaling entry, re-run the optimizer for that
   one mode, and confirm 2-Star is back to 1 failed class. Add p5k to whatever is checked on
   every pool.
3. Decide draco's published RTP: converge it onto 0.9665 or publish 0.9650.
4. Correct the ladder-obtainability table in `game_config.py` and the stale docstrings in
   `game_optimization.py`; make `check_risk_gates.py` read costs from the config.
5. Add the two missing Python tests (`max_symbol`, `check_repeat` zero-win redraw).

Nothing here changes the design. Items 2 and 3 are optimizer-only work; the rest is text and
tests.
