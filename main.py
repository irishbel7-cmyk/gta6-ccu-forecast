"""GTA VI Twitch CCU forecast: comparable-launch median curve in log space.

Reads one twitch-ccu-case/v1 JSON per <id>.in in the input directory and writes
<id>.out with five quantiles (0.05..0.95) of the Twitch category viewer count
for each of hours 2..24 of release day.

Method, per hour h (1-based, hour 1 = the case's hour-1 print p1):
  ratio[h] = viewers(hour h) / viewers(hour 1) across past big launches
             (the case's `comparables`, each aligned to its own day_start).
Selection: comparables whose notes carry "Tier: comparable" (dropping
early-access-contaminated and weak rows and the target's own pre-release
history), preferring midnight-local rolling console unlocks -- the same shape
as a PS5/Xbox midnight release. If fewer than 6 remain, fall back to every
tier-comparable row; if none at all, fall back to a persistence forecast.
  center[h] = weighted median of ratio[h]   (robust to simultaneous-global spikes)
  spread[h] = 0.9 * population stddev of log(ratio[h]), floored at 0.25
  q_tau[h]  = p1 * center[h] * exp(z_tau * spread[h])
with z the standard normal quantiles at the levels. Output rows are
non-decreasing by construction.
"""

import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]
MIN_SPREAD = 0.25
SPREAD_SCALE = 0.9


def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def comparable_ratios(case, hours):
    """Return list of (name, weight, [ratio per hour index 0..23])."""
    day_start = parse_ts(case["day_start"])
    rows = []
    for comp in case.get("comparables") or []:
        unlock = (comp.get("unlock") or "")
        m = re.search(r"Tier: ([a-z\-]+)", unlock)
        tier = m.group(1) if m else "none"
        if tier != "comparable":
            continue
        hourly = {}
        for pt in comp.get("hourly") or []:
            try:
                t = parse_ts(pt["from"])
            except Exception:
                continue
            idx = (t - parse_ts(comp["day_start"])).total_seconds() / 3600.0
            if float(idx).is_integer():
                hourly[int(idx)] = pt.get("viewers") or 0
        base = hourly.get(0)
        if not base or base <= 0:
            continue
        ratios = []
        ok = True
        for h in range(24):
            v = hourly.get(h)
            if v is None or v <= 0:
                ok = False
                break
            ratios.append(v / base)
        if not ok:
            continue
        # GTA VI is a console-only, midnight-local rolling unlock: weight the
        # launches that share that shape higher.
        u = unlock.lower()
        platforms = (comp.get("platforms") or "").lower()
        weight = 1.0
        if "midnight local" in u:
            weight += 2.0
        if ("ps5" in platforms or "ps4" in platforms or "switch" in platforms or "xbox" in platforms) and "pc" not in platforms:
            weight += 1.0
        if "rolling" in u:
            weight += 0.5
        rows.append((comp.get("name", "?"), weight, ratios))
    return rows


def wmedian(pairs):
    pairs = sorted(pairs, key=lambda x: x[0])
    total = sum(w for _, w in pairs)
    if total <= 0:
        return pairs[len(pairs) // 2][0]
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= total / 2.0:
            return v
    return pairs[-1][0]


def forecast_case(case, name):
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))

    rows = comparable_ratios(case, None)
    # Prefer the console midnight-local shape when there is enough of it.
    strong = [r for r in rows if r[1] >= 3.0]
    pool = strong if len(strong) >= 6 else rows

    out_hours = []
    for row in case["forecast"]:
        h = row["hour"]
        idx = h - 1
        if pool:
            pairs = [(r[2][idx], r[1]) for r in pool]
            center = wmedian(pairs)
            lv = [math.log(r[2][idx]) for r in pool]
            mean = sum(lv) / len(lv)
            var = sum((x - mean) ** 2 for x in lv) / len(lv)
            spread = max(MIN_SPREAD, SPREAD_SCALE * math.sqrt(var))
        else:
            center = 1.0
            spread = max(MIN_SPREAD, 0.15 * math.sqrt(h - 1))
        q = [p1 * center * math.exp(z * spread) for z in Z]
        out_hours.append({"hour": h, "q": q})

    return {"hours": out_hours}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
