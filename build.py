#!/usr/bin/env python3
"""Build data/viruses.json, data/meta.json and index.html from the upstream workbook.

    python3 build.py            # normalize the data and render the page
    python3 build.py --report   # print the normalization report, write nothing

Input is data/raw/zhang-human-infective-rna-viruses-v2.xlsx, the figshare
release documented in data/source.json and fetched by fetch_data.py, plus
data/spillover.json for the SpillOver risk scores.

Every number the page prints is computed here. Nothing about the catalogue is
typed into src/template.html.
"""
import argparse
import collections
import datetime
import html
import json
import pathlib
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "zhang-human-infective-rna-viruses-v2.xlsx"
SOURCE = ROOT / "data" / "source.json"
SPILLOVER = ROOT / "data" / "spillover.json"
TEMPLATE = ROOT / "src" / "template.html"

SITE_URL = "https://curtishoffmann.com/human_infective_rna_viruses/"
AUTHOR = "Curtis Hoffmann"
AUTHOR_URL = "https://curtishoffmann.com"

# Column positions in the upstream sheet. The reference columns are followed by
# unnamed continuation columns holding further PubMed identifiers for the same
# claim, so each group is read as a span.
COL = {
    "name": 0, "species": 1, "genus": 2, "family": 3, "ictv": 4,
    "enveloped": 5, "genome": 6, "seq_id": 7, "year": 8,
    "country": 9, "region": 10, "lat": 11, "lon": 12,
    "discovery_ref": 13,
    "level": 14, "level_refs": (15, 18),
    "vector": 18, "vector_order": 19, "vector_refs": (20, 22),
    "routes": (22, 30), "route_refs": (30, 32),
    "hosts": (32, 37), "host_refs": (37, 39),
}
ROUTE_NAMES = ["Inhalation", "Ingestion", "Sexual contact", "Iatrogenic",
               "Fomites", "Broken skin", "Maternal", "Direct contact"]
HOST_NAMES = ["Human only", "Non-human primate", "Other mammals", "Birds",
              "Other vertebrates"]

# Transmission level, as defined in the source paper's scheme. The previous
# version of this site collapsed 4a and 4b to the integer 0, which made the
# most human-transmissible viruses look like the least. Levels are kept as the
# source writes them.
LEVEL_LABEL = {
    "2": "Level 2 — limited onward transmission between humans",
    "3": "Level 3 — longer chains of transmission between humans",
    "4a": "Level 4a — sustained human-to-human transmission, with an animal reservoir",
    "4b": "Level 4b — sustained human-to-human transmission, no animal reservoir needed",
}

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS = {"m": M[1:-1], "p": "http://schemas.openxmlformats.org/package/2006/relationships"}


# ------------------------------------------------------------- workbook reader

