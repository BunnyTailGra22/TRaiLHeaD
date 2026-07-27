# TRaiLHEAD — Metric Spec

Every derived number in the dashboard, and how it is computed. Formulas here are the
source of truth for what the charts mean.

## EP — Effort Points

```
EP = distance_km + elevation_gain_m / 100
```

One number for the size of a run, treating **100 m of climb as equivalent to 1 km flat**.
Every load metric in the Training tab is built on it.

**EPH** = `EP / hours` — effort density, i.e. how hard a session was rather than how big.

Only activities whose type contains `run` are counted. Type is bucketed to `trail` if the
type string contains `trail`, otherwise `road`.

---

## Training tab

### Progressive Overload — Acute EP vs Optimal Range

An ACWR (acute:chronic workload ratio) model over a **gap-free daily EP series**: sessions
summed per calendar day, from the first session through `max(today, last session)`, with
**rest days contributing 0**. Rest days are real data points, not gaps — that is what
makes the decay actually decay.

**Acute EP** — exponentially-weighted rolling *sum*, 7-day time constant:

```
ACUTE_TAU   = 7
ACUTE_DECAY = exp(-1/7) ≈ 0.8669
acute[i]    = ep[i] + acute[i-1] × ACUTE_DECAY
```

A workout enters at 100% of its EP and fades: ~50% left after 5 days, ~37% after 7, ~24%
after 10, ~5% after 3 weeks. Being a sum rather than an average, its magnitude sits at
roughly one week's worth of EP.

**Chronic EP** — exponentially-weighted moving *average* of the acute series:

```
CHRONIC_WEEKS = 4                                  (fixed — not user-selectable)
α             = 1 - exp(-1 / (CHRONIC_WEEKS × 7))
chronic[i]    = chronic[i-1] + α × (acute[i] - chronic[i-1])
chronic[0]    = acute[0]                           (seed)
```

The 4-week window is **fixed by design**. It is the model's definition of "what you are
accustomed to", not a view preference — if it moved, the optimal range would move
underneath the very reading it is meant to judge, and two sessions could not be compared.
The header note names both time constants (`acute … (7d) · chronic … (4 wk)`) so the
fixed windows stay visible now that there is no pill showing them.

**Optimal Range** — the shaded band:

```
ACWR_LOW = 0.8,  ACWR_HIGH = 1.4
band     = 0.8 × chronic  →  1.4 × chronic
```

The band rides with Chronic EP, so it asks "is this week big *relative to your recent
norm*", not against any fixed target.

**Status** — each day's dot on the Acute EP line:

| Position | Ratio | Colour | Meaning |
|---|---|---|---|
| Above band | > 1.4 | red `#b3746e` | ⚠ spike risk |
| Inside band | 0.8 – 1.4 | dark `#453f37` | ✓ optimal |
| Below band | < 0.8 | gold `#bd9a4f` | ↓ detraining |

**View scope** — 4 / 8 / 13 wk pills (default 8) pan the x-axis only. Acute and chronic
are computed over full history and then sliced, so the curves themselves never change
with the scope; only how much of them you see does.

> **Deviation from the literature.** Textbook ACWR runs both windows over the same daily
> load series. Here Chronic is a second smoothing pass over the *Acute* curve, so it
> chases Acute with a lag and the ratio self-centres near 1.0. The chart reads as "change
> of pace vs. your own recent trend" more than as load against an independent fitness
> baseline. The 1.4 upper bound is also looser than the commonly cited 1.3. Worth knowing
> before comparing these numbers against published thresholds.

### Cumulative EP — Year-over-Year
Running cumulative total by day-of-year, one line per year, metric switchable between
Total EP / Distance / Elevation / Sessions.

### Monthly EP — Road vs Trail
Stacked bars, one year at a time, EP split by session type.

