# Race plan framework

A reusable checklist for pacing a trail race from your own data.

> **Your own data on fixed ground beats any model.** Use benchmark courses for fitness, past splits for shape, and HRV for readiness.

---

## 1. Planning strategy: seven steps, in order

| # | Step | What to do |
|---|---|---|
| 1 | **Course** | Split the GPX at decision points. Treat cutoffs as leave-by times and find the one that binds first. |
| 2 | **Fitness now** | Race EP/h ≈ 劍中劍 EP/h over the last 6 weeks × 0.70–0.73. |
| 3 | **Readiness** | Check load ratio, HRV and resting HR in race week, then decide whether to start on the target or the fallback. |
| 4 | **Section shape** | Use your own course file first, then past checkpoint (CP) splits from peers, then personal terrain factors. |
| 5 | **Second half** | Fade is the biggest unknown. State it, and check it against long benchmark runs. |
| 6 | **Tiers + cues** | Set four tiers and one decision point. Add an HR cap, a fuel kit and interval, and a stop limit. |
| 7 | **Label** | Mark every number as data-backed or assumed. |

---

## 2. Data: what to collect before planning

### Essential (always available; the plan can't be built without these)

- **Course GPX, checkpoints, cutoffs, gear list.** Check whether each cutoff is an arrival or a leave-by time. List the mandatory items for your distance.
- **Training load, HRV, resting HR trends.** These are the readiness gate: load ratio 0.7–0.9, HRV within baseline.
- **Benchmark performance: 劍 and 劍中劍.** You run the same route each time, so a change in EP/h shows a real change in fitness.
- **Recent races ÷ benchmark.** Dividing race EP/h by benchmark EP/h keeps the prediction rule calibrated.
- **Hardest recent effort and health context.** These show the fatigue you carry into the race. Illness explains outliers.

### Nice to have (sharpens the plan when available)

- **Your own FIT/GPX from this course.** This is the best calibration: real splits, real stops, and where you broke down.
- **Heart rate with every split.** It separates fitness from effort.
- **Climb rate by altitude.** Climbing slows by about 30% above 3,000 m.
- **Past CP stop times.** These are often the easiest minutes to save.
- **Weather, trail conditions, blood work.** Ferritin and Hb are the only check for anemia.

### No course file? Get the section shape from these, in order

1. **Official CP splits from past editions.** Use finishers with an ITRA score near yours.
2. **Other runners' timed tracks.** Look for Strava or Drive GPX files of the same route.
3. **Terrain model on the course GPX.** Multiply your personal terrain factors by your predicted race EP/h.
4. **Check against cutoffs.** Every tier must clear the binding cutoff with a buffer.

---

## 3. Core formulas and personal factors

These are calibrated on your races. Update them after each race.

**Effort**

```
EP   = km + climb m / 100
EP/h = EP ÷ hours            (compares effort across terrain)
```

**Prediction rule**

```
Race EP/h ≈ 劍中劍 EP/h (last 6 weeks pre-race) × 0.70–0.73
```

| Race | 劍中劍 EP/h before the race | Race EP/h | Ratio |
|---|---|---|---|
| Hmong50 2025 (54 km) | 11.6 | 8.1 | **0.70** |
| 福爾摩沙古道 40K 2026 (39 km) | 12.3 | 9.02 | **0.73** |

The longer the race, the lower the ratio, so use the low end of the range.

**Cutoff safety**

```
Latest leave time at a point = the earliest of: (each later cutoff − planned time from here to it)
```

An even pace can miss an early cutoff even when the finish time looks safe.

**Personal terrain factors**

```
Section time = section EP ÷ (race EP/h × factor)
```

| Terrain | Default | Personal | Change |
|---|---|---|---|
| Road, opening | 1.40 | **1.40** | = |
| Road, last 5 km | 1.25 | **1.12** | ▼ |
| **Steep climb > 15%** | 0.88 | **1.23** | ▲ (biggest change) |
| Re-climb, rolling up | 0.85–0.95 | **1.07–1.15** | ▲ |
| Technical mixed trail | 0.90 | **0.79** | ▼ |
| Technical descent | 1.00 | **0.87–0.90** | ▼ |
| Forest-road descent | 1.05–1.25 | **0.98** | ▼ |