def _col_index(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_sheet(path, sheet_name="data"):
    """Read one worksheet into a list of rows. Standard library only."""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter(M + "t")))
    rels = {r.get("Id"): r.get("Target") for r in
            ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).findall("p:Relationship", NS)}
    part = None
    for sh in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", NS):
        if sh.get("name") == sheet_name:
            target = rels[sh.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")]
            part = "xl/" + target.lstrip("/").replace("xl/", "", 1)
    if part is None:
        raise SystemExit(f"worksheet {sheet_name!r} not found in {path}")
    rows = []
    for row in ET.fromstring(z.read(part)).iter(M + "row"):
        cells = {}
        for c in row:
            ref = c.get("r")
            if not ref:
                continue
            v = c.find("m:v", NS)
            if c.get("t") == "s" and v is not None:
                val = shared[int(v.text)]
            elif c.get("t") == "inlineStr":
                node = c.find("m:is", NS)
                val = "".join(x.text or "" for x in node.iter(M + "t")) if node is not None else None
            else:
                val = v.text if v is not None else None
            cells[_col_index(ref)] = val
        if cells:
            rows.append([cells.get(i) for i in range(max(cells) + 1)])
    return rows


# -------------------------------------------------------------- normalization

REPORT = collections.Counter()
INVISIBLE = {"‎", "‏", "​", "­", "﻿"}


def clean(value, field=None):
    """Trim, collapse runs of whitespace and drop invisible formatting marks.

    The upstream workbook carries trailing spaces on many names and a
    left-to-right mark on some vector orders. Those are recorded in the
    normalization report rather than fixed silently.
    """
    if value is None:
        return None
    s = str(value)
    if s.strip() in ("", "None", "NA", "N/A"):
        return None
    stripped = "".join(ch for ch in s if ch not in INVISIBLE)
    if stripped != s and field:
        REPORT[f"invisible character removed: {field}"] += 1
    collapsed = re.sub(r"\s+", " ", stripped).strip()
    if collapsed != stripped and field:
        REPORT[f"whitespace trimmed: {field}"] += 1
    return collapsed or None


def flagged(value):
    """The source marks some cells with a trailing asterisk and never says why."""
    if value is None:
        return None, False
    s = str(value)
    if s.endswith("*"):
        return s[:-1].strip() or None, True
    return s, False


def as_int(value):
    v = clean(value)
    if v is None:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def as_float(value):
    v = clean(value)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def as_bool(value):
    """Read a 0/1 cell, tolerating the source's asterisk, and say if it carried one.

    Returns (value, marked). The asterisk appears on both ones and zeros, so it
    qualifies the cell rather than negating it. An earlier version of this site
    read "1*" as not-1 and stored zero, which silently emptied the transmission
    routes of 45 species and collapsed transmission levels 4a and 4b to zero.
    """
    v = clean(value)
    if v is None:
        return None, False
    base, mark = flagged(v)
    if base not in ("0", "1"):
        return None, mark
    return base == "1", mark


def pmids(row, span):
    """Collect the PubMed identifiers in a reference column and its overflow."""
    lo, hi = span
    out = []
    for i in range(lo, hi):
        v = clean(row[i] if i < len(row) else None)
        if not v:
            continue
        for part in re.split(r"[;,/]\s*", v):
            part = part.strip()
            if part.isdigit():
                out.append(part)
    return list(dict.fromkeys(out))


def build_records():
    rows = read_sheet(RAW)
    header, body = rows[0], rows[1:]
    if clean(header[COL["name"]]) != "Common name":
        raise SystemExit("unexpected first column; the upstream layout has changed")

    records = []
    for row in body:
        species = clean(row[COL["species"]] if len(row) > COL["species"] else None, "species")
        if not species:
            continue  # trailing blank rows in the workbook

        level_raw, level_flag = flagged(clean(row[COL["level"]], "level"))
        order_raw, order_flag = flagged(clean(row[COL["vector_order"]], "vectorOrder"))
        _, vector_flag = flagged(clean(row[COL["vector"]], "vector"))

        marks = []
        if level_flag:
            marks.append("Transmission level")
        if order_flag:
            marks.append("Vector order")

        routes = {}
        for i, label in enumerate(ROUTE_NAMES):
            idx = COL["routes"][0] + i
            val, mark = as_bool(row[idx] if idx < len(row) else None)
            routes[label] = bool(val)
            if mark:
                marks.append(label)
        vector_on, vector_mark = as_bool(row[COL["vector"]] if COL["vector"] < len(row) else None)
        vector_on = bool(vector_on)
        if vector_mark or vector_flag:
            marks.append("Vector")
        hosts = {}
        for i, label in enumerate(HOST_NAMES):
            idx = COL["hosts"][0] + i
            val, mark = as_bool(row[idx] if idx < len(row) else None)
            hosts[label] = bool(val)
            if mark:
                marks.append(label)
        for m in marks:
            REPORT[f"source asterisk preserved: {m}"] += 1

        rec = {
            "name": clean(row[COL["name"]], "name"),
            "species": species,
            "genus": clean(row[COL["genus"]], "genus"),
            "family": clean(row[COL["family"]], "family"),
            "ictvId": clean(row[COL["ictv"]]),
            "enveloped": as_bool(row[COL["enveloped"]])[0],
            "genome": clean(row[COL["genome"]], "genome"),
            "seqId": clean(row[COL["seq_id"]], "seqId"),
            "year": as_int(row[COL["year"]]),
            "country": clean(row[COL["country"]], "country"),
            "region": clean(row[COL["region"]], "region"),
            "lat": as_float(row[COL["lat"]]),
            "lon": as_float(row[COL["lon"]]),
            "transmissionLevel": level_raw,
            "transmissionLevelLabel": LEVEL_LABEL.get(level_raw),
            "vector": vector_on,
            "vectorOrder": order_raw,
            "routes": routes,
            "hosts": hosts,
            "refs": {
                "discovery": pmids(row, (COL["discovery_ref"], COL["discovery_ref"] + 1)),
                "transmissionLevel": pmids(row, COL["level_refs"]),
                "vector": pmids(row, COL["vector_refs"]),
                "routes": pmids(row, COL["route_refs"]),
                "hosts": pmids(row, COL["host_refs"]),
            },
            "sourceMarked": sorted(set(marks)),
        }
        if level_raw and level_raw not in LEVEL_LABEL:
            REPORT[f"unmapped transmission level: {level_raw}"] += 1
        records.append(rec)

    # SpillOver risk scores, joined by ICTV species name.
    spill = json.loads(SPILLOVER.read_text(encoding="utf-8"))
    by_species = {r["species"]: r for r in spill["rankings"]}
    joined = 0
    for rec in records:
        hit = by_species.get(rec["species"])
        if hit:
            rec["spillover"] = {"score": hit["score"], "rank": hit["rank"]}
            joined += 1
    if joined != spill["count"]:
        raise SystemExit(f"spillover join matched {joined} of {spill['count']} rankings")

    records.sort(key=lambda r: (r["name"] or "").lower())
    return records


# ------------------------------------------------------------------- the facts

def summarize(records):
    years = [r["year"] for r in records if r["year"]]
    levels = collections.Counter(r["transmissionLevel"] for r in records if r["transmissionLevel"])
    families = collections.Counter(r["family"] for r in records if r["family"])
    genomes = collections.Counter(r["genome"] for r in records if r["genome"])
    regions = collections.Counter(r["region"] for r in records if r["region"])
    routes = collections.Counter()
    for r in records:
        for k, v in r["routes"].items():
            if v:
                routes[k] += 1
        if r["vector"]:
            routes["Vector"] += 1
    hosts = collections.Counter()
    for r in records:
        for k, v in r["hosts"].items():
            if v:
                hosts[k] += 1

    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    return {
        "generated": datetime.date.today().isoformat(),
        "source": source,
        "counts": {
            "species": len(records),
            "families": len(families),
            "genera": len({r["genus"] for r in records if r["genus"]}),
            "countries": len({r["country"] for r in records if r["country"]}),
            "regions": len(regions),
            "genomeTypes": len(genomes),
        },
        "years": {"earliest": min(years), "latest": max(years), "missing": len(records) - len(years)},
        "levels": dict(sorted(levels.items())),
        "levelLabels": LEVEL_LABEL,
        "families": dict(families.most_common()),
        "genomes": dict(genomes.most_common()),
        "regions": dict(regions.most_common()),
        "routes": dict(routes.most_common()),
        "hosts": dict(hosts.most_common()),
        "gaps": {
            "noSequenceId": sum(1 for r in records if not r["seqId"]),
            "noTransmissionRoute": sum(1 for r in records if not any(r["routes"].values()) and not r["vector"]),
            "noHostCategory": sum(1 for r in records if not any(r["hosts"].values())),
            "noSpilloverScore": sum(1 for r in records if "spillover" not in r),
            "sourceMarked": sum(1 for r in records if r["sourceMarked"]),
            "sharedCoordinates": sum(
                n for n in collections.Counter(
                    (r["lat"], r["lon"]) for r in records if r["lat"] is not None).values() if n > 1),
        },
        "spillover": json.loads(SPILLOVER.read_text(encoding="utf-8"))["note"],
        "normalization": dict(sorted(REPORT.items())),
    }


# ----------------------------------------------------------------- the page

def e(s):
    return html.escape("" if s is None else str(s), quote=True)


def n(v):
    return f"{v:,}"


def fill(template, mapping):
    def sub(m):
        key = m.group(1)
        if key not in mapping:
            raise KeyError(f"no value for placeholder {{{{{key}}}}}")
        return str(mapping[key])
    return re.sub(r"\{\{(\w+)\}\}", sub, template)


def facts_table(meta):
    """The catalogue's shape, as a table the page prints before any script runs."""
    rows = []
    for label, pairs in (
        ("Genome type", meta["genomes"].items()),
        ("Region of first report", meta["regions"].items()),
    ):
        items = " · ".join(f"{e(k)} <b>{n(v)}</b>" for k, v in pairs)
        rows.append(f"<tr><th scope=\"row\">{label}</th><td>{items}</td></tr>")
    levels = " · ".join(
        f'{e(k)} <b>{n(v)}</b>' for k, v in sorted(meta["levels"].items()))
    rows.append(f'<tr><th scope="row">Transmission level</th><td>{levels}</td></tr>')
    routes = " · ".join(f"{e(k)} <b>{n(v)}</b>" for k, v in meta["routes"].items())
    rows.append(f'<tr><th scope="row">Transmission route</th><td>{routes}</td></tr>')
    hosts = " · ".join(f"{e(k)} <b>{n(v)}</b>" for k, v in meta["hosts"].items())
    rows.append(f'<tr><th scope="row">Host range</th><td>{hosts}</td></tr>')
    return "\n          ".join(rows)


def level_list(meta):
    out = []
    for key, label in sorted(meta["levelLabels"].items()):
        count = meta["levels"].get(key, 0)
        text = label.split("—", 1)[1].strip()
        out.append(f'<li><b>Level {e(key)}</b> ({n(count)} species) — {e(text)}</li>')
    return "\n            ".join(out)


def gaps_list(meta):
    g = meta["gaps"]
    total = meta["counts"]["species"]
    return "\n            ".join([
        f'<li><b>{n(g["noSequenceId"])}</b> of {n(total)} records carry no reference sequence accession.</li>',
        f'<li><b>{n(g["noTransmissionRoute"])}</b> have no transmission route recorded, which means the source '
        f'found no evidence to record, not that no route exists.</li>',
        f'<li><b>{n(g["noHostCategory"])}</b> have no host category recorded.</li>',
        f'<li><b>{n(g["noSpilloverScore"])}</b> have no SpillOver risk score, because SpillOver ranks a '
        f'different set of viruses; <b>{n(total - g["noSpilloverScore"])}</b> do.</li>',
        f'<li><b>{n(g["sourceMarked"])}</b> carry at least one cell the source marks with an asterisk. The '
        f'mark appears on both yes and no values and the dataset does not define it, so each value is read '
        f'as it stands and the mark is kept alongside it.</li>',
        f'<li><b>{n(g["sharedCoordinates"])}</b> records sit on coordinates shared with at least one other '
        f'record, so the first-report locations are not plotted on a map.</li>',
    ])


def jsonld(meta):
    s = meta["source"]
    doc = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Human-Infective RNA Viruses",
        "description": (
            f'A searchable atlas of the {n(meta["counts"]["species"])} RNA virus species known to infect '
            f'humans, with ICTV taxonomy, transmission level and route, host range, and first-report year '
            f'and place, covering {meta["years"]["earliest"]} to {meta["years"]["latest"]}.'),
        "url": SITE_URL,
        "creator": {"@type": "Person", "name": AUTHOR, "url": AUTHOR_URL},
        "isBasedOn": f"https://doi.org/{s['doi']}",
        "citation": ("Zhang F, Lu L, Brierley L, Hietanen H, Woolhouse MEJ. A complete catalogue of "
                     "human-infective RNA viruses. Scientific Data. 2026;13:981. "
                     "doi:10.1038/s41597-026-07281-5"),
        "license": s["license_url"],
        "temporalCoverage": f'{meta["years"]["earliest"]}/{meta["years"]["latest"]}',
        "dateModified": meta["generated"],
        "isAccessibleForFree": True,
        "variableMeasured": [
            {"@type": "PropertyValue", "name": k}
            for k in ("ICTV species", "ICTV genus", "ICTV family", "Genome type", "Envelope",
                      "Transmission level", "Transmission route", "Host range",
                      "Year of first report", "Country of first report")
        ],
    }
    return json.dumps(doc, ensure_ascii=False, indent=2)


