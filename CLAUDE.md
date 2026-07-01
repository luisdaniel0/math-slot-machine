# Keybearer — Stake Engine lines slot (in development)

Kingdom Hearts–inspired key game. Scaffolded from `games/0_0_lines`.
Learner project: build step-by-step, explain decisions, don't bulk-complete.

## Design spec (the blueprint — build to this)

- **Identity:** Lines, high volatility, 0.96 RTP.
  Fantasy: collect keys → charge a climbing Vault multiplier toward the master win.
- **Core:** 5x4 board, 20 paylines, 25,000x wincap.
  Bet modes: `base` (1.0), `buy_super` (~520x, cost = super avg ÷ 0.96).
- **Features:** one "Key" scatter, count-based:
  - 3 keys → Standard FG (8/12 spins; local 2x–10x adding wilds; retrigger 2+ → +5)
  - 4 keys → Super FG (12 spins; CLIMBING VAULT mult — each key adds +2..+50,
    persists, multiplies every line win; retrigger 3+)
  - 5 keys → Mega Super (bigger starting Vault; ~1/100k; NATURAL ONLY, not buyable)
- **Symbols:** W (5-kind only; 2–10x mult in Standard FG only), K (scatter, no line pay),
  H1–H4, L1–L5. Top-heavy paytable, top 5-kind = 80x.
- **Slice tables:**
  - base: wincap 0.01 (1/2.5M) | super 0.25 (1/2000) | standard 0.35 (1/180) | basegame 0.35 (1/5) | zero 0
  - buy_super: wincap 0.02 | super 0.94  (→ 0.96 of cost)
- **Strips:** BR0 (keys: 3→1/150, 4→1/2000, 5→1/100k; wilds rare; lows-heavy),
  FR_STD (wild-rich), FR_SUP (key-rich to charge Vault), WCAP (juiced).
- **Volatility:** base m2m 6–12, buy m2m 4–8.

## Build status
- [x] Scaffolded from 0_0_lines, renamed game_id/working_name
- [x] Section 2: 5x4 board + core params in game_config.py
      (num_rows [4]*5, wincap 25000, rtp 0.96, 20 paylines across all 4 rows)
- [x] Sections 3–4: features, symbols, paytable
      (W 5-kind=80 only; H1-H4/L1-L5 top-heavy; scatter renamed S->K in
      special_symbols + reel CSVs; triggers 3->8/4->12/5->12, retrig +5;
      padding wild mult 2x-10x. DEFERRED to §5: betmode mult_values still
      reach 50x -- cap to 10x for Standard FG / repurpose for Vault.)
- [x] Section 5: slice tables → game_optimization.py + betmode redesign
      (renamed bonus->buy_super cost 520 PROVISIONAL; base 5 slices
      wincap/super/standard/basegame/0, buy 2 slices; standard=3keys super=4keys
      via scatter_triggers; verify_optimization_input passes, both modes RTP=0.96)
- [x] NEW MECHANIC: climbing Vault multiplier for Super/Mega FG
      Vault = engine global_multiplier (persists; reset_book sets 1/sim).
      KEY INSIGHT: switched lines strategy "symbol"->"combined" or the Vault
      multiplies nothing. charge_vault() adds +2..+50 per Key (super/mega only);
      wilds keep local 2-10x in Standard only; Mega pre-charges mega_start_vault;
      retrigger gate feature-aware (std 2+, super/mega 3+). Unit-tested.
