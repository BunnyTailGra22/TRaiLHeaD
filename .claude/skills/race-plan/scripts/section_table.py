#!/usr/bin/env python3
"""Section table: one plan (the target tier), one row per section.

Used by build_plan.py for plan.md / plan.html. Also runs on its own to re-render
the table from an existing plan.json:

    python3 section_table.py --sections sections.json --plan out/plan.json --out out/table.html \
        [--groups '1-5:大爬升,6-8:起伏,9-11:雙坡'] [--kcal-h 250] [--water-h 500] [--png]

Columns: 區段 · 里程 · 爬升 · 下降 · EP · 耗時 · EPH · 抵達 · 停留 · 最晚離開 · 熱量 · 飲水.
耗時 / EPH are moving; 抵達 is arrival before the stop; kcal and water are intake targets
for the section's moving time. The binding cutoff row is orange, other aid rows blue.
--groups draws a labelled bracket over a run of rows (row numbers = checkpoint index).
"""
import argparse, html, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SKILL, hm_to_min, min_to_hm, clock

esc = html.escape

CSS = '''
table.st{width:100%;border-collapse:collapse;font-size:15.5px;font-variant-numeric:tabular-nums}
table.st th{font-weight:400;font-size:14px;color:#6b7177;text-align:right;padding:7px 5px;border-bottom:1.5px solid #c9cdd1;white-space:nowrap}
table.st th.nm{text-align:left} table.st td{text-align:right;padding:7px 5px;border-bottom:1px solid #e6e8ea;white-space:nowrap}
table.st td.nm{text-align:left} table.st td.g,table.st th.g{border:none;width:30px;padding:0}
table.st td.g{vertical-align:middle;text-align:center;color:#6b7177;font-size:14px}
table.st td.g span{display:inline-block;writing-mode:vertical-rl;letter-spacing:2px;border-left:1.5px solid #9aa0a6;padding:4px 0 4px 5px}
table.st tr.bind td:not(.g){background:#f8e5d3;font-weight:700;color:#7a3a10}
table.st tr.aid td:not(.g){background:#e3edf6;font-weight:700;color:#1d3d5c}
table.st tr.fin td{font-weight:700} table.st span.cut{color:#C85200} table.st span.fin{color:#6b7177;font-weight:400}
table.st tr.tot td{font-weight:700;border-top:1.5px solid #9aa0a6;border-bottom:none;padding-top:11px}
.stnote{color:#8a9096;font-size:13px;margin-top:8px;line-height:1.6}
'''
HEAD = ['區段', '里程 km', '爬升 m', '下降 m', 'EP', '耗時', 'EPH', '抵達', '停留', '最晚離開', '熱量 kcal', '飲水 ml']


def _r(x, n):
    return int(round(x / n) * n)


def parse_groups(s):
    """'1-5:大爬升,6-8:起伏' -> {1: (5, '大爬升'), 6: (3, '起伏')}"""
    out = {}
    for part in filter(None, (s or '').split(',')):
        rng, label = part.split(':', 1)
        a, b = map(int, rng.split('-'))
        out[a] = (b - a + 1, label.strip())
    return out


def build(S, R, kcal_h, water_h, tier='target'):
    """Rows and totals for one tier. R is the plan.json dict."""
    T = R['tiers'][tier]; cps, secs = S['checkpoints'], S['sections']; c = S['course']
    start = hm_to_min(R['start']); n = len(cps); bind = (R.get('binding') or {}).get('idx')
    rows, mv_tot, stop_tot, kcal_tot, water_tot = [], 0.0, 0.0, 0, 0
    for i, cp in enumerate(cps):
        name = cp['name']
        if 0 < i < n - 1 and not cp['aid'] and cp.get('ele') is not None:
            name += f' {cp["ele"]:,.0f} m'
        kind = 'bind' if i == bind else ('fin' if i == n - 1 else ('aid' if cp['aid'] else ''))
        row = dict(i=i, name=name, kind=kind, arr=clock(start + T['arr'][i]))
        if i:
            s = secs[i - 1]; mv = T['mins'][i - 1]; stop = R['stops'][i] or 0
            ll = R['latest_leave'][i]
            row.update(dist=s['dist'], gain=s['gain'], loss=s['loss'], ep=s['ep'], mv=mv, eph=s['ep'] / (mv / 60),
                       stop=stop, leave=clock(start + ll) if ll is not None else '—',
                       kcal=_r(mv / 60 * kcal_h, 10), water=_r(mv / 60 * water_h, 50))
            mv_tot += mv; stop_tot += stop; kcal_tot += row['kcal']; water_tot += row['water']
        rows.append(row)
    ll = R['latest_leave'][-1]
    tot = dict(dist=c['total_km'], gain=c['gain'], loss=c['loss'], ep=c['ep'], mv=mv_tot, eph=c['ep'] / (mv_tot / 60),
               arr=clock(start + T['arr'][-1]), stop=stop_tot, leave=clock(start + ll) if ll is not None else '—',
               kcal=kcal_tot, water=water_tot)
    return rows, tot


