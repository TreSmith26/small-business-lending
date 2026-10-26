"""Build the Excel workbook and the Tableau data extract from the cleaned loans."""
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_parquet(ROOT / "data" / "processed" / "loans_clean.parquet")
df["Quarter"] = df.ApprovalDate.dt.year.astype(str) + "-Q" + df.ApprovalDate.dt.quarter.astype(str)

# ---------------- Tableau extract ----------------
g = ["ApprovalFY", "Quarter", "ProjectState", "Sector", "MethodFamily", "BusinessAge", "SizeBand"]
tab = (df.groupby(g, observed=True)
         .agg(Loans=("GrossApproval", "size"), TotalApproved=("GrossApproval", "sum"),
              SBAGuaranteed=("SBAGuaranteedApproval", "sum"), SumInterestRate=("InitialInterestRate", "sum"),
              JobsSupported=("JobsSupported", "sum"))
         .reset_index()
         .rename(columns={"ApprovalFY": "FiscalYear", "ProjectState": "State", "MethodFamily": "Product"}))
tab["PartialYear"] = tab.FiscalYear.eq(2026)
(ROOT / "tableau").mkdir(exist_ok=True)
tab.to_csv(ROOT / "tableau" / "sba_7a_tableau_extract.csv", index=False)
print(f"Tableau extract: {len(tab):,} rows")

# ---------------- Excel workbook ----------------
F = "Arial"
H_FILL = PatternFill("solid", fgColor="0B2545")
SUB_FILL = PatternFill("solid", fgColor="EEF5FB")
IN_FILL = PatternFill("solid", fgColor="FFFF00")
thin = Side(style="thin", color="D5DCE4")
BOX = Border(top=thin, bottom=thin, left=thin, right=thin)

def header(ws, row, labels, col=1):
    for i, t in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=t)
        c.font = Font(name=F, bold=True, color="FFFFFF")
        c.fill = H_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BOX

def title(ws, text, sub=None):
    ws["A1"] = text
    ws["A1"].font = Font(name=F, bold=True, size=16, color="0B2545")
    if sub:
        ws["A2"] = sub
        ws["A2"].font = Font(name=F, italic=True, size=10, color="52606D")

def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[get_column_letter(i)].width = x

wb = Workbook()

# Data sheet: FY x State x Sector aggregate (formulas on other sheets reference it)
agg = (df.groupby(["ApprovalFY", "ProjectState", "Sector"], observed=True)
         .agg(Loans=("GrossApproval", "size"), Total=("GrossApproval", "sum"),
              SumRate=("InitialInterestRate", "sum"))
         .reset_index().sort_values(["ApprovalFY", "ProjectState", "Sector"]))
data = wb.active
data.title = "Data"
title(data, "Aggregated SBA 7(a) loans: fiscal year x state x industry",
      "Source: SBA 7(a) FOIA data, FY2020 to June 30, 2026 (data.sba.gov). Cancelled loans removed. Built by src/build_excel_tableau.py.")
header(data, 4, ["Fiscal Year", "State", "Industry Sector", "Loans", "Total Approved ($)", "Sum of Interest Rates", "Avg Rate (%)"])
r0 = 5
for i, row in enumerate(agg.itertuples(index=False)):
    r = r0 + i
    data.cell(r, 1, int(row.ApprovalFY))
    data.cell(r, 2, row.ProjectState)
    data.cell(r, 3, row.Sector)
    data.cell(r, 4, int(row.Loans))
    data.cell(r, 5, float(row.Total))
    data.cell(r, 6, float(row.SumRate))
    data.cell(r, 7, f"=IFERROR(F{r}/D{r},0)")
last = r0 + len(agg) - 1
for row in data.iter_rows(min_row=r0, max_row=last, max_col=7):
    for c in row:
        c.font = Font(name=F, size=10)
for r in range(r0, last + 1):
    data.cell(r, 5).number_format = "$#,##0"
    data.cell(r, 6).number_format = "#,##0.00"
    data.cell(r, 7).number_format = "0.00"
data.freeze_panes = "A5"
data.auto_filter.ref = f"A4:G{last}"
widths(data, [12, 8, 36, 10, 20, 20, 12])
RNG = lambda col: f"Data!${col}${r0}:${col}${last}"

# Summary sheet
s = wb.create_sheet("Summary", 0)
title(s, "SBA 7(a) Small Business Lending, FY2020 to June 2026",
      "All figures calculate from the Data sheet with SUMIFS. FY2026 is a partial year (October 2025 to June 2026).")
