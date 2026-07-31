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

> EP measures the *size* of a run and is kept that way deliberately. It is **not** the best
> predictor of the overnight recovery cost — duration is, by roughly 3× the explained
> variance, because `elev / 100` under-weights climb against the clock. See
> [RECOVERY-PATTERN.md](RECOVERY-PATTERN.md#ep-is-not-the-best-dose-variable--duration-is).
> Changing the divisor would break comparability with three years of history, so it stays.

Only activities whose type contains `run` are counted. Type is bucketed to `trail` if the
type string contains `trail`, otherwise `road`.

---

## Training tab

### Progressive Overload — Acute EP for Stimulation

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
The header note and the legend both name it as an **exponential** weighting over 4 weeks
(`chronic … (4 wk exp.)`), so the smoothing is visible in the chart rather than only here:
it is an EWMA, not a flat 28-day mean, and the distinction matters when reading how fast
the band chases a change of pace.

**Optimal Range** — the shaded band:

```
ACWR_LOW = 0.8,  ACWR_HIGH = 1.4
band     = 0.8 × chronic  →  1.4 × chronic
```

The band rides with Chronic EP, so it asks "is this week big *relative to your recent
norm*", not against any fixed target.

**Status** — each day's dot on the Acute EP line, two states rather than three:

| Position | Ratio | Colour | Meaning |
|---|---|---|---|
| Inside band | 0.8 – 1.4 | green `#7f9d78` | ✓ optimal |
| Outside band | < 0.8 or > 1.4 | red `#b3746e` | ⚠ out of range |

Above and below still mean different things — spike risk versus detraining — and the
tooltip names which. But the palette answers the binary question only, so the eye reads
"in range or not" at a glance without decoding a third hue. The Acute EP **line** is green
too; **Chronic EP is grey** `#9d9488`, dashed, along with the band fill, so the whole
reference apparatus recedes and colour only ever means the reading.

This is the shared load palette (`LOAD_IN` / `LOAD_OUT` / `LOAD_REF` in `index.html`),
used identically by 7-Day Acute Load beside it — the pair sits side by side, so green and
red must mean the same thing in both.

**Header note** — `acute N (7d exp.) · chronic N (4 wk exp.)`. The ratio and its verdict
are deliberately **not** shown. The dots already say in-range or not, and a headline number
invited reading the ratio as a score when it self-centres near 1.0 by construction (see the
deviation note below). The figure is still in the per-day tooltip.

**Garmin Recovery / Strained** are painted as vertical washes behind the curves, the same
`_loadStatusBands` plugin and the same colours as on 7-Day Acute Load beside it — so a bad
stretch lines up visually across both models.

They are joined **by date key, not by index**: this series starts with the first activity
(2024-01 here) while the TrainingLoad tab starts 2026-01, so index alignment would be
meaningless. Days with no TrainingLoad row simply carry no band. The key is built from
**local** date fields (`localDayKey`), because the EP grid keys on local midnight while the
sheet's date strings parse as UTC — comparing `Date` objects directly slips a day in any
timezone behind UTC.

**View scope** — 4 / 8 / 13 / 26 wk pills (default 8) pan the x-axis only. Acute and
chronic are computed over full history and then sliced, so the curves themselves never
change with the scope; only how much of them you see does.

> **Deviation from the literature.** Textbook ACWR runs both windows over the same daily
> load series. Here Chronic is a second smoothing pass over the *Acute* curve, so it
> chases Acute with a lag and the ratio self-centres near 1.0. The chart reads as "change
> of pace vs. your own recent trend" more than as load against an independent fitness
> baseline. The 1.4 upper bound is also looser than the commonly cited 1.3. Worth knowing
> before comparing these numbers against published thresholds.

The bands do carry recovery information — watch days run at 22% above the band against 12%
inside it — but *below* the band is not a rested state: it collects illness and travel weeks
and has the worst RHR of the three. Measured in
[RECOVERY-PATTERN.md](RECOVERY-PATTERN.md#does-the-progressive-overload-band-track-recovery).

**This chart cannot judge progression, only spike risk.** Because chronic is a second
smoothing of acute, the ratio is scale-free: across 2026 the episode where VO₂max fell and
the one where it rose had the same ACWR median (1.08 vs 1.09) while their chronic EP
differed by a third. Nothing on the Training tab judges progression — the level and slope
that would are worked out in [PROGRESSION.md](PROGRESSION.md) and its script, not charted.

### 7-Day Acute Load — Against the Ceiling

Garmin's own `Acute Load` (its 7-day exponentially weighted load), plotted against the
level above which Garmin's own Recovery or Strained flag has always followed. Nothing is
derived from EP here — this is the second opinion, sitting beside Progressive Overload.

**The ceiling is computed, not a constant:**

```
CEIL_LOOKAHEAD = 14 days
CEIL_MIN_FLAGS = 3
FLAG_STATES    = RECOVERY | STRAINED
ceiling = max(acute[i])  over all i where no flagged day falls in (date[i], date[i]+14d]
```

Deriving it keeps the rule honest as data accumulates instead of freezing a number that
goes stale. The look-ahead walks **by date, not by row index**, so a gap in the sheet
cannot silently shorten the window. With fewer than `CEIL_MIN_FLAGS` flagged days the
ceiling is `null` and the rule is simply not drawn — a missing line, never a guessed one.

On Jan–Jul 2026 it lands at **890**: the three spikes above it (1055, 921, 937) were each
followed by Recovery within 6–11 days. Below it there is no dose-response —
days at 400–850 get flagged 30–38% of the time. It is a threshold, not a slope.

| Position | Marker | Colour |
|---|---|---|
| Under the ceiling | ● small | green `#7f9d78` |
| Over | ● large | red `#b3746e` |

Same shared load palette as Progressive Overload, and the same grammar: the **ceiling rule
is grey** `#9d9488` dashed, like Chronic EP is there. The dots that cross already carry the
warning — a red rule would say it twice. Size doubles on a crossing so the reading survives
greyscale, per the encoding rule in DESIGN.md.

Garmin's Recovery and Strained stretches are painted as vertical washes behind the line by
the `_loadStatusBands` plugin — Chart.js has no band primitive on a category axis. Bands
are passed as **plugin options**, not hung off the config object: Chart.js wraps that in
its own `Config`, so a stray property on it never reaches the chart.

**View scope** — 4 / 8 / 13 / 26 wk pills (default 26). The ceiling is derived from full
history, so panning the view never moves the rule; only the crossing count in the header
note changes.

> Read the flag as the *trough*, not the summit. Every Recovery onset in this data landed
> on a day when acute load had already fallen to 296–452 at ratio 0.5–0.6, after a peak in
> the preceding fortnight. 890 is not the load that hurts — it is the load that could not
> be held. And Training Status is not a load model: Garmin folds in HRV and sleep, which is
> why the one Strained episode began at a below-median load of 496.

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
| TrainingLoad | `TrainingLoad!A1:G1300` | 7-Day Acute Load vs the ceiling |

**Activities columns** (name-mapped, configurable): Start Time, Distance (km), Elevation
Gain (m), Duration (min), Type. `Activity Name` is read if present, for 專項 categories.

**Sleep columns**: Date, Resting HR (bpm), Overnight HRV (ms), Total (min), Sleep Score,
Avg SpO₂, Avg Respiration *(all configurable)*; Quality, Sleep Start, Sleep End, Baseline
Low (ms), Baseline High (ms), 7d Avg (ms), HRV Status *(hardcoded header names)*.

**Biometrics columns** (all hardcoded): Date, Weight (kg), BMI, Body Fat %, Body Water %,
Muscle Mass (kg), Bone Mass (kg), Visceral Fat, Metabolic Age, Physique Rating.

Lookup is by header name, case-insensitive, so column order in the sheet does not matter.
A missing column resolves to `-1` and yields `null` values rather than an error.

**TrainingLoad columns** (all hardcoded): Date, Acute Load, Chronic Load, Load Ratio,
Training Status. VO₂ Max and Training Readiness are in the tab but **not read** — see the
Progression section for why VO₂max is kept out of the charts.

> The `TrainingLoad` tab *upserts* rather than appending, because Garmin revises recent
> load figures for days afterwards. Anything reading it must expect rows to change, not
> just accumulate — the last week of 7-Day Acute Load can move without any new training.
> It also starts far later than Activities (2026-01 here, against 2024-01), so the chart
> covers a shorter window than the rest of the Training tab and **hides itself entirely**
> when the tab is absent rather than rendering an empty frame.
>
> Reading it does **not** make it the source for Progressive Overload. That chart still
> computes its own ACWR from EP, so the model stays inspectable and trail elevation is
> weighted in. The two sit side by side deliberately: one model this repo can explain,
> one Garmin's, as an independent second opinion.
