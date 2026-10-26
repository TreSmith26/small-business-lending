"""Inject the SQL query outputs into the report template.

Writes two files:
  report/sba_report.html  page content only (no html/head wrapper)
  report/index.html       standalone page for GitHub Pages
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
names = ["yearly_volume", "sector_mix", "product_comparison", "business_age", "top_lenders",
         "lender_concentration", "state_ranking", "virginia_sectors", "richmond_region",
         "rate_trend", "size_bands", "resolved_outcomes"]
data = {n: pd.read_csv(ROOT / "outputs" / f"{n}.csv").to_dict(orient="list") for n in names}
body = (ROOT / "report" / "template.html").read_text().replace("/*DATA*/null", json.dumps(data))
(ROOT / "report" / "sba_report.html").write_text(body)

head_end = body.index("</style>") + len("</style>")
page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">\n"
        + body[:head_end]
        + "\n</head>\n<body style=\"margin:0\">\n" + body[head_end:] + "\n</body>\n</html>\n")
(ROOT / "report" / "index.html").write_text(page)
print("Wrote report/sba_report.html and report/index.html")
