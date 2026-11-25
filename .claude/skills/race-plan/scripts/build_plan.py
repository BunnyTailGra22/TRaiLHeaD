#!/usr/bin/env python3
"""Build a race plan: four tiers (target shown per section), cutoff check, per-section EP/EPH, kcal and water.

    python3 build_plan.py --sections sections.json --start 05:30 --benchmark-eph 12.3 \
        --out-dir out/ [--race-eph 9.0] [--date 2026-11-21] [--profile profile.yaml] [--png]

Writes plan.json, plan.md and plan.html (+ plan.png with --png) to --out-dir.
"""
import argparse, html, json, math, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SKILL, TERRAIN_ZH, load_profile, hm_to_min, min_to_hm, clock, dump

esc = html.escape


# ------------------------------------------------------------------ model
def ratio_for(km, p):
    lo, hi = p['benchmark']['ratio_low'], p['benchmark']['ratio_high']
    if km <= 40: return hi
    if km >= 54: return lo
    return hi + (lo - hi) * (km - 40) / 14


def simulate(S, eph, fade, factors, stops, dec_idx):
    """Return per-checkpoint arr/dep (minutes after start) and per-section minutes."""
    secs = S['sections']
    arr, dep, mins = [0.0], [stops[0]], []
    t = stops[0]
    for k, s in enumerate(secs):
        e = eph * (fade if k >= dec_idx else 1.0)
        m = s['ep'] / (e * factors[s['terrain']]) * 60
        mins.append(m); t += m; arr.append(t); t += stops[k + 1]; dep.append(t)
    return dict(arr=arr, dep=dep, mins=mins)


def cut_rel(cps, start):
    out = []
    for c in cps:
        m = hm_to_min(c['cutoff'])
        if m is None: out.append(None); continue
        r = m - start
        if r < 0: r += 1440
        out.append(r)
    return out


def buffers(sim, cuts):
    return [None if c is None else c - d for c, d in zip(cuts, sim['dep'])]


def latest_leave(sim, cuts):
    n = len(cuts); out = []
    for i in range(n):
        cand = [cuts[j] - (sim['dep'][j] - sim['dep'][i]) for j in range(i, n) if cuts[j] is not None]
        out.append(min(cand) if cand else None)
    return out


def solve_cutoff_line(S, factors, stops, cuts, dec_idx):
    if not any(c is not None for c in cuts): return None
    ok = lambda e: min(b for b in buffers(simulate(S, e, 1.0, factors, stops, dec_idx), cuts) if b is not None) >= 0
    lo, hi = 0.5, 40.0
    if not ok(hi): return None
    for _ in range(60):
        m = (lo + hi) / 2
        if ok(m): hi = m
        else: lo = m
    return hi


