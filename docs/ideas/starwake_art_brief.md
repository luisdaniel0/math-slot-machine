# Starwake — art & animation brief

**Uptown Games · 5×4 constellation slot for Stake Engine**

A brief for artists, animators and motion designers. Everything below is fixed by the
finished maths unless marked **open**. Style direction is deliberately left open — that's
what we're hiring for.

---

## 1. The game in one paragraph

Starwake is a celestial slot. Winning lines trace a **constellation** onto the reels one
star at a time; when the shape completes, the constellation "wakes" and a **beast** — a
2×2 creature made of stars — steps onto the board and walks around it for the rest of the
round, collecting falling stars and growing a multiplier that pays out any winning line it
touches. Four constellations of increasing size and greed: **Corvus** the crow, **Ursa**
the bear, **Draco** the dragon, and a rarer **Ascendant Draco**.

The round is two acts, and the split matters for pacing:

- **Act 1 — Charge.** Ordinary spins. Wins light up stars in a fixed pattern.
- **Act 2 — Roam.** The beast is awake. **This is where 87–96% of all money is paid.**
  Act 1 is anticipation; Act 2 is the payoff. The animation budget should reflect that.

---

## 2. Fixed technical facts

| | |
|---|---|
| Grid | 5 reels × 4 rows, 20 paylines |
| Paying symbols | 4 high (H1–H4), 5 low (L1–L5) |
| Special symbols | **W** wild · **S** scatter · **M** multiplier star |
| Bet modes | 6 (base, ante, and 4 buy options) |
| Max win | 25,000× the bet, on every mode |
| Platform | Stake Engine (web, desktop + mobile + popout) |

**Animation format.** Skeletal (Spine) is preferred over sprite sheets for the beasts —
they move continuously and rigged animation keeps the atlas small. ⚠ **Confirm the runtime
before starting:** the frontend needs a matching Spine runtime, and editor/runtime versions
must agree (a 4.x export will not load in a 3.8 runtime). Deliverables should include the
source `.spine` projects, not only exports.

**Open:** final resolution targets and atlas budgets follow from the frontend framework,
which isn't built yet. Design at a 1920×1080 reference and ensure everything reads on a
375px-wide phone. Number of background variants across the six bet modes is also open.

---

## 3. The four constellations

Each is a fixed pattern of cells on the 5×4 grid. These positions are **locked by the
maths** — the shapes can be restyled but not moved.

```
CORVUS — 4 stars, a diamond        URSA — 7 stars, a dipper
  . * . . .                          . . * * .
  * . * . .                          * * . . *
  . * . . .                          * * . . .
  . . . . .                          . . . . .

DRACO — 11 stars, a serpent        ASCENDANT — same 11, two already lit
  . . * . *
  . * * . *
  * * . * *
  * . . . *
```

They are **never on screen together** — one per round. Each needs its own visual identity
while reading as part of one family.

| | stars | feature spins | beast | star values | personality |
|---|---|---|---|---|---|
| Corvus | 4 | 10 | 2×2 crow | up to 25 | cheap, fast, **wild** — bites often, occasionally huge |
| Ursa | 7 | 15 | 2×2 bear | up to 50 | the **forgiving** one — pays back most often |
| Draco | 11 | 15 | 2×2 dragon | up to 100 | rarely completes, pays enormously when it does |
| Ascendant | 11 | 15 | 2×2 dragon | up to 100 | Draco, but two stars start lit — the premium form |

⚠ **Corvus is not the "safe little one".** It is the cheap, volatile tier — it busts more
than any other buy and delivers the most frequent big wins. Ursa is the gentle one. Please
don't design Corvus as cute and harmless; it should feel scrappy and dangerous.

---

## 4. Asset list

