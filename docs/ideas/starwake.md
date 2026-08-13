# STARWAKE (working title — alt: *Firmament* / *Empyrean* / *Starborn*)

> Flagship-candidate Stake Engine slot. Celestial / star-atlas theme. A high-vol
> 5×4 lines game whose bonus is about **drawing a constellation in the sky** — fill
> the star pattern and the mythical beast it depicts **wakes up and roams the reels**,
> paying as it goes. Two signature ideas fused: a Hex-Bloom-style *fill-the-shape*
> collection, and a NetEnt-style *walking wild* — earned, not handed to you.
> "Starwake" = you *wake* the beast, and a *wake* is the trail a moving thing leaves.

## Problem Statement
**How might we ship a high-volatility 5×4 payline slot with one or two genuinely
distinctive mechanics — in a market where wilds are almost all per-spin — that stays
*fun to watch* in the base game (not the usual dry high-vol grind) and gives the
player a meaningful choice about the kind of bonus they get, while keeping the math
tractable enough to actually converge and clear?**

## Recommended Direction
The bonus **is** the game, and the base game feeds it. Every idea is made of the same
material — *wins light stars, stars summon beasts* — top to bottom, so nothing feels
bolted on.

**Base game — star scatters (standard on purpose).** The scatter **is a star**, and
the count grades the tier: **3 stars → Corvus, 4 → Ursa, 5 → Draco.** *"Enough stars
in the sky wake a beast; more stars wake a greater one."* The tier is visibly earned
on the board, the 4th/5th star is a built-in anticipation beat (frontend scatter
slowdown machinery comes free), and tier rarity is tuned directly on the reel strips —
decoupled from the paytable. This maps exactly onto the proven Keybearer slice
architecture (3/4/5 scatters → tier via `scatter_triggers` forcing), so the trigger
costs zero invention. *(A no-scatter per-spin win meter — Hex Bloom's base hook — was
adopted and then reverted: meters work in cascade/cluster games where every spin
chains many symbol-wins, but on a non-cascading lines game the meter would sit dead
on ~2/3 of spins, and the SDK's forcing + frontend anticipation are scatter-native.
Novelty budget stays in the feature, not the doorway.)*

**Bonus — charge → bloom → roam.**
1. **Dealt / chosen.** You get a named constellation (from the meter tier naturally,
   or by buying a specific tier). It's drawn onto the grid as dim, empty star outlines
   sitting on specific cells — a dot-to-dot waiting to be filled.
2. **Charge.** Over a fixed run of free spins, **star symbols land only on that
   constellation's live cells** and light them up. Each lit star **immediately becomes
   a permanent sticky wild** for the rest of the feature — so partial progress pays
   real money, on every remaining spin. *The drawing pays you while you draw it.*
3. **Bloom.** Light every star → the constellation is complete → **the beast it depicts
   wakes up** as an oversized block wild (2×2 / 2×3 / 3×3 by tier).
4. **Roam.** The beast walks one column per spin and, instead of exiting, **wraps around
   the board** (rising again on the far side, drifting vertically each lap so it hits
   different paylines). Its **multiplier climbs every spin it survives.** A guaranteed
   minimum roam window means even a last-spin completion still pays.

**Why this is differentiated:** a wild you *build*, that *persists*, that *moves*, and
whose multiplier *climbs* — against a market of per-spin wilds. Two clip moments per
bonus: the awakening spike, then the escalating roam.

### The one mechanic that does double duty (the whole idea)
A lit star is **both** progress toward the beast **and** a wild that pays right now.
That's what converts the bonus from an all-or-nothing gamble into a smooth escalation
with a jackpot top — and it's what makes a *big* constellation worth chasing even
though you'll rarely complete it (see "two different games" below).

## Core spec
- **Board:** 5×4, 20 paylines, high volatility. Top-heavy paytable. Wild substitutes
  for paying symbols; **pays 5-kind only** (block wild spans 2–3 reels so it can't
  self-pay a short wild line over a longer real-symbol line). *(Wild-pay rule inherited
  from the Keybearer/Penthouse lineage; confirm in build.)*
