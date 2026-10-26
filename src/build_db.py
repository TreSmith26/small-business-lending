"""Load the cleaned loans into a SQLite database so the analysis can be done in SQL."""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "sba_7a.db"

def main() -> None:
    df = pd.read_parquet(ROOT / "data" / "processed" / "loans_clean.parquet")
    df["ApprovalDate"] = df["ApprovalDate"].dt.strftime("%Y-%m-%d")
    df["ApprovalMonth"] = df["ApprovalMonth"].dt.strftime("%Y-%m")
    df["SizeBand"] = df["SizeBand"].astype(str)
    cols = ["ApprovalDate", "ApprovalMonth", "ApprovalFY", "PartialYear", "LocationID", "BankName",
            "GrossApproval", "SBAGuaranteedApproval", "GuaranteePct", "ProcessingMethod", "MethodFamily",
            "InitialInterestRate", "FixedorVariableInterestInd", "TermInMonths", "NaicsCode", "Sector",
            "IsFranchise", "ProjectCounty", "ProjectState", "BusinessType", "BusinessAge", "LoanStatus",
            "GrossChargeOffAmount", "IsRevolver", "JobsSupported", "CollateralInd", "SizeBand"]
    DB.unlink(missing_ok=True)
    with sqlite3.connect(DB) as con:
        df[cols].to_sql("loans", con, index=False)
        con.execute("CREATE INDEX idx_fy ON loans(ApprovalFY)")
        con.execute("CREATE INDEX idx_state ON loans(ProjectState)")
        con.execute("CREATE INDEX idx_sector ON loans(Sector)")
    print(f"Loaded {len(df):,} loans into {DB.relative_to(ROOT)} (table: loans)")

if __name__ == "__main__":
    main()
