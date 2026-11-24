"""Shared helpers for the race-plan skill (GPX, geometry, profile, time)."""
import csv, json, math, os, xml.etree.ElementTree as ET

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TERRAINS = ["road_open", "road_end", "steep_climb", "reclimb", "technical_mixed",
            "descent_technical", "descent_forest_road"]
TERRAIN_ZH = {"road_open": "柏油・開場", "road_end": "柏油・終段", "steep_climb": "陡上 >15%",
              "reclimb": "回爬", "technical_mixed": "技術混合", "descent_technical": "技術下坡",
              "descent_forest_road": "林道下坡"}


def hav(a1, o1, a2, o2):
    R = 6371000.0
    p1, p2 = math.radians(a1), math.radians(a2)
    dp, dl = p2 - p1, math.radians(o2 - o1)
    return 2 * R * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def load_gpx(path):
    """Return track points [(lat, lon, ele)] from the first track (all segments)."""
    root = ET.parse(path).getroot()
    ns = root.tag.split('}')[0].strip('{') if root.tag.startswith('{') else ''
    q = (lambda t: f'{{{ns}}}{t}') if ns else (lambda t: t)
    pts = []
    for p in root.iter(q('trkpt')):
        e = p.find(q('ele'))
        pts.append((float(p.get('lat')), float(p.get('lon')), float(e.text) if e is not None else None))
    if not pts:
        raise SystemExit(f'no <trkpt> in {path}')
    if any(p[2] is None for p in pts):
        raise SystemExit('track has points without elevation; add elevation (e.g. from a mapping tool) first')
    return pts


def cumdist(pts):
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + hav(a[0], a[1], b[0], b[1]))
    return [x / 1000 for x in d]


def gain_loss(ele, th=3.0):
    """Hysteresis gain/loss in metres (threshold th) — matches how FT40 2026 was calibrated."""
    g = l = 0.0
    ref = ele[0]
    for x in ele:
        if x - ref >= th:
            g += x - ref; ref = x
        elif ref - x >= th:
            l += ref - x; ref = x
    return g, l


def hm_to_min(s):
    if s in (None, ''):
        return None
    h, m = s.strip().split(':')[:2]
    return int(h) * 60 + int(m)


def min_to_hm(m, sign=False):
    neg = m < 0
    m = abs(int(round(m)))
    s = f'{m // 60:d}:{m % 60:02d}'
    return ('-' if neg else ('+' if sign else '')) + s


def clock(m):
    m = int(round(m)) % (24 * 60)
    return f'{m // 60:02d}:{m % 60:02d}'


def load_profile(path=None):
    import yaml
    path = path or os.path.join(SKILL, 'profile.yaml')
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def read_checkpoints(path):
    """CSV columns: name,km,lat,lon,cutoff,stop_min,aid,surface,terrain,decision (km or lat/lon required)."""
    rows = []
    with open(path, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            r = {k.strip(): (v or '').strip() for k, v in r.items() if k}
            rows.append(dict(
                name=r.get('name', ''),
                km=float(r['km']) if r.get('km') else None,
                lat=float(r['lat']) if r.get('lat') else None,
                lon=float(r['lon']) if r.get('lon') else None,
                cutoff=r.get('cutoff') or None,
                stop_min=float(r['stop_min']) if r.get('stop_min') else None,
                aid=r.get('aid', '') in ('1', 'y', 'yes', 'true', 'Y'),
                surface=(r.get('surface') or 'trail').lower(),
                terrain=r.get('terrain') or None,
                decision=r.get('decision', '') in ('1', 'y', 'yes', 'true', 'Y'),
            ))
    if len(rows) < 2:
        raise SystemExit('checkpoint file needs at least a start and a finish row')
    return rows


def dump(obj, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