- **RTP / wincap:** target **96.70% displayed** — converge each mode to ~0.9665–0.9669
  (≤ cap always; displays as 96.7%). Native games all run at the cap and players compare
  displayed RTP, so 0.96-with-buffer leaves visible value on the shelf (decided after
  reviewing a live game's info screen: every mode at exactly 96.70%). Wincap **25,000×**,
  reachable
  in every mode but overwhelmingly concentrated in the Draco (greedy) tier. Base can
  reach it too (astronomically rare — "rolled Draco + completed + completed early"),
  so base players can still dream.
- **Scatter = the star symbol.** 3/4/5 stars trigger Corvus/Ursa/Draco. Star density
  on the strips is the tier-rarity dial (targets TBD in tuning; Keybearer's 3/4/5-key
  rates — ~1/150, ~1/2000, ~1/100k — are a reasonable starting shape).
- **The star-landing rule is load-bearing (the critical balance point):** stars must
  drop at a **constant global rate per spin (λ)**, *not* a fixed per-cell probability.
  Per-cell probability makes completion time ∝ H_K (logarithmic in star count K) → the
  tier ladder collapses to ~1.5× and the choice becomes fake. Constant λ makes
  completion time ∝ K·H_K → a real ~4× ladder. **Implement as: stars come off the reel
  strips at fixed density (constant λ for free); a star landing on a dead cell flies to
  an unlit constellation cell** (constant λ, no wasted stars, looks like the
  constellation pulling stars into itself).
- **Multiplier lives on the beast** (attached, climbs per roam spin) — *not* a global
  meter. Distinguishes it from the Keybearer/Penthouse Vault lineage.

### Tiers (the volatility ladder — real constellations, public-domain)
| Tier | Constellation | Stars | Beast wild | Character |
|---|---|---|---|---|
| Safe | **Corvus** (the crow) | 4 | 2×2 | ~near-certain completion, modest beast, long roam. A reliable beast-hunt. |
| Balanced | **Ursa Major** (the great bear / Big Dipper) | 7 | 2×3 | ~coin-flip completion. Maximum tension. **The one people stream.** |
| Greedy | **Draco** (the dragon) | 11 | 3×3 | ~rarely completes — but you light ~8 of 11 anyway, so **~40% of the board floods with sticky wilds** and pays hard on its own, with a lottery ticket on a giant beast. |

*Star counts chosen to match the real sky: Corvus = 4 (exact), Big Dipper = 7 (exact),
Draco simplified from ~14 to 11. Shapes are stylized and snapped to grid cells —
recognizable, not astronomically accurate.*

**The tiers are two different games, by construction** (this is the design working):
- **Small** = few wilds, big climbing multiplier — you came for the beast, you get it.
- **Large** = you'll rarely wake the beast, but the board becomes a *wild carpet* that
  pays on its own — the journey pays even though the destination almost never arrives.
Neither is a trap; they're comparable value, genuinely different experiences. This is
the thing DOA2's three bonus modes get right — here it falls out structurally.

### Bet modes (6)
| Mode | Cost | What it is |
|---|---|---|
| `base` | 1× | 3/4/5 star scatters trigger the tier. Landing the 5th star = pure hype. |
| `ante_starfall` | ~1.5–3× | **"Starfall"** — denser star scatters on ante strips: more triggers AND a richer tier mix (4th/5th star proportionally likelier). One knob (scatter density) buys both. Honest label: *lower* volatility (more frequent bonuses = smoother). Partially answers the reopened base-boost question for players who opt in. |
| `buy_mystery_spin` | **150×** | **"One Wake"** — ONE spin, the constellation dealt already complete and the beast already roaming; *which* beast is the mystery (corvus / ursa / draco, 15/25/60). Replaced `buy_corvus` Aug 13 2026, because cost-adjusted volatility read corvus **1.85** against ursa **1.88** — the two cheapest products were the same product at two prices. The corvus TIER is untouched; only the buy is gone. **The one mode that does not publish 25,000×:** one spin with one 2×2 tops out at a measured 19,778× at every roam density, so it publishes an honest **15,000×** — which at a 150× ticket is 100× cost, better than Miko Spin's 40× and Rage Spins' 71×. Market shape: Miko Spin (250×, one spin, guaranteed 2×2) and Rage Spins (350×, single powerful spin). |
| `buy_ursa` | ~mid | Pay to guarantee the balanced tier — the coin-flip bonus. |
| `buy_draco` | ~high | Pay to guarantee the greedy tier. **This is where the 25,000× lives.** |
| `buy_mystery` | **~500× (target)** | **"Let the Sky Decide"** — weighted random constellation. TARGET COST 500× (market-standard mystery price — Rage Bait/C&C/Captain Death all 500×; fixes the ladder so mystery is the "premium random shot" between guaranteed-Ursa 283× and guaranteed-Draco 651×). Reach 500× by weighting the mix toward Draco (cost = avg_win/rtp, an output). Probabilities MUST be displayed as the ACTUAL post-opt mix per compliance. Math-cheap: weighted mix over the three tier books, no new feature code. |

*Buy prices are **outputs, not inputs**: cost = avg win ÷ RTP. Design the tier, measure
its average, the price falls out (Keybearer's buy moved 520 → 390 purely because the
feature changed). The ladder is a choice; the rungs are measurements.*

### Symbols — one star atlas
- **Scatter = Star.** Triggers the bonus by count (3/4/5); inside the feature the same
  star is what lands on constellation cells and lights them. One symbol, one meaning,
  both games.
- **Wild:** the block/beast wild + the sticky lit-stars. (Same symbol family; the star
  is the wild in miniature.)
- **Highs H1–H4:** four more real constellation beasts — Leo (lion), Cygnus (swan),
  Aquila (eagle), Lupus (wolf).
- **Lows L1–L5:** card ranks rendered as constellation line-art (cheap, forgettable by
  design, still coherent).

## Key Assumptions to Validate
- [ ] **Constant-λ star landing produces the intended completion ladder on real reels.**
      *Target (analytic, λ≈1.5/spin over 10 spins): Corvus ~95%, Ursa ~44%, Draco ~2%.*
      *Test:* sim the feature per tier; confirm the ladder holds once real strips +
      paylines replace the uniform-landing assumption. These are tuning targets, not
      results.
- [ ] **The sticky-wild carpet doesn't blow the RTP ceiling.** Draco lights ~8 of 20
      cells = ~40% of the board wild. *Test:* measure feature RTP per tier; expect Draco
      to fight the cap hardest — λ, feature length, and beast-multiplier scale are the
      dials.
- [ ] **Star-scatter density on the strips lands the intended tier rates** (Corvus
      common → Draco rare) without flooding the feature, where the same star symbol
      must land at constant λ. One symbol serving two roles across two contexts =
      per-context reel strips (BR vs FR), same as Keybearer's key. *Test:* measure
      3/4/5-scatter rates off the base strips; tune independently of FR star density.
- [ ] **Beast walk + wrap + climb reaches 25,000× in some mode AND holds RTP ≤ 0.967.**
      *Test:* generate → optimize; confirm convergence + wincap slice reachable. (Per the
      house gotcha: convergence failure = fix strips/λ/multiplier, not the opt config —
      the optimizer can't invent a tail that isn't in the raw outcomes.)
- [ ] **The base game is watchable enough as a scatter hunt.** With the meter reverted,
      base is a standard high-vol scatter hunt again — genre-normal (DOA2) but dry by
      modern standards. Scatter anticipation (4th/5th star slowdown) may be enough;
      if playtests say it isn't, the parked base-boost ideas come back (see Open
      Questions). *Test:* fun-mode playtest; judge, don't assume.
