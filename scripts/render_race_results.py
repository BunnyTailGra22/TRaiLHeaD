import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, Rectangle
import sys

T = dict(text="#2E333B", text2="#57606C", muted="#7B848F", faint="#A3ACB9",
         grid="#C8D0D9", page="#FFFFFF", panel="#F4F6F8",
         data="#1170AA", focus_fill="#FC7D0B", focus_text="#C85200")
have = {f.name for f in fm.fontManager.ttflist}
TEXT = [f for f in ["Segoe UI", "Inter", "Noto Sans CJK TC"] if f in have] or ["DejaVu Sans"]
MONO = [f for f in ["Roboto Mono", "Noto Sans Mono CJK TC"] if f in have] or ["DejaVu Sans Mono"]
FS = dict(headline=22, subtitle=15, title=14.4, label=12, data=12, footer=12, source=9.6)
plt.rcParams.update({"font.family": TEXT, "text.color": T["text"], "figure.facecolor": T["page"]})

def hms(s):
    h, m, sec = map(int, s.split(":")); return h + m / 60 + sec / 3600

races = [  # name, date, cat, ctry, NL, km, dplus, itra, time, total, fin, dnf, m, f, grank, gtot, ag, orank
    ("TNF100 Taipei\nStage 50K", "2023-05-21", "50K", "TPE", True, 51, 2440, "3", "9:20:37", 327, 296, 31, 78, 22, 95, 254, 20, 113),
    ("TNF100\n21K", "2025-05-11", "Half marathon", "TPE", True, 21, 670, "0", "2:32:49", 192, 186, 6, 79, 21, 82, 152, 14, 90),
    ("Chiang Mai by UTMB\nHmong 50", "2025-12-06", "50K", "THA", False, 56, 2400, "n/a", "9:49:32", 2151, 2105, 46, 69, 31, 596, 1488, 69, 782),
    ("Trail Mt. Dadu\nTMD 4K", "2026-02-01", "10K (4 km)", "TPE", True, 4, 163, "0", "0:35:55", 119, 119, 0, 45, 55, 12, 54, 2, 17),
    ("Pinlin SuperTea\n21K", "2026-04-19", "Half marathon", "TPE", True, 24, 1110, "1", "3:13:59", 184, 181, 3, 65, 35, 29, 119, 5, 35),
    ("Formosa Trail\n40 km", "2026-11-21", "Marathon", "TPE", True, 39, 2380, "2", "6:55:07", 446, 422, 24, 66, 34, 52, 296, 1, 67),
]
FOCUS = 5

# Derived metrics
for r in races:
    pass
def ep(r): return r[5] + r[6] / 100
def eph(r): return ep(r) / hms(r[8])
def gtop(r): return 100 * r[14] / r[15]
def otop(r): return 100 * r[17] / r[9]
def dnfr(r): return 100 * r[11] / r[9]

# rows: (label, value fn, mono, best-fn or None, section)
rows = [
    ("Date", lambda r: r[1], True, None, 0),
    ("Category", lambda r: r[2], False, None, 0),
    ("Country", lambda r: r[3], False, None, 0),
    ("National League", lambda r: "Yes" if r[4] else "No", False, None, 0),
    ("Distance / D+", lambda r: f"{r[5]} km / {r[6]:,} m", True, None, 0),
    ("ITRA score", lambda r: r[7], True, None, 0),
    ("Finish time", lambda r: r[8], True, None, 0),
    ("Participants", lambda r: f"{r[9]:,}", True, None, 1),
    ("Finishers / DNF", lambda r: f"{r[10]:,} / {r[11]}", True, None, 1),
    ("DNF rate", lambda r: f"{dnfr(r):.1f}%", True, None, 1),
    ("Field M / F", lambda r: f"{r[12]}% / {r[13]}%", True, None, 1),
    ("Gender rank", lambda r: f"{r[14]} / {r[15]:,}", True, None, 2),
    ("Gender top %", lambda r: f"{gtop(r):.1f}%", True, ("min", gtop), 2),
    ("Age-group rank", lambda r: f"{r[16]}", True, ("min", lambda r: r[16]), 2),
    ("General rank", lambda r: f"{r[17]} / {r[9]:,}", True, None, 2),
    ("Overall top %", lambda r: f"{otop(r):.1f}%", True, ("min", otop), 2),
    ("Effort (EP)", lambda r: f"{ep(r):.1f}", True, None, 3),
    ("Speed (EP/h)", lambda r: f"{eph(r):.2f}", True, ("max", eph), 3),
]
SECTIONS = ["Race", "Field", "Placing", "Effort"]

