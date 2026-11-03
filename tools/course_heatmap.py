#!/usr/bin/env python3
"""Render the Course Heatmap figure shown on the dashboard's Training tab.

    python3 tools/course_heatmap.py light   -> assets/EP_vs_Slope.png
    python3 tools/course_heatmap.py dark    -> assets/EP_vs_Slope-dark.png

Source data is the Notion route-plan table (planned routes), not the Google Sheet
activity log, which is why the figure is a committed asset rather than drawn live.
The palettes mirror :root and html[data-theme="dark"] in index.html — change one,
change the other.

Label placement is solved, not hand-tuned: each label block is measured, then
offsets are searched until it clears every marker, every other label, the legend,
the quadrant tags and the guide labels. The script asserts the result.
"""
import sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D

plt.rcParams["font.family"] = ["PingFang HK", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# name, EP, dist_km, ascent_m, slope_pct.  EP and slope are both derivable from
# distance and ascent; check_consistency() below re-derives them as a guard.
R = [
 ("臨溪路100巷",  1.974, 0.834,  114, 13.7),
 ("軍艦岩繞圈",   4.99,  3.44,   155,  4.5),
 ("中社路",       6.5,   4.0,    250,  6.3),
 ("風櫃嘴",       9.0,   5.0,    400,  8.0),
 ("五指山古道",   9.65,  6.4,    325,  5.1),
 ("劍南路",      11.5,   9.0,    250,  2.8),
 ("劍中劍",      22.5,  18.0,    450,  2.5),
 ("三進七星山",  23.0,  11.0,   1200, 10.9),
 ("劍風劍",      34.0,  26.0,    800,  3.1),
 ("劍中風",      40.0,  30.0,   1000,  3.3),
 ("陽明山十連峰",41.26, 23.0,   1826,  7.9),
]

def check_consistency():
    bad = 0
    for n, ep, d, a, sl in R:
        if abs(ep - (d + a/100)) > 0.005 or abs(sl - a/(d*1000)*100) > 0.05:
            print(f"  !! {n}: EP/slope do not match distance+ascent"); bad += 1
    print(f"data check: {len(R)} routes, {bad} inconsistent")
    assert bad == 0

THEME = (sys.argv[1] if len(sys.argv) > 1 else "light").lower()
if THEME == "dark":
    BG, CARD, BORDER = "#1c1a18", "#26231f", "#3d3832"
    TEXT, MUTED = "#ece6dd", "#a79d91"
    RAMP = ["#8fb8c7", "#9bbb93", "#d7b465", "#cd7e3c", "#b04e46"]
    OUT = "assets/EP_vs_Slope-dark.png"
else:
    BG, CARD, BORDER = "#e9e4dc", "#f9f6f1", "#dcd4c8"
    TEXT, MUTED = "#453f37", "#6f675c"
    RAMP = ["#6f97a6", "#7f9d78", "#bd9a4f", "#a5602a", "#8f3f38"]
    OUT = "assets/EP_vs_Slope.png"
HEAT = LinearSegmentedColormap.from_list("morandi_heat", RAMP)

check_consistency()

x   = np.array([r[1] for r in R])          # EP      -> x
y   = np.array([r[4] for r in R])          # slope % -> y
asc = np.array([r[3] for r in R]); dst = np.array([r[2] for r in R])
XMAX, YMAX = 47.0, 15.6

fig = plt.figure(figsize=(8, 8), dpi=200); fig.patch.set_facecolor(BG)
ax  = fig.add_axes([0.105, 0.085, 0.735, 0.775]); ax.set_facecolor(CARD)
cax = fig.add_axes([0.875, 0.085, 0.022, 0.775])

# Iso-distance guides. EP = d*(1 + slope/10) rearranges to slope = 10*(EP/d - 1),
# so each distance is a straight line meeting slope 0 at EP = d.
static_txt = []
for d in (5, 10, 20, 30):
    x_end = min(XMAX, d * (1 + YMAX/10))
    y_end = 10*(x_end/d - 1)
    ax.plot([d, x_end], [0, y_end], color=MUTED, lw=0.7, ls=(0,(5,4)), alpha=0.33, zorder=1)
    if x_end >= XMAX - 0.01:
        static_txt.append(ax.text(XMAX-0.25, y_end+0.12, f"{d} km", fontsize=8,
            color=MUTED, alpha=0.9, ha="right", va="bottom", zorder=1))
    else:
        y_lab = YMAX - 1.6                 # below the quadrant tag, not beside it
        static_txt.append(ax.text(d*(1 + y_lab/10) + 0.3, y_lab, f"{d} km", fontsize=8,
            color=MUTED, alpha=0.9, ha="left", va="top", zorder=1))

mx, my = np.median(x), np.median(y)
ax.axvline(mx, color=BORDER, lw=1.1, zorder=0); ax.axhline(my, color=BORDER, lw=1.1, zorder=0)
static_txt.append(ax.text(mx+0.35, 0.3, f"median EP {mx:g}", fontsize=7.5, color=MUTED,
        ha="left", va="bottom", alpha=.9, zorder=2))
static_txt.append(ax.text(XMAX-0.4, my+0.18, f"median {my:g}%", fontsize=7.5, color=MUTED,
        ha="right", va="bottom", alpha=.9, zorder=2))

QUAD = [(0.5, YMAX-0.3, "Short & steep · climbing", "left",  "top"),
        (XMAX-0.5, YMAX-0.3, "Long & steep · hardest", "right", "top"),
        (0.5, 0.25, "Easy · recovery",              "left",  "bottom"),
        (XMAX-0.5, 0.25, "Long & gradual · volume", "right", "bottom")]
quad_arts = [ax.text(tx, ty, s, fontsize=10, color=MUTED, ha=ha, va=va, alpha=0.95,
    zorder=2, fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.3", fc=CARD, ec=BORDER, lw=0.6, alpha=0.88))
    for tx, ty, s, ha, va in QUAD]

norm = Normalize(vmin=asc.min(), vmax=asc.max())
sizes = 70 + (dst/dst.max())**0.75 * 880
sc = ax.scatter(x, y, s=sizes, c=asc, cmap=HEAT, norm=norm,
                edgecolors=TEXT, linewidths=0.9, alpha=0.93, zorder=4)

r = np.corrcoef(x, y)[0, 1]
ax.set_xlim(0, XMAX); ax.set_ylim(0, YMAX)
ax.set_xlabel("EP   (= distance km + ascent m ÷ 100)", fontsize=12, color=TEXT, labelpad=14)
ax.set_ylabel("Slope %   (total ascent ÷ horizontal distance)", fontsize=12, color=TEXT, labelpad=12)
ax.tick_params(colors=MUTED, labelsize=10)
for sp in ax.spines.values(): sp.set_color(BORDER)
ax.grid(True, color=BORDER, lw=0.6, alpha=0.5); ax.set_axisbelow(True)
ax.yaxis.set_major_formatter(lambda v, p: f"{v:g}%")

hdr0 = fig.text(0.105, 0.945, "Course Heatmap", fontsize=19, color=TEXT, fontweight="bold")
hdr1 = fig.text(0.105, 0.915, "Slope % vs. EP  ·  colour = total ascent (m+)  ·  bubble size = distance (km)"
                              "  ·  dashed = equal-distance guides", fontsize=9.5, color=MUTED)
hdr2 = fig.text(0.105, 0.891,
       f"r = {r:+.2f} (n = {len(R)}, weak negative, not significant)  →  volume and steepness are "
       f"independent dimensions", fontsize=9.5, color=MUTED)

cb = fig.colorbar(sc, cax=cax); cb.set_label("Total Ascent (m+)", fontsize=9.5, color=TEXT, labelpad=8)
cb.ax.tick_params(colors=MUTED, labelsize=8.5); cb.outline.set_edgecolor(BORDER)

handles = [Line2D([],[], marker="o", ls="", markerfacecolor=CARD, markeredgecolor=TEXT,
                  markersize=np.sqrt(70+(d/dst.max())**0.75*880)/2.6, label=f"{d:g} km")
           for d in (1, 10, 30)]
leg = ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.995, 0.845),
                frameon=True, fontsize=9, labelcolor=TEXT, title="Distance",
                title_fontsize=9, borderpad=0.7, labelspacing=1.05, handletextpad=1.2)