# ------------------------------------------------------------------ fueling
def fuel_schedule(S, sim, p, stops, total_min):
    F = p['fueling']; kit = F['kit']; cps = S['checkpoints']; secs = S['sections']
    hours = total_min / 60
    lo_c, hi_c = F['targets']['carbs_g_h']
    target_c = hi_c if hours > 9 else lo_c
    interval = 40 if hours > 9 else F['gel_interval_min']
    wt = p['athlete']['weight_kg']; caf_max = F['targets']['caffeine_mg_kg_max'] * wt
    aid_idx = [i for i, c in enumerate(cps) if c['aid']]

    def where(t):
        for k, s in enumerate(secs):
            if sim['dep'][k] <= t < sim['arr'][k + 1]: return k
        return None

    def build(iv):
        items, t = [], iv
        while t < total_min - 15:
            k = where(t); tt, note = t, ''
            if k is not None and secs[k]['terrain'].startswith('descent') and sim['mins'][k] >= 15:
                tt, note = sim['dep'][k], f'{secs[k]["to"]} 下坡前'
            near_aid = any(sim['arr'][i] - 5 <= tt <= sim['dep'][i] + 10 for i in aid_idx)
            if not near_aid and (not items or tt - items[-1]['t'] >= 15):
                items.append(dict(t=tt, sec=k, note=note))
            t += iv
        # assign item types
        half = total_min / 2; bar_done = 0; chews = 0
        for it in items:
            it['type'] = 'gel'
        for it in items:
            if bar_done < F.get('bars_per_race', 1) and it['t'] >= half and it['sec'] is not None \
                    and secs[it['sec']]['terrain'] in ('steep_climb', 'reclimb'):
                it['type'] = 'bar'; bar_done += 1
        if bar_done < F.get('bars_per_race', 1):
            for it in items:
                if it['t'] >= half and it['type'] == 'gel': it['type'] = 'bar'; bar_done += 1; break
        for it in items:
            if chews < F.get('chews_per_race', 2) and it['type'] == 'gel' and it['sec'] is not None \
                    and secs[it['sec']]['terrain'] == 'technical_mixed':
                it['type'] = 'chew'; chews += 1
        n_el = max(1, round(total_min / F['electrolyte_interval_min']))
        n_aid = len(aid_idx)
        tot = dict(carbs=0.0, sodium=0.0, caffeine=0.0, kcal=0.0)
        def add(item, n=1):
            for k in tot: tot[k] += kit[item].get(k, 0) * n
        for it in items: add(it['type'])
        add('electrolyte', n_el); add('aid_stop', n_aid); add('caffeine_tablet')
        return items, n_el, n_aid, tot

    iv = interval
    while True:
        items, n_el, n_aid, tot = build(iv)
        if tot['carbs'] / hours >= target_c or iv <= 30: break
        iv -= 5
    # caffeine cap: turn bars into gels if over
    while tot['caffeine'] > caf_max and any(i['type'] == 'bar' for i in items):
        b = next(i for i in items if i['type'] == 'bar'); b['type'] = 'gel'
        for k, v in (('carbs', kit['gel']['carbs'] - kit['bar']['carbs']), ('caffeine', -kit['bar']['caffeine']),
                     ('sodium', kit['gel']['sodium'] - kit['bar']['sodium'])):
            tot[k] += v
    water = n_el * kit['electrolyte'].get('water_ml', 500)
    per_h = dict(carbs=tot['carbs'] / hours, sodium=tot['sodium'] / hours, fluid=water / hours,
                 caffeine_mg_kg=tot['caffeine'] / wt)
    counts = {k: sum(1 for i in items if i['type'] == k) for k in ('gel', 'bar', 'chew')}
    counts.update(electrolyte=n_el, aid_stop=n_aid, caffeine_tablet=1)
    short = max(0, math.ceil((target_c * hours - tot['carbs']) / kit['gel']['carbs']))
    return dict(interval=iv, items=items, counts=counts, totals=tot, per_h=per_h, target_carbs=target_c, short_gels=short,
                electrolyte_every=F['electrolyte_interval_min'])


def row_fuel(sim, fuel, p, aid, total_min):
    """Allocate kcal and water to table rows. Row i (i >= 1) covers [dep[i-1], dep[i]):
    section i-1 plus the stop at checkpoint i, so aid-station food counts on its own row."""
    kit = p['fueling']['kit']; dep = sim['dep']; n = len(dep)
    rows = [dict(kcal=0.0, water=0.0, gel=0, bar=0, chew=0, electrolyte=0, aid=bool(aid[i]) and i > 0) for i in range(n)]
    def row_of(t):
        for i in range(1, n):
            if t < dep[i]: return i
        return n - 1
    for it in fuel['items']:
        r = rows[row_of(it['t'])]; r[it['type']] += 1; r['kcal'] += kit[it['type']]['kcal']
    every = fuel['electrolyte_every']
    for e in range(1, fuel['counts']['electrolyte'] + 1):
        r = rows[row_of(min(e * every, total_min - 1))]; r['electrolyte'] += 1; r['kcal'] += kit['electrolyte']['kcal']
    rate = fuel['per_h']['fluid']
    for i in range(1, n):
        r = rows[i]
        if r['aid']: r['kcal'] += kit['aid_stop']['kcal']
        r['water'] = round((dep[i] - dep[i - 1]) / 60 * rate / 50) * 50
    return rows