The factors come from 福爾摩沙古道 40K 2026: each section's EP/h ÷ race EP/h (9.02). EP gives no credit for descending, so a descent factor below 1 is normal. The gap from the default is what to train. These values come from a single race run 6 days after a big mountain effort, so update them after the next race.

---

## 4. Plan tiers and decision point

Carry all four tiers. Switch between them; don't improvise.

| Tier | Meaning | Use when |
|---|---|---|
| **Stretch** | Best-day pace | Early splits are ahead and HR is under the cap |
| **Target** | Evidence-backed | Benchmark rule, with fade stated |
| **Fallback** | Second-half plan | Switch at the decision point if you're behind |
| **Cutoff line** | Floor, zero buffer | Front-loaded, because the early cutoff binds first |

### Decision point and in-race cues

- **Decision point:** the first binding cutoff. Compare your arrival with the target and fallback times.
- **HR cap:** cap the opening road, using your benchmark HR to set it.
- **Fuel interval:** one gel every 45 min (every 40 min if the race is over 9 h). Finish eating before long descents.
- **Stop limit:** a fixed number of minutes per aid station, written on the plan.

### Pitfalls to avoid

- ✕ Scaling an old race or an ITRA score instead of using your benchmark
- ✕ Estimating past splits with an even pace
- ✕ Aligning different years by distance instead of by location
- ✕ Assuming an even pace clears early cutoffs
- ✕ Using default terrain factors instead of your own

---

## 5. Fueling plan

Hourly targets and your tested kit, from 福爾摩沙古道 40K 2026 (body weight 62 kg).

### Hourly targets

| Item | Target | FT40 2026 |
|---|---|---|
| Carbs | 60–70 g/h (70 if the race is over 9 h) | **60** |
| Sodium | 400–500 mg/h (more in heat) | **390** |
| Fluid | 400–800 ml/h | **≈500** |
| Caffeine, total | 3–6 mg/kg (≈190–370 mg) | **5.2** (320 mg) |
| Energy replaced | 30–50% of energy burned | **48%** |

FT40 totals: 415 g carbs, 2,700 mg sodium and 320 mg caffeine in 6:55. Fueling was not the limiter.

### Tested kit: what each item is for

| Item (per unit) | Carbs g | Sodium mg | Caffeine | When | FT40 |
|---|---|---|---|---|---|
| 雙速咖啡因雙層錠 (dual-release tablet) | — | — | 200 mg | 30–60 min before the start | 1 |
| **Betery 能量果膠 PRO** (45 g gel, glucose:fructose 2:1) | 30.0 | 1.2 | — | Main fuel: one every 45 min | 6 |
| UP 咖啡因能量棒 芒果可可 (28 g bar) | 21.7 | 12 | 75 mg | On a climb, in the second half | 1 |
| UP FOCHEWS 能量軟糖 (20 g chew) | 17.9 | 5 | — | Technical trail; easy to chew | 2 |
| **水動能電解質液 PLUS 鋅** (7 g in 500 ml) | 5.0 | 442 | — | One pack every 60–70 min; supplies 98% of the sodium | 6 |
| Aid station, per stop (banana, fruit + ≈225 ml cola) | ≈70 | ≈20 | ≈22 mg | Banana and cola first; stop under 5 min | 2 |

**7 h race kit:** tablet 1 · gels 7 · bar 1 · chews 2 · electrolyte 6 · 2 aid stops → about **62 g/h carbs, 390 mg/h sodium, 5 mg/kg caffeine**.

**Rules**

- The pre-race tablet is already an effective caffeine dose (3.2 mg/kg). Add 75 mg doses only in the second half, and keep the total at or under 6 mg/kg.
- Eat solids on climbs. Finish eating before long descents, and don't eat while descending.
- Sodium comes almost entirely from the electrolyte. Skipping one pack costs about 64 mg/h.
- For races over 9 h, rehearse 70 g/h on a long 劍中劍 run first.

---

**Takeaway:** your benchmark predicts your race. Race EP/h ≈ **劍中劍 EP/h × 0.70–0.73**, personal terrain factors set the time for each section, and the tested kit fuels it at 60–70 g carbs/h.

<sub>The rule and factors come from the Hmong50 2025 and 福爾摩沙古道 40K 2026 (official 6:55:07, 9.02 EP/h) Garmin FIT files and the Garmin sync sheet. Kit values are from package nutrition labels; aid-station values are estimates. EP = Effort Points (ITRA).</sub>