def _cells(r, md=False):
    if 'dist' not in r:
        return ['—'] * 6 + [r['arr'], '—', '—', '—', '—']
    leave = r['leave']
    if r['kind'] == 'bind':
        leave = f'**{leave}**' if md else f'<span class="cut">{leave}</span>'
    elif r['kind'] == 'fin' and not md:
        leave = f'<span class="fin">{leave}</span>'
    return [f'{r["dist"]:.2f}', f'+{r["gain"]:,}', f'−{r["loss"]:,}', f'{r["ep"]:.1f}', min_to_hm(r['mv']),
            f'{r["eph"]:.1f}', r['arr'], f'{r["stop"]:g}' if r['stop'] else '—', leave, f'{r["kcal"]:,}', f'{r["water"]:,}']


def _tot_cells(t):
    return [f'{t["dist"]:.2f}', f'+{t["gain"]:,}', f'−{t["loss"]:,}', f'{t["ep"]:.1f}', min_to_hm(t['mv']),
            f'{t["eph"]:.1f}', t['arr'], f'{t["stop"]:g}', t['leave'], f'{t["kcal"]:,}', f'{t["water"]:,}']


def note(kcal_h, water_h):
    return (f'最晚離開＝依計畫配速倒推，仍趕得上之後所有關門的離站時間；橘列為全程最緊的關門，藍列為補給站。'
            f'耗時、EPH 為移動時間；熱量 {kcal_h:.0f} kcal/h、飲水 {water_h:.0f} ml/h 按移動時間計。')


def html_table(S, R, kcal_h, water_h, groups=''):
    rows, tot = build(S, R, kcal_h, water_h); G = parse_groups(groups)
    covered = {i for a, (sp, _) in G.items() for i in range(a, a + sp)}
    out = ['<table class="st"><tr><th class="g"></th>' + ''.join(
        f'<th class="{"nm" if k == 0 else ""}">{h}</th>' for k, h in enumerate(HEAD)) + '</tr>']
    for r in rows:
        i = r['i']
        g = (f'<td class="g" rowspan="{G[i][0]}"><span>{esc(G[i][1])}</span></td>' if i in G
             else ('' if i in covered else '<td class="g"></td>'))
        out.append(f'<tr class="{r["kind"]}">{g}<td class="nm">{esc(r["name"])}</td>'
                   + ''.join(f'<td>{x}</td>' for x in _cells(r)) + '</tr>')
    out.append('<tr class="tot"><td class="g"></td><td class="nm">全程合計</td>'
               + ''.join(f'<td>{x}</td>' for x in _tot_cells(tot)) + '</tr></table>')
    return ''.join(out)


def md_table(S, R, kcal_h, water_h, groups=''):
    rows, tot = build(S, R, kcal_h, water_h); G = parse_groups(groups)
    label = {a: lab for a, (sp, lab) in G.items()}
    L = ['| 段落 | ' + ' | '.join(HEAD) + ' |', '|---|---|' + '---:|' * (len(HEAD) - 1)]
    for r in rows:
        nm = f'**{r["name"]}**' if r['kind'] in ('bind', 'aid', 'fin') else r['name']
        L.append(f'| {label.get(r["i"], "")} | {nm} | ' + ' | '.join(_cells(r, md=True)) + ' |')
    L.append('| | **全程合計** | ' + ' | '.join(f'**{x}**' for x in _tot_cells(tot)) + ' |')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sections', required=True); ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--title', default='')
    ap.add_argument('--groups'); ap.add_argument('--kcal-h', type=float); ap.add_argument('--water-h', type=float)
    ap.add_argument('--png', action='store_true')
    a = ap.parse_args()
    S = json.load(open(a.sections, encoding='utf-8')); R = json.load(open(a.plan, encoding='utf-8'))
    tb = R.get('table', {})
    kcal_h = a.kcal_h or tb.get('kcal_h', 250); water_h = a.water_h or tb.get('water_ml_h', 500)
    groups = a.groups if a.groups is not None else tb.get('groups', '')
    c = S['course']; T = R['tiers']['target']; start = hm_to_min(R['start'])
    fdir = os.path.join(SKILL, 'assets', 'fonts')
    fonts = ''.join(f'<link rel="stylesheet" href="file://{fdir}/noto-sans-tc/{w}.css">' for w in (400, 500, 700))
    sub = (f'{R["date"]}　{R["start"]} 起跑｜目標完賽 {min_to_hm(T["finish"])}（{clock(start + T["finish"])}）｜'
           f'{c["total_km"]:.2f} km・+{c["gain"]:,} m・EP {c["ep"]:.1f}｜{R["basis"]}')
    page = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">{fonts}<style>
*{{box-sizing:border-box;margin:0;padding:0}} html,body{{background:#fff}}
body{{font-family:'Noto Sans TC',sans-serif;color:#2b2f33;padding:40px 36px 32px;width:1080px}}
h1{{font-size:28px;font-weight:700;margin-bottom:6px}} .sub{{color:#6b7177;font-size:15px;margin-bottom:22px}}
{CSS}</style></head><body><h1>{esc(a.title or R["title"])}</h1><div class="sub">{esc(sub)}</div>
{html_table(S, R, kcal_h, water_h, groups)}<div class="stnote">{note(kcal_h, water_h)}</div></body></html>'''
    open(a.out, 'w', encoding='utf-8').write(page)
    print(a.out)
    if a.png:
        png = os.path.splitext(a.out)[0] + '.png'
        subprocess.run(['node', os.path.join(SKILL, 'scripts', 'render.js'), a.out, png, '1080'], check=True)
        subprocess.run([sys.executable, os.path.join(SKILL, 'scripts', 'png_dpi.py'), png], check=True)


if __name__ == '__main__':
    main()
