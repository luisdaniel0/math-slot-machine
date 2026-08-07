"""Pull a published Stake Engine competitor's full math telemetry. ~2 seconds, no login.

    env/bin/python tools/analysis/competitor_pull.py rage-bait
    env/bin/python tools/analysis/competitor_pull.py coins-and-cauldrons mushroom-madness

The slug is the last path segment of the stakestats game URL.

⚠ THE API RETURNS EVERY VERSION. This filters to activeVersion; without that you can
easily read a retired build (Coins and Cauldrons v11 has base std dev 29.2, v13 has 59.9 --
they doubled a live game's volatility between versions).

⚠ maxMultiplier IS COST-NORMALISED, which is the trick that recovers a rival's BUY PRICES:
    cost = base_cap / maxMultiplier
Buy prices are published nowhere else.

⚠ "HIT" MEANS DIFFERENT THINGS ON DIFFERENT SITES. stakestats hitFrequency is P(>= 1x);
StakeCruncher's HIT is P(any win) and equals 100 - bust. Both are self-consistent; bust
agrees. This prints bust and derives any-win from it, so the columns are unambiguous.

What this does NOT give (use stakecruncher.com/slots-tracker/stats/<slug>/<ver>/<mode>,
which is client-rendered so it needs a browser rather than curl): MAX WIN CHANCE, median
win, top-heavy RTP, dry-streak percentiles, chance-of-multiplier-or-better.
"""
import json
import sys
import urllib.request

API = "https://stakestats.net/api/games/%s"


def pull(slug):
    req = urllib.request.Request(API % slug, headers={
        "accept": "application/json",
        "user-agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def show(slug):
    d = pull(slug)
    av = d.get("activeVersion")
    modes = [m for m in d.get("modes", [])
             if m.get("version") == av and m.get("standardDeviation") is not None]
    if not modes:
        modes = [m for m in d.get("modes", []) if m.get("standardDeviation") is not None]
        print("(no stats on activeVersion %s -- showing every version with stats)" % av)

    print("\n%s -- %s, v%s   (%d modes)" % (
        d.get("name"), d.get("publisher", {}).get("name"), av, len(modes)))
    if not modes:
        print("  no stats published for this game yet")
        return

    cap = max(m["maxMultiplier"] for m in modes)
    print("  base cap %s\n" % (format(cap, ",.0f") + "x"))
    print("  %-24s %8s %8s %9s %8s %9s %8s %11s" % (
        "mode", "cost", "RTP", "std dev", "bust%", "any win%", ">=1x%", "outcomes"))
    for m in sorted(modes, key=lambda x: -x["maxMultiplier"]):
        bust = m["bustFrequency"]
        print("  %-24s %7.0fx %7.2f%% %9.3f %7.2f%% %8.2f%% %7.2f%% %11s" % (
            m["name"], cap / m["maxMultiplier"], m["rtp"] * 100,
            m["standardDeviation"], bust, 100 - bust, m["hitFrequency"],
            format(m["events"], ",")))

    print()
    for m in sorted(modes, key=lambda x: -x["maxMultiplier"]):
        v = m["metrics"]["volatility"]
        print("    %-24s max %10s   vol rank %6d/%d (%.1f pct) %s" % (
            m["name"], format(m["maxMultiplier"], ",.0f") + "x",
            v["rank"], v["rankTotal"], v["percentile"], v["category"]))

    tpl = next((m.get("replayUrlTemplate") for m in modes if m.get("replayUrlTemplate")), None)
    if tpl:
        print("\n    replay URL format: %s" % tpl)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for slug in sys.argv[1:]:
        try:
            show(slug)
        except Exception as exc:  # noqa: BLE001 -- a bad slug should not kill the batch
            print("\n%s -- FAILED: %s" % (slug, exc))


if __name__ == "__main__":
    main()