- [ ] **Fixed-length feature still delivers high vol.** The tail must come from
      *completion-time × tier* (finish early with a big beast = jackpot), not from
      feature length. *Test:* measure m2m per mode; Keybearer's fixed feature fell to
      ~2.2 — if we land there too, fatten the beast multiplier / widen the tier spread,
      do NOT re-lengthen the feature.
- [ ] **All six modes converge within the 0.5% RTP band** (approval gate: every mode
      within 0.5% of every other) at the ~0.9665–0.9669 target. *Test:*
      production-sim-count optimization runs per mode; Keybearer showed the base RTP
      dial is sim-count dependent — tune at 1e6. Six convergences is the workload we
      signed up for by picking the full lineup; ante + mystery are the cheap ones
      (reused feature books, different trigger density / mix weights).
- [ ] **Tail metrics pass the 2★ risk limits** (CVaR ≤ 700, ETL(>40× cost) ≤ 0.8,
      P(≥5000×)/P(≥10000×) caps — exact thresholds to be re-read from the live review
      sheet; the published table's ordering looks like a typo). The carpet + climbing
      ladder should naturally spread RTP across intermediate wins (no gaps), which is
      what these metrics reward. *Test:* read them off the PAR sheet at production count.
- [ ] **Base hit rate ≥ 1 in 20 non-zero wins** (approval gate; ~90% non-paying = 
      rejection grounds). Top-heavy paytable must keep enough small-win texture.
      *Test:* hit-rate table from the first run.

## MVP Scope
**Goal: prove the charge→bloom→roam bonus feels good and the math converges — cheaply.**

**In:**
- Fork `games/0_0_lines` → new game id (`starwake`); 5×4 / 20 lines.
- **One** constellation tier (start with Ursa) wired end-to-end: dealt outline →
  constant-λ star landing on live cells → lit star = sticky wild → complete → beast
  block wild → walk + wrap + climbing multiplier → guaranteed roam window.
- Base trigger: 3 star scatters → the one tier (standard scatter machinery).
- Generate → optimize to ~0.96 with the wincap reachable via a completed-early beast.

**Out (until the core is proven):** all three tiers + the 4-mode buy menu, vertical-drift
polish, per-beast roam shapes, final art/sound, big-win presentation. Get **one tier +
the roam** working first.

## Not Doing (and Why)
- **No cascades** — tempting (Hex Bloom's meter relies on them) but it's a real engine
  change and drifts us off the `0_0_lines` sample. We tune the threshold to paylines
  instead.
- **No freeform "any 2×2 blooms anywhere"** — that's a percolation problem with a
  threshold cliff and no tier ladder. Dealt constellations = coupon-collector math
  (tractable, smoothly tunable) with a natural ladder.
- **No variable feature length as the volatility lever** — fixed spins + guaranteed
  roam. Volatility comes from the beast tail, not from length (learned on Keybearer).
  *Refined Jul 2026: length is now fixed PER TIER (Corvus 10, Ursa 15, Draco 15)
  rather than one global number. This does not reopen the rule — every tier is still
  a fixed length and no retrigger can extend it, so length is never a source of
  volatility. It turned out to be a **price** lever instead: spins move a tier's
  COMPLETION RATE, and completion is what a buy's economy rides on. 10→15 took Draco
  12%→32% completion and closed its win-range gap (a compliance gate); the same 15
  spins made Corvus, which already completes ~94%, unpriceable below ~375x against a
  200x target, because extra spins add no completions to a tier that already
  completes — they just lengthen every roam and lift the body. Division of labour:
  **length fixes the shape, ladders fix the price, cell maps fix tier separation.***
- **No global multiplier** — the multiplier rides the beast (attached, climbing). One
  multiplier system only.
- **No walking-wild that exits the board** — it *wraps*. An exiting walk would kill the
  "finish early = longer roam" tail, which is our whole fat tail.
- **No per-beast roam behavior in v1** — one roam rule for all tiers first (per-beast
  shapes/paths are a lovely stretch, but they multiply the balancing surface).
- **No Enhanced-RTP chase** — ship ≤ 0.967; RTP isn't the lever for native games.

## Open Questions
- ~~Where does the mechanic live?~~ **RESOLVED — free-spins feature only** (bounds
  persistence structurally; base is a clean stateless overlay).
- ~~Freeform vs dealt shape?~~ **RESOLVED — dealt named constellation.**
- ~~What does the beast do while roaming?~~ **RESOLVED — random roam + climbing
  multiplier** (C&C/MIKO-style; changed from directional-walk+wrap — random is fine
  because the tail depends on how LONG the beast stays, not the path, and it never
  exits; random also kills big-beast monotony. Climbing multiplier unchanged.)
- ~~How does a constellation cell light up?~~ **RESOLVED — a WINNING PAYLINE crossing
  the cell lights it** (changed from star-landing/λ/fly-to-cell — "your wins trace the
  constellation"). Trade-offs accepted: (+) theme integration, snowball dynamic (lit
  wild → more wins → more cells), simpler feature code; (−) constellation SHAPE now
  matters mathematically (cells on more paylines light faster), completion rates are
  sim-derived not analytic (95/44/2% targets retired), tuning is more coupled, and
  cold-start features can fizzle. KEY compliance note: partial progress MUST pay
  (ETL ≤ 0.8 + no-win-gaps forbid a pure nothing-or-jackpot Draco even in its own
  mode) — the snowball provides the required intermediate-win spread; the cold end
  needs a fill floor if buy-mode bust runs high.
- ~~How many tiers / spread?~~ **RESOLVED — 3: Corvus 4 / Ursa 7 / Draco 11.**
- ~~Trigger: meter or scatters?~~ **RESOLVED — star scatters, 3/4/5 = tier** (the
  no-scatter meter was adopted then reverted: it needs cascades to feel alive, and the
  SDK/frontend machinery is scatter-native; see Recommended Direction).
- ~~Natural entry: random reveal or choice?~~ **RESOLVED — earned by scatter count**
  (visible on the board; buys let you pay to pick).
- **Base-game boost — REOPENED.** The meter was the answer; reverting it leaves base a
  standard scatter hunt. Maybe that's fine (genre-normal). Parked candidates if not:
  *stars pay small in base* (zero new mechanics, teaches "stars are good"), *beast
  sighting* (rare one-spin oversized wild cameo — the feature's hero moment in
  miniature, colossal-in-base precedent exists). Decide after first playtest, not
  before.
- **Beast sizes / all-2×2 pivot — PLAYTEST WATCH-ITEM.** Current 2×2 / 2×3 / 3×3 may
  implement awkwardly (the 3×3 barely fits a 5×4 — ~6 roam positions, 45% of the board).
  Option: make ALL beasts 2×2 and differentiate tiers purely by completion difficulty
  (4/7/11 cells) + the multiplier ladder. Cost: code trivial (size is config), MATH =
  a full Phase B re-converge (beast size is a primary payout lever). Middle path: keep
  Corvus 2×2 / Ursa 2×3, make Draco a 2×4 **serpent** (fits the board, still big). Decide
  after a real playtest of the roam feel — you can't judge "awkward" without the frontend.
  Same lever family as the ceiling item below. (CLAUDE.md "PICK UP HERE" #2a.)
- **Corvus/Ursa ceilings maybe too conservative — PLAYTEST WATCH-ITEM.** Market check
  (stakestats, Jul 2026): return-on-stake (maxWin ÷ cost) is Corvus 1,500/224 = **6.7×**,
  Ursa 4,750/283 = 16.8×, Draco 25,000/651 = 38×. Comparable low-vol *buys* elsewhere sit
  far higher — Rage Bait's buys 50–100× (all reach the 25k cap), Waylanders' capped
  bonus3 = 80×. So Corvus at 6.7× is the most-capped buy in the survey. Defensible (a true
  non-lottery "grind" buy is real differentiation) but may feel flat to the buy crowd.
  Lever = raise the per-tier multiplier ladders → lifts ceilings toward 50–100× with RTP
  untouched — the *same* lever as the beast-size item. (Reading note: stakestats
  "Max Multiplier" for a buy is COST-normalized = maxWin/cost; our published maxWin is
  base-bet.) (CLAUDE.md "PICK UP HERE" #2b.)
- **In-feature retrigger (+1 spin per star) — PARKED LEVER, currently OFF.** Market
  split: C&C retriggers, MIKO doesn't (MIKO is the higher-vol design — not a
  coincidence). In OUR game this is NOT a C&C-style retrigger: stars are the charge
  mechanic falling at λ≈1.5/spin (frequent, not a rare lucky event), so "+1/star"
  reads as length-inflation, not a punchy moment. Worse, it auto-extends slow-
  completing features, flattening the completion-time×tier tail that IS our
  volatility (the Keybearer m2m-2.2 antipattern). Plumbing note: stars only land on
  live cells, so post-completion none land → it only extends the CHARGE phase =
  effectively a "raise completion rates" dial, not excitement. Fully reversible (it's
  the exact block removed from run_freespin) BUT it's a math-model change → must land
  BEFORE submission lock and re-tunes all 6 modes. Pull ONLY if the measure loop shows
  the feature feels too short / completion rates come in low. Default: stays off.
- ~~Max win structure?~~ **RESOLVED — 25,000× concentrated in Draco; per-mode ceilings
  displayed** (the approval guidelines *require* each mode's max win to be displayed AND
  "realistically obtainable" — better than ~1 in 10M — so each mode states its true
  ceiling and gets a wincap slice weight ≥ ~1e-7; Corvus states an honest lower max if
  its 2×2 beast can't reach 25,000×).
- **Naming:** Starwake / Firmament / Empyrean / Starborn — check vs Stake catalogue +
  basic trademark search before committing.
- ~~**Feature length** (baseline 10 spins?) and **guaranteed roam window** size~~ —
  RESOLVED Jul 2026. Length is PER TIER: Corvus 10, Ursa 15, Draco 15 (see the
  "no variable feature length" note above for why it split). Roam window floor is
  **2**, down from 5: at 5 the floor was carrying ~70% of buy_draco's value and it
  *created* the Draco win-range gap, since a guaranteed 5 spins of a just-switched-on
  multiplier put the cheapest possible completion at 3,016x against a carpet topping
  out at 336x. Lowering it also serves the doc's own "finish early = longer roam"
  goal: that span was 5→9 spins at floor 5 (1.8x) but is 2→14 at floor 2.
- ~~**Beast multiplier scale** (start value + per-spin climb increment)~~ — RESOLVED.
  Not a start+increment: each tier gets an explicit **geometric ladder**, generated
  from three numbers and pasted literally into `game_config.constellation_mult_ladders`
  so the compliance "all obtainable values" table stays auditable:
  `ladder[i] = start * (top/start) ** ((i/(n-1)) ** curve)`. START prices the common
  late completion (= the cliff floor), TOP prices the rare early one (= the ceiling),
  and CURVE > 1 holds the early rungs down so the two decouple. This is the only knob
  that lowers the mean and raises the ceiling at once — a paytable cut scales body and
  tail together. Chosen: Corvus 1:200:2.5, Ursa 1:500:2, Draco 2:600:1.5.
  > ⚠️ **SUPERSEDED Aug 5 2026 by ACT TWO, and the config still lies about it.** The
  > climbing ladder was replaced by star collection: the beast collects multiplier
  > stars and its multiplier is the **sum of collected star values**, not a rung.
  > `constellation_mult_ladders` is still present, still exported and still validated,
  > but it is **unreachable in every tier** (`ActTwo()` is true wherever a tier has
  > star values, which is all four). A ladder edit today is a silent no-op. See the
  > Aug 13 2026 entry at the top of `games/starwake/CLAUDE.md`.
- ~~**Draco 3×3 = 45% board coverage**~~ — RESOLVED: **all three beasts are 2×2.**
  The deciding argument was not RTP pressure but that *the roam barely works at 3×3*.
  Roam positions on a 5×4: 2×2 = 12, 2×3 = 8, 3×3 = 6. The dragon shuffling between
  six spots undermines the signature "beast roams each spin" mechanic on the showpiece
  tier. One size also means one frontend sprite rig and one roam animation instead of
  three, and 2×2 is the readable market block-wild idiom. **Tier identity survives via
  the sticky cells, not the beast footprint**: at wake the board is 8 / 11 / 15 of 20
  cells wild (4/7/11 lit + the 2×2). The constellation covers the sky; the beast
  prowls over it — arguably the better story.
- ~~**Buy-menu shape:** just the 3 tier buys, or also a Hex-Bloom-style single "enhanced
  spin" product?~~ **RESOLVED Aug 13 2026 — the single-spin product, and the tier buys
  went from 3 to 2.** They did feel flat, and it was measurable rather than a matter of
  taste: cost-adjusted volatility read corvus 1.85 / ursa 1.88, so the 200× and 300×
  rungs were selling one product twice. `buy_corvus` out, `buy_mystery_spin` in at 150×.
  The menu is now **different products** — 150× one spin (highest volatility, lowest
  price), 300× coin flip, 400× lottery, 500× random tier — rather than a price ladder.
  Two mystery buys is precedented: Rage Bait ships two at 500× separated only by
  bust-vs-tail shape (0.00% / 46.52%). Ours separate on LENGTH.
- **Vertical-drift rule** for the wrap (how far it shifts each lap).

## Design Lineage (what we borrowed, and from where)
- **Fill-the-shape → block wild:** Hex Bloom (pentagram → block wild sized 2×2/3×3/4×4).
  We adapted its *shape-completion* summon. (Its per-spin meter base hook was tried and
  reverted — it needs cascades.)
- **Walking wild / self-contained journey arc:** NetEnt's Jack and the Beanstalk (walks
  one step per respin, 3× on wild wins). We kept the walk + multiplier, swapped *exit*
  for *wrap* to preserve the completion-time tail.
- **Meaningful risk choice at the same EV:** DOA2's three selectable bonus modes. We
  deliver it structurally via tier = two different games, plus buyable tiers.
- **Persistent-state discipline + fixed feature length:** our own Keybearer/Penthouse
  lineage (Vault ladder, fixed 15-spin feature, "optimizer can't invent outcomes").

## Compliance Gates (from the Stake approval guidelines — hard limits, 2★ tier)
- **RTP 90.0–96.70%**, all modes within a **0.5% band** of each other.
- **Wincap 25,000× = exactly the 2★ maximum** (zero headroom; 100,000× needs 3★).
  Per-mode max win **displayed** and **obtainable** (≥ ~1e-7 in the lookup table).
- **Buy cost multiplier ≤ 1,000×**; tail-probability leniency ×0.8 for 200–500× costs.
- **Hit rate:** non-zero wins ≥ 1 in 20; base std dev 0.6–50; no win-range gaps between
  small pays and the max; zero-weight payouts must not dominate the published table.
- **CVaR ≤ 700 (normalized), ETL(≥40× cost) ≤ 0.8** — operator tail-risk caps.
- **Statelessness:** no jackpots, gamble features, continuation, or cashout. (Starwake:
  stateful *feature* inside one book — compliant. The rejected tier-upgrade-gamble idea
  would NOT have been.)
- **Beast multiplier values must be enumerable** — rules must "list all obtainable
  values" for special symbols, so the published set must be fixed, not open-ended.
  ✅ **RESOLVED Aug 13 2026 — and the enumerable thing is the STAR, not the beast.**
  The gate used to be met by the climbing ladder, which Act Two made inert (above). The
  fix is not a bigger table: the *special symbol* is the multiplier star, and its
  obtainable values are exactly the per-tier star tables — five to seven rows, exact,
  weights summing to 100. The beast multiplier is a **derived running total**
  (`1 + collected`), described by a rule the way any collect mechanic is, and its
  obtainable set is a **range** — x1, then every whole number from x3 up (x2 is
  provably unreachable: it needs 1 collected and the smallest star is 2).
  ⚠️ Do **not** publish a per-tier multiplier maximum. The combinatorial bound is
  unreachable and the pool-observed max is a sample that grows with sample size; the
  only honest bound is the 25,000x win cap. Copy and tables:
  `docs/ideas/starwake_rules_screen.md`; measurement: `enumerate_multipliers.py`.
- **Replay mandatory** — publicly shareable, per-mode event IDs requested at review
  (normal win / big win / wincap / loss / bonus trigger). Fixed ~10-spin feature keeps
  every replay, including wincap, a tight watchable clip (the Keybearer 10-minute-replay
  failure is structurally impossible here).
- **Unique assets only** — web-sdk sample art will not be approved; generic AI assets
  are a listed rejection reason. Full custom art is mandatory.
- **Effective quality bar is 2★** (1★ = "not published, resubmit"). Depth is fine
  (tier choice + collection + beast); art/polish is the gating risk.
- **Post-approval lock:** no math changes, no new modes after approval. All 6 modes,
  all 3 constellations, final tuning must be in the submitted version — submission is
  the finish line, not a checkpoint.
- **Title:** "Starwake" clean of banned terms (Megaways/Gates of/Bonanza/Enhanced RTP);
  verify no lobby collision before locking.
- **Tile art:** bright, no dark edges — a deliberate constraint on a night-sky theme
  (vibrant nebula palette, bright beast foreground). BG + FG PNG ≤ 3MB combined +
  **provider logo** → needs a **studio name + logo** (critical path, undecided).
- **stake.us social language:** route ALL UI copy through language files from day one
  with `sweeps_<lang>` variants ("Buy Bonus"→"Get Bonus", bet→play, cash→coins...).
  Thematic copy ("light the stars", "wake the beast") is naturally social-safe.
- **Rules popup:** per-mode RTP + cost + max win, all symbol payouts, scatter access
  text ("3 stars award..."), UI guide, malfunction disclaimer (template provided).

## Benchmarks (measured off live games, stakestats.net, July 2026)
Calibration points, not templates — we take different things from each.

| Metric | Coins & Cauldrons (Meta Gaming) | MIKO (Paperclip) | Starwake target |
|---|---|---|---|
| RTP, all modes | 96.01% flat | 96.00% flat (±0.02%!) | **96.65–96.69** (displays 96.7 — shelf advantage; cap-runners like Rage Bait exist but flat-96.0 is the norm) |
| Base bust rate | 69.8% | 83.4% | ~70–80% is market-proven for Very High vol |
| Base win freq (≥1× bet) | 7.5% | 7.4% | ~7–8% — convergent market number |
| Base std dev | 59.9 (**3★ edge**, cap 60) | 31.7 | **< 50 (2★ cap)**, expect ~35–48 |
| Wincap | 50,000× @ ~1e-6 (3★) | 10,000× | 25,000× (2★ max) @ ~1e-6 weight |
| RTP above 100× | 41% | **60%** | Draco-heavy tail has ample precedent |
| Ante | `bonus2x` = feature-only lottery (93% bust, empty sub-0.5× buckets) — NOT our model | `ANTE` = classic: **3× cost**, bust ≈ base, **std dev halved**, vol label −1 notch | **Starfall = MIKO's model**; cost up to 3× is normal |
| Buy modes | bust 0.00%, ~22% return > cost | same (BONUS/SUPER/SPECIAL/MYSTERY, Low vol) | bust 0% structural (any lit star pays); mystery-buy precedent confirmed |
| Architecture | — | base & ANTE share identical 98,998 unique multipliers → **same outcome library, different weights** | validates our shared-books + slice-weights ante plan |

Convergence quality bar: both games land all modes within ~±0.02% of target —
far tighter than the 0.5% compliance band. That's what the optimizer runs must hit.

**Mystery-buy audit (stakestats TrueTransparency, Jul 2026)** — informs `buy_mystery`:
| Game | Cap | Mystery cost | Tier split (displayed) | Top-tier freq → share of payback |
|---|---|---|---|---|
| Rage Bait (Meta) | 25,000× | **500×** | 4/5/6 scatter = 45/45/10% | 6-sc: 10% → **52%** |
| Captain Death (Valkyrie) | 100,000× | **500×** | 2/3/4/5 sc = 60.9/5/25/9.1% | 5-sc: 9.1% → **80%** (at ETL cap) |

Takeaways: (1) 500× is the standard mystery price even at our 25k cap (Rage Bait).
(2) The rarest tier carries 50–80% of payback — but ETL caps concentration at 0.80
(Captain Death sits exactly there), and the middle tiers still pay a spread (no
win-gaps). (3) Odds are displayed truthfully. → Starwake mystery: target 500×,
Draco-weighted, publish the real mix (see Bet modes table + CLAUDE.md pickup #1).

## Path to Cleared
Grounded in the Stake Engine docs in this repo: `docs/rgs_docs/{RGS,data_format}.md`,
`docs/math_docs/{quickstart, uploads_section/upload_info}.md`. **Design is essentially
done; remaining work is tuning + a frontend build.**

> ⚠️ **Not yet on the radar:** (a) provider access is a *gate*; (b) the **frontend is a
> whole separate build** (~half the work) and needs a **custom event vocabulary** both
> math and frontend speak (star-lands, star-sticks, beast-wakes, beast-roams,
> multiplier-climbs); (c) the constant-λ star-landing rule must be enforced in the
> strips or the whole tier ladder silently breaks.

**Phase 0 — Provider access (GATE — start now)**
- [ ] Apply / get accepted as a Stake Engine provider (engine.stake.com; invite-only).
- [ ] Obtain your **Team Name** (appears in the game URL).

**Phase 1 — Math (fork `0_0_lines`)**
- [x] Fork → `games/starwake` (from 0_0_lines): 5×4, 20 four-row paylines (keybearer's
      proven set), wincap 25,000, rtp 0.9665, scatter "S" = Star. SMOKE-VERIFIED:
      6k books both modes in ~7s; 25,000× wincap books force successfully even on
      sample math (with >1000-repeat warnings — expected until WCAP strips exist).
      Still sample DNA: paytable, triggers, strips, 2 modes, no feature engine.
- [ ] Base trigger: 3/4/5 star scatters → Corvus/Ursa/Draco (`scatter_triggers` slices,
      Keybearer-style); star density on base strips = tier-rarity dial.
- [ ] Feature: dealt constellation outline; **constant-λ** star landing on live cells;
      lit star = sticky wild; complete → beast block wild; walk + wrap + vertical drift +
      climbing multiplier; guaranteed roam window; **fixed** feature length.
- [ ] `game_optimization.py` slice tables → converge ~0.96, wincap 25,000× reachable;
      4 bet modes (base + 3 tier buys). Run 100k+ sims/mode → PAR sheet.

**Phase 2 — Event vocabulary (math ↔ frontend bridge)**
- [ ] Custom events on top of stock `reveal / winInfo / setWin / setTotalWin / finalWin`:
      `constellationDealt`, `starLit` (→ sticky wild), `beastWake`, `beastRoam`
      (position), `multiplierClimb`.
- [ ] Everything encoded in the **book** (source of truth); frontend plays it back — no
      client-side outcome computation that could diverge from `payoutMultiplier`.

**Phase 3 — Frontend (web-sdk — the big new workstream)**
- [ ] Fork `web-sdk/apps/lines` → starwake frontend; render the events.
- [ ] Build: scatter anticipation (4th/5th star slowdown), the dealt-constellation
      outline + star-lighting, the sticky wilds, the beast block wild + walk/wrap
      animation, the climbing multiplier readout.
- [ ] RGS integration; URL params (never hardcode `rgs_url`); money as integers
      (6 decimals); languages; jurisdiction flags. Standard big-win count-up — no cutscene.
- [ ] **Replay mode** (mandatory): `replay=true` param → fetch `/bet/replay/...`, Play /
      Play Again buttons, betting UI hidden, slimmed UI, works in Popout S view.
- [ ] Popout/mini-player + mobile scaling; all assets from Stake CDN (no external fetches).
- [ ] All UI copy via language files incl. `sweeps_<lang>` social variants; buy-mode
      confirmation dialog (>2× cost); sound toggle; spacebar-bet; autoplay confirmation;
      rules popup (per-mode RTP/cost/max win, paytable, multiplier ladder values, UI
      guide, disclaimer).

**Phase 4 — Upload / publish** — index.json + lookup CSV + game logic `.jsonl.zst`;
`payoutMultiplier` hash match; upload via `upload_to_aws()` / ACP. Plus submission
collateral: promo blurb, tile BG/FG assets, provider logo, and an **event-ID finder**
(small tool to locate normal/big/wincap/loss/trigger books per mode for reviewers).

**Phase 5 — Clear / verify** — Stake preliminary checks (format, payout/probability,
CSV↔logic hash, RTP from lookup); provably-fair (stateless game — all outcomes
pre-generated; Starwake qualifies: stateful *feature*, not stateful *game*); end-to-end
RGS test; approval ~24h.
