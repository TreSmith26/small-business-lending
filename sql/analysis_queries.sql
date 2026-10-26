-- SBA 7(a) Small Business Lending Analysis, FY2020 to June 2026
-- Database: data/processed/sba_7a.db  (table: loans, one row per funded loan; cancelled loans removed)
-- Each query answers one business question. Run all of them with: python src/run_queries.py

-- Q1. How has SBA 7(a) lending changed year over year?
-- name: yearly_volume
SELECT ApprovalFY AS fiscal_year,
       PartialYear AS partial_year,
       COUNT(*) AS loans,
       ROUND(SUM(GrossApproval) / 1e9, 2) AS total_billions,
       ROUND(AVG(GrossApproval), 0) AS avg_loan,
       ROUND(AVG(InitialInterestRate), 2) AS avg_rate
FROM loans
GROUP BY ApprovalFY
ORDER BY ApprovalFY;

-- Q2. Which industries receive the most SBA-backed lending dollars?
-- name: sector_mix
SELECT Sector,
       COUNT(*) AS loans,
       ROUND(SUM(GrossApproval) / 1e9, 2) AS total_billions,
       ROUND(100.0 * SUM(GrossApproval) / (SELECT SUM(GrossApproval) FROM loans), 1) AS pct_of_dollars,
       ROUND(AVG(GrossApproval), 0) AS avg_loan
FROM loans
GROUP BY Sector
ORDER BY total_billions DESC;

-- Q3. How do the main loan products compare on size, rate, and term?
-- name: product_comparison
SELECT MethodFamily AS product,
       COUNT(*) AS loans,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM loans), 1) AS pct_of_loans,
       ROUND(100.0 * SUM(GrossApproval) / (SELECT SUM(GrossApproval) FROM loans), 1) AS pct_of_dollars,
       ROUND(AVG(GrossApproval), 0) AS avg_loan,
       ROUND(AVG(InitialInterestRate), 2) AS avg_rate,
       ROUND(AVG(TermInMonths), 0) AS avg_term_months,
       ROUND(100.0 * AVG(GuaranteePct), 1) AS avg_guarantee_pct
FROM loans
GROUP BY MethodFamily
ORDER BY loans DESC;

-- Q4. Do startups and new businesses get different terms than established ones?
-- name: business_age
SELECT BusinessAge,
       COUNT(*) AS loans,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM loans), 1) AS pct_of_loans,
       ROUND(AVG(GrossApproval), 0) AS avg_loan,
       ROUND(AVG(InitialInterestRate), 2) AS avg_rate,
       ROUND(100.0 * AVG(CASE WHEN CollateralInd = 'Y' THEN 1.0 ELSE 0 END), 1) AS pct_collateralized,
       ROUND(100.0 * AVG(CASE WHEN IsFranchise THEN 1.0 ELSE 0 END), 1) AS pct_franchise
FROM loans
GROUP BY BusinessAge
ORDER BY loans DESC;

-- Q5. How concentrated is SBA lending among lenders? (Top 10 share of dollars)
-- name: top_lenders
WITH lender AS (
    SELECT BankName, COUNT(*) AS loans, SUM(GrossApproval) AS dollars, AVG(GrossApproval) AS avg_loan
    FROM loans GROUP BY BankName
)
SELECT BankName AS lender,
       loans,
       ROUND(dollars / 1e9, 2) AS total_billions,
       ROUND(100.0 * dollars / (SELECT SUM(dollars) FROM lender), 1) AS pct_of_dollars,
       ROUND(avg_loan, 0) AS avg_loan
FROM lender
ORDER BY dollars DESC
LIMIT 10;

-- Q5b. Market concentration: number of lenders and share held by the top 10
-- name: lender_concentration
WITH lender AS (
    SELECT BankName, SUM(GrossApproval) AS dollars FROM loans GROUP BY BankName
), ranked AS (
    SELECT dollars, ROW_NUMBER() OVER (ORDER BY dollars DESC) AS rnk FROM lender
)
SELECT (SELECT COUNT(*) FROM lender) AS lenders,
       ROUND(100.0 * SUM(CASE WHEN rnk <= 10 THEN dollars END) / SUM(dollars), 1) AS top10_pct_of_dollars,
       ROUND(100.0 * SUM(CASE WHEN rnk <= 50 THEN dollars END) / SUM(dollars), 1) AS top50_pct_of_dollars