**Symbols — 18 distinct artworks.** Ten paying symbols (H1–H4 high, L1–L5 low, plus the
wild **W**), the scatter **S**, and the multiplier star **M** in **seven value states**
(2, 3, 5, 10, 25, 50, 100) — the number is part of the art, and all seven appear in play.
Each symbol needs: idle, land, win animation, and a blur/motion state for spinning.

**Constellations (4)** — the star pattern itself, in unlit and lit states, plus the
connecting lines that draw between stars as they light. The completed shape needs a
"formed" moment.

**Beasts — 3 designs, not 4.** Crow, bear and dragon, each a **2×2 block** occupying four
grid cells. Ascendant reuses the dragon, so it is a state/reskin rather than a fourth
creature. Each needs: wake/spawn, idle, a walk cycle for moving between positions, a
collect/feed animation, and a reaction as the multiplier grows large.
⚠ **The feed loop is the highest-value animation in the game.** It repeats several times
per round and has to stay satisfying on the thirtieth viewing.

**Backgrounds** — base game, plus a distinct Act 2 state. Ante and buy modes may want
variants. **Open:** how many.

**UI** — six-mode buy menu with prices, feature counter, win presentation tiers (small /
big / huge / max win), the info & rules screens.

---

## 5. The 16 moments that need animating

This is the actual event list the game engine emits. **Every one of these is a distinct
thing the player sees**, and it's the closest thing to a shot list:

| event | what happens on screen |
|---|---|
| `reveal` | reels stop, symbols land |
| `winInfo` / `setWin` / `setTotalWin` / `finalWin` | a line wins, counters tick |
| `freeSpinTrigger` | scatters land, the feature begins |
| `updateFreeSpin` / `freeSpinEnd` | spin counter, feature ends |
| `constellationDealt` | **the constellation appears** — which beast you got |
| `starLit` | a winning line crosses a cell and a star ignites |
| `beastWake` | **the shape completes and the beast steps onto the board** |
| `beastRoam` | the beast walks to a new position |
| `starsLanded` | multiplier stars fall onto the reels |
| `starsCollected` | the beast takes them; the multiplier climbs |
| `constellationAscend` | **the rare one — see below** |
| `wincap` | the 25,000× ceiling is hit |

### The three that carry the game

**`beastWake`** is the single most important moment. It's the transition from Act 1 to
Act 2, and everything after it is where the money lives. It should feel like the round
genuinely changes gear.

**`starsCollected`** is the heartbeat of Act 2 — it repeats several times per round and
the multiplier visibly grows each time. It needs to be satisfying on the 30th viewing, not
just the first.

**`constellationAscend`** fires roughly **1 in 20,000 Corvus rounds** and is the *only*
route by which Corvus can reach 25,000×. Mid-roam, the sky starts raining much larger
stars. It must read as a **visible change on the board itself** — bigger, brighter,
different stars falling — not a banner or a text overlay. This is a moment a streamer
should clip. It currently has no art at all.

⚠ `multiplierClimb` appears in some older documentation. It is **dead**. Don't build for it.

---

## 6. Two structural requirements

**Replay must work from any point.** Stake requires a replay mode where any past round can
be re-watched. Every animation must be able to start cold from any event without depending
on having seen an earlier one. Practically: no animation state that only exists because
something previous happened.

**Performance is graded.** The game receives a human quality review covering art,
animation, sound, performance and depth — and that review is what sets the star rating.
Mobile performance is part of it.

---

## 7. What we're looking for

**Open — this is the brief's real question.** We have no locked art direction. Celestial /
constellation / night sky is the theme; everything else is up for proposal. We're
interested in seeing what you'd do with it.

Useful to include in a response:
- portfolio, ideally including slot or casino work
- a view on style direction for this theme
- rough scope and timeline for the asset list in §4
- whether you cover animation as well as static art, or work with an animator

---

## 8. Contact

**Open** — add your contact details, budget range and timeline before sending.

*This brief describes finished, tested game maths. Payout structure, constellation shapes,
grid layout and the event list are fixed. Art direction is not.*
