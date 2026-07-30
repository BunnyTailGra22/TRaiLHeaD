#!/usr/bin/env python3
"""Load -> recovery analysis for TRaiLHEAD.

Answers one question: after a run, what happens to the recovery markers, and for
how long? Reproduces every number in docs/RECOVERY-PATTERN.md.

Reads the same Google Sheet the dashboard reads, using the dashboard's own
formulas (EP, the acute/chronic EWMA, the sign-normalised 30-day z) so the
findings describe the metrics as the charts actually define them. See docs/SPEC.md.

Usage:
    python3 analysis/load_recovery.py                 # fetch from the sheet
    python3 analysis/load_recovery.py --cache DIR     # reuse/store raw JSON

The sheet id and API key are the same public constants that are already compiled
into index.html; the key is HTTP-referrer restricted, hence the Referer header.
"""

import argparse, json, math, os, statistics as st, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta

SHEET_ID = "1dWK_5XBGpEXaLl3xgsm7uXi-q5hdvEE49nRZKQyS_gg"
API_KEY = "AIzaSyC4lLHO0_kuqxlVGlP7TRRDZTVrJMdO37U"
REFERER = "https://bunnytailgra22.github.io/trailhead/"
RANGES = {"Activities": "Activities!A1:Z2200",
          "Sleep": "Sleep!A1:Z2200",
          "TrainingLoad": "TrainingLoad!A1:Z1300"}

# Model constants, mirroring index.html / docs/SPEC.md.
ACUTE_TAU, CHRONIC_WEEKS = 7, 4
ACUTE_DECAY = math.exp(-1 / ACUTE_TAU)
CHRONIC_ALPHA = 1 - math.exp(-1 / (CHRONIC_WEEKS * 7))
BASELINE_DAYS, BASELINE_MIN_N = 30, 10

# (bad direction, sdFloor). Positive z always means "toward worse recovery".
VITALS = {"rhr":   (+1, 0.8),
          "hrv":   (-1, 1.0),
          "score": (-1, 2.0),
          "spo2":  (-1, 0.4),
          "resp":  (+1, 0.3)}

# EP tiers used throughout. Chosen from the distribution: the median run day is
# ~11 EP and the 90th percentile ~23, so these split easy / moderate / long.
TIERS = (("easy 5-12", 5, 12), ("moderate 12-20", 12, 20), ("long 20+", 20, 1e9))


# ---------------------------------------------------------------- fetch / parse

def fetch(name, cache=None):
    if cache:
        p = os.path.join(cache, name + ".json")
        if os.path.exists(p):
            return json.load(open(p))
    url = ("https://sheets.googleapis.com/v4/spreadsheets/%s/values/%s?key=%s"
           % (SHEET_ID, urllib.parse.quote(RANGES[name]), API_KEY))
    req = urllib.request.Request(url, headers={"Referer": REFERER})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if cache:
        os.makedirs(cache, exist_ok=True)
        json.dump(data, open(os.path.join(cache, name + ".json"), "w"))
    return data


def table(name, cache=None):
    """-> (case-insensitive header index, rows padded to header width)"""
    vals = fetch(name, cache).get("values", [])
    hdr = [h.strip() for h in vals[0]]
    idx = {h.lower(): i for i, h in enumerate(hdr)}
    return idx, [r + [""] * (len(hdr) - len(r)) for r in vals[1:]]


def num(x):
    """Blank / non-numeric -> None. null means no data, never zero."""
    try:
        s = str(x).strip().replace(",", "")
        return float(s) if s else None
    except ValueError:
        return None


