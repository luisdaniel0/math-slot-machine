# Killswitch — Reference Teardown

*A ground-truth study of Killswitch (Terminal Games, © 2026) — the reference game for the
Fighter slot concept. Built from the in-game rules screens plus streamer bonus footage.
Purpose: capture exactly how it works so we can decide what to copy, what to change, and what
our own math must account for. Confidence levels are flagged — **[CONFIRMED]** = read directly
from the rules text or clearly visible in footage; **[INFERRED]** = reconstructed and worth
verifying with slow-mo before we rely on it.*

---

## 1. Core structure [CONFIRMED]

- **5 reels × 5 rows** (5×5 grid).
- **19 fixed paylines**, pay **left-to-right**, **3+ matching** symbols.
- **Max win 50,000x**.
- **RTP 96.01%** — identical across *all* modes (base + every buy). Same signature as our
  "RTP constant across modes" plan.
- Provider: Terminal Games (same studio ecosystem as our reference — the © 2026 Terminal Games
  legal footer matches Stake Engine native titles).

## 2. Paytable shape [CONFIRMED]

Top-heavy, small absolute numbers (the multiplier mechanic does the heavy lifting, not base pays):

| Symbol | 3 / 4 / 5 |
|--------|-----------|
| Wolf (top enemy) | — / — / **5.00x** |
| Gold beast | 1.00 / 2.50 / 5.00 |
| Red shark | 0.75 / 1.50 / 3.00 |
| Grenade | 0.50 / 1.00 / 2.00 |
| Pistol | 0.50 / 0.75 / 1.50 |
| A | 0.10 / 0.30 / 0.50 |
| K / Q / J | 0.10 / 0.30 / 0.50 |

- Top 5-kind is only **5.00x**. Everything interesting comes from wild multipliers, not base pays.
- No wild pay row — the **wild only exists as a converted enemy** (see §3). It substitutes; it
  doesn't have its own line-pay value.
- **Takeaway for us:** keep base pays deliberately low/flat so the multiplier mechanic is the
  star. Our Keybearer paytable (top 5-kind = 80x) is far punchier at base — if we adopt a
  Killswitch-style multiplier engine, we should flatten the base paytable or we'll blow the RTP
  budget.

## 3. The conversion mechanic — enemies → multiplier wilds [CONFIRMED]

The core loop, and the thing our Fighter concept reskins:

1. Symbols land. Some are **Enemy** symbols (two footprints seen in the wild):
   - **Small enemy (1×1)** → converts to a wild worth **+10x** (base game).
   - **2×2 enemy** → converts via a **4-rocket-hit combo** to a wild worth **+100x** (base game).
2. **Before wins are evaluated**, "rockets" hit the enemies and **convert them into Wilds**, each
   wild carrying its multiplier value.
3. Lines then evaluate with the wilds substituting.

**Bonus values are higher than base** — the Bonus-mode text says the *same* small=+10x / 2×2=+100x,
but streamer bonus footage showed wilds valued 100x, 110x, 210x, 220x, meaning in the feature the
multipliers **accumulate/carry** rather than resetting to the flat +10/+100 each spin (see §5).

## 4. How a line actually pays — SUM, not multiply [CONFIRMED]

Rules text, verbatim: *"Wild multipliers on a winning line are added together before being applied
to that line win."*

```
line win = base_symbol_pay(combo) × (SUM of wild multipliers the line passes through) × line_bet
```

- Two wilds on a line = `100 + 110 = 210`, **never** `100 × 110`.
- This settles the Fighter doc §7 open decision **by precedent**: Killswitch is **additive**.
  If we go **multiplicative** instead, that's our differentiator — but it's a much bigger
  volatility lever and forces a lower base hit rate to stay in RTP budget. (Decision still ours;
  precedent is "sum".)

## 5. The multiplier engine — RUNNING COUNTER + per-spin stamping [RESOLVED]

The single most important mechanic to get right, and the answer is subtle: it is **neither** a pure
global scalar (Keybearer Vault) **nor** sticky per-tile accumulation. It's a hybrid.

**The model (resolved by the arithmetic-sequence proof below):**

1. **One running multiplier counter.** Carries across the whole feature, **never resets**. This is
   the Vault-like part — the persistent state is a *single number*, not a board.
