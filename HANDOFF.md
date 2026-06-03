# Project Handoff — Garmin → Google Sync + TRaiLHEAD Dashboard

> Handoff document for AI/human co-workers. Two connected projects share one Google Sheet.

---

## Overview

| Project | Role | Location |
|---|---|---|
| **garmin_google_sync** | Python backend — pulls Garmin Connect data → writes to Google Sheet | `~/Documents/garmin_google_sync/` |
| **TRaiLHEAD dashboard** | Frontend — reads the same Sheet, renders Chart.js visualizations | `~/Documents/Claude/Projects/TRaiLHEAD/` |

Data flow: **Garmin Connect → Python sync → Google Sheet → Dashboard webpage**

---

## 1. Garmin → Google Sync (Python)

### Structure
```
main.py                  # CLI entry: --since YYYY-MM-DD, --no-fit, --no-sheets, --spreadsheet-id
config.py                # .env loader; auto-extracts Sheet ID from full URL
auth/garmin_auth.py      # garminconnect login
auth/google_auth.py      # Google OAuth2 flow (writes/refreshes token.json)
garmin/client.py         # Thin wrapper over garminconnect API
garmin/activities.py     # Activity dataclass parsing
garmin/biometrics.py     # HR, steps, weight, sleep, HRV fetchers
gservices/fit.py         # ⚠️ folder RENAMED from google/ (avoided namespace clash with google-auth)
gservices/sheets.py      # Writes Activities, Biometrics, Sleep tabs
models/activity.py       # Activity dataclass
models/biometric.py      # BiometricRecord, SleepRecord, HRVSummary
sync/engine.py           # Orchestration + deduplication
sync/state.py            # Last-sync timestamp (sync_state.json)
utils/logger.py          # Shared logger
utils/transforms.py      # Unit conversions, Garmin→Fit type map
.github/workflows/daily_sync.yml  # Daily run 7AM HKT (cron '0 23 * * *')
requirements.txt
.env                     # ⚠️ contains LIVE credentials (gitignored)
```

### Sheet tabs written
- **Activities** — dedup by Activity ID (col A)
- **Biometrics** — one row/day: Date, Weight, BMI, Body Fat %, Body Water %, Muscle Mass, Bone Mass, Visceral Fat, Metabolic Age, Physique Rating (Garmin Index scale)
- **Sleep** — Date, Sleep Score, Quality, Sleep Start/End, Total/Deep/Light/REM/Awake mins, Restless Moments, Resting HR, Body Battery Change, Avg SpO₂, Lowest SpO₂, Avg Respiration, Lowest Respiration, Overnight HRV, Baseline Low/High, 7d Avg, HRV Status

### Key API findings (important — saves rediscovery)
All Sleep metrics are **top-level in the sleep response** (`get_sleep_data`), NOT separate API calls:
- `restlessMomentsCount` → Restless Moments
- `bodyBatteryChange` → Body Battery Change
- `restingHeartRate` → Resting HR
- `avgOvernightHrv`, `hrvStatus` → HRV
- `averageRespirationValue`, `lowestRespirationValue` → Respiration
- `averageSpO2Value`, `lowestSpO2Value` → SpO₂
- Sleep score is a **dict**: `{'value': 56, 'qualifierKey': 'POOR'}` — handled in code
- Body battery values nested in `bodyBatteryValuesArray: [[ts_ms, level], ...]` (fetched prev+current day) — but `bodyBatteryChange` top-level is simpler and now used

### Behaviors
- **Deduplication** by date (Sleep/Biometrics) or Activity ID (Activities)
- Column A gets explicit `yyyy-mm-dd` Google date format so read-back matches write value (critical for dedup)
- All tabs **auto-sort by date descending** after each write
- Requires **Python 3.11+** (`datetime.UTC`). User machine runs system Python 3.14 at `/usr/local/bin/python3.14`

### Deployment
- GitHub repo: `garmin_google_sync`, runs via GitHub Actions daily
- Secrets: `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `SPREADSHEET_ID`, `GOOGLE_CLIENT_SECRETS` (base64), `GOOGLE_TOKEN` (base64)
- Workflow opts into Node 24: `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`
- To change schedule: edit cron in `daily_sync.yml` (UTC; HKT = UTC+8)

---

## 2. TRaiLHEAD Dashboard (frontend)

### Location & hosting
- Source: `~/Documents/Claude/Projects/TRaiLHEAD/index.html` (+ `training_dashboard.html` working copy)
- Live: `https://bunnytailgra22.github.io/trailhead/` (repo `TRaiLHeaD`, GitHub Pages, root)
- Single self-contained HTML file (Chart.js via CDN). No build step.

### Features
- YoY summary cards, cumulative EP, monthly road/trail stacked, 13-wk rolling EP, EP-vs-EPH scatter, recent-8-week load table
- **Biometric chart** — defaults to HRV, Resting HR, SpO₂; toggles for Sleep Score / Sleep hrs; 30/90/180/All range; **Daily vs 7d-avg** smoothing (centered rolling average)
- **Password gate** — client-side MD5, stored in localStorage. Change via `echo -n "newpass" | md5` → update `PASS_HASH` constant → push
- `DEFAULT_SHEET_ID` + `DEFAULT_API_KEY` hardcoded so no config entry needed; reads Activities + Sleep tabs in parallel, joins Sleep→Activities by date

### Design
- **Morandi palette** (warm cream bg `#e9e4dc`, cards `#f5f1ea`, dusty accents: blue `#8a9ba5`, sage `#97a682`, clay `#c0987e`, mauve `#aa93a2`) + modern minimalist
- Colors live in CSS `:root` AND hardcoded in JS (`YEAR_COLORS`, `BIO_CFG`, chart theme functions) — update both
- **Mobile-responsive**: `min-width:0` grid guards prevent horizontal overflow; legends move to bottom on phones; axis labels thin/rotate; charts re-render on orientation change

### Security
- Sheets API key **restricted by HTTP referrer** to `bunnytailgra22.github.io/*` in Google Cloud Console
- Sheet shared as "Anyone with link → Viewer" (read-only; key cannot write)

---

## Open Items / Watch-outs
- ⚠️ `.env` stores Garmin email + password in plaintext — flag if hardening is requested
- Weight/body-composition columns only populate when there are Index-scale weigh-ins in the date range
- Dashboard repo was renamed `trailhead` → `TRaiLHeaD`; git remote shows a redirect notice but pushes work
- Two GitHub Personal Access Tokens may be in use — `repo` + `workflow` scopes required
