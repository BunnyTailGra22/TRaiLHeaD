#!/usr/bin/env python3
"""Progression analysis for TRaiLHEAD.

Answers: what is the optimal training load for progressive overload, and can
VO₂max tell us? Reproduces every number in docs/PROGRESSION.md.

The short version of the result: the Progressive Overload chart's ACWR cannot
answer this, because it is scale-free by construction. Section A demonstrates
that on the data. Sections B and C build the definition it is missing -- a level
and a slope -- and section E shows why the tempting VO₂max correlation is mostly
an autocorrelation artefact.

Shares the sheet loaders and model functions with load_recovery.py (same
directory, so sys.path[0] finds it) rather than duplicating them.

Usage:
    python3 analysis/progression.py                 # fetch from the sheet
    python3 analysis/progression.py --cache DIR     # reuse/store raw JSON
"""

import argparse, math, random, statistics as st
from datetime import timedelta

from load_recovery import (BASELINE_DAYS, acwr, daily_ep, load_sleep, load_sessions,
                           num, parse_date, pearson, p_from_t, table, zscores)

# Chronic ramp is measured over 28 days and reported as %/week, so it is
# comparable to the "add 5-10% a week" heuristic. A 28-day base below this is too
# small to take a ratio of -- 5 EP of chronic load is a fortnight off, and every
# percentage against it is noise.
RAMP_WINDOW = 28
RAMP_MIN_BASE = 5.0

# Recovery cost is scored over the 14 days FOLLOWING the ramp, not during it: the
# question is what the ramp cost you, not what you felt while doing it.
COST_WINDOW = 14
COST_MIN_N = 7

RAMP_BANDS = ((-1e9, -5, "shedding  < -5"), (-5, 0, "easing   -5..0"),
              (0, 3, "building   0..3"), (3, 7, "ramping    3..7"),
              (7, 12, "hard ramp 7..12"), (12, 1e9, "spiking    >12"))

# The ramp band this analysis lands on. Not a literature import -- section B is
# where it comes from.
RAMP_TARGET_LOW, RAMP_TARGET_HIGH = 3.0, 7.0

BLOCK_LENGTHS = (28, 42, 60, 90)
N_PERM = 4000
SEED = 11


def head(title):
    print("\n" + "=" * 78 + "\n" + title + "\n" + "=" * 78)


def star(p):
    return "  *" if p is not None and p < 0.05 else ""


def load_vo2(cache=None):
    """VO₂max from the TrainingLoad tab. The dashboard deliberately does not read
    this tab (docs/ARCHITECTURE.md); this script does, as a second opinion.
    Note it UPSERTS rather than appends -- Garmin revises recent rows for days
    afterwards, so re-running this can move the most recent numbers."""
    idx, rows = table("TrainingLoad", cache)
    out = {}
    for r in rows:
        dt = parse_date(r[idx["date"]][:10])
        if not dt:
            continue
        out[dt.date()] = {"vo2": num(r[idx["vo₂ max"]]),
                          "ratio": num(r[idx["load ratio"]]),
                          "status": (r[idx["training status"]] or "").strip()}
    return out


def ramp_series(days, chronic):
    """Chronic-EP growth over the trailing RAMP_WINDOW, as %/week.

    None for the first RAMP_WINDOW days and wherever the base is too small --
    a gap, not a zero, so nothing downstream mistakes "unknown" for "flat"."""
    out = {}
    for d in days:
        base_day = d - timedelta(RAMP_WINDOW)
        base = chronic.get(base_day)
        if base is None or base < RAMP_MIN_BASE:
            out[d] = None
        else:
            out[d] = (chronic[d] / base - 1) * 100 / (RAMP_WINDOW / 7)
    return out


def find_episodes(vo2):
    """Split the VO₂max window at its trough and at the point it plateaus.

    Derived from the VO₂max series itself, NOT chosen to make the load contrast
    look good -- but that cuts the other way too: because the boundaries come
    from the outcome, the load differences between episodes are descriptive and
    cannot be read as a test. See the note printed in section D."""
    have = sorted(d for d in vo2 if vo2[d]["vo2"] is not None)
    if len(have) < 60:
        return []
    trough = min(have, key=lambda d: (vo2[d]["vo2"], d))
    after = [d for d in have if d > trough]
    if not after:
        return []
    peak_val = max(vo2[d]["vo2"] for d in after)
    # first day that reaches within 0.1 (Garmin's quantum) of the post-trough peak
    peak = next(d for d in after if vo2[d]["vo2"] >= peak_val - 0.1)
    eps = [("falling", have[0], trough), ("rising", trough + timedelta(1), peak)]
    if peak < have[-1]:
        eps.append(("plateau", peak + timedelta(1), have[-1]))
    return eps


