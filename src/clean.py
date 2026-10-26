"""Clean the SBA 7(a) FOIA data and save an analysis-ready Parquet file.

Cleaning decisions (each one is explained in the README):
  1. Drop cancelled loans (LoanStatus = CANCLD). They were approved but never funded,
     so they would overstate lending.
  2. Drop borrower names and street addresses. Analysis is done at the aggregate level only.
  3. Map 6-digit NAICS codes to 2-digit industry sectors.
  4. Group processing methods into four families (Preferred Lender, Express, Standard, Other).
  5. Flag the partial fiscal year (FY2026 data runs through June 30, 2026).
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "FOIA_7a_FY2020_Present_asof_260630.csv"
OUT = ROOT / "data" / "processed" / "loans_clean.parquet"

SECTORS = {
    "11": "Agriculture, Forestry & Fishing", "21": "Mining & Oil/Gas", "22": "Utilities",
    "23": "Construction", "31": "Manufacturing", "32": "Manufacturing", "33": "Manufacturing",
    "42": "Wholesale Trade", "44": "Retail Trade", "45": "Retail Trade",
    "48": "Transportation & Warehousing", "49": "Transportation & Warehousing",
    "51": "Information", "52": "Finance & Insurance", "53": "Real Estate & Rental",
    "54": "Professional & Technical Services", "55": "Management of Companies",
    "56": "Admin, Support & Waste Services", "61": "Educational Services",
    "62": "Health Care & Social Assistance", "71": "Arts, Entertainment & Recreation",
    "72": "Accommodation & Food Services", "81": "Other Services", "92": "Public Administration",
}

def method_family(m: str) -> str:
    if not isinstance(m, str):
        return "Other"
    if m.startswith("Preferred Lenders"):
        return "Preferred Lender (PLP)"
    if m in ("SBA Express Program", "Export Express"):
        return "SBA Express"
    if m in ("7a General", "7a with EWCP", "7(a) WCP"):
        return "Standard 7(a)"
    return "Other"

def main() -> None:
    keep = ["ApprovalDate", "ApprovalFY", "LocationID", "BankName", "BankState",
            "GrossApproval", "SBAGuaranteedApproval", "ProcessingMethod", "InitialInterestRate",
            "FixedorVariableInterestInd", "TermInMonths", "NaicsCode", "NaicsDescription",
            "FranchiseName", "ProjectCounty", "ProjectState", "BusinessType", "BusinessAge",
            "LoanStatus", "GrossChargeOffAmount", "RevolverStatus", "JobsSupported", "CollateralInd"]
    df = pd.read_csv(RAW, usecols=keep, low_memory=False)
    n_raw = len(df)

    df = df[df["LoanStatus"] != "CANCLD"].copy()
    n_kept = len(df)

    df["ApprovalDate"] = pd.to_datetime(df["ApprovalDate"])
    df["ApprovalMonth"] = df["ApprovalDate"].dt.to_period("M").dt.to_timestamp()
    df["Sector"] = df["NaicsCode"].astype(str).str[:2].map(SECTORS).fillna("Unclassified")
    df["MethodFamily"] = df["ProcessingMethod"].map(method_family)
    df["IsFranchise"] = df["FranchiseName"].notna()
    df["IsRevolver"] = df["RevolverStatus"].eq("Y")
    df["GuaranteePct"] = df["SBAGuaranteedApproval"] / df["GrossApproval"]
    df["BusinessAge"] = df["BusinessAge"].fillna("Unanswered").replace({
        "Existing or more than 2 years old": "Existing (2+ years)",
        "New Business or 2 years or less": "New (2 years or less)",
        "Startup, Loan Funds will Open Business": "Startup",
    })
    df["PartialYear"] = df["ApprovalFY"].eq(2026)
    df["SizeBand"] = pd.cut(df["GrossApproval"], [0, 50_000, 150_000, 350_000, 1_000_000, 5_000_001],
                            labels=["Under $50K", "$50K-$150K", "$150K-$350K", "$350K-$1M", "$1M-$5M"],
                            right=False)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    print(f"Raw rows: {n_raw:,}  |  Cancelled removed: {n_raw - n_kept:,}  |  Clean rows: {n_kept:,}")
    print(f"Saved {OUT.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