W, H = 16, 9
fig = plt.figure(figsize=(W, H), dpi=240)
cv = fig.add_axes([0, 0, 1, 1]); cv.set_xlim(0, W); cv.set_ylim(0, H); cv.axis("off")

L, R = 0.55, W - 0.55
labw = 2.35
colw = (R - L - labw) / len(races)
cx = [L + labw + colw * (i + 0.5) for i in range(len(races))]

cv.text(L, H - 0.45, "Formosa Trail 40 km: first age-group win and best gender placing yet",
        fontsize=FS["headline"], weight="bold", va="top")
cv.text(L, H - 0.92, "Trail race results, 2023–2026 · 6 races, all finished",
        fontsize=FS["subtitle"], color=T["text2"], va="top")

top = H - 1.45
hdr_h = 0.66
rh = 0.315
body_top = top - hdr_h
body_bot = body_top - rh * len(rows)

# focus column outline
cv.add_patch(FancyBboxPatch((cx[FOCUS] - colw / 2 + 0.06, body_bot - 0.04),
                            colw - 0.12, top - body_bot + 0.08,
                            boxstyle="round,pad=0,rounding_size=0.08",
                            fc="none", ec=T["focus_fill"], lw=2, zorder=3))

# section panels (alternate)
for s in range(len(SECTIONS)):
    idx = [i for i, rw in enumerate(rows) if rw[4] == s]
    y0 = body_top - rh * (idx[-1] + 1); y1 = body_top - rh * idx[0]
    if s % 2 == 0:
        cv.add_patch(FancyBboxPatch((L, y0), R - L, y1 - y0,
                     boxstyle="round,pad=0,rounding_size=0.08", fc=T["panel"], ec="none", zorder=0))

# header
for i, r in enumerate(races):
    col = T["focus_text"] if i == FOCUS else T["text"]
    cv.text(cx[i], top - hdr_h / 2 + 0.02, r[0], ha="center", va="center",
            fontsize=FS["label"], weight="semibold", color=col, linespacing=1.25)
cv.plot([L, R], [body_top, body_top], color=T["grid"], lw=1, zorder=1)
cv.text(L + 0.15, top - hdr_h / 2 + 0.02, "Race", va="center", fontsize=FS["label"],
        weight="semibold", color=T["text2"])

# body
for j, (lab, fn, mono, best, sec) in enumerate(rows):
    yc = body_top - rh * (j + 0.5)
    cv.text(L + 0.15, yc, lab, va="center", fontsize=FS["label"], color=T["text2"])
    bi = None
    if best:
        vals = [best[1](r) for r in races]
        bi = vals.index(min(vals) if best[0] == "min" else max(vals))
    for i, r in enumerate(races):
        isb = (i == bi)
        cv.text(cx[i], yc, fn(r), ha="center", va="center", fontsize=FS["data"],
                family=MONO if mono else TEXT,
                weight="bold" if isb else ("medium" if mono else "normal"),
                color=T["data"] if isb else T["text"], zorder=4)

cv.text(L, 0.62, "Long-race speed rose to 9.08 EP/h, up from about 8.1 EP/h at both earlier 50Ks.",
        fontsize=FS["footer"], color=T["text2"])
cv.text(L, 0.3, "Source: race result screenshots. Top % = rank ÷ all starters (lower is better). "
        "EP = km + D+/100. Bold blue = best in row. Mt. Dadu is listed as 10K but measured 4 km.",
        fontsize=FS["source"], color=T["faint"])

out = sys.argv[1]
fig.savefig(out, dpi=240)
print(out)