leg.get_frame().set_facecolor(CARD); leg.get_frame().set_edgecolor(BORDER)
leg.get_title().set_color(MUTED)

# ── collision-free label placement ──────────────────────────────────────────
fig.canvas.draw(); rend = fig.canvas.get_renderer()
DPP = fig.dpi / 72.0
marker_px = [(ax.transData.transform((xi, yi)), np.sqrt(s/np.pi)*DPP)
             for xi, yi, s in zip(x, y, sizes)]

def block_size(name, detail):
    t1 = ax.text(0, 0, name, fontsize=10.5, transform=None)
    t2 = ax.text(0, 0, detail, fontsize=7.5, transform=None)
    b1 = t1.get_window_extent(rend); b2 = t2.get_window_extent(rend)
    t1.remove(); t2.remove()
    return max(b1.width, b2.width), b1.height + 3*DPP + b2.height

def rects_overlap(a, b, pad=0):
    return not (a[2]+pad < b[0] or b[2]+pad < a[0] or a[3]+pad < b[1] or b[3]+pad < a[1])

def rect_circle_hit(rect, c, rad, pad=2.0):
    cx, cy = c
    nx, ny = min(max(cx, rect[0]), rect[2]), min(max(cy, rect[1]), rect[3])
    return (cx-nx)**2 + (cy-ny)**2 < (rad+pad)**2

