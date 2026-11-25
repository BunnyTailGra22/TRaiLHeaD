---
name: race-plan
description: Build a trail-race pacing and fueling plan from the runner's own data (course GPX + checkpoints/cutoffs, 劍中劍 benchmark EP/h, readiness, personal terrain factors, tested fuel kit), and calibrate it after the race from the FIT file. Use when the user asks for a race plan, 比賽計畫, 配速計畫, 完賽時間預估, 關門/cutoff check, 補給計畫, or 賽後分析/校準 for a trail or mountain race.
---

# Race plan (v0.2)

Turns the Race plan framework (`references/framework.md`) into a repeatable procedure.
Method is generic; everything personal lives in `profile.yaml`.

**Core rule:** race EP/h ≈ 劍中劍 EP/h (last 6 weeks) × 0.70–0.73; section time = section EP ÷ (race EP/h × personal terrain factor); stops added separately. EP = km + climb m / 100.

## Inputs

| Input | Need | How to get it |
|---|---|---|
| Course GPX with elevation | essential | race website; put in a new folder per race |
| Checkpoints CSV (km or lat/lon, cutoffs, aid, surface) | essential | build from the race guide; format in `scripts/split_course.py` docstring; example in `examples/ft40-2026/checkpoints.csv` |
| 劍中劍 EP/h, last 6 weeks | essential | Garmin sync sheet (Activities tab) if the Google Sheets connector works; otherwise ask the user |
| Readiness: load ratio, HRV, resting HR (race week) | essential | Garmin sync sheet (TrainingLoad, Sleep tabs) or ask |
| Mandatory gear list | essential | race rules for the distance; list it by hand |
| Own FIT from a past edition, peers' CP splits | nice to have | sharpen section shape; see framework "No course file?" ladder |

Ask only for what is missing. Confirm whether each cutoff is **leave-by** or **arrival** — the scripts treat cutoffs as leave-by.

## Workflow

Run scripts with the skill path: `S=.claude/skills/race-plan` from the TRaiLHeaD repo root.

1. **Course** — split and classify:
   ```
   python3 $S/scripts/split_course.py --gpx course.gpx --cp checkpoints.csv --out sections.json --name "<race>"
   ```
   Check the printed terrain classes against what the user knows of the course (rules: `references/terrain-rules.md`). Fix wrong ones with the `surface` or `terrain` column and rerun. Surface (road / forest_road) cannot be read from a GPX — ask.
2. **Fitness now** — get the 劍中劍 EP/h (median of the last 6 weeks; drop sick or aborted runs).
3. **Readiness gate** — load ratio 0.7–0.9 and HRV in baseline → start on target. Outside the band → say so in the plan and start on the fallback tier.
4. **Plan** (section shape, second half, tiers, fueling):
   ```
   python3 $S/scripts/build_plan.py --sections sections.json --start 05:30 --benchmark-eph <EPH> --date <YYYY-MM-DD> --out-dir out --png
   ```
   Outputs `plan.md`, `plan.html`, `plan.png` (1080 px wide ×2, 240 DPI), `plan.json`.
   - Four tiers: stretch (target ×1.04), target (benchmark × distance-interpolated ratio), fallback (ratio_low, ×0.90 after the decision point), cutoff line (solved: zero buffer at the binding cutoff). Only the target arrives in the section table; the others appear as finish times (KPI card and 其他配速).
   - Section table (lean): km, section km, climb/descent, terrain, **EP**, **EPH** (section EP ÷ moving time; the total row includes stops, so it matches the target EPH), time, target arrival, **熱量 kcal** (carried items eaten on the section + food at the aid station it arrives at, with the items listed under the number), **飲水 ml** (plan fluid rate × section time incl. the stop), cutoff, latest leave.
   - Latest leave time per checkpoint and the binding cutoff.
   - Fuelling from the kit (no separate time list; it is folded into the table's 熱量 column) in `profile.yaml`: carbs every 45 min (shortened until ≥ 60 g/h, floor 30 min; 40 min / 70 g/h if > 9 h), moved to before long descents, bar on a second-half climb, chews on technical trail, electrolyte every 65 min, caffeine capped at 6 mg/kg. If the target still isn't met it says how many extra gels to carry.
   - `--race-eph X` overrides the benchmark; `--default-factors` uses default instead of personal factors (use for a first race or a very different terrain type).
5. **Review before handing over** — sanity-check against any past edition (own FIT or peers' splits). If the target finish differs from evidence by > 10%, say why or adjust `--race-eph`.
6. **Label** — keep the plan's 標記 line; add the mandatory gear list and any race-specific notes (sunset, water-only stations, river crossings).
7. Deliver the PNG (and md) in Traditional Chinese unless the user writes in English.

## After the race

```
python3 $S/scripts/post_race.py --fit race.fit --sections sections.json --official H:MM:SS --benchmark-eph <EPH> --out-dir out
```
- Matches checkpoints by **location** (never distance); dwell = time within 60 m of an aid station.
- Prints section EP/h, factor = section moving EP/h ÷ race EP/h (official time), the benchmark ratio, and suggested factors (average of current and this race).
- Use the official time, not the watch (watches often run past the finish).
- **Ask the user before editing `profile.yaml`.** Skip averaging for anomalous races (illness, anaemia, big effort in the prior 7 days, extreme weather) — record them in `benchmark.history` with a note instead. Bump `updated:`.
- If a rule in the framework changes, update `references/framework.md` too.

## Output style

White background, flat fills, Tableau colour-blind palette (blue #1170AA primary, orange #C85200 for cutoffs/highlights, greys for structure), Noto Sans TC + Roboto Mono (bundled in `assets/fonts`), sentence case, one key message, small muted source line. Render any custom HTML with `node $S/scripts/render.js page.html out.png 1080` then `python3 $S/scripts/png_dpi.py out.png`.

## Requirements

Python 3 with `pyyaml` and `fitdecode` (post-race only); Node with `playwright` and Chromium for PNG output.

## Limits of v0.2

- Ratio rule: 2 races (40 km and 54 km); interpolated by distance, extrapolation outside 30–60 km is a guess.
- Terrain factors: one race (FT40 2026, run 6 days after a big mountain day). Treat as provisional.
- Aid-station food is an estimate (≈70 g carbs per stop).
- No altitude correction (> 3,000 m slows climbing ~30%: lower the steep_climb/reclimb factors by hand) and no night-section adjustment.
- Gear list, weather and sunset are not generated.

## Files

- `profile.yaml` — personal parameters (ratio, factors, tiers, kit, targets)
- `references/framework.md` — the full framework (strategy, data, formulas, tiers, fueling)
- `references/terrain-rules.md` — classification thresholds and factor definition
- `scripts/` — `split_course.py`, `build_plan.py`, `post_race.py`, `render.js`, `png_dpi.py`, `common.py`
- `examples/ft40-2026/` — course GPX, checkpoints, FIT and outputs (plan reproduces the 6:55 result: target 6:56)