- [x] Section 6: reel strips via reels/generate_reels.py (re-runnable, weight
      tables). BR0 lows-heavy/rare-W; FR_STD wild-rich; FR_SUP key-rich (charges
      Vault); WCAP key+top juiced. Config loads BR0/FR_STD/FR_SUP/WCAP, routes
      standard->FR_STD, super->FR_SUP, wincap->FR_SUP+WCAP.
      MEASURED BR0: 3key 1/176 (target 1/150, close), 4key 1/3552 (t 1/2000),
      5key 1/222k (t 1/100k) -- tail ~2x rare, REFINE in run/measure loop.
      (Slices force key counts via scatter_triggers, so this doesn't block run.)
- [x] Section 7: m2m settings (base 6-12, buy 4-8 in ConstructParameters)
- [x] Run → optimize → verify: base 0.9623, buy_super 0.9600 @ 100k sims/mode.
      buy converged instantly (free-hr super slice); base overshot to 0.991.
      ROOT CAUSE: every base slice had a FIXED hit-rate -> over-constrained ->
      optimizer settles high (uniform across slices; sims & m2m barely move it).
      FIX: basegame hr is the global RTP dial. NOTE the dial is sim-count
      dependent -- tune it at production sim count, not a quick run:
        @20k:  hr5=0.991 hr7=0.971 hr8=0.965 free=0.919
        @100k: hr8=0.974 hr9=0.967 hr10=0.962   <- LOCKED basegame hr=10
      Also added check_freespin_entry gate so basegame/0 slices reject natural
      triggers (correct, but not the overshoot cause).
      For submission: run 1e6/mode; base may want hr~10.4 for exact 0.960.

## Runtime fixes (found by first `make run`)
- KeyError on freegame retrigger: key-rich FR_SUP shows 6+ Keys; base engine
  indexes freespin_triggers by exact count. FIX: spin awards are now TIER-based
  in game_executables (update_freespin_amount / update_fs_retrigger_amt), not
  count-indexed. freespin_triggers only supplies trigger minimums now.
- Freegame ran unbounded: retrigger branching factor was 1.81 (>1). FIX: lowered
  FR_SUP key density (K 12->6), Super/Mega retrigger +5->+3 (Standard stays +5),
  hard cap config.max_fs_spins=60, and run_freespin now stops on wincap_triggered
  / max_fs_spins. Branching now 0.32; avg feature ~17 spins. Smoke: 4500 sims in 2s.

## Feature pacing + legibility pass (Storybook playtest feedback)
- PROBLEM: Super/Mega could run 40-60 spins (retriggers chaining on key-rich
  FR_SUP) -- boring/flawed pacing; and the Vault charged by a random 2..50 per
  Key, so players couldn't read "what a Key is worth".
- FIX 1 (length): Super/Mega NO LONGER retrigger (check_fs_condition returns
  False for them) -> fixed 12 spins. Standard keeps its retrigger. max_fs_spins
  60->20. MEASURED (12k super books): every feature now exactly 12 spins, tail
  gone; zero-pay still impossible (check_repeat gate); win-rate ~28%/spin.
- FIX 2 (legibility): vault_increment_values is now 3 legible tiers
  {3:75,10:20,25:5} (bronze/silver/gold, mean ~5.5) instead of random 2..50.
  charge_vault emits per-Key breakdown via update_global_mult_event(key_charges=
  [{reel,row,value}]) -> new `keyCharges` field on the updateGlobalMult event so
  the FE can fly a clear "+N" from each Key into the running Vault total.
- CONSEQUENCES: buy_super avg win ~halved (median 394->209x) so the PROVISIONAL
  buy cost (~520x) should drop to ~avg/0.96 at production sim count. Wincap still
  reachable in 12 spins (tested: 0% unreachable) but needs ~155 re-rolls/wincap
  book (was cheaper with 60 spins) -- slower wincap slice, not a correctness bug.
- update_global_mult_event key_charges arg defaults None => other games' events
  unchanged.

## Gotchas
- Wilds pay 5-kind only (avoids short wild-line overriding longer real-symbol lines).
- The Vault multiplier is the genuinely new code vs 0_0_lines — persistent global mult.
- Two-stage pipeline: game_config.py generates; game_optimization.py re-weights to 0.96.
- Optimizer can't invent outcomes — convergence failures = fix strips/paytable/Vault, not opt config.