# TRaiLHEAD — Defining Optimal Training Load

What "optimal training load" means here, why the Progressive Overload chart cannot define
it, and what VO₂max can and cannot support. Every number is reproduced by
`analysis/progression.py`.

Data: **2024-01-05 → 2026-07-30** for load and recovery; VO₂max only **2026-01-01 →
2026-07-30** (211 days).

---

## The problem: ACWR is scale-free

Progressive Overload looks like the chart that should answer "what load is optimal". It
cannot, and your own data shows why. Splitting 2026 at the VO₂max trough and its
post-trough peak gives three episodes:

| Episode | VO₂max | ACWR median | in band | **chronic EP median** | chronic drift |
|---|---|---|---|---|---|
| Jan 1 – Mar 21 | 50.6 → 49.5 *(falling)* | **1.08** | 69% | **39.3** | +1.7 |
| Mar 22 – May 14 | 49.5 → 50.8 *(rising)* | **1.09** | 80% | **52.7** | +10.1 |
| May 15 – Jul 30 | 50.8 → 50.7 *(plateau)* | 0.87 | 62% | 41.7 | −11.5 |

**The falling and rising episodes have the same ACWR median — 1.08 and 1.09 — while their
chronic EP differs by a third.** The ratio cannot separate the block where VO₂max dropped
from the block where it climbed. [SPEC.md](SPEC.md) already names the mechanism: chronic is
a second smoothing pass over acute, so the ratio self-centres near 1.0 no matter what
absolute load it is riding on.

That is not a bug. ACWR is a **spike-risk** instrument and a good one — the previous
analysis found watch days at 22% above the band against 12% inside it. But spike risk and
progression are different questions, and a scale-free number cannot answer the second one.

The in-band share is not useless (it is highest in the rising block, 80%) but it is a
weaker and noisier signal than the chronic level sitting right next to it.

---

## The definition: level, slope, ceiling

Progressive overload needs three terms. The dashboard previously had one.

### 1. Ceiling — don't spike *(unchanged)*

ACWR upper bound **1.4**, exactly as Progressive Overload already draws it. This is the
only one of the three that was already validated against recovery data. No change.

### 2. Slope — ramp at 3–7 %/week

Chronic-EP growth over the trailing 28 days, expressed as %/week, scored against the
recovery cost over the **following** 14 days — what the ramp cost you, not how you felt
during it:

| Ramp | days | watch-day % | RHR z next 14d | chronic median |
|---|---|---|---|---|
| shedding < −5 %/wk | 106 | **22%** | **+0.338** | 17.6 |
| easing −5..0 | 314 | 15% | −0.036 | 22.1 |
| building 0..3 | 180 | 15% | −0.030 | 31.6 |
| **ramping 3..7** | 170 | **12%** | **−0.111** | 45.1 |
| hard ramp 7..12 | 77 | 13% | +0.082 | 37.8 |
| spiking > 12 | 56 | 12% | −0.063 | 24.9 |

**Ramping at 3–7 %/week was your best-tolerated state** — the lowest watch-day rate and the
best resting HR of any band, better than easing off. This band is not imported from the
literature; it is where your own recovery markers were best. That it lands close to the
familiar "add 5–10% a week" heuristic is a coincidence worth noting, not the reason for it.

**Shedding load was the worst state by a wide margin** (22% watch days, RHR +0.338). That
fits [RECOVERY-PATTERN.md](RECOVERY-PATTERN.md): the detraining band collects illness and
travel rather than rest, so a falling chronic load is usually the *consequence* of poor
recovery, not a route to good recovery.

Your own distribution: p10 −5.2, median +0.5, p90 +9.3 %/wk. A 3–7% target is inside what
you already do.

> **The caveat that limits this table.** The 7–12 and >12 rows look harmless, but their
> chronic medians are 37.8 and 24.9 — big percentage ramps happened from a *small base*,
> which is cheap. A 12% week on a chronic of 20 is a different event from a 12% week on a
> chronic of 55. Slope is confounded by level, which is exactly why the definition needs
> both terms and neither alone. Do not read "spiking >12 is fine".

