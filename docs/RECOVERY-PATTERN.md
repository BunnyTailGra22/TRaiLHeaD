# TRaiLHEAD — The Recovery Pattern

What the sheet says about how recovery responds to training load. Every number here is
reproduced by `analysis/load_recovery.py`, which reads the same Google Sheet the dashboard
reads and uses the formulas in [SPEC.md](SPEC.md).

Data: **2024-01-05 → 2026-07-30**, 938 days, 316 run days (34% of days), 4,121 total EP,
920 sleep nights.

---

## The finding

**Recovery is a one-night event.** A run costs one night of elevated resting HR and
suppressed HRV, and by the second night the markers are already back — in fact slightly
*below* where they started. Nothing measurable survives to the third night.

| Night | RHR | HRV | Sleep score | Respiration |
|---|---|---|---|---|
| **D+1** first night after | **+0.28 \*** | **+0.34 \*** | −0.04 | −0.00 |
| **D+2** | **−0.28 \*** | −0.11 | **−0.22 \*** | **−0.22 \*** |
| D+3 | −0.08 | −0.10 | −0.26 | −0.17 |
| D+4 | −0.19 | +0.12 | −0.31 | −0.24 |
| D+5 | −0.19 | — | −0.24 | −0.23 |

Units are the dashboard's own sign-normalised z, where **positive always means *toward
worse recovery***. `*` = p < 0.05. Each cell is a paired difference against **that
effort's own preceding night**, on isolated efforts only (no second run inside the
window), so the tail belongs to one run.

Read down the RHR column and the shape is the whole story: one night up, one night down,
then nothing.

### Why it's paired

The obvious test — compare post-run nights against a pool of rest nights — gives the wrong
answer here, and it's worth knowing why. Rest nights are not a neutral reference: the pool
mixes genuine easy days with illness weeks, travel and injury layoffs, all of which raise
RHR on their own. It also *contains* the D+2 nights, which are the lowest nights in the
dataset, so the reference gets dragged down by the very effect being measured.

Pairing each night against the same effort's preceding night removes all of that. The
design passes its negative control: run the identical test on rest days and the effect is
+0.048 z (p=0.46, n=389) — no signal where there should be none.

### How big, in real units

z-scores are the dashboard's language but not anyone's intuition. The same effect in bpm,
against each night's own 30-day median:

| Dose on the run day | n | Next-night RHR |
|---|---|---|
| rest day | 606 | −0.22 bpm |
| easy (EP 5–12) | 189 | +0.08 bpm |
| moderate (EP 12–20) | 67 | +0.29 bpm |
| long (EP 20+) | 37 | **+1.08 bpm** |

So the honest magnitude is **about one beat per minute after a long day, and essentially
nothing after an easy one.** The pattern is statistically clean and physiologically real,
and it is also small. It is a signal for reading trends across weeks, not for deciding
what to do tomorrow morning.

### Dose grading is weaker than the on/off signal

| Dose | n | Paired Δ RHR z at D+1 | p |
|---|---|---|---|
| all run days | 297 | +0.278 | 0.0007 \* |
| easy 5–12 | 185 | +0.281 | 0.0083 \* |
| moderate 12–20 | 66 | +0.125 | 0.4650 |
| long 20+ | 37 | +0.459 | 0.0248 \* |

Long > easy, as expected — but moderate lands *below* easy and misses significance. With
66–185 nights per tier that non-monotonicity is well inside noise, so the defensible claim
is narrow: **that you ran shows up more reliably than how much you ran.** The bpm table
above, which uses all nights rather than tiered subsets, is where the graded response
actually shows.

---

## EP is not the best dose variable — duration is

This is the actionable result. Against next-night RHR z, on 303 scored run days:

| Predictor | r | p |
|---|---|---|
| distance km | +0.075 | 0.19 |
| **EP** = dist + elev/100 | +0.151 | 0.0079 \* |
| elevation m | +0.220 | 0.0001 \* |
| **duration hrs** | **+0.271** | **0.0000 \*** |

And when all three components compete in one model:

```
RHR z(D+1) ~ distance + elevation + duration        n=303   R² = 0.082
  distance km     b = −0.026    p = 0.11
  elevation m     b = +0.00021  p = 0.51
  duration hrs    b = +0.224    p = 0.0016  *
```

**Only duration survives.** Distance and elevation both fall away once hours are in the
model — their apparent effects were duration wearing a costume. Duration alone explains
R² = 0.074 against EP's R² = 0.023: **time on feet accounts for roughly three times the
recovery variance that EP does.**