def items_zh(r):
    parts = [f'{ITEM_ZH[k]} {r[k]}' for k in ('gel', 'bar', 'chew', 'electrolyte') if r[k]]
    if r['aid']: parts.append('補給站')
    return '・'.join(parts)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sections', required=True); ap.add_argument('--profile')
    ap.add_argument('--start', required=True, help='HH:MM')
    ap.add_argument('--benchmark-eph', type=float); ap.add_argument('--race-eph', type=float)
    ap.add_argument('--default-factors', action='store_true', help='use default instead of personal factors')
    ap.add_argument('--date', default=''); ap.add_argument('--title', default='')
    ap.add_argument('--out-dir', required=True); ap.add_argument('--png', action='store_true')
    a = ap.parse_args()
    if not (a.benchmark_eph or a.race_eph):
        raise SystemExit('give --benchmark-eph (劍中劍 EP/h, last 6 weeks) or --race-eph')

    S = json.load(open(a.sections, encoding='utf-8')); p = load_profile(a.profile)
    cps, secs = S['checkpoints'], S['sections']; km = S['course']['total_km']
    start = hm_to_min(a.start)
    col = 'default' if a.default_factors else 'personal'
    factors = {k: v[col] for k, v in p['terrain_factors'].items()}
    stops = [c['stop_min'] if c['stop_min'] is not None else (p['pacing']['default_stop_min'] if c['aid'] else 0)
             for c in cps]
    stops[0] = 0; stops[-1] = 0
    cuts = cut_rel(cps, start)
    dec_idx = next((i for i, c in enumerate(cps) if c['decision']), None)
    if dec_idx is None: dec_idx = next((i for i, c in enumerate(cps) if c['cutoff'] and i > 0), len(cps) - 1)

    # tier EP/h
    T = p['tiers']
    if a.race_eph:
        r_mid = None; e = dict(stretch=a.race_eph * T['stretch']['uplift'], target=a.race_eph, fallback=a.race_eph * 0.96)
        basis = f'指定比賽 EPH {a.race_eph:.2f}'
    else:
        r_mid = ratio_for(km, p); b = a.benchmark_eph
        e = dict(stretch=b * r_mid * T['stretch']['uplift'], target=b * r_mid, fallback=b * p['benchmark']['ratio_low'])
        basis = f"{p['benchmark']['name']} EPH {b:.1f} × {p['benchmark']['ratio_low']:.2f}–{p['benchmark']['ratio_high']:.2f}（本場 {r_mid:.3f}）"
    tiers = {}
    for name in ('stretch', 'target', 'fallback'):
        tiers[name] = dict(eph=e[name], fade=T[name]['fade'],
                           sim=simulate(S, e[name], T[name]['fade'], factors, stops, dec_idx))
    ce = solve_cutoff_line(S, factors, stops, cuts, dec_idx)
    if ce: tiers['cutoff'] = dict(eph=ce, fade=1.0, sim=simulate(S, ce, 1.0, factors, stops, dec_idx))
    for t in tiers.values():
        t['buffers'] = buffers(t['sim'], cuts); t['finish'] = t['sim']['arr'][-1]
        t['misses'] = [cps[i]['name'] for i, b in enumerate(t['buffers']) if b is not None and b < 0]
    tgt = tiers['target']; latest = latest_leave(tgt['sim'], cuts)
    binding = None
    if 'cutoff' in tiers:
        bi = min((i for i, b in enumerate(tiers['cutoff']['buffers']) if b is not None),
                 key=lambda i: tiers['cutoff']['buffers'][i])
        binding = dict(idx=bi, name=cps[bi]['name'], target_buffer=tgt['buffers'][bi])
    fuel = fuel_schedule(S, tgt['sim'], p, stops, tgt['finish'])
    fuel['rows'] = row_fuel(tgt['sim'], fuel, p, [c['aid'] for c in cps], tgt['finish'])

    os.makedirs(a.out_dir, exist_ok=True)
    title = a.title or S['course']['name']
    res = dict(title=title, date=a.date, start=a.start, basis=basis, ratio=r_mid, factor_set=col,
               decision=cps[dec_idx]['name'], binding=binding, stops=stops, cutoffs_rel=cuts, latest_leave=latest,
               tiers={k: dict(eph=v['eph'], fade=v['fade'], finish=v['finish'], misses=v['misses'],
                              arr=v['sim']['arr'], dep=v['sim']['dep'], mins=v['sim']['mins'], buffers=v['buffers'])
                      for k, v in tiers.items()},
               fuel=fuel, course=S['course'])
    dump(res, os.path.join(a.out_dir, 'plan.json'))
    md = render_md(S, res, p, start)
    open(os.path.join(a.out_dir, 'plan.md'), 'w', encoding='utf-8').write(md)
    open(os.path.join(a.out_dir, 'plan.html'), 'w', encoding='utf-8').write(render_html(S, res, p, start))
    print(md)
    if a.png:
        out = os.path.join(a.out_dir, 'plan.png')
        subprocess.run(['node', os.path.join(SKILL, 'scripts', 'render.js'), os.path.join(a.out_dir, 'plan.html'), out, '1080'], check=True)
        subprocess.run([sys.executable, os.path.join(SKILL, 'scripts', 'png_dpi.py'), out], check=True)