### 3. Level — chronic EP, as your own percentiles

| p10 | p25 | median | p75 | p90 | now |
|---|---|---|---|---|---|
| 15 | 18 | 27 | 43 | 55 | **43** (75th pct) |

The one productive episode ran at ~53. That is n=1, so the dashboard reports **percentiles,
not a target** — enough to show that level is the axis that moved, not enough to prescribe
a number.

---

## VO₂max: directional only, and here is exactly why

The tempting number is spectacular and mostly an artifact. Preceding-28-day EP against the
next 28 days of VO₂max change gives **r = +0.777, naive p < 0.000001** — computed on
*overlapping daily windows* of two series whose lag-1 autocorrelation is 0.980 (VO₂max) and
0.997 (chronic EP). 211 days of daily-sampled 42-day windows is about **5 independent
blocks, not 211.** That is textbook spurious regression.

Under a circular block permutation that keeps the serial structure in the null:

| block length | p | null 95th pct \|r\| |
|---|---|---|
| 28d | 0.004 \* | 0.617 |
| 42d | 0.016 \* | 0.625 |
| 60d | 0.095 | 0.777 |
| 90d | 0.165 | 0.777 |

Detrending both series linearly leaves r = +0.731, block-42 p = 0.011.

**Verdict: it survives at short block lengths and fails at long ones.** Directionally
supported, not established. It rests on one seasonal swing.

The load composition of the episodes is consistent with the direction:

| Episode | EP/wk | hrs/wk | run days/wk | chronic median |
|---|---|---|---|---|
| falling | 40.9 | 4.2 | 3.5 | 39.3 |
| **rising** | **54.2** | **6.0** | 3.8 | **52.7** |
| plateau | 37.4 | 4.0 | 2.7 | 41.7 |

Note the rising block is +33% EP and +43% hours over the falling block at almost the same
number of run days — the sessions got *longer*, which is the same currency
[RECOVERY-PATTERN.md](RECOVERY-PATTERN.md) found driving recovery cost.

### Why not to fit a band to VO₂max at all

- **The episode boundaries are derived from the VO₂max series itself.** The load contrast
  above is therefore descriptive. It is n=3 episodes, not 3 trials.
- **Garmin's VO₂max is estimated from pace-at-HR**, so it partly measures "did you run
  fast" rather than "did you get fitter". A block of quality road running raises it in ways
  a block of equivalent hiking-paced climbing does not.
- **It is quantized to 0.1 and only 19% of consecutive days change at all** (40 of 210).
  The entire 7-month range is 1.4 points, about 2.8% of the value.
- Heat is unmodelled, and this is a Taipei summer.

Revisit at ~18 months of VO₂max. The instrumentation is now in place to make that
re-analysis a re-run rather than a rebuild.

---

## What the dashboard shows

**Progression — Chronic EP & Ramp Rate** (Training tab, row 3). Chronic EP on the left
axis, 28-day ramp %/week on the right, with the 3–7% band shaded. Ramp markers carry state
in shape as well as colour: ● in band, ▲ ramping hard, ▼ shedding. The paired panel gives
the current chronic level against your own percentiles.

Both series are computed over full history and then sliced to the scope pills (13 / 26 wk /
1 y), so the ramp is already warm at the left edge instead of opening with a month of
nulls. Ramp is `null` — a gap, never zero — for the first 28 days and wherever the 28-day
base is under 5 EP, because a percentage against a fortnight off is noise.

Progressive Overload is deliberately untouched. Two charts, two questions.

---

## Reproducing

```bash
python3 analysis/progression.py                       # fetch from the sheet
python3 analysis/progression.py --cache /tmp/th-cache  # cache the raw JSON
```

Standard library only; shares its loaders with `analysis/load_recovery.py`. The permutation
test is seeded, so the p-values above reproduce exactly. Sections: A the scale-free
demonstration, B the ramp-rate table, C the level percentiles, D the VO₂max episodes,
E the autocorrelation analysis.

> The TrainingLoad tab that carries VO₂max **upserts rather than appends** — Garmin revises
> recent rows for days afterwards — so re-running this can move the most recent numbers
> without any new training having happened.