### 專項訓練 Seasonality
One bubble per qualifying session: x = date within the calendar year, y = EPH, bubble
**area ∝ EP**, colour = category. Categories are matched **most-specific first**, so a
session only ever lands in one:

| Category | Test |
|---|---|
| 劍中劍 | name contains 劍中劍 |
| 劍% | name contains 劍 |
| 三進 | name contains 三進 |
| ≥50 km | distance ≥ 50 |
| >20 km | distance > 20 |

### Distribution by Category
Hand-rolled box-and-whisker per category: whisker min→max, box Q1→Q3, median rule, plus
faint jittered dots for the raw sessions. Quartiles by linear interpolation between order
statistics.

### Recent 8 Weeks Load Summary
Table of the last 8 ISO weeks: EP, distance, elevation, hours, session count, EPH, and
the road/trail split as a percentage of that week's EP.

---

## Recovery tab

### HRV Status — Overnight HRV vs Baseline Range

Straight from Garmin — nothing is derived. Plots nightly `Overnight HRV (ms)` against
Garmin's own `Baseline Low (ms)` / `Baseline High (ms)` band and its `7d Avg (ms)` line.

Baseline bounds are **forward-filled** (and leading blanks back-filled) so the band spans
the full width instead of fragmenting on rows where Garmin left the columns empty.

Overnight HRV is drawn as **dots only, no connecting line** — the line implied a
continuity across nights that the data does not have. Each dot is shaped *and* coloured by
Garmin's `HRV Status`:

| Status | Marker | Colour |
|---|---|---|
| Balanced | ● circle | green `#7f9d78` |
| Unbalanced | ■ square | orange `#c08552` |
| Low | ▲ triangle | red `#ab5a52` |
| Poor | ▲ triangle | deep red `#8f3f38` |

The ramp is deliberately green → orange → red → deeper red, so severity reads as heat even
before you consult the legend. Poor is a darkened Low rather than a new hue, so the two most
serious states group visually.

Status matching is exact-first, then substring with **longest key first** — otherwise
`UNBALANCED` would match on `BALANCED`. Unknown/blank status falls back to grey `#9d9488`.

Scope: 4 / 8 / 13 / 26 wk (default 8), applied as a date cutoff before rendering.

### Recovery Vitals — Nightly vs Personal 30-day Baseline

Three sleep-derived vitals, each judged against **its own** rolling personal baseline.

```
window  = trailing 30 calendar days, STRICTLY BEFORE the day itself
min n   = 10 non-null days in that window, else no baseline (a gap, not a guess)
centre  = median of the window          (robust to one bad night)
spread  = max(sample SD, sdFloor)       (sdFloor guards a zero-width band)
band    = median ± spread
```

Excluding the day itself is deliberate: tonight's spike must not widen the band that
judges tonight.

| Vital | Bad direction | dp | sdFloor |
|---|---|---|---|
| Resting HR | high (+1) | 0 | 0.8 |
| Avg SpO₂ | low (−1) | 1 | 0.4 |
| Avg Respiration | high (+1) | 1 | 0.3 |

**Sign-normalised z** — the key trick. Positive always means *toward worse recovery*, for
every vital, regardless of which direction is bad for that metric:

```
z = bad_sign × (value - median) / spread
```

**Status** — each dot is shaped and coloured by z, on the same three-state scale:

| z | Status | Marker | Colour |
|---|---|---|---|
| z < −1 | Above baseline | ● circle | blue `#6f97a6` |
| −1 ≤ z ≤ 1 | Within baseline | ■ square | green `#7f9d78` |
| z > 1 | Off baseline | ▲ triangle | red `#ab5a52` |

Green marks the *expected* state here — "within your normal" is the healthy reading, so it takes
the reassuring colour. Blue (not green) marks Above baseline because better-than-usual is
noteworthy rather than a goal, and it must stay visually distinct from "normal".

Dots only, no connecting line, same reasoning as the HRV chart.

