"""Download the official SBA 7(a) FOIA loan data (FY2020 to present) and its data dictionary.

Source: U.S. Small Business Administration, 7(a) & 504 FOIA dataset
https://data.sba.gov/dataset/7a-504-foia  (public domain)

The raw CSV is about 180 MB, so it is not stored in this repository. Run:
    python data/download_data.py
"""
from pathlib import Path
from urllib.request import urlretrieve

BASE = "https://data.sba.gov/sites/default/files/uploaded_resources/"
FILES = {
    "FOIA_7a_FY2020_Present_asof_260630.csv": BASE + "FOIA_7a_FY2020_Present_asof_260630.csv",
    "7a_504_foia_data_dictionary.xlsx": BASE + "7a_504_foia_data_dictionary.xlsx",
}

raw = Path(__file__).parent / "raw"
raw.mkdir(exist_ok=True)
for name, url in FILES.items():
    out = raw / name
    if out.exists():
        print(f"Already have {name}")
        continue
    print(f"Downloading {name} ...")
    urlretrieve(url, out)
print("Done. If SBA has published a newer file, update the file names above from the dataset page.")
