# World Cup (0_0_worldcup)

5-reel, 4-row lines-pay slot with 20 paylines. Derived from the 0_0_lines sample.

RTP: 0.97 (both modes)
Wincap: 5000x
Volatility: very high (per-spin std ~14.4) — top-heavy, bonus-driven design.

## Symbols / theme mapping

  W  = Wild        (substitutes for all paying symbols; pays 5-kind only, 100x)
  H1 = Trophy      (top symbol: 2 / 15 / 100 for 3/4/5-kind)
  H2 = Golden Boot
  H3 = Star Jersey
  H4 = Ref Cards
  L1 = Yellow Ball
  L2 = Red Ball
  L3 = Blue Ball
  L4 = Orange Ball
  L5 = Green Ball
  S  = Scatter     (freespin trigger; no line pays; art asset TBD)

Wild pays 5-kind only by design: if 3/4-kind Wilds pay, the line calculation can
pick a short Wild win over a longer win through the same Wilds (see lines.py).

## Base game

- Reels: BR0.csv (219 stops/reel). Wilds rare (2/reel). Trophy deliberately
  thinned to 10/reel for rarity (script-seeded edit, backfilled with lows).
- Scatters weighted 5/1/5/1/5 across reels; 3/4/5 scatters trigger 8/12/15
  free spins.
- Lows pay below bet on 3-kind ("dust" wins). Paying spin ~1 in 4,
  average win 1.8x. Carries 45% of RTP.

## Free game

- Reels: FR0.csv. Wilds are frequent (11-17/reel) and carry multipliers
  (2x-50x); multipliers on a winning line add together and multiply the
  line win when > 1.
- 2+ scatters award extra spins (2:3, 3:5, 4:8, 5:12).
- Triggers ~1 in 200 base spins; average total bonus ~100x.
  Carries 50% of RTP, plus a 2% wincap band (5000x hits ~1 in 250k spins).
- FRWCAP.csv is a wild-dense strip used only for forced wincap simulations.

## Bet modes

- base  (cost 1.0)   — standard spin
- bonus (cost 100.0) — bonus buy, forces freespin entry, same 0.97 RTP

## Optimization targets (game_optimization.py)

  base:  wincap rtp 0.02 | freegame rtp 0.50 hr 200 | basegame rtp 0.45 hr 4.0
  bonus: wincap rtp 0.02 | freegame rtp 0.95