That is a coherent story rather than a contradiction. EP is a deliberate measure of *how
big a run was* — distance with climb converted into distance-equivalent — and it does that
job well. But the overnight autonomic cost tracks how long the body was working, and EP's
`elev / 100` divisor systematically under-weights climb relative to the clock: 1,000 m of
ascent adds 10 EP while adding a great deal more than 10 km worth of time. Every single-
predictor test above agrees, ranking elevation ahead of EP and EP ahead of distance.

**Recommendation: do not change EP.** It anchors every chart in the Training tab and three
years of history are comparable in its units; redefining it would invalidate all of that to
optimise a correlation of 0.27. The better move is to keep EP as the load metric and treat
**duration as the recovery-cost metric** — the load table already carries hours per week,
so the number is present, just not currently read that way.

### Trail vs road is this same fact in disguise

| Group | days | EP md | elev md | hrs md | RHR z D+1 |
|---|---|---|---|---|---|
| trail-dominant, EP 20+ | 21 | 25.3 | 1,174 m | **4.5** | +0.837 |
| road-dominant, EP 20+ | 18 | 23.0 | 493 m | **2.0** | +0.137 |

Trail days look six times costlier at matched EP — but the difference is +0.700 z with
p = 0.12, **not significant**, and the two groups differ by more than a factor of two in
hours. Surface and duration cannot be separated in this dataset, and the regression above
says the hours are what matter. This table is not independent evidence about terrain; it is
the duration finding seen from the side, and it also shows precisely how EP under-weights
climb: 25 EP of trail and 23 EP of road are nominally the same run and are nowhere near it.

---

## Does the Progressive Overload band track recovery?

Same-night recovery, grouped by the ACWR state the chart would have been showing:

| State | days | rhr z | hrv z | resp z | score z | watch-day % |
|---|---|---|---|---|---|---|
| detraining < 0.8 | 266 | +0.23 | −0.17 | +0.08 | +0.20 | 18% |
| optimal 0.8–1.4 | 531 | −0.13 | −0.03 | +0.06 | +0.15 | **12%** |
| spike risk > 1.4 | 141 | +0.09 | −0.55 | +0.31 | +0.38 | **22%** |

Partly, and with two caveats that matter.

The band does carry information: **watch days run at 22% in spike risk against 12% in the
optimal band**, nearly double, and respiration and sleep score are both worst there. The
chart's shaded region is not decorative.

But **HRV goes the other way** — z of −0.55 in spike risk means HRV sitting *above* its own
baseline. That is the 30-day rolling median at work: a sustained high-load stretch is also a
fit stretch, and the baseline travels with it, so a training block can be simultaneously
"above the band" and "HRV better than my recent normal". Do not read the HRV column here as
a contradiction of the D+1 finding; they answer different questions, one about chronic state
and one about the acute response.

And **detraining is not a clean rested state** — RHR is the worst of the three groups there
(+0.23). That band collects illness weeks, travel and injury alongside genuine easy weeks.
Low load is sometimes the *consequence* of poor recovery rather than a cause of good
recovery, and the ACWR ratio cannot tell those apart.

---

## Confidence and limits

**What the load series is not:** an artefact of the EP formula. Garmin's independently
computed Acute Load correlates with the dashboard's Acute EP at **r = +0.707** (n = 211,
p < 0.0001) over the window where both exist. Two different models of the same training
see the same shape.

Things to hold against every number above:

- **HRV covers 207 of 920 nights**, starting only 2026-01-01 — the column is blank before
  that. Every HRV figure rests on ~94 paired observations, not ~300. The D+1 HRV result is
  the most interesting number in this document and the least well supported; treat it as
  suggestive and re-run this analysis once there are two years of HRV.
- **Only 3 run days exceed EP 35**, so the top of the dose range is unmeasured. The "long
  20+" tier is doing the work of describing everything from a 20 EP road run to an 80 EP
  mountain day.
- **R² ≈ 0.08 at best.** Duration is the best predictor available and it still leaves 92%
  of next-night RHR variance unexplained. Sleep, alcohol, heat, work stress and illness all
  live in that residual. This model orders training days; it does not forecast a night.
- **Sleep score and respiration carry no next-night load signal at all** (−0.04 and −0.00,
  both p > 0.5). Their only significant movement is the D+2 dip. If you are looking for the
  cost of yesterday's run, look at RHR and HRV; the sleep-quality columns do not know
  about it.
- Correlational throughout, single subject, no intervention. "A long day is followed by one
  poor night" is well supported; "a long day *causes* one poor night" is an inference the
  design cannot make on its own.

---

## Reproducing

```bash
python3 analysis/load_recovery.py                       # fetch from the sheet
python3 analysis/load_recovery.py --cache /tmp/th-cache  # cache the raw JSON
```

Standard library only, no dependencies. Sections map to this document: A the paired dose
effect, B the lag profile, C the bpm magnitudes, D the duration finding, E trail vs road,
F the ACWR band, G the Garmin cross-check.