TIER_ZH = dict(stretch='衝刺', target='目標', fallback='保守', cutoff='關門線')
ITEM_ZH = dict(gel='凝膠', bar='能量棒', chew='軟糖', electrolyte='電解質')


def render_md(S, R, p, start):
    cps, secs = S['checkpoints'], S['sections']; tg = R['tiers']['target']; F = R['fuel']; c = S['course']
    L = [f"# {R['title']} 完賽計畫", '',
         f"{R['date']} {R['start']} 起跑｜{c['total_km']} km・+{c['gain']} m・EP {c['ep']}", '',
         f"- **預測依據：** {R['basis']}",
         f"- **目標完賽：** {min_to_hm(tg['finish'])}（{clock(start + tg['finish'])}），目標 EPH {tg['eph']:.2f}",
         f"- **決策點：** {R['decision']}"]
    if R['binding']:
        L.append(f"- **最先卡關的關門：** {R['binding']['name']}（目標餘裕 {min_to_hm(R['binding']['target_buffer'])}）")
    for k, t in R['tiers'].items():
        if t['misses']: L.append(f"- ⚠ {TIER_ZH[k]}會錯過關門：{'、'.join(t['misses'])}")
    rf = F['rows']
    L += ['', '## 分段', '',
          'EPH = 段 EP ÷ 移動時間（合計含停留）；熱量含該段隨身補給與抵達站補給；飲水以 '
          f"{F['per_h']['fluid']:.0f} ml/h 估", '',
          '| # | 檢查點 | km | 段 km | 爬/降 m | 地形 | EP | EPH | 用時 | 抵達 | 熱量 kcal | 飲水 ml | 補給 | 關門 | 最晚離站 |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for i, cp in enumerate(cps):
        s = secs[i - 1] if i else None
        ll = clock(start + R['latest_leave'][i]) if R['latest_leave'][i] is not None and i < len(cps) - 1 else ''
        stop = f"（停 {R['stops'][i]:.0f}′）" if R['stops'][i] else ''
        if s:
            m = tg['mins'][i - 1]
            seg = (f"{s['dist']:.1f} | +{s['gain']}/−{s['loss']} | {TERRAIN_ZH[s['terrain']]} | {s['ep']:.1f} | "
                   f"{s['ep'] / m * 60:.1f} | {m:.0f}′")
            fu = f"{rf[i]['kcal']:.0f} | {rf[i]['water']:.0f} | {items_zh(rf[i])}"
        else:
            seg, fu = '— | — | — | — | — | —', '— | — | —'
        L.append(f"| {i} | {cp['name']}{stop} | {cp['km']:.1f} | {seg} | {clock(start + tg['arr'][i])} | {fu} | {cp['cutoff'] or ''} | {ll} |")
    L.append(f"| | **合計** | {c['total_km']} | | +{c['gain']} | | {c['ep']} | {c['ep'] / tg['finish'] * 60:.2f} | {min_to_hm(tg['finish'])} | "
             f"{clock(start + tg['finish'])} | {sum(r['kcal'] for r in rf):.0f} | {sum(r['water'] for r in rf):.0f} | | | |")
    L += ['', '其他配速完賽：' + '・'.join(f"{TIER_ZH[k]} {min_to_hm(R['tiers'][k]['finish'])}" for k in ('stretch', 'fallback', 'cutoff') if k in R['tiers'])]
    L += ['', '## 補給', '',
          f"- **節奏：** 每 {F['interval']} 分一份碳水，長下坡前提前吃；電解質每 {F['electrolyte_every']} 分一包；起跑前 30–60 分咖啡因錠",
          f"- **數量：** 凝膠 {F['counts']['gel']}・能量棒 {F['counts']['bar']}・軟糖 {F['counts']['chew']}・電解質 {F['counts']['electrolyte']}・補給站 {F['counts']['aid_stop']} 站・咖啡因錠 1",
          *([f"- ⚠ 碳水未達目標：補給站多拿或另帶 {F['short_gels']} 條凝膠"] if F['short_gels'] else []),
          f"- **每小時：** 熱量 {sum(r['kcal'] for r in F['rows']) / (R['tiers']['target']['finish'] / 60):.0f} kcal・碳水 {F['per_h']['carbs']:.0f} g/h（目標 ≥{F['target_carbs']}）・鈉 {F['per_h']['sodium']:.0f} mg/h・水 {F['per_h']['fluid']:.0f} ml/h・咖啡因 {F['per_h']['caffeine_mg_kg']:.1f} mg/kg",
          '', '## 賽中提示', '',
          f"- **心率上限：** 開場柏油 ≤ {p['pacing']['hr_cap_opening']}",
          f"- **決策點：** {R['decision']}，比對目標與保守的抵達時間，落後就切換保守計畫",
          '- **停留上限：** ' + '、'.join(f"{cps[i]['name']} {R['stops'][i]:.0f} 分" for i in range(len(cps)) if R['stops'][i]),
          '', '## 數字標記', '',
          f"- **有資料依據：** 賽道 GPX、基準換算比例（{len(p['benchmark']['history'])} 場）、個人地形係數（FT40 2026）、補給商品營養標示",
          '- **假設：** 停留時間、保守計畫衰退 0.90、補給站碳水、地形分類（坡度規則，可在 checkpoints.csv 覆寫）',
          '- **必帶裝備：** 依大會規定另列（此腳本不產生）']
    return '\n'.join(L) + '\n'


def render_html(S, R, p, start):
    cps, secs = S['checkpoints'], S['sections']; tg = R['tiers']['target']; F = R['fuel']; c = S['course']
    fdir = os.path.join(SKILL, 'assets', 'fonts')
    fonts = ''.join(f'<link rel="stylesheet" href="file://{fdir}/{f}/{w}.css">' for f in ('noto-sans-tc', 'roboto-mono') for w in (400, 500, 700))
    # profile svg
    W, H, padL, padR, top, bot = 984, 190, 44, 8, 14, 26
    prof = S['profile']; ys = [q[1] for q in prof]
    y0, y1 = min(ys), max(ys); y0 -= (y1 - y0) * 0.05
    X = lambda k: padL + (W - padL - padR) * k / c['total_km']
    Y = lambda e: top + (H - top - bot) * (1 - (e - y0) / (y1 - y0))
    poly = ' '.join(f'{X(a):.1f},{Y(b):.1f}' for a, b in prof)
    area = f'M{X(0):.1f},{H - bot} L' + poly.replace(' ', ' L') + f' L{X(c["total_km"]):.1f},{H - bot} Z'
    marks = ''
    for i, cp in enumerate(cps):
        x = X(cp['km']); y = Y(cp['ele']); col = '#C85200' if cp['cutoff'] else '#1170AA'
        marks += f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{H - bot}" stroke="{col}" stroke-width="1" stroke-dasharray="2 3"/>'
        marks += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{col}"/><text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">{i}</text>'
    ticks = ''.join(f'<text x="{X(k):.1f}" y="{H - 8}" text-anchor="middle" font-size="12" fill="#7B848F">{k}</text>' for k in range(0, int(c['total_km']) + 1, 5))
    eticks = ''.join(f'<text x="{padL - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="12" fill="#7B848F">{v}</text><line x1="{padL}" x2="{W - padR}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#E6EAEE"/>'
                     for v in range(int(math.ceil(y0 / 500) * 500), int(y1) + 1, 500))
    svg = f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{eticks}<path d="{area}" fill="#EAF3FA"/><polyline points="{poly}" fill="none" stroke="#1170AA" stroke-width="2"/>{marks}{ticks}</svg>'
    rows = ''; rf = F['rows']
    for i, cp in enumerate(cps):
        s = secs[i - 1] if i else None
        ll = clock(start + R['latest_leave'][i]) if R['latest_leave'][i] is not None and i < len(cps) - 1 else ''
        stop = f'<small>停 {R["stops"][i]:.0f}′</small>' if R['stops'][i] else ''
        if s:
            m = tg['mins'][i - 1]
            seg = (f'<td class="m">{s["dist"]:.1f}</td><td class="m">+{s["gain"]}/−{s["loss"]}</td>'
                   f'<td><span class="tt {s["terrain"]}">{TERRAIN_ZH[s["terrain"]]}</span></td>'
                   f'<td class="m">{s["ep"]:.1f}</td><td class="m">{s["ep"] / m * 60:.1f}</td><td class="m">{m:.0f}′</td>')
            fu = (f'<td class="m fu">{rf[i]["kcal"]:.0f}<small>{esc(items_zh(rf[i]))}</small></td>'
                  f'<td class="m">{rf[i]["water"]:.0f}</td>')
        else:
            seg, fu = '<td></td>' * 6, '<td></td>' * 2
        cls = ' class="cut"' if cp['cutoff'] else ''
        rows += (f'<tr{cls}><td><span class="no">{i}</span></td><td class="nm"><b>{esc(cp["name"])}</b>{stop}</td><td class="m">{cp["km"]:.1f}</td>'
                 f'{seg}<td class="m tg">{clock(start + tg["arr"][i])}</td>{fu}<td class="m c">{cp["cutoff"] or ""}</td><td class="m">{ll}</td></tr>')
    kc = sum(r['kcal'] for r in rf); wa = sum(r['water'] for r in rf)
    rows += (f'<tr class="tot"><td></td><td class="nm"><b>合計</b></td><td class="m">{c["total_km"]:.1f}</td><td></td>'
             f'<td class="m">+{c["gain"]}</td><td></td><td class="m">{c["ep"]:.1f}</td><td class="m">{c["ep"] / tg["finish"] * 60:.2f}</td>'
             f'<td class="m">{min_to_hm(tg["finish"])}</td><td class="m tg">{clock(start + tg["finish"])}</td>'
             f'<td class="m">{kc:.0f}</td><td class="m">{wa:.0f}</td><td></td><td></td></tr>')
    bind = (f'{esc(R["binding"]["name"])} 餘裕 {min_to_hm(R["binding"]["target_buffer"])}' if R['binding'] else '無關門')
    warn = ''.join(f'<div class="warn">⚠ {TIER_ZH[k]}會錯過關門：{esc("、".join(t["misses"]))}</div>' for k, t in R['tiers'].items() if t['misses'])
    if F['short_gels']:
        warn += f'<div class="warn">⚠ 碳水未達 {F["target_carbs"]} g/h：補給站多拿或另帶 {F["short_gels"]} 條凝膠</div>'
    k = F['counts']
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">{fonts}<style>
:root{{--blue:#1170AA;--bt:#A3CCE9;--btint:#EAF3FA;--ox:#C85200;--of:#FC7D0B;--ot:#FFBC79;--otint:#FFF2E6;
--g1:#57606C;--g2:#7B848F;--g3:#A3ACB9;--grid:#C8D0D9;--card:#F4F6F8;--t:#2E333B;--bdark:#0B3A57;--odark:#4A2500}}
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{background:#fff}}
body{{width:1080px;padding:44px 48px 36px;font-family:"Segoe UI","Noto Sans TC",sans-serif;color:var(--t);font-size:18px;line-height:1.4}}
.m,.kv{{font-family:"Roboto Mono","Noto Sans TC",monospace}}
h1{{font-size:34px;line-height:1.3}} .sub{{color:var(--g1);font-size:18px;margin-top:6px}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:20px}}
.k{{background:var(--card);border-radius:14px;padding:12px 16px}} .k.hl{{background:var(--btint)}}
.kl{{font-size:15px;color:var(--g1)}} .kv{{font-size:32px;font-weight:700;color:var(--blue);line-height:1.2}} .ks{{font-size:14px;color:var(--g2)}}
h2{{font-size:22px;margin:22px 0 8px;display:flex;gap:10px;align-items:baseline}} h2 span{{font-size:14.5px;font-weight:400;color:var(--g2)}}
table{{width:100%;border-collapse:collapse;font-size:15.5px}}
th{{font-size:13.5px;color:var(--g2);font-weight:500;text-align:right;padding:4px 5px;border-bottom:1.5px solid var(--grid)}} th.l{{text-align:left}}
td{{padding:5px 5px;border-bottom:1px solid #E6EAEE;vertical-align:middle}} td.m{{text-align:right;white-space:nowrap}}
td.tg{{background:var(--btint);color:var(--bdark);font-weight:700}} td.c{{color:var(--ox);font-weight:700}}
tr.cut td.nm b{{color:var(--odark)}}
.nm b{{font-weight:500}} .nm small{{display:block;font-size:12.5px;color:var(--g2)}}
.no{{display:inline-flex;width:22px;height:22px;border-radius:50%;background:var(--blue);color:#fff;font-size:12px;font-weight:700;align-items:center;justify-content:center}}
tr.cut .no{{background:var(--ox)}}
.tt{{font-size:13px;border-radius:6px;padding:1px 7px;background:var(--card);color:var(--g1);white-space:nowrap}}
.tt.steep_climb,.tt.reclimb{{background:var(--blue);color:#fff}} .tt.descent_technical,.tt.descent_forest_road{{background:var(--otint);color:var(--odark)}}
td.fu small{{display:block;font-family:"Noto Sans TC",sans-serif;font-size:11.5px;color:var(--g2);font-weight:400}}
tr.tot td{{border-top:1.5px solid var(--grid);border-bottom:none;font-weight:700}}
.fl{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:10px}} .bx{{background:var(--card);border-radius:12px;padding:10px 16px;font-size:15.5px;color:var(--g1)}}
.bx b{{color:var(--t)}} .bx li{{list-style:none;padding:3px 0}}
.warn{{margin-top:10px;background:var(--otint);color:var(--odark);border-radius:10px;padding:8px 14px;font-weight:700}}
.foot{{margin-top:18px;border-top:1.5px solid var(--grid);padding-top:10px;font-size:17px;color:var(--g1)}} .foot b{{color:var(--t)}}
.src{{font-size:13.5px;color:var(--g3);margin-top:6px}}
</style></head><body>
<h1>{esc(R["title"])}・目標 {min_to_hm(tg["finish"])} 完賽計畫</h1>
<div class="sub">{esc(R["date"])}　{R["start"]} 起跑｜{c["total_km"]} km・+{c["gain"]} m・EP {c["ep"]}｜{esc(R["basis"])}</div>
<div class="kpis">
 <div class="k hl"><div class="kl">目標完賽</div><div class="kv">{min_to_hm(tg["finish"])}</div><div class="ks">抵達 {clock(start + tg["finish"])}</div></div>
 <div class="k"><div class="kl">目標 EPH</div><div class="kv">{tg["eph"]:.2f}</div><div class="ks">衝刺 {R["tiers"]["stretch"]["eph"]:.2f}・保守 {R["tiers"]["fallback"]["eph"]:.2f}</div></div>
 <div class="k"><div class="kl">最先卡關</div><div class="kv">{min_to_hm(R["binding"]["target_buffer"]) if R["binding"] else "—"}</div><div class="ks">{bind}</div></div>
 <div class="k"><div class="kl">碳水</div><div class="kv">{F["per_h"]["carbs"]:.0f}</div><div class="ks">g/h・鈉 {F["per_h"]["sodium"]:.0f} mg/h</div></div>
</div>{warn}
<h2>剖面與檢查點<span>橘色 = 有關門</span></h2>{svg}
<h2>分段<span>EPH = 段 EP ÷ 移動時間（合計含停留）；熱量含該段隨身補給與抵達站補給；飲水 {F["per_h"]["fluid"]:.0f} ml/h</span></h2>
<table><thead><tr><th class="l">#</th><th class="l">檢查點</th><th>km</th><th>段 km</th><th>爬／降 m</th><th class="l">地形</th><th>EP</th><th>EPH</th><th>用時</th><th>抵達</th><th>熱量 kcal</th><th>飲水 ml</th><th>關門</th><th>最晚離站</th></tr></thead><tbody>{rows}</tbody></table>
<div class="fl">
 <div class="bx"><ul><li><b>數量：</b>凝膠 {k["gel"]}・能量棒 {k["bar"]}・軟糖 {k["chew"]}・電解質 {k["electrolyte"]} 包・咖啡因錠 1・補給站 {k["aid_stop"]} 站</li>
 <li><b>每小時：</b>熱量 {kc / (tg["finish"] / 60):.0f} kcal・碳水 {F["per_h"]["carbs"]:.0f} g・鈉 {F["per_h"]["sodium"]:.0f} mg・水 {F["per_h"]["fluid"]:.0f} ml・咖啡因 {F["per_h"]["caffeine_mg_kg"]:.1f} mg/kg</li></ul></div>
 <div class="bx"><ul><li><b>心率上限：</b>開場柏油 ≤ {p["pacing"]["hr_cap_opening"]}</li>
 <li><b>決策點：</b>{esc(R["decision"])}；落後目標就切換保守</li>
 <li><b>節奏：</b>每 {F["interval"]} 分一份碳水，長下坡前提前吃；電解質每 {F["electrolyte_every"]} 分一包；起跑前 30–60 分咖啡因錠</li>
 <li><b>其他配速：</b>{"・".join(f"{TIER_ZH[t]} {min_to_hm(R['tiers'][t]['finish'])}" for t in ("stretch", "fallback", "cutoff") if t in R["tiers"])}</li></ul></div>
</div>
<div class="foot"><b>標記：</b>資料依據＝賽道 GPX、基準換算（{len(p["benchmark"]["history"])} 場）、個人地形係數、營養標示；假設＝停留時間、保守衰退 0.90、補給站碳水、坡度規則分類。必帶裝備依大會規定另列。</div>
<div class="src">race-plan skill v{p.get("version", "0.1")}｜地形係數：{"個人" if R["factor_set"] == "personal" else "預設"}｜EP = km + 爬升 m ÷ 100</div>
</body></html>'''


if __name__ == '__main__':
    main()