def sec_scale_free(days, per_day, chronic, ratio, vo2, episodes):
    head("A. WHY ACWR CANNOT DEFINE OPTIMAL LOAD — it is scale-free")
    if not episodes:
        print("  not enough VO₂max data to segment")
        return
    print("  The same chart state across three different fitness outcomes.\n")
    print(f"  {'episode':<34}{'VO₂max':>14}{'ACWR md':>9}{'in band':>9}"
          f"{'chronic md':>12}{'chronic drift':>15}")
    for name, a, b in episodes:
        dd = [d for d in days if a <= d <= b]
        rts = [ratio[d] for d in dd if ratio[d] is not None]
        chs = [chronic[d] for d in dd]
        v0, v1 = vo2[a]["vo2"], vo2[b]["vo2"]
        label = f"{a.strftime('%b %-d')} – {b.strftime('%b %-d')}  {name}"
        print(f"  {label:<34}{f'{v0} → {v1}':>14}{st.median(rts):>9.2f}"
              f"{100 * sum(1 for r in rts if 0.8 <= r <= 1.4) / len(rts):>8.0f}%"
              f"{st.median(chs):>12.1f}{chs[-1] - chs[0]:>+15.1f}")
    print("\n  The falling and rising episodes have essentially the SAME ACWR median while")
    print("  their chronic EP differs by about a third. That is the whole argument: the")
    print("  ratio cannot separate the block where VO₂max dropped from the one where it")
    print("  climbed. docs/SPEC.md already explains the mechanism — chronic is a second")
    print("  smoothing pass over acute, so the ratio self-centres near 1.0. It measures")
    print("  spike risk, not progression.")
    print("\n  What does separate them is the absolute chronic EP level and its drift. The")
    print("  in-band share is not useless (it is highest in the rising block) but it is a")
    print("  weaker and noisier signal than the level sitting right next to it.")


def sec_ramp_cost(days, chronic, ramp, Z):
    head("B. SLOPE — what ramp rate did you actually tolerate?")
    print(f"  For each day: chronic-EP growth over the preceding {RAMP_WINDOW}d as %/week,")
    print(f"  against the recovery cost over the FOLLOWING {COST_WINDOW}d. A watch day is")
    print("  the co-movement flag from docs/SPEC.md: >=2 of 3 vitals >=1 SD on their bad side.\n")

    def watch(d):
        zs = [Z[k].get(d) for k in ("rhr", "spo2", "resp")]
        return None if any(z is None for z in zs) else sum(z > 1 for z in zs) >= 2

    scored = []
    for d in days:
        if ramp.get(d) is None:
            continue
        fut = [d + timedelta(k) for k in range(1, COST_WINDOW + 1)]
        w = [x for x in (watch(f) for f in fut) if x is not None]
        zr = [Z["rhr"][f] for f in fut if f in Z["rhr"]]
        if len(w) < COST_MIN_N or len(zr) < COST_MIN_N:
            continue
        scored.append((ramp[d], 100 * sum(w) / len(w), st.mean(zr), chronic[d]))

    print(f"  {'ramp (%/wk)':<20}{'days':>6}{'watch%':>9}{'RHR z next 14d':>17}{'chronic md':>12}")
    for lo, hi, lbl in RAMP_BANDS:
        sel = [s for s in scored if lo <= s[0] < hi]
        if len(sel) < 10:
            print(f"  {lbl:<20}{len(sel):>6}{'too few':>9}")
            continue
        print(f"  {lbl:<20}{len(sel):>6}{st.mean([s[1] for s in sel]):>8.0f}%"
              f"{st.mean([s[2] for s in sel]):>+17.3f}{st.median([s[3] for s in sel]):>12.1f}")

    rates = sorted(s[0] for s in scored)
    print(f"\n  your own ramp distribution: p10 {rates[int(.1 * len(rates))]:+.1f}"
          f"   median {st.median(rates):+.1f}"
          f"   p90 {rates[int(.9 * len(rates))]:+.1f} %/wk   (n={len(rates)} days)")
    print(f"\n  Read: ramping at {RAMP_TARGET_LOW:.0f}-{RAMP_TARGET_HIGH:.0f}%/wk was the "
          "BEST-tolerated state, better than")
    print("  easing off. Shedding load was the worst by a wide margin — consistent with")
    print("  docs/RECOVERY-PATTERN.md, where the detraining band collects illness and")
    print("  travel rather than rest. Low load is often the consequence of poor recovery.")
    print("\n  CAVEAT that limits this table: the 7-12 and >12 rows look harmless but sit")
    print("  at low chronic medians — big percentage ramps happened from a small base,")
    print("  which is cheap. Slope is confounded by level, which is exactly why the")
    print("  definition needs both terms and neither alone.")