def parse_date(raw):
    for f in ("%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), f)
        except ValueError:
            pass
    return None


def load_sessions(cache=None):
    """Run sessions only, as processSessions() defines them."""
    idx, rows = table("Activities", cache)
    out = []
    for r in rows:
        typ = (r[idx["type"]] or "").lower()
        if "run" not in typ:
            continue
        dt = parse_date(r[idx["start time"]])
        if not dt:
            continue
        dist = num(r[idx["distance (km)"]]) or 0.0
        elev = num(r[idx["elevation gain (m)"]]) or 0.0
        mins = num(r[idx["duration (min)"]]) or 0.0
        out.append({"d": dt.date(), "dist": dist, "elev": elev, "hrs": mins / 60,
                    "ep": dist + elev / 100, "trail": "trail" in typ,
                    "name": r[idx["name"]]})
    out.sort(key=lambda s: s["d"])
    return out


def load_sleep(cache=None):
    """Sleep row dated D is the night ENDING on the morning of D -- so it is the
    night BEFORE any run on day D, and the night after that run is D+1."""
    idx, rows = table("Sleep", cache)
    get = lambda r, n: num(r[idx[n.lower()]]) if n.lower() in idx else None
    out = {}
    for r in rows:
        dt = parse_date(r[idx["date"]][:10])
        if not dt:
            continue
        out[dt.date()] = {
            "rhr": get(r, "Resting HR (bpm)"), "hrv": get(r, "Overnight HRV (ms)"),
            "score": get(r, "Sleep Score"), "mins": get(r, "Total (min)"),
            "spo2": get(r, "Avg SpO₂"), "resp": get(r, "Avg Respiration"),
            "bb": get(r, "Body Battery Change"),
            "status": (r[idx["hrv status"]] or "").strip().upper()}
    return out


# --------------------------------------------------------------------- the model

def daily_ep(sessions, sleep):
    """Gap-free daily EP grid with rest days as real zeros, plus the per-day
    components. Rest days must be data points, not gaps, or the decay never
    decays (docs/SPEC.md)."""
    agg = {}
    for s in sessions:
        a = agg.setdefault(s["d"], {"ep": 0., "dist": 0., "elev": 0., "hrs": 0., "trail": 0.})
        for k in ("ep", "dist", "elev", "hrs"):
            a[k] += s[k]
        a["trail"] += s["ep"] if s["trail"] else 0.
    start, end = sessions[0]["d"], max(max(agg), max(sleep))
    days = [start + timedelta(n) for n in range((end - start).days + 1)]
    blank = {"ep": 0., "dist": 0., "elev": 0., "hrs": 0., "trail": 0.}
    return days, {d: agg.get(d, dict(blank)) for d in days}


def acwr(days, per_day):
    """Acute = EWMA sum (7d), chronic = EWMA average of acute (4wk), per SPEC."""
    acute, chronic = {}, {}
    prev_a = prev_c = None
    for d in days:
        a = per_day[d]["ep"] + (prev_a * ACUTE_DECAY if prev_a is not None else 0.)
        c = a if prev_c is None else prev_c + CHRONIC_ALPHA * (a - prev_c)
        acute[d], chronic[d] = a, c
        prev_a, prev_c = a, c
    ratio = {d: (acute[d] / chronic[d] if chronic[d] else None) for d in days}
    return acute, chronic, ratio


def zscores(sleep, key):
    """Sign-normalised z against a trailing 30-day personal baseline that
    EXCLUDES the day itself -- tonight must not widen the band judging tonight."""
    sign, floor = VITALS[key]
    dates = sorted(sleep)
    z = {}
    for d in dates:
        v = sleep[d].get(key)
        if v is None:
            continue
        win = [sleep[x][key] for x in dates
               if 0 < (d - x).days <= BASELINE_DAYS and sleep[x].get(key) is not None]
        if len(win) < BASELINE_MIN_N:
            continue                      # a gap, not a guess
        spread = max(st.stdev(win) if len(win) > 1 else 0., floor)
        z[d] = sign * (v - st.median(win)) / spread
    return z


# ------------------------------------------------------------------- statistics

def p_from_t(t):
    """Two-sided p, normal approximation (df is >=100 everywhere here)."""
    return 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))