s["A4"] = "Lending by fiscal year"
s["A4"].font = Font(name=F, bold=True, size=12, color="0B2545")
header(s, 5, ["Fiscal Year", "Loans", "Total Approved ($)", "Avg Loan ($)", "Avg Rate (%)", "YoY Change in $"])
years = sorted(df.ApprovalFY.unique())
for i, y in enumerate(years):
    r = 6 + i
    s.cell(r, 1, str(y) + ("*" if y == 2026 else ""))
    s.cell(r, 7, int(y)).font = Font(name=F, color="FFFFFF", size=8)  # helper key (hidden column G)
    s.cell(r, 2, f"=SUMIFS({RNG('D')},{RNG('A')},G{r})")
    s.cell(r, 3, f"=SUMIFS({RNG('E')},{RNG('A')},G{r})")
    s.cell(r, 4, f"=IFERROR(C{r}/B{r},0)")
    s.cell(r, 5, f"=IFERROR(SUMIFS({RNG('F')},{RNG('A')},G{r})/B{r},0)")
    s.cell(r, 6, "" if i == 0 else (f"=IFERROR(C{r}/C{r-1}-1,0)" if y != 2026 else "n/a (partial year)"))
yl = 6 + len(years) - 1
s.cell(yl + 1, 1, "Total")
s.cell(yl + 1, 2, f"=SUM(B6:B{yl})")
s.cell(yl + 1, 3, f"=SUM(C6:C{yl})")
s.cell(yl + 1, 4, f"=IFERROR(C{yl+1}/B{yl+1},0)")
for c in range(1, 7):
    s.cell(yl + 1, c).font = Font(name=F, bold=True)
    s.cell(yl + 1, c).border = Border(top=Side(style="thin", color="0B2545"), bottom=Side(style="double", color="0B2545"))
s.column_dimensions["G"].hidden = True
for r in range(6, yl + 2):
    s.cell(r, 2).number_format = "#,##0"
    s.cell(r, 3).number_format = "$#,##0"
    s.cell(r, 4).number_format = "$#,##0"
    s.cell(r, 5).number_format = "0.00"
    s.cell(r, 6).number_format = "0.0%;-0.0%;-"
    for c in range(1, 7):
        if s.cell(r, c).font.name != F:
            s.cell(r, c).font = Font(name=F, bold=s.cell(r, c).font.bold)

sr = yl + 4
s.cell(sr, 1, "Lending by industry sector (all years)").font = Font(name=F, bold=True, size=12, color="0B2545")
header(s, sr + 1, ["Industry Sector", "Loans", "Total Approved ($)", "Avg Loan ($)", "Share of $"])
sectors = df.groupby("Sector").GrossApproval.sum().sort_values(ascending=False).index.tolist()
for i, sec in enumerate(sectors):
    r = sr + 2 + i
    s.cell(r, 1, sec)
    s.cell(r, 2, f"=SUMIFS({RNG('D')},{RNG('C')},A{r})")
    s.cell(r, 3, f"=SUMIFS({RNG('E')},{RNG('C')},A{r})")
    s.cell(r, 4, f"=IFERROR(C{r}/B{r},0)")
    s.cell(r, 5, f"=IFERROR(C{r}/$C${yl+1},0)")
    s.cell(r, 2).number_format = "#,##0"
    s.cell(r, 3).number_format = "$#,##0"
    s.cell(r, 4).number_format = "$#,##0"
    s.cell(r, 5).number_format = "0.0%"
    for c in range(1, 6):
        s.cell(r, c).font = Font(name=F)
se = sr + 1 + len(sectors)
s.cell(se + 2, 1, "* FY2026 covers October 2025 to June 30, 2026 only, so it is not comparable to full years.").font = Font(name=F, italic=True, size=9, color="52606D")
widths(s, [36, 12, 20, 16, 14, 22])
s.freeze_panes = "A4"

ch = BarChart()
ch.type = "col"
ch.title = "Total approved by fiscal year ($)"
ch.y_axis.title = "$"
ch.add_data(Reference(s, min_col=3, min_row=5, max_row=yl), titles_from_data=True)
ch.set_categories(Reference(s, min_col=1, min_row=6, max_row=yl))
ch.legend = None
ch.height, ch.width = 7.5, 15
s.add_chart(ch, "H4")
lc = LineChart()
lc.title = "Average interest rate by fiscal year (%)"
lc.add_data(Reference(s, min_col=5, min_row=5, max_row=yl), titles_from_data=True)
lc.set_categories(Reference(s, min_col=1, min_row=6, max_row=yl))
lc.legend = None
lc.height, lc.width = 7.5, 15
s.add_chart(lc, "H20")