def sec_level(days, chronic):
    head("C. LEVEL — chronic EP, against your own history")
    chs = sorted(chronic[d] for d in days)
    q = lambda f: chs[int(f * len(chs))]
    print(f"  chronic EP over {len(days)} days:")
    print(f"    p10 {q(.10):.0f}    p25 {q(.25):.0f}    median {st.median(chs):.0f}"
          f"    p75 {q(.75):.0f}    p90 {q(.90):.0f}")
    print(f"    now {chronic[days[-1]]:.0f}"
          f"  ({100 * sum(1 for c in chs if c <= chronic[days[-1]]) / len(chs):.0f}th percentile"
          " of your own history)")
    print("\n  Reported as percentiles, not a target. One productive episode is not enough")
    print("  to prescribe a level; it is enough to show that level is the axis that moved.")


def sec_vo2_episodes(days, per_day, chronic, vo2, episodes):
    head("D. VO₂max — what the episodes look like, described not tested")
    if not episodes:
        print("  not enough VO₂max data")
        return
    print(f"  {'episode':<30}{'days':>6}{'EP/wk':>8}{'hrs/wk':>8}{'run d/wk':>10}"
          f"{'chronic md':>12}")
    for name, a, b in episodes:
        dd = [d for d in days if a <= d <= b]
        wk = len(dd) / 7
        print(f"  {a.strftime('%b %-d')} – {b.strftime('%b %-d')}  {name:<14}{len(dd):>6}"
              f"{sum(per_day[d]['ep'] for d in dd) / wk:>8.1f}"
              f"{sum(per_day[d]['hrs'] for d in dd) / wk:>8.1f}"
              f"{sum(1 for d in dd if per_day[d]['ep'] > 0) / wk:>10.1f}"
              f"{st.median([chronic[d] for d in dd]):>12.1f}")

    vals = [vo2[d]["vo2"] for d in sorted(vo2) if vo2[d]["vo2"] is not None]
    ds = sorted(d for d in vo2 if vo2[d]["vo2"] is not None)
    changed = sum(1 for i in range(1, len(ds))
                  if (ds[i] - ds[i - 1]).days == 1
                  and abs(vo2[ds[i]]["vo2"] - vo2[ds[i - 1]]["vo2"]) > 1e-9)
    print(f"\n  VO₂max: n={len(vals)} days, range {min(vals)}–{max(vals)}"
          f" (a {max(vals) - min(vals):.1f}-point spread)")
    print(f"  quantised to 0.1, and only {changed} of {len(ds) - 1} consecutive days"
          f" change at all ({100 * changed / (len(ds) - 1):.0f}%).")
    print("\n  Two reasons not to optimise against this number:")
    print("   - the episode boundaries are derived FROM the VO₂max series, so the load")
    print("     contrast above is descriptive. It is n=3 episodes, not 3 trials.")
    print("   - Garmin's VO₂max is estimated from pace-at-HR, so it partly measures")
    print("     'did you run fast' rather than 'did you get fitter'.")