**"All (deviation)" mode** plots all three z-series together. There, **colour stays the
metric identity and shape alone carries the status** — recolouring by status would fuse
the three series into one indistinguishable cloud.

**Watch day** — the co-movement flag: a night where **≥2 of 3** vitals sit ≥1 SD on their
bad side. Requires all three vitals present; otherwise the night is "not scored" rather
than counted as clean.

Computed over full history then sliced to the scope (4 / 8 / 13 / 26 wk, default 8), so
the 30-day window is 30 *calendar* days and the band is warm at the left edge.

### Sleep quality scale (shared)

**One** colour scale for both sleep charts. They sit side by side; a colour must mean the
same thing in each.

| Band | Score | Colour |
|---|---|---|
| Excellent | ≥ 90 | slate blue `#5f7d8c` |
| Good | 80 – 89 | sage green `#7f9d78` |
| Fair | 60 – 79 | gold `#bd9a4f` |
| Poor | < 60 | rose `#b3746e` |

`sleepQuality(quality, score)` prefers Garmin's own `Quality` label and falls back to the
score bands (Garmin's own cutoffs) when the column is absent — which the raster needs,
having no quality column of its own. No score and no label → grey `#9d9488`.

### Sleep Consistency — one bar = one night
One horizontal floating bar per night, bedtime → wake, on a clock axis running from 18:00
(`hrsSince18`, so an evening→morning night maps to a single monotonic 0–24 range).
Newest night on top. Median bedtime and median wake are drawn as dashed vertical rules.
Regularity is reported as the **standard deviation of bedtime in minutes** — aligned bar
edges mean a consistent schedule. Scope 30 / 60 / 90 d.

### Sleep Duration → Score
Scatter, x = duration (h), y = sleep score, colour = shared quality scale, one dataset per
band so the legend is interactive. The most recent night is drawn as a large hollow ring.
Pearson **r** and the regression are computed on duration vs score and reported in the
header, with |r| bucketed as negligible (<0.2) / weak (<0.4) / moderate (<0.6) / strong.
Scope 30 / 60 / 90 / 180 / 365 d.

### Body Composition
Straight plots of the Biometrics tab: weight, body fat %, muscle mass, BMI, body water %,
visceral fat. Stat cards show the latest non-null reading per metric.

---

## Source data

Google Sheet, three tabs, read via the Sheets v4 REST API.

| Tab | Default range | Used for |
|---|---|---|
| Activities | `Activities!A1:L5000` | sessions, all Training-tab charts |
| Sleep | `Sleep!A1:V5000` | sleep map, HRV, vitals, both sleep charts |
| Biometrics | `Biometrics!A1:J3000` | body composition |

**Activities columns** (name-mapped, configurable): Start Time, Distance (km), Elevation
Gain (m), Duration (min), Type. `Activity Name` is read if present, for 專項 categories.

**Sleep columns**: Date, Resting HR (bpm), Overnight HRV (ms), Total (min), Sleep Score,
Avg SpO₂, Avg Respiration *(all configurable)*; Quality, Sleep Start, Sleep End, Baseline
Low (ms), Baseline High (ms), 7d Avg (ms), HRV Status *(hardcoded header names)*.

**Biometrics columns** (all hardcoded): Date, Weight (kg), BMI, Body Fat %, Body Water %,
Muscle Mass (kg), Bone Mass (kg), Visceral Fat, Metabolic Age, Physique Rating.

Lookup is by header name, case-insensitive, so column order in the sheet does not matter.
A missing column resolves to `-1` and yields `null` values rather than an error.

> The sheet also carries a **`TrainingLoad`** tab (Garmin's own acute/chronic load, ACWR,
> training status, VO₂ max, training readiness), written by `garmin_google_sync`. The
> dashboard does **not** read it. Progressive Overload deliberately computes its own ACWR
> from EP so the model is inspectable and trail elevation is weighted in — Garmin's figures
> are kept alongside as an independent second opinion, not as the chart's source.