# State Explorer: pick a state, see its numbers
ex = wb.create_sheet("State Explorer", 1)
title(ex, "State Explorer", "Pick a state in the yellow cell. Every number below recalculates from the Data sheet.")
ex["A4"] = "State (2-letter code):"
ex["A4"].font = Font(name=F, bold=True)
ex["B4"] = "VA"
ex["B4"].fill = IN_FILL
ex["B4"].font = Font(name=F, bold=True, color="0000FF", size=12)
states = sorted(df.ProjectState.dropna().unique())
lists = wb.create_sheet("Lists")
for i, st in enumerate(states, 1):
    lists.cell(i, 1, st)
lists.sheet_state = "hidden"
dv = DataValidation(type="list", formula1=f"=Lists!$A$1:$A${len(states)}", allow_blank=False)
ex.add_data_validation(dv)
dv.add("B4")
ex["A6"], ex["B6"] = "Total loans", f"=SUMIFS({RNG('D')},{RNG('B')},$B$4)"
ex["A7"], ex["B7"] = "Total approved ($)", f"=SUMIFS({RNG('E')},{RNG('B')},$B$4)"
ex["A8"], ex["B8"] = "Average loan ($)", "=IFERROR(B7/B6,0)"
ex["A9"], ex["B9"] = "Average interest rate (%)", f"=IFERROR(SUMIFS({RNG('F')},{RNG('B')},$B$4)/B6,0)"
ex["A10"], ex["B10"] = "Share of national dollars", f"=IFERROR(B7/SUM({RNG('E')}),0)"
ex["A11"], ex["B11"] = "National rank by dollars", "=IFERROR(MATCH($B$4,Lists!$B$1:$B${n},0),\"\")".replace("{n}", str(len(states)))
for r, fmt in zip(range(6, 12), ["#,##0", "$#,##0", "$#,##0", "0.00", "0.00%", "0"]):
    ex.cell(r, 2).number_format = fmt
    ex.cell(r, 1).font = Font(name=F)
    ex.cell(r, 2).font = Font(name=F, bold=True)
# national rank helper: states sorted by dollars in Lists!B
rank_order = df.groupby("ProjectState").GrossApproval.sum().sort_values(ascending=False).index.tolist()
for i, st in enumerate(rank_order, 1):
    lists.cell(i, 2, st)
ex.cell(11, 3, "Rank list is precomputed in the hidden Lists sheet, sorted by total dollars.").font = Font(name=F, italic=True, size=9, color="52606D")
header(ex, 13, ["Fiscal Year", "Loans", "Total Approved ($)", "Avg Rate (%)"])
for i, y in enumerate(years):
    r = 14 + i
    ex.cell(r, 1, int(y))
    ex.cell(r, 2, f"=SUMIFS({RNG('D')},{RNG('B')},$B$4,{RNG('A')},A{r})")
    ex.cell(r, 3, f"=SUMIFS({RNG('E')},{RNG('B')},$B$4,{RNG('A')},A{r})")
    ex.cell(r, 4, f"=IFERROR(SUMIFS({RNG('F')},{RNG('B')},$B$4,{RNG('A')},A{r})/B{r},0)")
    ex.cell(r, 2).number_format = "#,##0"
    ex.cell(r, 3).number_format = "$#,##0"
    ex.cell(r, 4).number_format = "0.00"
    for c in range(1, 5):
        ex.cell(r, c).font = Font(name=F)
er = 14 + len(years) + 1
header(ex, er, ["Industry Sector", "Loans", "Total Approved ($)", "Share of State $"])
for i, sec in enumerate(sectors):
    r = er + 1 + i
    ex.cell(r, 1, sec)
    ex.cell(r, 2, f"=SUMIFS({RNG('D')},{RNG('B')},$B$4,{RNG('C')},A{r})")
    ex.cell(r, 3, f"=SUMIFS({RNG('E')},{RNG('B')},$B$4,{RNG('C')},A{r})")
    ex.cell(r, 4, f"=IFERROR(C{r}/$B$7,0)")
    ex.cell(r, 2).number_format = "#,##0"
    ex.cell(r, 3).number_format = "$#,##0"
    ex.cell(r, 4).number_format = "0.0%"
    for c in range(1, 5):
        ex.cell(r, c).font = Font(name=F)
