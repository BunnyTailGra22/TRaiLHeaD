"""Scatter of race effort (EP) vs speed (EP/h).

Usage: python3 scripts/render_ep_vs_eph.py ep-vs-eph.png
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

T = dict(text="#2E333B", text2="#57606C", muted="#7B848F", faint="#A3ACB9",
         grid="#C8D0D9", page="#FFFFFF", data="#1170AA", short="#A3ACB9",
         focus_fill="#FC7D0B", focus_text="#C85200")
have = {f.name for f in fm.fontManager.ttflist}
TEXT = [f for f in ["Segoe UI", "Inter", "Noto Sans CJK TC"] if f in have] or ["DejaVu Sans"]
MONO = [f for f in ["Roboto Mono", "Noto Sans Mono CJK TC"] if f in have] or ["DejaVu Sans Mono"]
FS = dict(headline=22, subtitle=15, label=12, tick=12, data=12, footer=12, source=9.6)
plt.rcParams.update({
    "font.family": TEXT, "text.color": T["text"], "figure.facecolor": T["page"],
    "axes.facecolor": T["page"], "axes.edgecolor": T["grid"], "grid.color": T["grid"],
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "xtick.color": T["muted"], "ytick.color": T["muted"], "axes.labelcolor": T["text2"],
    "xtick.labelsize": FS["tick"], "ytick.labelsize": FS["tick"],
})

LONG_EP = 60
# label, km, D+, time, label offset (points), alignment
RACES = [
    ("QILAN50 '21", 49, 2270, "7:06:07", (10, 8), "left"),
    ("Formosa 40K '22", 39, 2360, "11:31:47", (-12, 0), "right"),
    ("TNF 50K '23", 51, 2440, "9:20:37", (0, -18), "center"),
    ("TNF 21K '25", 21, 670, "2:32:49", (-10, -16), "right"),
    ("Chiang Mai '25", 56, 2400, "9:49:32", (0, 18), "center"),
    ("Dadu 4K '26", 4, 163, "0:35:55", (10, -14), "left"),
    ("Pinlin 21K '26", 24, 1110, "3:13:59", (8, 10), "left"),
    ("Formosa 40K '26", 39, 2380, "6:55:07", (-12, 0), "right"),
]
FOCUS = len(RACES) - 1
PREV = 1  # same course, earlier run

def hours(t):
    h, m, s = map(int, t.split(":")); return h + m / 60 + s / 3600
pts = [(lab, km + d / 100, (km + d / 100) / hours(t), off, ha) for lab, km, d, t, off, ha in RACES]

W, H = 9, 9
fig = plt.figure(figsize=(W, H), dpi=240)
cv = fig.add_axes([0, 0, 1, 1]); cv.set_xlim(0, W); cv.set_ylim(0, H); cv.axis("off")
ax = fig.add_axes([1.15 / W, 1.55 / H, (W - 1.6) / W, (H - 3.55) / H])

ax.set_xlim(0, 90); ax.set_ylim(4.5, 12)
ax.set_xticks(range(0, 91, 15)); ax.set_yticks(range(6, 13, 2))
ax.grid(axis="y", lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)
for t in ax.get_xticklabels() + ax.get_yticklabels():
    t.set_fontfamily(MONO)
ax.set_xlabel("Effort (EP = km + D+/100) — how big the race is", fontsize=FS["label"], labelpad=10)
ax.set_ylabel("Speed (EP/h) — how fast you covered it", fontsize=FS["label"], labelpad=10)

# long-race zone
ax.axvspan(LONG_EP, 90, color="#F4F6F8", zorder=0)
ax.text(LONG_EP + 1, 11.75, f"Long races (EP ≥ {LONG_EP})", fontsize=FS["label"],
        color=T["text2"], va="top")

# same-course arrow
_, x0, y0, _, _ = pts[PREV]; _, x1, y1, _, _ = pts[FOCUS]
ax.annotate("", xy=(x1, y1 - 0.18), xytext=(x0, y0 + 0.18),
            arrowprops=dict(arrowstyle="-|>", color=T["text2"], lw=1.6, mutation_scale=14))
ax.text(x0 - 1.5, (y0 + y1) / 2, f"Same course\n+{y1 - y0:.2f} EP/h\n(−4 h 37 min)",
        fontsize=FS["label"], color=T["text"], va="center", ha="right", linespacing=1.35)

for i, (lab, ep, eph, off, ha) in enumerate(pts):
    if i == FOCUS:
        fc, ec, tc = T["focus_fill"], T["focus_fill"], T["focus_text"]
    elif ep >= LONG_EP:
        fc, ec, tc = T["data"], T["data"], T["data"]
    else:
        fc, ec, tc = T["short"], T["text2"], T["text2"]
    ax.scatter([ep], [eph], s=110, color=fc, edgecolor=ec, linewidth=1.2, zorder=4)
    ax.annotate(f"{lab}  {eph:.2f}", (ep, eph), xytext=off, textcoords="offset points",
                ha=ha, va="center", fontsize=FS["data"], color=tc,
                weight="semibold" if i == FOCUS else "medium")

cv.text(0.55, H - 0.5, "Same course, 4 years apart:\n+3.65 EP/h at Formosa 40 km", fontsize=FS["headline"],
        weight="bold", va="top", linespacing=1.2)
cv.text(0.55, H - 1.55, "Race effort vs speed, 8 races, 2021–2026", fontsize=FS["subtitle"],
        color=T["text2"], va="top")
cv.text(0.55, 0.62, "Bigger races usually run slower. QILAN50 '21 is still your fastest long race (10.10).",
        fontsize=FS["footer"], color=T["text2"])
cv.text(0.55, 0.3, "Source: race result screenshots. Blue = long race, grey = short race, orange = latest race.",
        fontsize=FS["source"], color=T["faint"])

fig.savefig(sys.argv[1], dpi=240)
print(sys.argv[1])
