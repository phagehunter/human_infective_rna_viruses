#!/usr/bin/env python3
"""Download the upstream dataset this atlas is built from.

Source
------
Zhang F, Lu L, Brierley L, Hietanen H, Woolhouse MEJ.
"Zhang et al. - Human-infective RNA virus database.xlsx"
figshare, version 2, published 2026-02-19.
DOI 10.6084/m9.figshare.30094726.v2
License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)

Companion paper: Zhang F, Lu L, Brierley L, Hietanen H, Woolhouse MEJ.
A complete catalogue of human-infective RNA viruses. Scientific Data.
2026;13:981. doi:10.1038/s41597-026-07281-5

The downloaded workbook is committed at data/raw/, because CC BY 4.0 permits
redistribution with attribution and a 147 KB file makes the build reproducible
without a network round trip. Run this script only to pick up a later version.

    python3 fetch_data.py            # download and verify, refuse to overwrite
    python3 fetch_data.py --force    # replace the committed copy

A new upstream version will have a different checksum. The script prints the
new value rather than trusting it: check the figshare record, then update
EXPECTED_MD5 and the provenance block in DATA.md in the same commit.
"""
import argparse
import hashlib
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
TARGET = RAW / "zhang-human-infective-rna-viruses-v2.xlsx"
SOURCE_META = ROOT / "data" / "source.json"

ARTICLE_ID = 30094726
VERSION = 2
API = f"https://api.figshare.com/v2/articles/{ARTICLE_ID}/versions/{VERSION}"
EXPECTED_MD5 = "4364e74b65441d18d2318ece3cd0267e"
EXPECTED_SIZE = 150945


def get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "nsf-rna-atlas-build/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true",
                    help="overwrite the committed workbook")
    args = ap.parse_args()

    if TARGET.exists() and not args.force:
        print(f"{TARGET.relative_to(ROOT)} is already present; pass --force to replace it.")
        return 0

    print(f"reading {API}")
    meta = json.loads(get(API))
    files = meta.get("files") or []
    if len(files) != 1:
        sys.exit(f"expected one file in the figshare record, found {len(files)}")
    f = files[0]

    print(f"downloading {f['name']} ({f['size']} bytes)")
    blob = get(f["download_url"])
    digest = hashlib.md5(blob).hexdigest()

    if digest != EXPECTED_MD5 or len(blob) != EXPECTED_SIZE:
        sys.exit(
            "the download does not match the version this build was written against.\n"
            f"  expected md5 {EXPECTED_MD5}, {EXPECTED_SIZE} bytes\n"
            f"  received md5 {digest}, {len(blob)} bytes\n"
            "If figshare has published a new version, check the record, then update\n"
            "EXPECTED_MD5, EXPECTED_SIZE, VERSION here and the provenance block in\n"
            "DATA.md, and re-run build.py so every count on the page follows."
        )

    RAW.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(blob)
    SOURCE_META.write_text(json.dumps({
        "title": meta.get("title"),
        "doi": meta.get("doi"),
        "version": meta.get("version"),
        "published_date": meta.get("published_date"),
        "license": (meta.get("license") or {}).get("name"),
        "license_url": (meta.get("license") or {}).get("url"),
        "authors": [a["full_name"] for a in meta.get("authors", [])],
        "file": f["name"],
        "size_bytes": f["size"],
        "md5": digest,
        "retrieved": __import__("datetime").date.today().isoformat(),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)} and {SOURCE_META.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