widths(ex, [34, 18, 20, 16])
c2 = BarChart()
c2.type = "col"
c2.title = "Selected state: total approved by fiscal year ($)"
c2.add_data(Reference(ex, min_col=3, min_row=13, max_row=13 + len(years)), titles_from_data=True)
c2.set_categories(Reference(ex, min_col=1, min_row=14, max_row=13 + len(years)))
c2.legend = None
c2.height, c2.width = 7.5, 15
ex.add_chart(c2, "F4")

# Virginia loans: loan-level, no borrower names or addresses
va = df[df.ProjectState == "VA"].sort_values("ApprovalDate")
vs = wb.create_sheet("Virginia Loans")
title(vs, "Virginia SBA 7(a) loans (loan level)", "Borrower names and addresses removed. Use the filters to explore by county, industry, or product.")
cols = [("Approval Date", "ApprovalDate"), ("Fiscal Year", "ApprovalFY"), ("County / City", "ProjectCounty"),
        ("Industry Sector", "Sector"), ("NAICS Description", "NaicsDescription"), ("Product", "MethodFamily"),
        ("Business Age", "BusinessAge"), ("Lender", "BankName"), ("Loan Amount ($)", "GrossApproval"),
        ("SBA Guarantee ($)", "SBAGuaranteedApproval"), ("Interest Rate (%)", "InitialInterestRate"),
        ("Term (Months)", "TermInMonths"), ("Jobs Supported", "JobsSupported")]
header(vs, 4, [c[0] for c in cols])
for i, row in enumerate(va[[c[1] for c in cols]].itertuples(index=False)):
    r = 5 + i
    for j, v in enumerate(row, 1):
        if hasattr(v, "to_pydatetime"):
            v = v.to_pydatetime().date()
        elif hasattr(v, "item"):
            v = v.item()
        c = vs.cell(r, j, v)
        c.font = Font(name=F, size=10)
    vs.cell(r, 1).number_format = "yyyy-mm-dd"
    vs.cell(r, 9).number_format = "$#,##0"
    vs.cell(r, 10).number_format = "$#,##0"
vl = 5 + len(va) - 1
vs.freeze_panes = "A5"
vs.auto_filter.ref = f"A4:M{vl}"
widths(vs, [13, 10, 22, 30, 36, 20, 22, 34, 15, 15, 12, 11, 11])

# About sheet
ab = wb.create_sheet("About", 0)
title(ab, "About this workbook")
notes = [
    ("Data source", "U.S. Small Business Administration, 7(a) FOIA loan data, FY2020 to present, as of June 30, 2026. https://data.sba.gov/dataset/7a-504-foia (public domain)."),
    ("What is a 7(a) loan?", "SBA's main small business loan program. Private lenders make the loans and SBA guarantees part of each one."),
    ("Cleaning", "Cancelled loans (approved but never funded) were removed: 50,104 of 388,338 rows. Borrower names and addresses were dropped."),
    ("Fiscal year", "SBA fiscal years run October 1 to September 30. FY2026 is partial (through June 30, 2026)."),
    ("Average rate", "Simple average of each loan's initial interest rate, not weighted by loan size."),
    ("Summary", "Year and industry totals, built with SUMIFS formulas over the Data sheet."),
    ("State Explorer", "Choose any state in the yellow cell to see its totals, trend, and industry mix."),
    ("Virginia Loans", "Every funded Virginia loan, ready for filtering or a PivotTable (Insert > PivotTable)."),
    ("Data", "Aggregated by fiscal year, state, and industry sector. All other sheets calculate from it."),
    ("Color code", "Yellow fill with blue text marks the one input cell. Everything else is a formula or source data."),
]
for i, (k, v) in enumerate(notes):
    ab.cell(3 + i, 1, k).font = Font(name=F, bold=True)
    c = ab.cell(3 + i, 2, v)
    c.font = Font(name=F)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ab.cell(3 + i, 1).alignment = Alignment(vertical="top")
widths(ab, [20, 100])

wb.move_sheet("Data", offset=len(wb.sheetnames))
out = ROOT / "excel" / "SBA_7a_Lending_Analysis.xlsx"
out.parent.mkdir(exist_ok=True)
wb.save(out)
print(f"Saved {out.relative_to(ROOT)}; sheets: {wb.sheetnames}")
