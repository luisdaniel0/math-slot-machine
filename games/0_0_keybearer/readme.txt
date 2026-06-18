# Keybearer

A Kingdom Hearts-inspired lines game. Collect Keys to unlock and charge a
climbing "Vault" multiplier on the way to the master win.

Format:      5 reels x 4 rows, 20 paylines, lines-pay (left to right)
Volatility:  high
Max win:     25,000x (hard cap)
Target RTP:  0.96

Bet modes:
  base       1.0x cost  -- standard play, all three features reachable
  buy_super  ~520x cost  -- buys directly into a Super FG (cost is provisional
                           until the Super average win is measured by sim;
                           final cost = Super average / 0.96). Mega Super is
                           NOT buyable.


Symbols
-------
  W       Wild. Substitutes for paying symbols. PAYS ON 5-KIND ONLY (top 5-kind
          = 80x). In Standard FG only, a Wild also carries a local 2x-10x
          multiplier applied to the line it completes.
  K       Key (scatter). Does NOT pay on lines. Keys count toward feature
          triggers and charge the Vault.
  H1-H4   High symbols (top-heavy; H1 5-kind = 80x).
  L1-L5   Low symbols.

Why Wilds pay 5-kind only: if 3/4-kind Wilds also paid, a short Wild line could
out-rank a longer real-symbol line on base payout, since the line calculation
picks the higher base win before multipliers (see docs lines_info.md). Limiting
Wilds to complete lines avoids that.


Features (chosen by how many Keys trigger the round)
----------------------------------------------------
3 Keys -> STANDARD FG  (8 spins)
  Wild-rich reels (FR_STD). Each Wild that helps complete a line carries a
  local 2x-10x multiplier. No Vault. Retriggers on 2+ Keys (+5 spins).

4 Keys -> SUPER FG  (12 spins)
  Key-rich reels (FR_SUP). The Vault (a persistent global multiplier) starts at
  1x. Every Key landing on a spin adds a random +2..+50 to the Vault, and the
  Vault multiplies EVERY line win on that spin. The Vault never decreases during
  the feature -- it ratchets up, so later spins are worth far more.
  Retriggers on 3+ Keys (+5 spins).

5 Keys -> MEGA SUPER  (12 spins)
  Same as Super, but the Vault begins pre-charged (bigger starting point).
  Natural-only (cannot be bought), ~1 in 100k. Retriggers on 3+ Keys (+5 spins).


The Vault, precisely
--------------------
The Vault is the engine's global_multiplier. Per Super/Mega spin, in order:
  1. draw board
  2. charge_vault(): for each Key on the board, add a random increment to the
     Vault (vault_increment_values in game_config.py)
  3. evaluate lines using the "combined" multiplier strategy, so:
        spin win = Vault x (sum of raw line wins this spin)
The Vault persists across spins (reset to 1 only at the start of each new game
round, in reset_book). In Standard FG the Vault stays at 1x and Wild local
multipliers are used instead.

Note: the "combined" strategy is required. The default "symbol" strategy ignores
global_multiplier, which would make the Vault display a number but do nothing.


Math / RTP control
------------------
Win SIZE is set by the feature; win FREQUENCY is set by the reels + optimizer.
RTP = sum(probability x payout) over all (enumerated) simulations = 0.96.
Base-mode RTP budget (slice table in game_optimization.py):
  wincap   0.01  (25,000x @ ~1/2.5M)
  super    0.25  (~500x   @ ~1/2,000)
  standard 0.35  (~63x    @ ~1/180)
  basegame 0.35  (~1.75x  @ ~1/5)
  zero     0.00
A huge win is "paid for" by being rare; the 25,000x cap bounds exposure.


Reels (regenerate with reels/generate_reels.py)
-----------------------------------------------
  BR0     base game    -- lows-heavy, Wilds rare, Keys calibrated
  FR_STD  Standard FG  -- wild-rich
  FR_SUP  Super/Mega   -- key-rich (charges the Vault)
  WCAP    wincap helper -- key-rich + boosted top symbol so 25,000x is reachable
Exact Key frequencies are tuned by simulation (run -> measure -> adjust).
