#!/usr/bin/env python3
"""Render one tier of a plan as a single section table (one plan, no tier columns).

    python3 section_table.py --sections sections.json --plan out/plan.json --out out/table.html \
        [--tier target] [--groups '1-5:大爬升,6-8:起伏,9-11:雙坡'] [--kcal-h 250] [--water-h 500] [--png]

Columns: 區段 · 里程 · 爬升 · 下降 · EP · 耗時 · EPH · 抵達 · 停留 · 最晚離開 · 熱量 · 飲水.
耗時 / EPH are moving; 抵達 is arrival before the stop; kcal and water are intake targets
for the section's moving time. The binding cutoff row is orange, other aid rows blue.
"""
import argparse, html, json, os, subprocess, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
esc = html.escape


def hm(m):
    m = round(m)
    return f'{m // 60}:{m % 60:02d}'


def clock(start, m):
    h, mi = map(int, start.split(':'))
    t = round(h * 60 + mi + m)
    return f'{t // 60 % 24:02d}:{t % 60:02d}'


def r(x, n):
    return int(round(x / n) * n)


def parse_groups(s):
    out = {}
    for part in filter(None, (s or '').split(',')):
        rng, label = part.split(':')
        a, b = map(int, rng.split('-'))
        out[a] = (b - a + 1, label)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sections', required=True); ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--tier', default='target')
    ap.add_argument('--groups', default=''); ap.add_argument('--title', default='')
    ap.add_argument('--kcal-h', type=float, default=250); ap.add_argument('--water-h', type=float, default=500)
    ap.add_argument('--png', action='store_true')
    a = ap.parse_args()

    S = json.load(open(a.sections, encoding='utf-8')); P = json.load(open(a.plan, encoding='utf-8'))
    T = P['tiers'][a.tier]; cps = S['checkpoints']; secs = S['sections']; start = P['start']
    bind = P['binding']['idx']; groups = parse_groups(a.groups); n = len(cps)

    rows, tot = [], dict(km=0, g=0, l=0, ep=0, mv=0, stop=0, kcal=0, water=0)
    for i, c in enumerate(cps):
        name = c['name']
        if 0 < i < n - 1 and not c['aid'] and c.get('ele') is not None:
            name += f' {c["ele"]:,.0f} m'
        if i == 0:
            cells = ['—'] * 6 + [start, '—', '—', '—', '—']
            cls = ''
        else:
            s = secs[i - 1]; mv = T['mins'][i - 1]; stop = P['stops'][i] or 0
            kcal = r(mv / 60 * a.kcal_h, 10); water = r(mv / 60 * a.water_h, 50)
            leave = clock(start, P['latest_leave'][i])
            for k, v in (('km', s['dist']), ('g', s['gain']), ('l', s['loss']), ('ep', s['ep']),
                         ('mv', mv), ('stop', stop), ('kcal', kcal), ('water', water)):
                tot[k] += v
            cells = [f'{s["dist"]:.2f}', f'+{s["gain"]:,}', f'−{s["loss"]:,}', f'{s["ep"]:.1f}', hm(mv),
                     f'{s["ep"] / (mv / 60):.1f}', clock(start, T['arr'][i]), f'{stop:g}' if stop else '—',
                     f'<span class="{"cut" if i == bind else ("fin" if i == n - 1 else "")}">{leave}</span>',
                     f'{kcal:,}', f'{water:,}']
            cls = 'bind' if i == bind else ('aid' if c['aid'] else ('fin' if i == n - 1 else ''))
        g = ''
        if i in groups:
            span, label = groups[i]
            g = f'<td class="grp" rowspan="{span}"><span>{esc(label)}</span></td>'
        elif not any(a0 <= i < a0 + sp for a0, (sp, _) in groups.items()):
            g = '<td class="grp0"></td>'
        rows.append(f'<tr class="{cls}">{g}<td class="nm">{esc(name)}</td>' + ''.join(f'<td>{x}</td>' for x in cells) + '</tr>')

    fin = T['arr'][-1]; c = S['course']
    total = (f'<tr class="tot"><td class="grp0"></td><td class="nm">全程合計</td><td>{c.get("total_km", tot["km"]):.2f}</td>'
             f'<td>+{c.get("gain", tot["g"]):,}</td><td>−{c.get("loss", tot["l"]):,}</td><td>{c.get("ep", tot["ep"]):.1f}</td><td>{hm(tot["mv"])}</td>'
             f'<td>{tot["ep"] / (tot["mv"] / 60):.1f}</td><td>{clock(start, fin)}</td><td>{tot["stop"]:g}</td>'
             f'<td>{clock(start, P["latest_leave"][-1])}</td><td>{tot["kcal"]:,}</td><td>{tot["water"]:,}</td></tr>')

    fdir = os.path.join(SKILL, 'assets', 'fonts')
    fonts = ''.join(f'<link rel="stylesheet" href="file://{fdir}/noto-sans-tc/{w}.css">' for w in (400, 500, 700))
    c = S['course']
    title = a.title or P['title']
    sub = (f'{P["date"]}　{start} 起跑｜目標完賽 {hm(fin)}（{clock(start, fin)}）｜{c["total_km"]:.2f} km・'
           f'+{c["gain"]:,} m・EP {c["ep"]:.1f}｜{P["basis"]}') if "total_km" in c else f'{P["date"]}　{start} 起跑｜目標完賽 {hm(fin)}'
    head = ['區段', '里程 km', '爬升 m', '下降 m', 'EP', '耗時', 'EPH', '抵達', '停留', '最晚離開', '熱量 kcal', '飲水 ml']
    page = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">{fonts}<style>
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{background:#fff}}
body{{font-family:'Noto Sans TC',sans-serif;color:#2b2f33;padding:40px 36px 32px;width:1080px;font-variant-numeric:tabular-nums}}
h1{{font-size:28px;font-weight:700;margin-bottom:6px}} .sub{{color:#6b7177;font-size:15px;margin-bottom:22px}}
table{{width:100%;border-collapse:collapse;font-size:16px}}
th{{font-weight:400;color:#6b7177;text-align:right;padding:8px 6px;border-bottom:1.5px solid #c9cdd1;white-space:nowrap}}
th:nth-child(2){{text-align:left}} td{{text-align:right;padding:8px 6px;border-bottom:1px solid #e6e8ea;white-space:nowrap}}
td.nm{{text-align:left}} td.grp,td.grp0,th.grp0{{border:none;width:34px;padding:0}}
td.grp{{vertical-align:middle;text-align:center;color:#6b7177;font-size:15px}}
td.grp span{{display:inline-block;writing-mode:vertical-rl;letter-spacing:2px;border-left:1.5px solid #9aa0a6;padding:4px 0 4px 6px}}
tr.bind td:not(.grp):not(.grp0){{background:#f8e5d3;font-weight:700;color:#7a3a10}}
tr.aid td:not(.grp):not(.grp0){{background:#e3edf6;font-weight:700;color:#1d3d5c}}
tr.fin td.nm,tr.fin td{{font-weight:700}} span.cut{{color:#C85200}} span.fin{{color:#6b7177;font-weight:400}}
tr.tot td{{font-weight:700;border-top:1.5px solid #9aa0a6;border-bottom:none;padding-top:12px}}
.note{{color:#8a9096;font-size:13px;margin-top:12px;line-height:1.6}}
</style></head><body><h1>{esc(title)}</h1><div class="sub">{esc(sub)}</div>
<table><tr><th class="grp0"></th>{''.join(f'<th>{h}</th>' for h in head)}</tr>{''.join(rows)}{total}</table>
<div class="note">最晚離開＝依計畫配速倒推，仍趕得上之後所有關門的離站時間；橘列為全程最緊的關門，藍列為補給站。耗時、EPH 為移動時間；熱量 {a.kcal_h:.0f} kcal/h、飲水 {a.water_h:.0f} ml/h 按移動時間計。<br>
race-plan skill｜地形係數：{"個人" if P.get("factor_set") == "personal" else "預設"}｜EP = km + 爬升 m ÷ 100</div>
</body></html>'''
    open(a.out, 'w', encoding='utf-8').write(page)
    print(a.out)
    if a.png:
        png = os.path.splitext(a.out)[0] + '.png'
        subprocess.run(['node', os.path.join(SKILL, 'scripts', 'render.js'), a.out, png, '1080'], check=True)
        subprocess.run([sys.executable, os.path.join(SKILL, 'scripts', 'png_dpi.py'), png], check=True)


if __name__ == '__main__':
    main()
