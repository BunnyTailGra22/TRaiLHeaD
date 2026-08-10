# TRaiLHEAD — Design

The visual system: palette, how meaning is encoded, layout, and the responsive rules.

## Theme

**Morandi · modern minimalist**, visibility-tuned. Muted warm-greige surfaces, deepened
marks so they stay AA-legible against the light background, and categorical colours that
also separate in greyscale.

Tokens live in `tokens/trailhead-tokens.json` and `tokens/trailhead-tokens.css`. They are
**reference only** — neither file is loaded at runtime. The live values are the CSS custom
properties in the `:root` block of `index.html`. If you change one, change both.

### Base

| Token | Value | Use |
|---|---|---|
| `--bg` | `#e9e4dc` | page background, warm greige |
| `--card` | `#f9f6f1` | cards, nav, panels |
| `--card2` | `#ece6dd` | secondary fills, pill backgrounds |
| `--border` | `#dcd4c8` | hairline borders |
| `--text` | `#453f37` | primary text, ~10:1 on card |
| `--muted` | `#6f675c` | labels, axis ticks, ~5.6:1 — WCAG AA |

### Categorical

Years are spread on **lightness as well as hue**, so the cumulative chart still reads when
printed or seen by a colour-blind viewer: 2024 `#5f7d8c` (L≈120), 2025 `#8a9a5b` (L≈146),
2026 `#a5602a` (L≈107). Road/trail reuse the 2024/2025 pair.

Biometric series each own a hue: HRV mauve `#9c8196`, sleep powder-blue `#6f97a6`, SpO₂
sage `#7f9d78`, RHR dusty rose `#b3746e`, respiration slate `#7e8aa2`, weight ochre
`#b39555`.

### Status

Two status families, because they answer different questions.

**Load & sleep quality** — a graded scale where both ends are informative:
green `#7f9d78` · gold `#bd9a4f` · rose `#b3746e` · clay `#a5602a`. Progressive Overload's
dots use dark `#453f37` for "inside the band" rather than green, because in-range is the
unremarkable case there and the eye should go to the deviations.

**Recovery status** (HRV Status, Recovery Vitals) — a heat ramp where severity should read
before the legend does: green `#7f9d78` → orange `#c08552` → red `#ab5a52` → deep red
`#8f3f38`. Plus blue `#6f97a6` for "off baseline in the *better* direction" — noteworthy,
not a goal, and kept clearly distinct from green.

Grey `#9d9488` means "no data / not scored" in both families.

The two families deliberately share green and diverge after it: green always means "this
is the state you want", while the warning hues differ so a recovery chart never reads as a
training chart.

## Encoding rules

**Colour is never the only carrier of meaning on the recovery charts.** Every status is
encoded twice — once in colour, once in marker shape — so the reading survives greyscale
and colour-blind vision:

The two channels carry different things, and keeping them separate is what makes the
system work:

- **Shape = position on the metric's own scale.** ● top tier · ■ middle tier · ▲ bottom
  tier. Purely ordinal, no judgement.
- **Colour = desirability.** Green is always "the state you want"; the warm ramp is always
  "attention".

| | ● circle | ■ square | ▲ triangle |
|---|---|---|---|
| **HRV Status** | Balanced — green | Unbalanced — orange | Low / Poor — red |
| **Recovery Vitals** | Above baseline — blue | Within baseline — green | Off baseline — red |

Note that green sits on ● in one chart and ■ in the other. That is not an inconsistency to
fix: HRV's scale is *balance-centric* (its top tier is the healthy one), while Vitals' is
*deviation-centric* (its middle tier is). Shape stays honest about scale position, colour
stays honest about desirability, and forcing either to bend would break the other.

The one place shape is *not* redundant is Recovery Vitals' "All (deviation)" mode, where
three metrics overlap: there colour identifies the metric and shape alone carries the
status.

**Nightly series are dots, not lines.** A connecting line between nights implies a
continuity the data does not have. Lines are reserved for genuinely continuous or smoothed
series — 7-day averages, 30-day medians, EWMA curves.

