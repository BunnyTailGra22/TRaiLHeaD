# TRaiLHEAD

A personal trail-running and recovery dashboard. Reads a Google Sheet of Garmin data and
renders it as Chart.js visualisations — training load on one tab, sleep and recovery on the
other.

**Live:** https://bunnytailgra22.github.io/trailhead/

```
Garmin Connect  ──►  garmin_google_sync  ──►  Google Sheet  ──►  TRaiLHEAD
```

The sheet is written by [garmin_google_sync](https://github.com/BunnyTailGra22/garmin_google_sync),
a Python job that runs daily on GitHub Actions. This repo is the read-only front end.

---

## Running it

There is no build step. Open `index.html` in a browser, or serve the directory:

```bash
python3 -m http.server 8000
```

The spreadsheet ID and API key are compiled into the page, so no configuration is needed —
enter the access password and it loads. Without network access to the Sheets API, the
**Load Sample Data** button synthesises three years of plausible sessions and takes the
same render path as real data.

## What's in it

**Training tab** — year-over-year summary cards, then:

| | |
|---|---|
| Cumulative EP | Monthly EP, road vs trail |
| Progressive Overload | 7-Day Acute Load vs the ceiling |
| Recent 8 Weeks load table (full width) | |
| Progression — Chronic EP & Ramp Rate | Chronic EP percentiles |
| Distribution by Category | 專項訓練 Seasonality |

**Recovery & Body tab**

| | |
|---|---|
| Sleep Duration → Score | Sleep Consistency |
| HRV Status | Recovery Vitals |
| Body Composition (full width) | |

Two metrics carry most of the weight:

- **EP (Effort Points)** = `distance_km + elevation_m/100` — one number for the size of a
  run that treats 100 m of climb as equivalent to 1 km flat. **EPH** = `EP/hours` is its
  density. Every load chart is built on these.
- **Progressive Overload** is an ACWR model: acute load is an exponentially-weighted
  7-day sum of daily EP, chronic is a 4-week average of that, and the shaded band is
  0.8–1.4 × chronic. Above the band is spike risk, below it is detraining. Being a ratio it
  is **scale-free**, so it reads spike risk but cannot judge progression.
- **7-Day Acute Load** is the second opinion beside it — Garmin's own load, plotted against
  a *derived* ceiling: the highest acute load never followed by Garmin's own Recovery or
  Strained flag within 14 days. It computes from the data rather than being hardcoded, and
  isn't drawn at all until there are enough flagged days to calibrate on.
- **Progression** supplies the two terms the ratio throws away: the *level* of chronic EP
  against your own percentiles, and its *slope* — 28-day chronic growth in %/week, against a
  3–7 %/wk band derived from your own recovery markers rather than the literature. See
  [docs/PROGRESSION.md](docs/PROGRESSION.md).

How the two tabs relate to each other is written up in
[docs/RECOVERY-PATTERN.md](docs/RECOVERY-PATTERN.md). Short version: a run costs **one**
night of elevated resting HR and suppressed HRV and is back by the second, the effect is
about 1 bpm after a long day, and **duration predicts that cost roughly three times better
than EP does** — worth knowing before reading too much into a single EP number.

**Recovery Vitals** judges Resting HR, SpO₂ and respiration against your *own* 30-day
rolling baseline rather than absolute numbers, because 48 bpm or 95% means nothing without
knowing what is normal for you. The strongest signal is co-movement — a "watch day" is one
where two of the three sit a standard deviation on their bad side at once.

## Files

```
index.html               the whole dashboard — HTML, CSS and JS in one file
training_dashboard.html  byte-identical copy, kept for the descriptive filename
prototype-monthly.html   scratch prototype, not part of the site
tokens/                  design tokens — reference only, not loaded at runtime
docs/
  ARCHITECTURE.md        how it's put together, data flow, rendering pattern
  DESIGN.md              palette, encoding rules, layout, responsive breakpoints
  SPEC.md                every derived metric and its formula
  RECOVERY-PATTERN.md    findings: how recovery responds to load
  PROGRESSION.md         findings: defining optimal load, and VO₂max
analysis/
  load_recovery.py       offline analysis, reproduces RECOVERY-PATTERN.md
  progression.py         offline analysis, reproduces PROGRESSION.md
```

`analysis/` is offline and not part of the site — a standard-library script that reads the
same sheet and reuses the formulas in SPEC.md, so the findings describe the metrics as the
charts actually define them.

`index.html` is what GitHub Pages serves. **The two HTML files must stay identical** —
nothing enforces it, so `cp index.html training_dashboard.html` on every commit that
touches the dashboard.

The only external dependency is Chart.js 4.4.1 from cdnjs. No CDN, no charts.

## Access

A client-side password gate: MD5 of the typed password is compared against a constant and
the hash is stored in `localStorage` so the device stays unlocked. To change it:

```bash
echo -n "newpassword" | md5
```

then update the `PASS_HASH` constant and push.

This is **obfuscation, not security.** The hash, the spreadsheet ID and the API key are all
in the page source. It keeps a casual visitor out of the URL; it does not protect the data.
The real controls are the sheet's sharing setting (link → Viewer, read-only) and the API
key's HTTP-referrer restriction to `bunnytailgra22.github.io/*`.

## Contributing to it later

Worth knowing before editing:

- Chart heights live in CSS on the `.chart-box` **wrapper**, one rule per id. Never put
  `height: !important` on a `<canvas>` — it fights Chart.js's device-pixel-ratio sizing and
  squashes the bitmap.
- Derived series are computed over **full history and then sliced** to the visible scope, so
  a rolling baseline is already warm at the left edge instead of ramping from zero. Scope
  pills never refilter the source data.
- `null` means "no data", never zero. Renderers produce a gap rather than invent a value.
- Every renderer must `destroy()` its previous Chart instance, or Chart.js throws
  *"Canvas is already in use"*.
- Switching tabs re-renders: a chart built inside a `display:none` panel measures 0×0.