2. **Reels drop fresh each spin — wilds are NOT position-locked / NOT sticky.** (Earlier "sticky
   tile" inference was WRONG; corrected by the evidence below.)
3. **Each enemy KO bumps the counter:** +10 (small 1×1), +100 (2×2). [CONFIRMED — matches rules text]
4. **Each KO'd enemy becomes a wild STAMPED with the counter's value at that instant.** So the wilds
   on any board are just the counter's climb *during that spin*, snapshotted onto tiles.
5. **Payout is POSITIONAL:** each winning line sums only the stamped wild values it physically
   crosses, then that sum multiplies the line's base pay. [CONFIRMED by rules text — "wild multipliers
   on a winning line are added together… applied to that line win."]
6. **Corner badge = the counter's current value** (= the last/highest stamp). See corner bullet below.

**THE PROOF — every observed board is a clean +10/+100 arithmetic ladder:**

| Board | Values | Gaps |
|-------|--------|------|
| Mystery early | 100, 110, 210, 220 | +10, +100, +10 |
| $0.20 spin 3 | 50, 60, 70, 80 | +10, +10, +10 |
| Spin 2 | 230, 330, 430, 440 | +100, +100, +10 |
| Spin 3 | 450, 550, 560, 570 | +100, +10, +10 |
| Spin 7 | 220, 320, 330, 340 | +100, +10, +10 |
| Max win | 670, 770, 780, 790, 890 | +100, +10, +10, +100 |

Six independent boards, all clean sequences. Impossible by coincidence under independent per-tile
compounding → the values are stamped in KO order from one carried-over counter. (Worked example:
spin 7 followed spin 5's counter of ~210 → 210+10=220, +100=320, +10=330, +10=340 → corner 340.)

**Why this matters for us — it dissolves the global-vs-positional dilemma:** Killswitch keeps a
**single scalar** (cheap to track, like the Vault) but **applies it positionally** (spiky feel). We
do NOT need to persist a 5×5 grid across spins — just one counter + this spin's enemy landings.

- **Caveat:** never captured the decisive "same tile, same cell, two consecutive spins" shot, but the
  six-board arithmetic evidence is far stronger than one positional glance. Treat as resolved.

- **The corner badge (the pink `Nx` HUD number) = the running COUNTER's current value** (equivalently,
  the highest/last stamp on the board). [RESOLVED] It only climbs during the feature. It is NOT a sum
  and NOT applied to wins (per-line stamped sum is the real math). **Design consequence: the badge is
  hype decoration** — it advertises the counter but does NOT represent the player's actual winning
  power, because payout depends on *this spin's* enemy landings vs. the paylines. Counter at `340x`
  but only two enemies land in bad spots → small win → the mechanical source of the "robbed" feeling
  (§14).

**What this means for our SECOND decision (the multiplier engine):** the false dilemma was
"global scalar OR positional." Killswitch shows a **third option that is both**: a single persistent
counter (cheap, Vault-like) *expressed positionally* via per-spin stamped wilds (spiky). Our real
choice is now:
- **Pure global Vault** (Keybearer-style): counter multiplies *every* line uniformly. Flattest,
  no "robbed" feeling, simplest.
- **Counter + positional stamping** (Killswitch-style): single counter, but only stamped tiles on a
  line count. Spiky, geometry variance, and the "robbed" feeling is inherent (a design lever, or a
  thing to defuse with a finisher — see §14).

## 6. Evaluation order — matters for our engine [CONFIRMED]

Observed directly: a Mystery-buy spin landed 5 scatters **and** paying lines; the board **paid the
line wins first, then the scatters triggered the bonus**. So within one spin:

1. Symbols land (including enemies **and** scatters).
2. Rockets convert enemies → multiplier wilds.
3. **Lines evaluate and pay** (base-spin wins are banked).
4. **Then** the scatter count resolves → bonus entry.

Steps 3 and 4 are **both** honored in the same spin — scatter trigger does not cancel the line pay.
Our engine must evaluate line wins on the trigger spin *and* enter the feature, not one or the other.

## 7. Bonus tiers — density is the ONLY lever [CONFIRMED]

Entry by scatter count (scatter = graffiti "Bonus" symbol):

| Trigger | Tier | Spins | What changes |
|---------|------|-------|--------------|
| 3 scatters | Bonus | 8 | Natural enemy density |
| 4 scatters | Super Bonus | 8 | **≥2 enemies guaranteed in view per spin** |
| 5 scatters | Epic Bonus | 8 | **≥4 enemies guaranteed in view per spin** |

- **All three tiers: 8 spins, same mechanic, same 50,000x ceiling.** The *only* difference between
  tiers is **guaranteed enemy density per spin.** More enemies → more conversions → the pool
  climbs faster/higher → bigger expected total. No longer features, no bigger base multipliers,
  no higher cap.
- Retriggers exist: "Bonus symbols award extra spins" during the feature.
- **Contrast with Keybearer:** our Mega tier scales the *starting Vault value*. Killswitch never
  touches the multiplier ceiling per tier — it only changes how many enemies show up. Cleaner,
  more legible tiering. Worth considering for our game: **density lever vs. starting-value lever.**

## 8. Bet modes / side bets [CONFIRMED]

Five optional modes beyond the base game (prices are the streamer's bet-scaled display, ratios are
what matter):

| Mode | Type | What it does |
|------|------|--------------|
| **Ante** | Toggle (+bet) | 5x bonus-trigger chance; raises total bet while active |
| **Max or Zero** | High-risk | One shot at the 50,000x cap or walk away with nothing (pure variance, no bonus spins) |
| **Bonus** | Buy | 8 spins, base rocket-wild setup |
| **Super** | Buy | 8 spins, guaranteed ≥2 enemies/spin |
| **Mystery** | Buy | Random roll — can land you in Epic |

- **Mystery** is a fun template: a single buy that randomly resolves to a tier (incl. the top Epic).
  Its rules note "In Epic, when Enemies appear, there are at least 4 in view."
- **Max or Zero** is a distinctive all-or-nothing mode with no equivalent in our current plan.

## 9. Celebration UI — FOUR distinct layers [CONFIRMED]

1. **Per-spin big-win animation** — character (fighter) + wolf combined pose over the spin's win
   number (e.g. "2,061.00", "4,716.00"). Fires on a big *single-spin* result mid-feature.
2. **Mid-feature named win-splash** — e.g. **"TOTAL CHAOS"** on a big win (themed vocabulary, not
   generic "Big/Mega Win"). **Repeatable** — fired twice in one feature (111.00 and 191.00), so it's
   a threshold trigger, not a one-time event. Real precedent for the Fighter doc §5 tiered KO
   celebrations (HIT → COMBO → K.O. → FLAWLESS VICTORY → FATALITY).
3. **MAX WIN splash (reserved)** — a yellow shattering "MAX WIN" burst, fired only when the 50,000x
   cap is hit. Separate, top-tier moment.
4. **End-of-feature "TOTAL WIN" card** — a branded summary using the wolf-crest logo as the frame,
   showing the cumulative total (footage: 13,007.10 on a $3 bet ≈ 4,335x base Bonus; **60,000.00 =
   50,000x max win** on a $1.20 Mystery run).

Also: the **WIN display runs as a cumulative feature total**, not per-spin — it climbs across all 8
spins and the balance stays frozen until the feature resolves.

## 10. What Killswitch does NOT have (our differentiation whitespace) [CONFIRMED]

- **No 3×3 enemy tier** — 2×2 is the ceiling. Our Mega-Boss (3×3, 9-hit) is genuinely new ground.
- **No finisher/super meter.**
- **No fighting-genre theming** — melee choreography + legible 1-on-1 strikes is a real UX edge
  over Killswitch's busy "enemies + guns + grenades + floating numbers + rocket FX" board.
- **No multiplicative option** — everything sums.

## 11. Math-build checklist — things our sim MUST account for

Direct implications for our Python math model, distilled from the above:

1. **Flatten base pays.** Top 5-kind should be low (Killswitch = 5.00x). The multiplier engine — not
   symbol pays — carries the RTP. Our current Keybearer paytable (80x top) is too hot for this.
2. **Decide the multiplier engine early** (§5). State is cheap either way — a single running counter
   (like the Vault). The choice is *application*: pure-global (counter × every line) vs. positional
   stamping (only stamped tiles on a line count). Positional needs us to simulate *where* enemies land
   vs. the 19/20 lines each spin; global reuses Keybearer's Vault wholesale.
3. **Decide SUM vs MULTIPLY** (§4 / Fighter §7). Sum = safer/flatter (precedent). Multiply = our
   differentiator but forces lower base hit-rate.
4. **Enemy footprint modeling.** 1×1 vs 2×2 (and our new 3×3) occupy multiple cells — the sim needs
   real 2D placement, not just per-reel symbol draws, because footprint + geometry drives which
   lines benefit. This is more than the standard lines engine does.
5. **Evaluation order** (§6): pay base-spin lines AND resolve scatter trigger in the same spin.
6. **Tier = density lever** (§7): the cleanest way to model Super/Epic is "force N enemies into
   view," not "raise the multiplier." Consider adopting this over Keybearer's starting-value lever.
7. **Persistence = ONE counter, not a board** (§5): a single scalar carries across spins (+10/+100
   per KO, never resets). Wilds are NOT sticky/position-locked — they're re-stamped fresh each spin
   from the carried counter. Reset the counter only at feature end.
8. **Two celebration layers** (§9): mid-feature named splashes on thresholds + one branded end card.
   Cheap to build, high virality — bake the thresholds into the math output so the frontend can
   fire them deterministically.
9. **Retriggers via scatters during the feature** (§7) — extra spins, needs a branching model that
   stays bounded (we already hit this exact problem in Keybearer; reuse those lessons).
10. **RTP constant across all modes** (§1) — buys and base all land at the same RTP; the optimizer
    re-weights per mode to the same target.

## 12. Open questions to close (needs more footage)

- ~~Corner-badge semantics~~ **RESOLVED (§5):** corner = the running counter's current value.
- ~~Exact accumulation formula~~ **RESOLVED (§5, §13b):** one running counter, +10 per small KO / +100
  per 2×2 KO, never resets; each wild stamped with the counter's value at its KO moment.
- ~~Sticky tiles vs. value-only carry~~ **RESOLVED (§5):** NOT sticky. Wilds re-drop fresh each spin;
  only the single counter persists. Proven by six boards all forming clean +10/+100 arithmetic ladders.
- **Small 1×1 enemy conversion in isolation** — confirm base +10 stamp (essentially settled by the
  50/60/70/80 ladder, which is all +10 small-enemy stamps).
- **Super/Epic pool ceilings in practice** — how high does the pool actually get at ≥2 / ≥4 density
  vs. base Bonus's ~350x? (Calibrates our own tier spacing.)
- **Max or Zero** internal structure — single spin? capped attempts?
- **Mid-feature 5-scatter event** (§13): tier-upgrade to Epic vs. retrigger (extra spins)? Footage
  couldn't disambiguate.

## 13. Mystery-spin teardown — extra findings

From a streamer clip: player **bought Mystery**, and on one spin the board landed **5 scatters
(reels 1–5)** while also converting enemies and paying lines. Notes:

- **Mid-bonus, not base game.** The wild values (100x / 110x / 210x / 220x) are high because the
  feature had already been accumulating — this is *in-feature* stacking, confirming §5, not a
  base-spin anomaly. Do not treat these numbers as base-game conversion values.
- **Mid-feature scatters are their own event.** Dropping 5 scatters *during* the bonus triggered
  something (Epic upgrade or a spin retrigger — unresolved), and it fired **after** the line wins
  paid. Evaluation order (§6) holds mid-feature too: convert → pay lines → scatter event.
- **Several 2×2 enemies coexist on one 5×5 board.** The high-density frame carried multiple large
  green ogres + a gold wolf + grenades + 5 scatters simultaneously — big footprints stack up. This
  directly constrains our **3×3 Mega-Boss** (9 of 25 cells): we must decide its collision/coexistence
  rules with other enemies.
- **Line-win figures observed:** 25.20 / 60.00 / 186.00 / 558.00 / 954.00 (on a $1.20 bet). Treat
  the climbing central figure as the **running tally animating**, not five independent line wins —
  don't try to sum them.

### 13a. Spin-by-spin (rest of the Mystery bonus) — new findings

- **Corner badge resolved here** (see §5): spin with wilds 230/330/430/440 showed corner = **440**
  (= highest, not sum). This footage is what closed the question.
- **Enemy and wild are DISTINCT sprites.** Pre-conversion enemy = **green glowing ogre** (2×2) /
  colored small beasts; post-conversion wild = **metallic red-eyed wolf head + multiplier badge**.
  A spin caught both states coexisting (unconverted green ogres left, converted wolves right). This
  is exactly our Fighter "enemy → KO → multiplier wild" transformation — confirms we want **two art
  states per enemy** with a visible conversion beat between them.
- **Wild values accumulate fast:** 100–220 range (early) → 230–450 range (spins 2–3), at +100
  intervals → sticky-tile compounding (§5).
- **THREE celebration layers total:**
  1. Per-spin big-win with character animation (fighter + wolf combined pose, e.g. "2,061.00").
  2. Mid-feature named threshold splash ("TOTAL CHAOS").
  3. Branded feature-end "TOTAL WIN" card.
- **Running WIN across this bonus:** ~1,783 (spin 2 start) → 2,061 (spin 2 celebrated) → 3,844
  (spin 3) on a $1.20 bet — climbing steeply, feature still going.

### 13b. The MAX WIN climax — how the cap is actually reached

This Mystery run hit the **50,000x max win** on spin **5/8**. The frames show exactly how:

- **Max win = board saturation.** Density escalated: spin 3 wilds at 450/550/570; spin 5 the board
  floods with green ogres → converts to a board that is *almost entirely* wolf wilds at
  **670 / 770 / 780 / 790 / 890x**. Every one of the 19 lines now crosses a stack of huge wilds →
  summed multipliers are astronomical → cap. Line wins of 9,703.68 and 9,960.00 fired on that spin.
- **KEY INSIGHT — the positional problem inverts with density.** Sparse wilds = "robbed" feeling
  (§14); saturated board = max win. The game lives on that gradient. This is the core volatility
  dial for anyone cloning the mechanic.
- **+10 / +100 accumulation CONFIRMED.** Spin-5 values 670→770 (**+100**, a 2×2 hit) sitting next to
  780→790 (**+10**, a small hit) prove both increment sizes coexist on sticky tiles. Closes §5/§12.
- **Corner badge climbed 570 → 890** = running max, still monotonic (§5). Confirmed again.
- **Cap is a HARD ceiling that ends the feature early.** MAX WIN fired on spin 5/8 → spins 6–8 never
  played. Final = **60,000.00 = 50,000x × $1.20** exactly (the mid-count 51,439.68 was just the
  animation resolving up to the capped total). Same `wincap_triggered → stop` logic we already built
  in Keybearer.
- **FOURTH celebration layer:** a reserved yellow shattering **"MAX WIN"** splash, distinct from the
  three in §9. Full ladder: per-spin animation → named threshold splash ("TOTAL CHAOS") → **MAX WIN**
  (reserved) → branded "TOTAL WIN" end card.

## 14. How we make it BETTER (the goal — not a reskin)

These are improvements, each traceable to a weakness visible in the footage. Success condition =
streamer adoption, so every edge is judged by "does this make it more legible / more shareable / less
frustrating to watch."

| Killswitch weakness (observed) | Our better version |
|---|---|
| **Board chaos** — simultaneous rockets, 4+ floating multipliers, 5 climbing win numbers, overlapping FX. Unparseable even on close study. | **Legible sequential KOs.** One fighter vs one enemy, staged in order. The viewer reads every hit. Biggest edge, and it's a pacing/choreography choice — costs no extra math. |
| **Positional "wasted multiplier"** — a 220x wild no payline crosses pays nothing; player feels robbed. The #1 frustration of positional wilds. | A **finisher / collect step** that sweeps live multipliers onto the win, OR a **global meter**, so a big number *always counts*. Kills the "robbed" feeling. |
| **Tiers are samey** — Bonus/Super/Epic are all 8 spins, only enemy density differs. No structural variety. | **Per-tier identity.** The **3×3 Mega-Boss exists only in the top tier** (and/or a finisher unlocks there). Escalation you can *see*, not just "more enemies." |
| **Illegible corner pool** — we couldn't decode what the badge represents even after close study. | **Named, labeled meter** (Combo / Vault ladder). Viewer reads "one KO from FATALITY" instantly. Legibility = shareability. |
| **Zero player agency** — pure watch-the-numbers. | Optional **EV-neutral choice** (target selection / finisher timing / variance fork). Agency = engagement, and it's certifiable if EV-neutral (see [[vaultbound-concept]]). |

**Through-line:** Killswitch's two exploitable weaknesses are **legibility** and the **"robbed"
feeling from positional multipliers**. Both fixes independently make the game more streamable, which
is exactly our win condition. The theme (melee, 1-on-1) is what *enables* the legibility fix — it's
not just cosmetic.

---

*Study status: effectively complete for design purposes. Core structure, paytable, conversion
values, sum-vs-multiply, positional multiplier, evaluation order, three-tier density model, all
five bet modes, and both celebration layers are captured. Remaining items in §12 are refinements,
not blockers.*
