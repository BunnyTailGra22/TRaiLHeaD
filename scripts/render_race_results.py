"""Render the trail race results infographic (trend charts + full results table).

Usage: python3 scripts/render_race_results.py race-results-2023-2026.png
To add a race, append a tuple to RACES (keep date order) and set FOCUS.
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch

T = dict(text="#2E333B", text2="#57606C", muted="#7B848F", faint="#A3ACB9",
         grid="#C8D0D9", page="#FFFFFF", panel="#F4F6F8",
         data="#1170AA", context="#57606C", short="#A3ACB9",
         focus_fill="#FC7D0B", focus_text="#C85200")
have = {f.name for f in fm.fontManager.ttflist}
TEXT = [f for f in ["Segoe UI", "Inter", "Noto Sans CJK TC"] if f in have] or ["DejaVu Sans"]
MONO = [f for f in ["Roboto Mono", "Noto Sans Mono CJK TC"] if f in have] or ["DejaVu Sans Mono"]
FS = dict(headline=22, subtitle=15, title=14.4, label=12, tick=12, data=12,
          footer=12, source=9.6)
plt.rcParams.update({
    "font.family": TEXT, "text.color": T["text"], "figure.facecolor": T["page"],
    "axes.facecolor": T["page"], "axes.edgecolor": T["grid"], "grid.color": T["grid"],
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "xtick.color": T["muted"], "ytick.color": T["muted"],
    "xtick.labelsize": FS["tick"], "ytick.labelsize": FS["tick"],
})

# name (table header), short name (chart tick), date, category, country, national league,
# km, D+, ITRA, time, total, finishers, DNF, %M, %F, gender rank, gender total, AG rank, overall rank
RACES = [
    ("TNF100 Taipei\nStage 50K", "TNF 50K", "2023-05-21", "50K", "TPE", True, 51, 2440, "3", "9:20:37", 327, 296, 31, 78, 22, 95, 254, 20, 113),
    ("TNF100\n21K", "TNF 21K", "2025-05-11", "Half marathon", "TPE", True, 21, 670, "0", "2:32:49", 192, 186, 6, 79, 21, 82, 152, 14, 90),
    ("Chiang Mai by UTMB\nHmong 50", "Chiang Mai 50", "2025-12-06", "50K", "THA", False, 56, 2400, "n/a", "9:49:32", 2151, 2105, 46, 69, 31, 596, 1488, 69, 782),
    ("Trail Mt. Dadu\nTMD 4K", "Dadu 4K", "2026-02-01", "10K (4 km)", "TPE", True, 4, 163, "0", "0:35:55", 119, 119, 0, 45, 55, 12, 54, 2, 17),
    ("Pinlin SuperTea\n21K", "Pinlin 21K", "2026-04-19", "Half marathon", "TPE", True, 24, 1110, "1", "3:13:59", 184, 181, 3, 65, 35, 29, 119, 5, 35),
    ("Formosa Trail\n40 km", "Formosa 40K", "2026-11-21", "Marathon", "TPE", True, 39, 2380, "2", "6:55:07", 446, 422, 24, 66, 34, 52, 296, 1, 67),
]
FOCUS = len(RACES) - 1
LONG_EP = 60  # races at or above this effort count as "long"

class R:
    def __init__(s, t):
        (s.name, s.short, s.date, s.cat, s.ctry, s.nl, s.km, s.dplus, s.itra, s.time,
         s.total, s.fin, s.dnf, s.pm, s.pf, s.grank, s.gtot, s.ag, s.orank) = t
        h, m, sec = map(int, s.time.split(":"))
        s.hours = h + m / 60 + sec / 3600
        s.ep = s.km + s.dplus / 100
        s.eph = s.ep / s.hours
        s.gtop = 100 * s.grank / s.gtot
        s.otop = 100 * s.orank / s.total
        s.dnfr = 100 * s.dnf / s.total
races = [R(t) for t in RACES]
n = len(races)

ROWS = [  # label, value fn, mono, best (direction, key) or None, section
    ("Date", lambda r: r.date, True, None, 0),
    ("Category", lambda r: r.cat, False, None, 0),
    ("Country", lambda r: r.ctry, False, None, 0),
    ("National League", lambda r: "Yes" if r.nl else "No", False, None, 0),
    ("Distance / D+", lambda r: f"{r.km} km / {r.dplus:,} m", True, None, 0),
    ("ITRA score", lambda r: r.itra, True, None, 0),
    ("Finish time", lambda r: r.time, True, None, 0),
    ("Participants", lambda r: f"{r.total:,}", True, None, 1),
    ("Finishers / DNF", lambda r: f"{r.fin:,} / {r.dnf}", True, None, 1),
    ("DNF rate", lambda r: f"{r.dnfr:.1f}%", True, None, 1),
    ("Field M / F", lambda r: f"{r.pm}% / {r.pf}%", True, None, 1),
    ("Gender rank", lambda r: f"{r.grank} / {r.gtot:,}", True, None, 2),
    ("Gender top %", lambda r: f"{r.gtop:.1f}%", True, ("min", lambda r: r.gtop), 2),
    ("Age-group rank", lambda r: f"{r.ag}", True, ("min", lambda r: r.ag), 2),
    ("General rank", lambda r: f"{r.orank} / {r.total:,}", True, None, 2),
    ("Overall top %", lambda r: f"{r.otop:.1f}%", True, ("min", lambda r: r.otop), 2),
    ("Effort (EP)", lambda r: f"{r.ep:.1f}", True, None, 3),
    ("Speed (EP/h)", lambda r: f"{r.eph:.2f}", True, ("max", lambda r: r.eph), 3),
]
N_SECTIONS = 4

W, H = 16, 14.1  # 3840 x 3384 px at 240 DPI
fig = plt.figure(figsize=(W, H), dpi=240)
cv = fig.add_axes([0, 0, 1, 1]); cv.set_xlim(0, W); cv.set_ylim(0, H); cv.axis("off")
L, Rm = 0.55, W - 0.55

def fax(x0, y0, x1, y1):  # axes placed in canvas inches
    return fig.add_axes([x0 / W, y0 / H, (x1 - x0) / W, (y1 - y0) / H])

# ---------- Header ----------
cv.text(L, H - 0.45, "Formosa Trail 40 km: best gender placing and fastest long race yet",
        fontsize=FS["headline"], weight="bold", va="top")
cv.text(L, H - 0.92, "Trail race results, 2023–2026 · 6 races, all finished",
        fontsize=FS["subtitle"], color=T["text2"], va="top")

# ---------- Chart panels ----------
ch_top, ch_bot = H - 1.45, H - 6.05
gap = 0.4
pw = (Rm - L - gap) / 2
for x0 in (L, L + pw + gap):
    cv.add_patch(FancyBboxPatch((x0, ch_bot), pw, ch_top - ch_bot,
                 boxstyle="round,pad=0,rounding_size=0.08", fc=T["panel"], ec="none", zorder=0))
xs = list(range(n))

def style(ax, ticklabels):
    ax.set_facecolor(T["panel"])
    ax.grid(axis="y", lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)
    ax.set_xticks(xs); ax.set_xticklabels(ticklabels, linespacing=1.35)
    for t in ax.get_xticklabels():
        t.set_color(T["muted"])
    ax.get_xticklabels()[FOCUS].set_color(T["focus_text"])
    for t in ax.get_yticklabels():
        t.set_fontfamily(MONO)
    ax.set_xlim(-0.45, n - 0.55)

# Left: placing trend
x0 = L
cv.text(x0 + 0.3, ch_top - 0.3, "Placing has climbed into the top 20%", fontsize=FS["title"],
        weight="semibold", va="top")
cv.text(x0 + 0.3, ch_top - 0.68, "Top % of field per race, lower is better (axis flipped so up = better)",
        fontsize=FS["label"], color=T["text2"], va="top")
ax1 = fax(x0 + 0.95, ch_bot + 0.85, x0 + pw - 0.35, ch_top - 1.2)
g = [r.gtop for r in races]; o = [r.otop for r in races]
ax1.plot(xs, o, color=T["context"], lw=2, marker="s", ms=6, zorder=3)
ax1.plot(xs, g, color=T["data"], lw=2.5, marker="o", ms=7, zorder=4)
ax1.plot([FOCUS], [g[FOCUS]], marker="o", ms=13, mfc="none", mec=T["focus_fill"], mew=2, zorder=5)
ax1.plot([FOCUS], [o[FOCUS]], marker="s", ms=12, mfc="none", mec=T["focus_fill"], mew=2, zorder=5)
ax1.set_ylim(66, 0)
ax1.set_yticks([0, 20, 40, 60]); ax1.set_yticklabels(["0%", "20%", "40%", "60%"])
for i in xs:
    gc = T["focus_text"] if i == FOCUS else T["data"]
    oc = T["focus_text"] if i == FOCUS else T["context"]
    # gender (larger %) sits lower → label below; overall sits higher → label above
    ax1.annotate(f"{g[i]:.1f}", (i, g[i]), xytext=(0, -10), textcoords="offset points",
                 ha="center", va="top", fontsize=FS["data"], family=MONO, weight="medium", color=gc)
    ax1.annotate(f"{o[i]:.1f}", (i, o[i]), xytext=(0, 10), textcoords="offset points",
                 ha="center", va="bottom", fontsize=FS["data"], family=MONO, weight="medium", color=oc)
style(ax1, [f"{r.short}\n{r.date[:7]}" for r in races])
# series key (direct labels collide at the line ends, so a compact key in the empty top-left)
ax1.text(0.0, 0.86, "●  Gender top %", transform=ax1.transAxes, color=T["data"],
         fontsize=FS["label"], weight="semibold", va="center")
ax1.text(0.0, 0.96, "■  Overall top %", transform=ax1.transAxes, color=T["context"],
         fontsize=FS["label"], weight="semibold", va="center")

# Right: speed
x0 = L + pw + gap
long_vals = [r.eph for r in races if r.ep >= LONG_EP]
cv.text(x0 + 0.3, ch_top - 0.3, f"Long-race speed up to {races[FOCUS].eph:.2f} EP/h",
        fontsize=FS["title"], weight="semibold", va="top")
cv.text(x0 + 0.3, ch_top - 0.68, "Speed in EP/h, higher is better · short races run faster, so compare like with like",
        fontsize=FS["label"], color=T["text2"], va="top")
ax2 = fax(x0 + 0.95, ch_bot + 0.85, x0 + pw - 0.35, ch_top - 1.2)
cols = [T["focus_fill"] if i == FOCUS else (T["data"] if r.ep >= LONG_EP else T["short"])
        for i, r in enumerate(races)]
ax2.bar(xs, [r.eph for r in races], color=cols, width=0.6, zorder=3)
ax2.set_ylim(0, 12.5); ax2.set_yticks([0, 3, 6, 9, 12])
for i, r in enumerate(races):
    c = T["focus_text"] if i == FOCUS else (T["data"] if r.ep >= LONG_EP else T["text2"])
    ax2.text(i, r.eph + 0.25, f"{r.eph:.2f}", ha="center", va="bottom", fontsize=FS["data"],
             family=MONO, weight="medium", color=c)
style(ax2, [f"{r.short}\nEP {r.ep:.0f}" for r in races])
ax2.text(0.0, 1.02, f"■ Long races (EP ≥ {LONG_EP})", transform=ax2.transAxes, color=T["data"],
         fontsize=FS["label"], weight="semibold", va="bottom")
ax2.text(0.36, 1.02, "■", transform=ax2.transAxes, color=T["short"],
         fontsize=FS["label"], weight="semibold", va="bottom")
ax2.text(0.395, 1.02, "Short races", transform=ax2.transAxes, color=T["text2"],
         fontsize=FS["label"], weight="semibold", va="bottom")

# ---------- Table ----------
labw = 2.35
colw = (Rm - L - labw) / n
cx = [L + labw + colw * (i + 0.5) for i in range(n)]
top = ch_bot - 0.45
hdr_h, rh = 0.66, 0.315
body_top = top - hdr_h
body_bot = body_top - rh * len(ROWS)

cv.add_patch(FancyBboxPatch((cx[FOCUS] - colw / 2 + 0.06, body_bot - 0.04),
                            colw - 0.12, top - body_bot + 0.08,
                            boxstyle="round,pad=0,rounding_size=0.08",
                            fc="none", ec=T["focus_fill"], lw=2, zorder=3))
for s in range(0, N_SECTIONS, 2):
    idx = [i for i, rw in enumerate(ROWS) if rw[4] == s]
    y0 = body_top - rh * (idx[-1] + 1); y1 = body_top - rh * idx[0]
    cv.add_patch(FancyBboxPatch((L, y0), Rm - L, y1 - y0,
                 boxstyle="round,pad=0,rounding_size=0.08", fc=T["panel"], ec="none", zorder=0))
for i, r in enumerate(races):
    cv.text(cx[i], top - hdr_h / 2 + 0.02, r.name, ha="center", va="center",
            fontsize=FS["label"], weight="semibold", linespacing=1.25,
            color=T["focus_text"] if i == FOCUS else T["text"])
cv.text(L + 0.15, top - hdr_h / 2 + 0.02, "Race", va="center", fontsize=FS["label"],
        weight="semibold", color=T["text2"])
cv.plot([L, Rm], [body_top, body_top], color=T["grid"], lw=1, zorder=1)
for j, (lab, fn, mono, best, sec) in enumerate(ROWS):
    yc = body_top - rh * (j + 0.5)
    cv.text(L + 0.15, yc, lab, va="center", fontsize=FS["label"], color=T["text2"])
    bi = None
    if best:
        vals = [best[1](r) for r in races]
        bi = vals.index(min(vals) if best[0] == "min" else max(vals))
    for i, r in enumerate(races):
        isb = i == bi
        cv.text(cx[i], yc, fn(r), ha="center", va="center", fontsize=FS["data"],
                family=MONO if mono else TEXT,
                weight="bold" if isb else ("medium" if mono else "normal"),
                color=T["data"] if isb else T["text"], zorder=4)

# ---------- Footer ----------
cv.text(L, 0.62, "Long-race speed: " + " → ".join(f"{v:.2f}" for v in long_vals)
        + " EP/h. Gender placing improved from 37.4% to 17.6% between the 50K in 2023 and Formosa.",
        fontsize=FS["footer"], color=T["text2"])
cv.text(L, 0.3, "Source: race result screenshots. Top % = rank ÷ all starters (lower is better). "
        "EP = km + D+/100. Bold blue in table = best in row. Mt. Dadu is listed as 10K but measured 4 km.",
        fontsize=FS["source"], color=T["faint"])

fig.savefig(sys.argv[1], dpi=240)
print(sys.argv[1])
