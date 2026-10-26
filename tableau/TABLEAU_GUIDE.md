# Building the Tableau Public dashboard

This guide walks you through building the interactive dashboard from `sba_7a_tableau_extract.csv`. It takes about 45 to 60 minutes the first time. Build it yourself: in an interview, you need to be able to explain every chart and calculation.

Tableau Public is free. Download it from public.tableau.com. Menu names below are from recent versions and can shift slightly between releases.

## 1. The data

`sba_7a_tableau_extract.csv` has 166,573 rows. Each row is a group of funded loans that share the same:

| Field | Meaning |
|---|---|
| FiscalYear | SBA fiscal year (Oct 1 to Sep 30) |
| Quarter | Calendar quarter, e.g. 2024-Q3 |
| State | Two-letter state where the project is located |
| Sector | Industry sector from the 2-digit NAICS code |
| Product | Preferred Lender (PLP), SBA Express, Standard 7(a), or Other |
| BusinessAge | Existing (2+ years), New (2 years or less), Startup, Change of Ownership, Unanswered |
| SizeBand | Loan size bucket |
| Loans | Number of loans in the group |
| TotalApproved | Total approved dollars |
| SBAGuaranteed | SBA-guaranteed dollars |
| SumInterestRate | Sum of initial interest rates (used to compute an average) |
| JobsSupported | Lender-reported jobs created plus retained (self-reported, not audited by SBA) |
| PartialYear | TRUE for FY2026, which only runs through June 30, 2026 |

Because rows are already grouped, **always use SUM(Loans) to count loans, never COUNT(rows)**.

## 2. Connect

1. Open Tableau Public, choose **Text file**, and select the CSV.
2. In the data pane, make sure **State** has the geographic role **State/Province** (right-click the field, then Geographic Role).
3. Change **FiscalYear** to a discrete Dimension (right-click, Convert to Discrete) so it works as a label.

## 3. Calculated fields

Create these from **Analysis > Create Calculated Field**:

- **Avg Loan Size**: `SUM([TotalApproved]) / SUM([Loans])`
- **Avg Interest Rate**: `SUM([SumInterestRate]) / SUM([Loans])`
- **Share of Dollars**: `SUM([TotalApproved]) / TOTAL(SUM([TotalApproved]))`
- **Guarantee %**: `SUM([SBAGuaranteed]) / SUM([TotalApproved])`

Format Avg Loan Size as currency, Avg Interest Rate as a number with 2 decimals, and the two percentages as percentages.

## 4. Worksheets

1. **Lending by Year**: FiscalYear on Columns, SUM(TotalApproved) on Rows, bar chart. Put PartialYear on Color so FY2026 is visibly different, and add a caption that FY2026 is partial.
2. **Rate Trend**: Quarter on Columns, Avg Interest Rate on Rows, line chart. Add a reference line or annotation at 2022-Q1 labeled "Fed begins raising rates (Mar 2022)".
3. **State Map**: double-click State to make a filled map, put SUM(TotalApproved) on Color and Avg Loan Size on Tooltip.
4. **Industry Mix**: Sector on Rows, SUM(TotalApproved) on Columns, sorted descending, horizontal bars with Share of Dollars as the label.
5. **Product Comparison**: Product on Rows, with SUM(Loans), SUM(TotalApproved), Avg Loan Size, and Avg Interest Rate as a text table or side-by-side bars.
6. **Size Bands**: SizeBand on Columns with both SUM(Loans) and SUM(TotalApproved) as percent of total (Quick Table Calculation > Percent of Total). This shows that most loans are small but most dollars are in $1M+ loans.

## 5. Dashboard

1. **Dashboard > New Dashboard**, size **Automatic** or 1200 x 900.
2. Layout: title and KPI tiles across the top (total dollars, total loans, avg loan size, avg rate), Lending by Year and Rate Trend in the middle, State Map and Industry Mix below.
3. Add filters for **State**, **Sector**, **Product**, and **BusinessAge**, and set each to "Apply to Worksheets > All Using This Data Source".
4. Click the map, then the funnel icon, to **Use as Filter**. Clicking a state now filters the whole dashboard.
5. Add a text box with the source: "Source: U.S. SBA 7(a) FOIA data, FY2020 to June 30, 2026, data.sba.gov. Cancelled loans excluded."

## 6. Publish

**File > Save to Tableau Public**. Sign in with a free account, and it publishes to your Tableau Public profile. Copy the link into the README (the "Tableau dashboard" link) and onto your resume.

## Checks before you publish

Your dashboard should match these totals from the SQL analysis:

- Total approved, all years: about **$179.1 billion** across **338,234** loans
- FY2025: about **$32.1 billion** across **64,096** loans
- Virginia: **$3.14 billion**, ranked **18th** by dollars

If your numbers differ, the usual cause is COUNT instead of SUM(Loans), or a filter left on.
