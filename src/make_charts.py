"""Create the report charts (PNG) from the SQL query outputs in outputs/."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
O = ROOT / "outputs"
IMG = ROOT / "images"
IMG.mkdir(exist_ok=True)

BLUE, ORANGE, AQUA, GRAY, INK = "#2a78d6", "#eb6834", "#1baf7a", "#9aa5b1", "#0b2545"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#c8d2dd", "axes.labelcolor": INK, "xtick.color": "#52606d", "ytick.color": "#52606d",
    "text.parse_math": False, "axes.grid": True, "grid.color": "#e8ecf0", "axes.axisbelow": True, "figure.dpi": 150,
})

def save(fig, name):
    fig.tight_layout()
    fig.savefig(IMG / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)

# 1. Yearly volume
y = pd.read_csv(O / "yearly_volume.csv")
fig, ax = plt.subplots(figsize=(8, 4.2))
colors = [BLUE if not p else "#a9c9f0" for p in y.partial_year]
bars = ax.bar(y.fiscal_year.astype(str).where(~y.partial_year.astype(bool), "2026*"), y.total_billions, color=colors, width=0.62)
ax.bar_label(bars, labels=[f"${v:.1f}B" for v in y.total_billions], padding=3, fontsize=10, color=INK)
ax.set_ylabel("Total approved ($ billions)")
ax.set_title("SBA 7(a) lending by fiscal year (funded loans)", loc="left", fontsize=13, color=INK, fontweight="bold")
ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:.0f}B"))
ax.text(0, -0.17, "*FY2026 is partial: data runs through June 30, 2026.", transform=ax.transAxes, fontsize=9, color="#52606d")
save(fig, "01_yearly_volume.png")

# 2. Sector mix (top 10)
s = pd.read_csv(O / "sector_mix.csv").head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 4.8))
bars = ax.barh(s.Sector, s.total_billions, color=BLUE, height=0.62)
ax.bar_label(bars, labels=[f"${v:.1f}B ({p:.0f}%)" for v, p in zip(s.total_billions, s.pct_of_dollars)], padding=4, fontsize=9.5, color=INK)
ax.set_xlabel("Total approved ($ billions)")
ax.set_title("Top 10 industries by SBA 7(a) dollars, FY2020 to June 2026", loc="left", fontsize=13, color=INK, fontweight="bold")
ax.set_xlim(0, s.total_billions.max() * 1.28)
ax.grid(axis="y", visible=False)
save(fig, "02_sector_mix.png")

# 3. Rate trend
r = pd.read_csv(O / "rate_trend.csv")
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(r.quarter, r.avg_rate, color=ORANGE, lw=2.4, marker="o", ms=3.5)
ax.set_ylabel("Average initial interest rate (%)")
ax.set_title("Average SBA 7(a) interest rate by quarter", loc="left", fontsize=13, color=INK, fontweight="bold")
ticks = [i for i, q in enumerate(r.quarter) if q.endswith("Q1")]
ax.set_xticks(ticks, [r.quarter[i][:4] for i in ticks])
ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
i22 = list(r.quarter).index("2022-Q1")
ax.axvline(i22, color=GRAY, ls="--", lw=1)
ax.text(i22 + 0.3, r.avg_rate.min() + 0.2, "Fed begins raising\nrates (Mar 2022)", fontsize=9, color="#52606d")
save(fig, "03_rate_trend.png")

# 4. Size bands: share of loans vs share of dollars
b = pd.read_csv(O / "size_bands.csv")
fig, ax = plt.subplots(figsize=(8, 4.2))
x = range(len(b))
w = 0.38
b1 = ax.bar([i - w / 2 for i in x], b.pct_of_loans, w, color=BLUE, label="Share of loans")
b2 = ax.bar([i + w / 2 for i in x], b.pct_of_dollars, w, color=ORANGE, label="Share of dollars")
ax.bar_label(b1, fmt="%.0f%%", padding=2, fontsize=9, color=INK)
ax.bar_label(b2, fmt="%.0f%%", padding=2, fontsize=9, color=INK)
ax.set_xticks(list(x), b.SizeBand)
ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.legend(frameon=False)
ax.set_title("Most loans are small, but most dollars go to $1M+ loans", loc="left", fontsize=13, color=INK, fontweight="bold")
save(fig, "04_size_bands.png")

# 5. Business age: charge-offs among resolved loans
c = pd.read_csv(O / "resolved_outcomes.csv")
fig, ax = plt.subplots(figsize=(8, 3.8))
bars = ax.barh(c.BusinessAge.iloc[::-1], c.chargeoff_pct_of_resolved.iloc[::-1], color=[GRAY, BLUE, BLUE, ORANGE], height=0.6)
ax.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=10, color=INK)
ax.set_xlabel("Charged off, as % of loans with a disclosed outcome")
ax.set_title("Newer businesses show more charge-offs among resolved loans", loc="left", fontsize=13, color=INK, fontweight="bold")
ax.set_xlim(0, c.chargeoff_pct_of_resolved.max() * 1.25)
ax.grid(axis="y", visible=False)
ax.text(0, -0.3, "Not a true default rate: SBA withholds the status of active loans. See README for the full caveat.", transform=ax.transAxes, fontsize=9, color="#52606d")
save(fig, "05_resolved_outcomes.png")

print("Charts saved to images/:", sorted(p.name for p in IMG.glob("*.png")))