def render(records, meta):
    t = TEMPLATE.read_text(encoding="utf-8")
    c, y, s = meta["counts"], meta["years"], meta["source"]
    description = (
        f'A free, searchable atlas of the {n(c["species"])} RNA virus species known to infect humans: '
        f'ICTV taxonomy, transmission level and route, host range, and where and when each was first '
        f'reported, from {y["earliest"]} to {y["latest"]}.')
    return fill(t, {
        "title": f'Human-Infective RNA Viruses — all {n(c["species"])} species, searchable',
        "description": e(description),
        "og_description": e(description),
        "canonical": SITE_URL,
        "author": AUTHOR,
        "jsonld": jsonld(meta),
        "species": n(c["species"]),
        "families": n(c["families"]),
        "genera": n(c["genera"]),
        "countries": n(c["countries"]),
        "genome_types": n(c["genomeTypes"]),
        "year_first": str(y["earliest"]),
        "year_last": str(y["latest"]),
        "facts_rows": facts_table(meta),
        "level_list": level_list(meta),
        "gaps_list": gaps_list(meta),
        "source_doi": e(s["doi"]),
        "source_version": str(s["version"]),
        "source_license": e(s["license"]),
        "source_license_url": e(s["license_url"]),
        "source_retrieved": e(s["retrieved"]),
        "generated": meta["generated"],
        "v": meta["generated"].replace("-", ""),
    })


