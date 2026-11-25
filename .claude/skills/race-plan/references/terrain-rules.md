# Terrain classification rules

Each section (checkpoint to checkpoint) gets one of seven classes. `split_course.py` applies the rules in this order; a `terrain` value in the checkpoint CSV overrides them.

| Order | Condition | Class | Personal factor (FT40 2026) |
|---|---|---|---|
| 1 | `surface = road` and the section starts in the first half | `road_open` | 1.40 |
| 2 | `surface = road` and the section starts in the second half | `road_end` | 1.12 |
| 3 | `surface = forest_road` and loss > gain | `descent_forest_road` | 0.98 |
| 4 | `surface = forest_road` and gain ≥ loss | `reclimb` | 1.10 |
| 5 | trail; min(gain, loss) ≥ 50% of max and max ≥ 4% of distance | `technical_mixed` | 0.79 |
| 6 | trail; gain > loss and gain ≥ 15% of distance | `steep_climb` | 1.23 |
| 7 | trail; gain > loss and gain ≥ 4% of distance | `reclimb` | 1.10 |
| 8 | trail; loss ≥ gain and loss ≥ 4% of distance | `descent_technical` | 0.88 |
| 9 | anything else (flat trail) | `technical_mixed` | 0.79 |

Gain and loss use a 3 m hysteresis on the GPX elevation (the same method used to calibrate the factors). Percentages are metres per 100 m of horizontal distance.

## Factor definition

```
factor = section moving EP/h ÷ race EP/h
race EP/h = course EP ÷ official finish time (stops included)
section time = section EP ÷ (race EP/h × factor) + planned stop
```

Because race EP/h includes stops and the factor uses moving time, summing section times plus stops reproduces the finish time. EP gives no credit for descending, so descent factors below 1 are normal; the gap between personal and default factors is what to train.

## When the rules get it wrong

- **Short sections (< 1.5 km)** are noisy: a 1 km connector can flip between classes. Merge it into a neighbour or override.
- **Runnable single-track descent** behaves like `descent_forest_road`; very rocky forest road behaves like `descent_technical`. Override from what the user knows.
- **Altitude > 3,000 m:** lower `steep_climb` and `reclimb` by about 30% by hand.
- **Night sections:** no rule yet; state the assumption.