ax_bb = ax.get_window_extent(rend)
blocked = ([leg.get_window_extent(rend)]
           + [q.get_window_extent(rend) for q in quad_arts]
           + [t.get_window_extent(rend) for t in static_txt])
blocked = [(b.x0, b.y0, b.x1, b.y1) for b in blocked]
placed, chosen = [], []
ANG = [0, -20, 20, -40, 40, -60, 60, 180, 160, -160, 140, -140,
       90, -90, 110, -110, -75, 75, 15, -15]

for i in sorted(range(len(R)), key=lambda i: -x[i]):
    name, ep, d, a, sl = R[i]
    detail = f"EP {ep:g} · {d:g} km · {a:,} m+"
    bw, bh = block_size(name, detail)
    (cx, cy), rad = marker_px[i]
    best = None
    for gap in (10, 14, 19, 25, 32, 40, 50, 62, 76, 92):
        for ang in ANG:
            th = np.radians(ang)
            dist = rad + gap + (bw/2 if abs(np.cos(th)) > 0.5 else bh/2)
            bx, by = cx + dist*np.cos(th), cy + dist*np.sin(th)
            rect = (bx-bw/2, by-bh/2, bx+bw/2, by+bh/2)
            if not (rect[0] >= ax_bb.x0+3 and rect[2] <= ax_bb.x1-3
                    and rect[1] >= ax_bb.y0+3 and rect[3] <= ax_bb.y1-3): continue
            if any(rect_circle_hit(rect, c, rr) for c, rr in marker_px): continue
            if any(rects_overlap(rect, o, 7) for o in placed + blocked): continue
            best = (rect, bx, by); break
        if best: break
    assert best is not None, f"no clear label slot for {name}"
    rect, bx, by = best
    placed.append(rect); chosen.append((i, bx, by, bw, bh, name, detail))

for i, bx, by, bw, bh, name, detail in chosen:
    (cx, cy), rad = marker_px[i]
    ex = min(max(cx, bx-bw/2), bx+bw/2); ey = min(max(cy, by-bh/2), by+bh/2)
    vx, vy = ex-cx, ey-cy; L = np.hypot(vx, vy)
    if L > rad + 13:                       # far enough to be ambiguous -> leader line
        ax.plot([cx + vx/L*(rad+2), ex - vx/L*3], [cy + vy/L*(rad+2), ey - vy/L*3],
                transform=None, color=MUTED, lw=0.8, alpha=0.55, zorder=5,
                solid_capstyle="round")
    ax.text(bx, by + bh*0.26, name,   fontsize=10.5, color=TEXT,  ha="center", va="center", transform=None, zorder=6)
    ax.text(bx, by - bh*0.30, detail, fontsize=7.5,  color=MUTED, ha="center", va="center", transform=None, zorder=6)

bad = sum(1 for rect in placed for c, rr in marker_px if rect_circle_hit(rect, c, rr))
pairs = sum(1 for i in range(len(placed)) for j in range(i+1, len(placed))
            if rects_overlap(placed[i], placed[j]))
assert bad == 0 and pairs == 0, f"collisions: {bad} marker, {pairs} label"
print(f"label check: {bad} marker collisions, {pairs} label overlaps")

W = fig.get_size_inches()[0]*fig.dpi
for t in (hdr0, hdr1, hdr2):
    assert t.get_window_extent(rend).x1 <= W-6, f"header overflows: {t.get_text()[:40]}"
print("header check: all lines fit the canvas")

fig.savefig(OUT, facecolor=BG, dpi=200)
from PIL import Image
im = Image.open(OUT)
print(f"saved {OUT} {im.size} square={im.size[0]==im.size[1]} | r={r:+.3f} | theme={THEME}")