FROM ranked;

-- Q6. Which states get the most lending, and how does Virginia rank?
-- name: state_ranking
WITH s AS (
    SELECT ProjectState, COUNT(*) AS loans, SUM(GrossApproval) AS dollars, AVG(GrossApproval) AS avg_loan
    FROM loans GROUP BY ProjectState
)
SELECT RANK() OVER (ORDER BY dollars DESC) AS rank_by_dollars,
       ProjectState AS state,
       loans,
       ROUND(dollars / 1e9, 2) AS total_billions,
       ROUND(avg_loan, 0) AS avg_loan
FROM s
ORDER BY dollars DESC;

-- Q7. Virginia deep dive: top industries for Virginia small businesses
-- name: virginia_sectors
SELECT Sector,
       COUNT(*) AS loans,
       ROUND(SUM(GrossApproval) / 1e6, 1) AS total_millions,
       ROUND(100.0 * SUM(GrossApproval) / (SELECT SUM(GrossApproval) FROM loans WHERE ProjectState = 'VA'), 1) AS pct_of_va_dollars
FROM loans
WHERE ProjectState = 'VA'
GROUP BY Sector
ORDER BY total_millions DESC
LIMIT 8;

-- Q8. Greater Richmond: lending by locality (Richmond City, Henrico, Chesterfield, Hanover)
-- name: richmond_region
SELECT ProjectCounty AS locality,
       COUNT(*) AS loans,
       ROUND(SUM(GrossApproval) / 1e6, 1) AS total_millions,
       ROUND(AVG(GrossApproval), 0) AS avg_loan
FROM loans
WHERE ProjectState = 'VA'
  AND ProjectCounty IN ('RICHMOND CITY', 'HENRICO', 'CHESTERFIELD', 'HANOVER')
GROUP BY ProjectCounty
ORDER BY total_millions DESC;

-- Q9. How did borrowing costs change? Average initial rate by quarter
-- name: rate_trend
SELECT SUBSTR(ApprovalMonth, 1, 4) || '-Q' || ((CAST(SUBSTR(ApprovalMonth, 6, 2) AS INTEGER) + 2) / 3) AS quarter,
       COUNT(*) AS loans,
       ROUND(AVG(InitialInterestRate), 2) AS avg_rate,
       ROUND(AVG(CASE WHEN FixedorVariableInterestInd = 'V' THEN InitialInterestRate END), 2) AS avg_variable_rate
FROM loans
GROUP BY quarter
ORDER BY quarter;

-- Q10. Loan size distribution: how many loans are small vs large?
-- name: size_bands
SELECT SizeBand,
       COUNT(*) AS loans,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM loans), 1) AS pct_of_loans,
       ROUND(100.0 * SUM(GrossApproval) / (SELECT SUM(GrossApproval) FROM loans), 1) AS pct_of_dollars
FROM loans
GROUP BY SizeBand
ORDER BY MIN(GrossApproval);

-- Q11. Charge-offs among loans with a disclosed outcome, by business age.
-- CAVEAT: SBA withholds the status of active loans (LoanStatus = EXEMPT), so this is NOT a true default rate.
-- It only compares loans that already ended (paid in full or charged off), which skews toward older, shorter loans.
-- name: resolved_outcomes
SELECT BusinessAge,
       SUM(CASE WHEN LoanStatus IN ('P I F', 'CHGOFF') THEN 1 ELSE 0 END) AS resolved_loans,
       SUM(CASE WHEN LoanStatus = 'CHGOFF' THEN 1 ELSE 0 END) AS charged_off,
       ROUND(100.0 * SUM(CASE WHEN LoanStatus = 'CHGOFF' THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN LoanStatus IN ('P I F', 'CHGOFF') THEN 1 ELSE 0 END), 0), 1) AS chargeoff_pct_of_resolved
FROM loans
WHERE BusinessAge <> 'Unanswered'
GROUP BY BusinessAge
ORDER BY chargeoff_pct_of_resolved DESC;
