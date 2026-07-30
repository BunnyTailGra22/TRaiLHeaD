# TRaiLHEAD — Architecture

How the dashboard is put together and how data moves through it.

## Shape of the thing

A **single self-contained HTML file**. No build step, no bundler, no framework, no
package.json. Open it in a browser and it runs.

```
index.html              the dashboard (HTML + CSS + JS in one file)
training_dashboard.html byte-identical copy of index.html
prototype-monthly.html  scratch prototype, not part of the site
README.md               what this is, how to run it, what to know before editing
tokens/                 design tokens, reference only — not loaded at runtime
  trailhead-tokens.css
  trailhead-tokens.json
docs/                   these documents
```

`index.html` is what GitHub Pages serves. `training_dashboard.html` is a duplicate kept
for the descriptive filename. **They must stay identical** — every change is made once
and copied across (`cp index.html training_dashboard.html`). Nothing enforces this
automatically, so it is a manual step on every commit that touches the dashboard.

The only external dependency is Chart.js 4.4.1, pulled from cdnjs at page load. There is
no offline fallback: no CDN, no charts.

## Runtime flow

```
initGate()
   └─ password ok / already stored
        └─ loadConfig()          localStorage → cfg  (hardcoded sheet id + key win)
             └─ loadData()
                  ├─ fetchRange(Activities!A1:L5000)   ─┐
                  ├─ fetchRange(Sleep!A1:V5000)         ├─ Promise.all, Sheets v4 REST
                  └─ fetchRange(Biometrics!A1:J3000)   ─┘
                       ├─ parseSleepRows()   → sleepMap  { 'YYYY-MM-DD': {...} }
                       ├─ parseBiometrics()  → _bodyComp [ {date, weight, ...} ]
                       └─ processSessions()  → sessions  [ {date, dist, elev, ep, ...} ]
                            └─ renderAll(sessions, sleepMap)
                                 └─ every chart renderer, in order
```

`loadSampleData()` bypasses the fetch entirely and synthesises three years of sessions
plus a sleep map, then calls `renderAll` — the same path the real data takes.

The **`TrainingLoad`** tab is deliberately not fetched here (see SPEC.md). The only thing
that reads it is `analysis/progression.py`, offline, for VO₂max — the dashboard itself stays
on its own EP-derived model.

## Offline analysis

`analysis/` is not part of the site and is never served. Two standard-library scripts read
the same sheet and reuse the documented formulas, so their findings describe the metrics as
the charts actually define them:

| Script | Reproduces |
|---|---|
| `load_recovery.py` | `docs/RECOVERY-PATTERN.md` |
| `progression.py` | `docs/PROGRESSION.md` |

`progression.py` imports its loaders and model functions from `load_recovery.py` — same
directory, so `sys.path[0]` resolves it with no packaging. Both take `--cache DIR` to reuse
raw JSON instead of re-fetching.

## Data model

Three structures, built once per load and held in module-level state:

| Global | Shape | Built by |
|---|---|---|
| `_sessions` | array of session objects, date-ascending | `processSessions()` |
| `_sleepMap` | object keyed `YYYY-MM-DD` | `parseSleepRows()` |
| `_bodyComp` | array of body-composition records, date-ascending | `parseBiometrics()` |

A **session** carries `date, dist, elev, hrs, type ('road'|'trail'), ep, name, year,
month, week` plus that day's sleep fields joined in by date key. Only rows whose activity
type contains `run` survive parsing.

A **sleepMap entry** carries `rhr, hrv, sleepMins, sleepScore, spo2, resp, quality,
start, end` and the HRV-status block `hrvBaseLo, hrvBaseHi, hrv7d, hrvStatus`.

Column lookup is **by header name, case-insensitively** (`ci()`), not by position, so
columns can be reordered in the sheet. Names are configurable in the ⚙ panel for the
common fields; the rest (`Quality`, `Sleep Start`, `Sleep End`, the HRV block, all of the
Biometrics tab) are hardcoded header strings.

Every value goes through `num()` — blank, non-numeric, and comma-decimal cells all
resolve to `null` rather than `NaN`, and **`null` means "no data", never zero**. Renderers
are expected to produce a gap rather than invent a value.

## Rendering

Each chart is a `render*(data)` function that owns one canvas. The pattern is uniform:

1. Slice/derive the series it needs from `_sessions` or `_sleepMap`.
2. Write its stat cards and header note into the DOM by id.
3. Build `datasets` + `options` (starting from `chartOpts()`).
4. `destroy()` the previous Chart instance, construct a new one.

Step 4 is not optional — Chart.js throws *"Canvas is already in use"* if a chart is
constructed over a live one. Every renderer keeps its instance in a `let _xChart = null`
module global for exactly this reason.

**Scope pills** (`.rpill`) never refilter source data. They set a module-level `_xWeeks`
/ `_xDays` variable and re-run the renderer. `renderProgressionChart` also keeps its
percentile panel on **full** history for the same reason: "where you sit" must not move when
the scope changes. Derived series that need history — rolling
baselines, EWMAs — are always computed over **full history and then sliced** to the
visible window, so a band is already warmed up at the left edge instead of ramping from
zero. `renderHrvStatus` is the one exception: it filters by date cutoff first.

**Tab switching re-renders.** A chart built while its panel is `display:none` measures
0×0, so `switchTab()` re-runs every renderer for the panel being shown.

**Resize re-renders only across the phone breakpoint.** A debounced `resize` listener
compares `isPhone()` (≤600px) to its previous value and only does full work when it
flips; otherwise Chart.js's own responsive resize handles it.

## Custom Chart.js plugins

Three things Chart.js can't draw natively are hand-rolled as plugins with an
`afterDatasetsDraw` hook onto the 2D context:

- `_boxPlugin` — box-and-whisker for the EPH distribution chart (whiskers, IQR box,
  median rule, jittered raw dots).
- `_rasterMedianLines` — median bedtime / wake vertical rules on the sleep raster.
- Baseline **bands** are not a plugin: they are two line datasets, an invisible upper
  bound followed by a lower bound with `fill:'-1'`, and the upper is hidden from the
  legend by a label filter (`item.text !== 'upper'`).

## Config and persistence

`cfg` holds the spreadsheet id, API key, tab ranges, and column-name mappings. It
round-trips through `localStorage` under `STORAGE_KEY`, and every ⚙ input auto-saves on
`input`. The sheet id and API key are **hardcoded constants that overwrite whatever was
stored** on every `loadConfig()`, so the panel's fields for those two are display-only in
practice.

## Access gate

A client-side password gate: MD5 of the typed password is compared against a constant
hash, and on success the hash is written to `localStorage` so the device stays unlocked.

This is **obfuscation, not security**. The hash, the spreadsheet id, and the API key are
all in the page source, which anyone can read. It keeps a casual visitor out of the URL;
it does not protect the data. The real control is the Google Sheets sharing setting and
the API key's own restrictions.

## Conventions worth keeping

- Comments explain **why**, especially where a line looks removable — `spanGaps:false`
  ("never fake a baseline"), the `new Date(d)` copy in the daily grid loop, the
  longest-key-first status matching that stops `UNBALANCED` matching `BALANCED`.
- Colour is never the sole carrier of meaning on the recovery charts; shape carries it
  too. See DESIGN.md.
- Chart heights live in CSS on the `.chart-box` wrapper, one id per chart. Paired cards
  in a `.two-col` row have their heights tuned so the two plot areas sit level.