*One scoped exception:* the **trail** on Sleep Duration → Score joins the last four nights
in date order. It is allowed because that chart's axes are duration and score — neither is
time — so the quality-band datasets scatter consecutive nights far apart and the recent
trajectory is otherwise unreadable. The line is the change; that is the whole point of it.
It stays honest by being strictly bounded: four nights, one chart, drawn behind the dots in
neutral grey, and faded oldest → newest (`segment.borderColor`) so direction reads without
an arrowhead. It is not a licence to connect nights anywhere else.

**Baseline bands are light warm grey** (`rgba(157,148,136,0.28)`), never coloured. The
band is context; the marks are the data. All three banded charts use the same fill so a
grey band always means "the range you are being judged against".

**Gaps are gaps.** Where a baseline cannot be computed, nothing is drawn
(`spanGaps:false`) — the chart never bridges a hole and never fabricates a band.

## Legends

Two idioms, kept visually consistent (both render as a coloured dot plus a label):

- **Chart.js legend** — used where series are real datasets and clicking to toggle them is
  useful (Sleep Duration → Score, the EP charts). Configured with `usePointStyle:true`.
- **HTML `.shape-key`** in the card header — used where the categories are per-point
  encodings inside a single dataset, which Chart.js cannot legend on its own: HRV Status,
  Recovery Vitals, Sleep Consistency.

Where two charts sit side by side, their legends must agree in **colour, label, and
order**. The sleep pair is the reference case: both use the shared quality scale in the
same Excellent → Good → Fair → Poor order.

## Layout

`main` is a vertical stack of `.chart-card`s. Pairs sit in a `.two-col` grid (`1fr 1fr`,
16px gap).

**Training tab** — Year-over-Year summary cards, then three paired rows:
1. Cumulative EP | Monthly EP
2. Progressive Overload | Recent 8 Weeks — Load Summary
3. Distribution by Category | 專項訓練 Seasonality

**Recovery & Body tab** — two paired rows, then one full-width card:
1. Sleep Duration → Score | Sleep Consistency
2. HRV Status | Recovery Vitals
3. Body Composition (full width)

Rows are paired by kind: the two sleep charts together, the two
nightly-vs-baseline charts together.

### Card anatomy

```
.chart-card
  .chart-header      title (left) · shape key + note + scope pills (right, wraps)
  .metric-pills      optional — switches what the chart plots
  .bio-stat-grid     optional — 4 latest-value cards
  .chart-box#id      fixed height in CSS; the canvas fills it
```

Chart height lives on the **wrapper**, one CSS rule per id — a single source of truth, so
Chart.js manages only the bitmap and DPR. Paired cards get their heights tuned so the two
*plot areas* sit level, accounting for whatever else is stacked above them:

| id | Height | Note |
|---|---|---|
| `#perf-box`, `#raster-box` | 420px | row 1, matched |
| `#bio-box` | 330px | row 2 — taller, HRV has no metric-pill row |
| `#vitals-box` | 280px | row 2 — shorter, carries a metric-pill row |
| `#body-box` | 260px | full width |

### Pills

- `.rpill` — **scope**. Changes the time window shown. Never changes what is computed:
  derived series are calculated over full history and sliced afterwards.
- `.mpill` — **metric**. Changes which series the chart plots.

A pill row is for view state only. A parameter that defines what a metric *means* does not
get pills — Chronic EP's 4-week window is fixed for exactly this reason, and the header
note names it (`chronic … (4 wk)`) so the constant stays visible.

## Responsive

| Breakpoint | Behaviour |
|---|---|
| ≤ 1200px | stat grids **inside** a `.two-col` drop to 2×2 — 4 across in a half-width column crushes to ~110px per card |
| ≤ 900px | `.two-col` and `.grid-2x2` collapse to one column; all stat grids 2×2; chart heights reduced |
| ≤ 600px | `isPhone()` — smaller fonts, fewer axis ticks, legends move to the bottom, some point radii shrink |

`isPhone()` is a JS-side breakpoint read at render time, not a media query, because it
changes Chart.js options rather than CSS. The resize handler only does a full re-render
when this breakpoint is actually crossed.

## Typography

System font stack throughout, including chart labels. 13px base. Section titles and stat
labels are 10px uppercase with `0.08em` letter-spacing in `--muted`. Stat figures are 22px
bold, summary figures 28px. Notes and axis ticks are 11px.

## Radii

Cards 14px · stat cards 8px · pills 20px · inputs 5px.