def sec_autocorrelation(days, per_day, chronic, vo2):
    head("E. WHY THE TEMPTING VO₂max CORRELATION IS MOSTLY AN ARTEFACT")
    random.seed(SEED)
    vd = sorted(d for d in vo2 if vo2[d]["vo2"] is not None)

    def lag1(series):
        m = st.mean(series)
        den = sum((x - m) ** 2 for x in series)
        return sum((series[k] - m) * (series[k - 1] - m) for k in range(1, len(series))) / den

    print(f"  lag-1 autocorrelation:  VO₂max {lag1([vo2[d]['vo2'] for d in vd]):.4f}"
          f"   chronic EP {lag1([chronic[d] for d in vd]):.4f}")
    print(f"  Both are near random walks. {len(vd)} days of daily-sampled 42-day windows is")
    print(f"  about {len(vd) // 42} independent blocks, not {len(vd)}.\n")

    W = 28
    xs, ys = [], []
    for d in vd:
        pre = [d - timedelta(k) for k in range(W)]
        fut = d + timedelta(W)
        if fut in vo2 and vo2[fut]["vo2"] is not None and all(x in chronic for x in pre):
            xs.append(sum(per_day[x]["ep"] for x in pre))
            ys.append(vo2[fut]["vo2"] - vo2[d]["vo2"])
    obs = pearson(xs, ys)
    print(f"  {W}d EP -> next-{W}d VO₂max change:  r={obs['r']:+.3f}"
          f"   naive p={obs['p']:.6f}   (n={obs['n']} OVERLAPPING windows)")

    def block_permute(y, bl):
        """Circular block permutation: shuffles whole blocks so within-block serial
        structure survives into the null. Shuffling single days would destroy it
        and hand back the same over-confident p-value."""
        blocks = [y[k:k + bl] for k in range(0, len(y), bl)]
        random.shuffle(blocks)
        return [v for b in blocks for v in b][:len(y)]

    def raw_r(a, b):
        res = pearson(a, b, min_n=3)
        return res["r"] if res else 0.0

    print(f"\n  block-permutation null ({N_PERM} draws, seed {SEED}):")
    print(f"    {'block length':<16}{'p':>8}{'null 95th pct |r|':>20}")
    for bl in BLOCK_LENGTHS:
        null = [abs(raw_r(xs, block_permute(ys, bl))) for _ in range(N_PERM)]
        p = sum(1 for z in null if z >= abs(obs["r"])) / N_PERM
        print(f"    {str(bl) + 'd':<16}{p:>8.3f}{sorted(null)[int(.95 * N_PERM)]:>20.3f}"
              + star(p))

    def detrend(v):
        n = len(v)
        t = list(range(n))
        mt, mv = st.mean(t), st.mean(v)
        b = sum((a - mt) * (c - mv) for a, c in zip(t, v)) / sum((a - mt) ** 2 for a in t)
        return [c - (mv + b * (a - mt)) for a, c in zip(t, v)]

    dx, dy = detrend(xs), detrend(ys)
    rd = raw_r(dx, dy)
    null = [abs(raw_r(dx, block_permute(dy, 42))) for _ in range(N_PERM)]
    print(f"\n  both series linearly detrended: r={rd:+.3f}"
          f"   block-42 p={sum(1 for z in null if z >= abs(rd)) / N_PERM:.3f}")
    print("\n  Verdict: the effect survives at short block lengths and fails at long")
    print("  ones. Directionally supported, not established — it rests on one seasonal")
    print("  swing. Do not fit a band to it; revisit at ~18 months of VO₂max.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", help="directory to cache raw sheet JSON in")
    args = ap.parse_args()

    sessions = load_sessions(args.cache)
    sleep = load_sleep(args.cache)
    vo2 = load_vo2(args.cache)
    days, per_day = daily_ep(sessions, sleep)
    _, chronic, ratio = acwr(days, per_day)
    ramp = ramp_series(days, chronic)
    Z = {k: zscores(sleep, k) for k in ("rhr", "spo2", "resp")}
    episodes = find_episodes(vo2)

    sec_scale_free(days, per_day, chronic, ratio, vo2, episodes)
    sec_ramp_cost(days, chronic, ramp, Z)
    sec_level(days, chronic)
    sec_vo2_episodes(days, per_day, chronic, vo2, episodes)
    sec_autocorrelation(days, per_day, chronic, vo2)
    print()


if __name__ == "__main__":
    main()