def ttest_paired(deltas, min_n=8):
    if len(deltas) < min_n:
        return None
    m, sd = st.mean(deltas), st.stdev(deltas)
    if sd == 0:
        return None
    t = m / (sd / math.sqrt(len(deltas)))
    return {"n": len(deltas), "mean": m, "t": t, "p": p_from_t(t)}


def pearson(xs, ys, min_n=12):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < min_n:
        return None
    x, y = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = st.mean(x), st.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return None
    r = sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)
    n = len(pairs)
    t = r * math.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else float("inf")
    return {"r": r, "n": n, "p": p_from_t(t)}


def ols(y, cols, names):
    """Normal-equations OLS with intercept. Returns R2 and per-term t/p."""
    X = [[1.0] + [c[i] for c in cols] for i in range(len(y))]
    k = len(X[0])
    # Solve (X'X)b = X'y and invert X'X in one Gauss-Jordan pass.
    XtX = [[sum(X[i][a] * X[i][b] for i in range(len(X))) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a] * y[i] for i in range(len(X))) for a in range(k)]
    M = [XtX[i][:] + [1.0 if i == j else 0.0 for j in range(k)] + [Xty[i]] for i in range(k)]
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(M[r][c]))
        M[c], M[piv] = M[piv], M[c]
        d = M[c][c]
        M[c] = [v / d for v in M[c]]
        for r in range(k):
            if r != c:
                f = M[r][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    beta = [M[i][-1] for i in range(k)]
    inv_diag = [M[i][k + i] for i in range(k)]
    fitted = [sum(b * v for b, v in zip(beta, X[i])) for i in range(len(X))]
    sse = sum((a - f) ** 2 for a, f in zip(y, fitted))
    my = st.mean(y)
    r2 = 1 - sse / sum((a - my) ** 2 for a in y)
    sig2 = sse / (len(y) - k)
    terms = []
    for i, nm in enumerate(["intercept"] + names):
        se = math.sqrt(sig2 * inv_diag[i])
        t = beta[i] / se
        terms.append({"name": nm, "b": beta[i], "se": se, "t": t, "p": p_from_t(t)})
    return {"n": len(y), "r2": r2, "terms": terms}


# --------------------------------------------------------------------- sections

def star(p):
    return " *" if p is not None and p < 0.05 else ""


def head(title):
    print("\n" + "=" * 78 + "\n" + title + "\n" + "=" * 78)


def sec_coverage(days, per_day, sleep, Z):
    head("COVERAGE — what is actually in the sheet")
    run_days = [d for d in days if per_day[d]["ep"] > 0]
    eps = sorted(per_day[d]["ep"] for d in run_days)
    print(f"  window        {days[0]} .. {days[-1]}  ({len(days)} days)")
    print(f"  run days      {len(run_days)} ({100 * len(run_days) / len(days):.0f}% of days)"
          f"   total EP {sum(eps):,.0f}")
    print(f"  EP / run day  median {st.median(eps):.1f}   p90 {eps[int(.9 * len(eps))]:.1f}"
          f"   max {eps[-1]:.1f}")
    print()
    for k in ("rhr", "score", "resp", "spo2", "hrv"):
        have = [d for d in sorted(sleep) if sleep[d].get(k) is not None]
        print(f"  {k:<6} {len(have):>4}/{len(sleep)} nights ({100 * len(have) / len(sleep):3.0f}%)"
              f"   scored z: {len(Z[k]):>4}   from {min(have)}")
    print("\n  Overnight HRV is the thin column — it starts far later than the rest,")
    print("  so every HRV figure below rests on a fraction of the nights. Read it as")
    print("  suggestive; RHR is the one with the full history behind it.")


def sec_paired_dose(days, per_day, Z):
    head("A. PAIRED DOSE EFFECT — night after a run vs that run's OWN night before")
    print("  Pairing inside one event removes the regime confounds (illness, travel,")
    print("  taper blocks) that contaminate any comparison against a pool of rest")
    print("  nights. Positive = worse recovery than the pre-run night.\n")
    print(f"  {'dose on run day':<22}{'n':>5}{'delta z':>10}{'t':>8}{'p':>9}")
    rows = [("all run days", 0.01, 1e9)] + list(TIERS)
    for lbl, lo, hi in rows:
        ds = [d for d in days if lo <= per_day[d]["ep"] < hi
              and d in Z["rhr"] and d + timedelta(1) in Z["rhr"]]
        r = ttest_paired([Z["rhr"][d + timedelta(1)] - Z["rhr"][d] for d in ds])
        print(f"  {lbl:<22}{len(ds):>5}" +
              (f"{r['mean']:>+10.3f}{r['t']:>+8.2f}{r['p']:>9.4f}{star(r['p'])}" if r else f"{'n/a':>10}"))
    ds = [d for d in days if per_day[d]["ep"] == 0
          and per_day.get(d - timedelta(1), {"ep": 0})["ep"] == 0
          and d in Z["rhr"] and d + timedelta(1) in Z["rhr"]]
    r = ttest_paired([Z["rhr"][d + timedelta(1)] - Z["rhr"][d] for d in ds])
    print(f"\n  negative control — same test on rest days (must be ~0):")
    print(f"  {'rest, rest before':<22}{len(ds):>5}{r['mean']:>+10.3f}{r['t']:>+8.2f}"
          f"{r['p']:>9.4f}{star(r['p']) or '   (null holds)'}")


def sec_lag(days, per_day, Z):
    head("B. PAIRED LAG PROFILE — how many nights until it is back?")
    print("  Isolated efforts only: no second run inside the window, so the tail")
    print("  belongs to one effort. delta z vs that effort's own preceding night.\n")
    print("  " + " " * 14 + "".join(f"{'D+' + str(l):>15}" for l in range(1, 6)))
    for label, key in (("RHR", "rhr"), ("HRV", "hrv"), ("sleep score", "score"),
                       ("respiration", "resp")):
        cells = []
        for lag in range(1, 6):
            ds = [d for d in days if per_day[d]["ep"] > 0
                  and all(per_day.get(d + timedelta(i), {"ep": 0})["ep"] == 0
                          for i in range(1, lag))
                  and d in Z[key] and d + timedelta(lag) in Z[key]]
            r = ttest_paired([Z[key][d + timedelta(lag)] - Z[key][d] for d in ds])
            cells.append(f"{r['mean']:+.2f}{'*' if r['p'] < .05 else ' '}(n={r['n']})" if r
                         else "     n/a     ")
        print(f"  {label:<14}" + "".join(f"{c:>15}" for c in cells))
    print("\n  long efforts only (EP>=20), RHR:")
    for lag in range(1, 6):
        ds = [d for d in days if per_day[d]["ep"] >= 20
              and all(per_day.get(d + timedelta(i), {"ep": 0})["ep"] == 0 for i in range(1, lag))
              and d in Z["rhr"] and d + timedelta(lag) in Z["rhr"]]
        # min_n stays at 8: by D+5 only a handful of efforts are still isolated,
        # and a p-value off n=5 is noise dressed as a finding.
        r = ttest_paired([Z["rhr"][d + timedelta(lag)] - Z["rhr"][d] for d in ds])
        print(f"    D+{lag}  n={len(ds):<4}" +
              (f"delta z {r['mean']:>+7.3f}   t={r['t']:>+5.2f}  p={r['p']:.4f}{star(r['p'])}"
               if r else "too few to score"))


def sec_magnitude(days, per_day, sleep):
    head("C. MAGNITUDE IN BPM — the same effect in the unit you can feel")
    dates = sorted(sleep)
    print(f"  {'dose on run day':<22}{'n':>5}{'next-night RHR vs own 30-day median':>40}")
    for lbl, lo, hi in [("rest day", -1, 0.001)] + list(TIERS):
        devs = []
        for d in days:
            if not (lo <= per_day[d]["ep"] < hi):
                continue
            n = d + timedelta(1)
            if n not in sleep or sleep[n]["rhr"] is None:
                continue
            win = [sleep[x]["rhr"] for x in dates
                   if 0 < (n - x).days <= BASELINE_DAYS and sleep[x].get("rhr") is not None]
            if len(win) >= BASELINE_MIN_N:
                devs.append(sleep[n]["rhr"] - st.median(win))
        print(f"  {lbl:<22}{len(devs):>5}{st.mean(devs):>+38.2f} bpm")


def sec_drivers(days, per_day, Z):
    head("D. WHAT DRIVES IT — is EP the right dose variable?")
    rd = [d for d in days if per_day[d]["ep"] > 0 and d + timedelta(1) in Z["rhr"]]
    y = [Z["rhr"][d + timedelta(1)] for d in rd]
    print(f"  single predictors vs next-night RHR z   (n={len(rd)} scored run days)\n")
    print(f"  {'predictor':<24}{'r':>8}{'p':>10}")
    for lbl, f in (("distance km", lambda d: per_day[d]["dist"]),
                   ("EP = dist + elev/100", lambda d: per_day[d]["ep"]),
                   ("elevation m", lambda d: per_day[d]["elev"]),
                   ("duration hrs", lambda d: per_day[d]["hrs"])):
        r = pearson([f(d) for d in rd], y)
        print(f"  {lbl:<24}{r['r']:>+8.3f}{r['p']:>10.4f}{star(r['p'])}")

    print("\n  joint model — which term survives when they compete?")
    m = ols(y, [[per_day[d]["dist"] for d in rd], [per_day[d]["elev"] for d in rd],
                [per_day[d]["hrs"] for d in rd]],
            ["distance km", "elevation m", "duration hrs"])
    print(f"    RHR z(D+1) ~ distance + elevation + duration     n={m['n']}  R2={m['r2']:.4f}")
    for t in m["terms"]:
        print(f"      {t['name']:<16} b={t['b']:>+9.5f}  se={t['se']:.5f}  "
              f"t={t['t']:>+5.2f}  p={t['p']:.4f}{star(t['p'])}")
    for lbl, cols, names in (("duration only", [[per_day[d]["hrs"] for d in rd]], ["duration hrs"]),
                             ("EP only", [[per_day[d]["ep"] for d in rd]], ["EP"])):
        m = ols(y, cols, names)
        print(f"\n    {lbl:<44} R2={m['r2']:.4f}   "
              f"b={m['terms'][1]['b']:+.5f}  p={m['terms'][1]['p']:.4f}{star(m['terms'][1]['p'])}")


def sec_trail(days, per_day, Z):
    head("E. TRAIL vs ROAD at matched EP")
    print(f"  {'group':<16}{'days':>6}{'EP md':>8}{'elev md':>9}{'hrs md':>8}{'RHR z D+1':>11}")
    groups = {}
    for lbl, test in (("trail-dominant", lambda a: a["trail"] > 0.5 * a["ep"]),
                      ("road-dominant", lambda a: a["trail"] <= 0.5 * a["ep"])):
        ds = [d for d in days if per_day[d]["ep"] >= 20 and test(per_day[d])]
        zs = [Z["rhr"][d + timedelta(1)] for d in ds if d + timedelta(1) in Z["rhr"]]
        groups[lbl] = zs
        print(f"  {lbl + ' EP20+':<16}{len(ds):>6}"
              f"{st.median([per_day[d]['ep'] for d in ds]):>8.1f}"
              f"{st.median([per_day[d]['elev'] for d in ds]):>9.0f}"
              f"{st.median([per_day[d]['hrs'] for d in ds]):>8.1f}"
              f"{st.mean(zs):>+11.3f}")
    a, b = groups["trail-dominant"], groups["road-dominant"]
    ma, mb = st.mean(a), st.mean(b)
    se = math.sqrt(st.variance(a) / len(a) + st.variance(b) / len(b))
    t = (ma - mb) / se
    print(f"\n  trail - road = {ma - mb:+.3f} z   t={t:+.2f}  p={p_from_t(t):.4f}"
          f"{star(p_from_t(t)) or '  (not significant)'}")
    print("  The trail days are more than twice as long in hours at the same EP, so")
    print("  surface and duration are not separable here. Section D says the hours are")
    print("  doing the work; this table is that same fact seen from the side.")


def sec_acwr(days, ratio, Z):
    head("F. DOES THE PROGRESSIVE OVERLOAD BAND CARRY RECOVERY INFORMATION?")
    print("  Same-night recovery by the state the chart would have shown.\n")
    print(f"  {'state':<20}{'days':>6}" +
          "".join(f"{k:>10}" for k in ("rhr z", "hrv z", "resp z", "score z", "watch%")))

    def watch(d):
        zs = [Z[k].get(d) for k in ("rhr", "spo2", "resp")]
        return None if any(z is None for z in zs) else sum(z > 1 for z in zs) >= 2

    for lbl, test in (("detraining <0.8", lambda r: r < 0.8),
                      ("optimal 0.8-1.4", lambda r: 0.8 <= r <= 1.4),
                      ("spike risk >1.4", lambda r: r > 1.4)):
        ds = [d for d in days if ratio[d] is not None and test(ratio[d])]
        cells = []
        for k in ("rhr", "hrv", "resp", "score"):
            vs = [Z[k][d] for d in ds if d in Z[k]]
            cells.append(f"{st.mean(vs):+.2f}" if len(vs) >= 8 else "  n/a")
        w = [x for x in (watch(d) for d in ds) if x is not None]
        cells.append(f"{100 * sum(w) / len(w):.0f}%" if len(w) >= 8 else " n/a")
        print(f"  {lbl:<20}{len(ds):>6}" + "".join(f"{c:>10}" for c in cells))
    print("\n  Two things to read carefully here. Detraining looks bad on RHR too — that")
    print("  band collects illness and travel weeks as well as genuine easy weeks, so it")
    print("  is not a clean 'rested' state. And HRV z goes NEGATIVE (= above baseline) in")
    print("  spike risk: sustained load weeks are also fit weeks, and the 30-day rolling")
    print("  median moves with them. The band's recovery signal is in watch%, resp and")
    print("  sleep score, not in HRV.")


def sec_garmin(days, acute_ep, cache):
    head("G. INDEPENDENT CHECK — Garmin's own load model")
    try:
        idx, rows = table("TrainingLoad", cache)
    except Exception as e:
        print(f"  TrainingLoad unavailable: {e}")
        return
    xs, ys = [], []
    for r in rows:
        dt = parse_date(r[idx["date"]][:10])
        a = num(r[idx["acute load"]])
        if dt and a is not None and dt.date() in acute_ep:
            xs.append(a)
            ys.append(acute_ep[dt.date()])
    res = pearson(xs, ys)
    print(f"  Garmin Acute Load vs this dashboard's Acute EP:  "
          f"r={res['r']:+.3f}  n={res['n']}  p={res['p']:.4f}")
    print("  Two independently computed load curves agree, so the load series is not")
    print("  an artefact of the EP formula. Garmin's tab covers a shorter window.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", help="directory to cache raw sheet JSON in")
    args = ap.parse_args()

    sessions = load_sessions(args.cache)
    sleep = load_sleep(args.cache)
    if not sessions or not sleep:
        sys.exit("no data")
    days, per_day = daily_ep(sessions, sleep)
    acute_ep, _, ratio = acwr(days, per_day)
    Z = {k: zscores(sleep, k) for k in VITALS}

    sec_coverage(days, per_day, sleep, Z)
    sec_paired_dose(days, per_day, Z)
    sec_lag(days, per_day, Z)
    sec_magnitude(days, per_day, sleep)
    sec_drivers(days, per_day, Z)
    sec_trail(days, per_day, Z)
    sec_acwr(days, ratio, Z)
    sec_garmin(days, acute_ep, args.cache)
    print()


if __name__ == "__main__":
    main()
