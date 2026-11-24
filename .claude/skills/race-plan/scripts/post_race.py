#!/usr/bin/env python3
"""Post-race calibration: actual section EP/h from a FIT file -> new terrain factors and benchmark ratio.

    python3 post_race.py --fit race.fit --sections sections.json --out-dir out/ \
        [--official 6:55:07] [--benchmark-eph 12.3] [--profile profile.yaml] [--utc-offset 8]

Checkpoints are matched to the watch track by location (nearest point within 60 m, in order),
never by distance. Aid-station dwell = time spent within 60 m of the checkpoint.
Factor = section moving EP/h / race EP/h (official time, stops included) — the same definition the planner uses.
"""
import argparse, datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import hav, load_profile, dump, min_to_hm, TERRAIN_ZH

SEMI = 180 / 2 ** 31


def load_fit(path):
    import fitdecode
    recs = []
    with fitdecode.FitReader(path) as fr:
        for f in fr:
            if isinstance(f, fitdecode.FitDataMessage) and f.name == 'record':
                v = {x.name: x.value for x in f.fields}
                if v.get('position_lat') is None or v.get('timestamp') is None: continue
                recs.append(dict(t=v['timestamp'], lat=v['position_lat'] * SEMI, lon=v['position_long'] * SEMI,
                                 hr=v.get('heart_rate')))
    if not recs: raise SystemExit('no GPS records in FIT file')
    return recs


def match(cps, recs, R=60):
    out, i0 = [], 0
    for c in cps:
        best = None
        for i in range(i0, len(recs)):
            d = hav(c['lat'], c['lon'], recs[i]['lat'], recs[i]['lon'])
            if d < R and (best is None or d < best[0]): best = (d, i)
            elif best and d > 250: break
        if best is None:
            out.append(None); continue
        i = best[1]; a = b = i
        while a > 0 and hav(c['lat'], c['lon'], recs[a - 1]['lat'], recs[a - 1]['lon']) < R: a -= 1
        while b < len(recs) - 1 and hav(c['lat'], c['lon'], recs[b + 1]['lat'], recs[b + 1]['lon']) < R: b += 1
        if not c['aid']: a = b = i                       # pass-through point: single timestamp
        out.append(dict(i=i, arr=a, dep=b, off=round(best[0])))
        i0 = b
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fit', required=True); ap.add_argument('--sections', required=True)
    ap.add_argument('--out-dir', required=True); ap.add_argument('--official', help='H:MM:SS official time')
    ap.add_argument('--benchmark-eph', type=float); ap.add_argument('--profile')
    ap.add_argument('--utc-offset', type=float, default=8, help='hours, for clock times (Taiwan = 8)')
    a = ap.parse_args()
    S = json.load(open(a.sections, encoding='utf-8')); p = load_profile(a.profile)
    cps, secs = S['checkpoints'], S['sections']
    recs = load_fit(a.fit); M = match(cps, recs)
    M[0] = M[0] or dict(i=0, arr=0, dep=0, off=None)
    if M[-1] is None: M[-1] = dict(i=len(recs) - 1, arr=len(recs) - 1, dep=len(recs) - 1, off=None)
    missing = [cps[i]['name'] for i, m in enumerate(M) if m is None]
    T = lambda i: recs[i]['t']
    if a.official:
        h, m, s = (list(map(int, a.official.split(':'))) + [0])[:3]
        total_h = h + m / 60 + s / 3600
    else:
        total_h = (T(M[-1]['arr']) - T(M[0]['dep'])).total_seconds() / 3600
    ep = S['course']['ep']; race_eph = ep / total_h

    rows, k = [], 0
    while k < len(secs):
        j = k + 1
        while M[j] is None: j += 1                         # merge across unmatched checkpoints
        ep_s = sum(s['ep'] for s in secs[k:j]); terr = secs[k]['terrain'] if j == k + 1 else 'merged'
        mins = (T(M[j]['arr']) - T(M[k]['dep'])).total_seconds() / 60
        hrs = [recs[i]['hr'] for i in range(M[k]['dep'], M[j]['arr'] + 1) if recs[i]['hr']]
        eph = ep_s / (mins / 60) if mins > 0 else 0
        rows.append(dict(frm=cps[k]['name'], to=cps[j]['name'], terrain=terr, ep=round(ep_s, 2), mins=round(mins, 1),
                         eph=round(eph, 2), factor=round(eph / race_eph, 2), hr=round(sum(hrs) / len(hrs)) if hrs else None,
                         clock=(T(M[j]['arr']) + datetime.timedelta(hours=a.utc_offset)).strftime('%H:%M'),
                         dwell=round((T(M[j]['dep']) - T(M[j]['arr'])).total_seconds() / 60, 1) if cps[j]['aid'] else 0))
        k = j
    agg = {}
    for r in rows:
        if r['terrain'] == 'merged': continue
        g = agg.setdefault(r['terrain'], [0, 0]); g[0] += r['ep']; g[1] += r['mins'] / 60
    newf = {t: round(e / h / race_eph, 2) for t, (e, h) in agg.items()}
    old = {t: v['personal'] for t, v in p['terrain_factors'].items()}
    sugg = {t: round((old[t] + newf[t]) / 2, 2) if t in newf else old[t] for t in old}
    ratio = round(race_eph / a.benchmark_eph, 3) if a.benchmark_eph else None
    stops = sum(r['dwell'] for r in rows)
    res = dict(course=S['course'], official_h=total_h, race_eph=round(race_eph, 2), ratio=ratio, stops_min=round(stops, 1),
               sections=rows, factors_this_race=newf, factors_current=old, factors_suggested=sugg, unmatched=missing)
    os.makedirs(a.out_dir, exist_ok=True); dump(res, os.path.join(a.out_dir, 'post_race.json'))
    L = [f"# {S['course']['name']} 賽後校準", '',
         f"- **完賽：** {min_to_hm(total_h * 60)}（{'官方' if a.official else '手錶'}）・EP {ep}・**比賽 EPH {race_eph:.2f}**",
         f"- **補給站停留：** {stops:.1f} 分"]
    if ratio: L.append(f"- **基準換算比例：** {race_eph:.2f} ÷ {a.benchmark_eph} = **{ratio}**（加入 profile.yaml 的 benchmark.history）")
    if missing: L.append(f"- ⚠ 未對上的檢查點（已合併路段）：{'、'.join(missing)}")
    L += ['', '## 分段', '', '| 路段 | 地形 | EP | 時間 | EPH | 係數 | 心率 | 抵達 | 停留 |', '|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        L.append(f"| {r['frm']} → {r['to']} | {TERRAIN_ZH.get(r['terrain'], '合併')} | {r['ep']} | {r['mins']:.0f}′ | {r['eph']} | {r['factor']} | {r['hr'] or ''} | {r['clock']} | {r['dwell'] or ''} |")
    L += ['', '## 地形係數', '', '| 地形 | 目前 | 本場 | 建議（平均） |', '|---|---|---|---|']
    for t in old:
        L.append(f"| {TERRAIN_ZH[t]} | {old[t]} | {newf.get(t, '—')} | **{sugg[t]}** |")
    L += ['', '更新 profile.yaml 前先確認：本場是否有疾病、賽前疲勞或天候等異常；異常場次只記錄，不平均進係數。']
    md = '\n'.join(L) + '\n'
    open(os.path.join(a.out_dir, 'post_race.md'), 'w', encoding='utf-8').write(md)
    print(md)


if __name__ == '__main__':
    main()