def write_sitemap(meta):
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{SITE_URL}</loc><lastmod>{meta['generated']}</lastmod>"
        "<changefreq>yearly</changefreq><priority>1.0</priority></url>\n"
        "</urlset>\n", encoding="utf-8")


def write_llms(meta):
    c, y, s = meta["counts"], meta["years"], meta["source"]
    scored = n(c["species"] - meta["gaps"]["noSpilloverScore"])
    levels = "\n".join(
        f'- Level {k}: {n(meta["levels"].get(k, 0))} species — '
        f'{v.split("—", 1)[1].strip()}'
        for k, v in sorted(meta["levelLabels"].items()))
    families = "\n".join(f"- {k}: {n(v)} species" for k, v in list(meta["families"].items())[:12])
    (ROOT / "llms.txt").write_text(f"""# Human-Infective RNA Viruses

> A searchable atlas of the {n(c["species"])} RNA virus species with documented human infection,
> built from the open catalogue of Zhang et al. Each record carries ICTV taxonomy, transmission
> level, transmission routes and vector, host range, and the year and country of the first
> reported human infection. First reports span {y["earliest"]} to {y["latest"]}.

Site: {SITE_URL}
Maintainer: {AUTHOR} ({AUTHOR_URL})
Source repository: https://github.com/phagehunter/human_infective_rna_viruses
Page built: {meta["generated"]}

## The data

Every record derives from one upstream release, committed to the repository unchanged:

- Dataset: Zhang F, Lu L, Brierley L, Hietanen H, Woolhouse MEJ. Human-infective RNA virus
  database. figshare, version {s["version"]}. doi:{s["doi"]}. Licensed {s["license"]}.
- Paper: Zhang F, Lu L, Brierley L, Hietanen H, Woolhouse MEJ. A complete catalogue of
  human-infective RNA viruses. Scientific Data. 2026;13:981. doi:10.1038/s41597-026-07281-5
- Risk scores: SpillOver: Viral Risk Ranking (spillover.global), covering {scored} of these species.

Anyone citing the catalogue should cite Zhang et al., not this site.

## Shape of the catalogue

- {n(c["species"])} species across {n(c["families"])} families and {n(c["genera"])} genera
- {n(c["countries"])} countries of first report, {n(c["genomeTypes"])} genome types
- First human reports from {y["earliest"]} to {y["latest"]}

### Transmission level

The level describes how far a virus travels between people. It is not a severity scale.

{levels}

### Largest families

{families}

## Limits a reader should know

- The catalogue records human infection, not disease burden, severity or current circulation.
- A blank transmission route or host means no recorded evidence, not evidence of absence.
- {n(meta["gaps"]["noSequenceId"])} records carry no reference sequence accession.
- {n(meta["gaps"]["noSpilloverScore"])} records have no SpillOver risk score.
- {n(meta["gaps"]["sourceMarked"])} records carry a cell the source marks with an asterisk whose
  meaning the dataset does not define; the value is shown as recorded and the mark is kept.
- Coordinates are the locality of first report and are not plotted, because
  {n(meta["gaps"]["sharedCoordinates"])} records share a point with at least one other.

See DATA.md in the repository for the checksum, the normalization report and the full provenance.
""", encoding="utf-8")


# ---------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true",
                    help="print the normalization report and write nothing")
    args = ap.parse_args()

    records = build_records()
    meta = summarize(records)

    print(f'{meta["counts"]["species"]} species, {meta["counts"]["families"]} families, '
          f'{meta["counts"]["genera"]} genera, {meta["counts"]["countries"]} countries, '
          f'first reports {meta["years"]["earliest"]} to {meta["years"]["latest"]}')
    print("transmission levels:", ", ".join(f"{k} {v}" for k, v in sorted(meta["levels"].items())))
    print("normalization applied:")
    for k, v in sorted(REPORT.items()):
        print(f"  {v:4}  {k}")
    print("gaps:", ", ".join(f"{k} {v}" for k, v in meta["gaps"].items()))

    if args.report:
        return

    (ROOT / "data" / "viruses.json").write_text(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (ROOT / "data" / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ROOT / "index.html").write_text(render(records, meta), encoding="utf-8")
    write_sitemap(meta)
    write_llms(meta)

    for p in ("data/viruses.json", "data/meta.json", "index.html"):
        print(f"  wrote {p:20} {(ROOT / p).stat().st_size / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
