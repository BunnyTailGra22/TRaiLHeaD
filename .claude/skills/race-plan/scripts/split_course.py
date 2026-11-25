#!/usr/bin/env python3
"""Split a course GPX at checkpoints and classify each section's terrain.

    python3 split_course.py --gpx course.gpx --cp checkpoints.csv --out sections.json [--name 'FT40'] [--th 3]

Checkpoint CSV (UTF-8, one row per point, start and finish included):
    name,km,lat,lon,cutoff,stop_min,aid,surface,terrain,decision
  km or lat/lon     position on the course (lat/lon is snapped to the track, in order)
  cutoff            leave-by clock time HH:MM (blank if none)
  stop_min          planned stop at this point (blank -> profile default if aid=1, else 0)
  aid               1 if aid station
  surface, terrain  describe the section that ENDS at this row
                    surface: trail (default) | road | forest_road
                    terrain: optional override, one of the 7 classes in references/terrain-rules.md
  decision          1 marks the decision point (fallback fade starts after it)
"""
import argparse, bisect, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_gpx, cumdist, gain_loss, hav, read_checkpoints, dump, TERRAINS, TERRAIN_ZH


def classify(km0, dist, g, l, surface, total, override=None):
    if override:
        if override not in TERRAINS:
            raise SystemExit(f'unknown terrain "{override}"; use one of {TERRAINS}')
        return override, 'csv'
    dm = max(dist * 1000, 1)
    up, dn = g / dm * 100, l / dm * 100
    if surface == 'road':
        return ('road_open' if km0 < total / 2 else 'road_end'), 'rule:surface'
    if surface in ('forest_road', 'forest-road', '林道'):
        return ('descent_forest_road' if l > g else 'reclimb'), 'rule:surface'
    big, small = max(g, l), min(g, l)
    if small >= 0.5 * big and big / dm * 100 >= 4:
        return 'technical_mixed', 'rule:grade'
    if g > l:
        if up >= 15: return 'steep_climb', 'rule:grade'
        if up >= 4: return 'reclimb', 'rule:grade'
        return 'technical_mixed', 'rule:grade'
    if dn >= 4: return 'descent_technical', 'rule:grade'
    return 'technical_mixed', 'rule:grade'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gpx', required=True); ap.add_argument('--cp', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--name', default='')
    ap.add_argument('--th', type=float, default=3.0, help='gain/loss hysteresis threshold, m')
    a = ap.parse_args()

    pts = load_gpx(a.gpx); D = cumdist(pts); E = [p[2] for p in pts]; total = D[-1]
    cps = read_checkpoints(a.cp)

    # place every checkpoint on the track (index into pts)
    i0 = 0
    for c in cps:
        if c['km'] is not None:
            c['km'] = min(max(c['km'], 0), total)
            c['i'] = min(bisect.bisect_left(D, c['km']), len(D) - 1)
        elif c['lat'] is not None:
            best = None
            for i in range(i0, len(pts)):
                dd = hav(c['lat'], c['lon'], pts[i][0], pts[i][1])
                if dd < 200 and (best is None or dd < best[0]): best = (dd, i)
                elif best and dd > 500: break
            if not best:
                raise SystemExit(f'checkpoint "{c["name"]}" is not within 200 m of the track after the previous one')
            c['i'] = best[1]; c['km'] = D[best[1]]
        else:
            raise SystemExit(f'checkpoint "{c["name"]}" needs km or lat/lon')
        i0 = c['i']
    for x, y in zip(cps, cps[1:]):
        if y['km'] <= x['km']:
            raise SystemExit(f'checkpoints out of order: "{x["name"]}" {x["km"]:.2f} km -> "{y["name"]}" {y["km"]:.2f} km')

    secs = []
    for x, y in zip(cps, cps[1:]):
        g, l = gain_loss(E[x['i']:y['i'] + 1], a.th)
        dist = y['km'] - x['km']
        t, src = classify(x['km'], dist, g, l, y['surface'], total, y['terrain'])
        secs.append(dict(frm=x['name'], to=y['name'], km0=round(x['km'], 3), km1=round(y['km'], 3),
                         dist=round(dist, 3), gain=round(g), loss=round(l), ep=round(dist + g / 100, 2),
                         up_pct=round(g / (dist * 10), 1), down_pct=round(l / (dist * 10), 1),
                         surface=y['surface'], terrain=t, terrain_source=src))
    G, L = gain_loss(E, a.th)
    prof, nxt = [], 0.0
    for d, e in zip(D, E):
        if d >= nxt: prof.append([round(d, 2), round(e)]); nxt += 0.1
    out = dict(course=dict(name=a.name or os.path.splitext(os.path.basename(a.gpx))[0], total_km=round(total, 2),
                           gain=round(G), loss=round(L), ep=round(total + G / 100, 1)),
               checkpoints=[dict(name=c['name'], km=round(c['km'], 2), lat=pts[c['i']][0], lon=pts[c['i']][1],
                                 ele=round(E[c['i']]), cutoff=c['cutoff'], stop_min=c['stop_min'], aid=c['aid'],
                                 decision=c['decision']) for c in cps],
               sections=secs, profile=prof)
    dump(out, a.out)
    print(f"{out['course']['name']}: {total:.2f} km  +{G:.0f}/-{L:.0f} m  EP {total + G / 100:.1f}")
    print(f"{'section':34s} {'km':>5s} {'+m':>5s} {'-m':>5s} {'EP':>5s} {'up%':>5s} {'dn%':>5s}  terrain")
    for s in secs:
        print(f"{s['frm'][:15]:>15s} → {s['to'][:15]:15s} {s['dist']:5.2f} {s['gain']:5d} {s['loss']:5d} {s['ep']:5.2f} "
              f"{s['up_pct']:5.1f} {s['down_pct']:5.1f}  {s['terrain']} ({TERRAIN_ZH[s['terrain']]}, {s['terrain_source']})")


if __name__ == '__main__':
    main()
