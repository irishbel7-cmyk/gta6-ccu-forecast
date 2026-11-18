# GTA VI Twitch CCU Forecast

[![gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![Rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/irishbel7-cmyk/gta6-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![Reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/irishbel7-cmyk/gta6-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)

Hour-by-hour forecast of the Twitch "Grand Theft Auto VI" category's concurrent
viewers over the 24 UTC hours of release day (2026-11-19), from the end of the
first hour on. Given hour 1's print, it emits 23 rows (hours 2..24) of five
quantiles (5/25/50/75/95).

Method: each past big launch in the case's `comparables` is aligned to its own
`day_start`, and the ratio `viewers(hour h) / viewers(hour 1)` is collected per
hour. Comparables are filtered to SullyGnome `Tier: comparable` rows and
weighted toward the shape GTA VI shares — console-only, midnight-local rolling
unlocks (PS5/Xbox). The center is the weighted median ratio (robust against
simultaneous-global launch spikes); the spread is the stddev of the log ratios,
floored and scaled. Quantiles are `p1 * center * exp(z_tau * spread)` with the
standard-normal `z`. No network, Python standard library only.

## Run

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Built for [make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/bounty/gta6-twitch-ccu-forecast-01). License: MIT (see `LICENSE`).
