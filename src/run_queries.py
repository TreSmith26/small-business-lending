"""Run every query in sql/analysis_queries.sql and save each result as a CSV in outputs/."""
from pathlib import Path
import re
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "sba_7a.db"
SQL = (ROOT / "sql" / "analysis_queries.sql").read_text()
OUT = ROOT / "outputs"

def queries(text: str):
    """Split the SQL file into (name, query) pairs using the '-- name:' markers."""
    parts = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.M)
    for name, body in zip(parts[1::2], parts[2::2]):
        body = re.split(r"^-- Q\d", body, flags=re.M)[0].strip()
        yield name, body

def main() -> None:
    OUT.mkdir(exist_ok=True)
    pd.set_option("display.width", 200)
    with sqlite3.connect(DB) as con:
        for name, q in queries(SQL):
            df = pd.read_sql_query(q, con)
            df.to_csv(OUT / f"{name}.csv", index=False)
            print(f"\n=== {name} ===")
            print(df.head(15).to_string(index=False))

if __name__ == "__main__":
    main()
