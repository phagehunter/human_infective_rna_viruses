# Human-Infective RNA Viruses

A free, searchable atlas of the 239 RNA virus species known to infect humans.

**Live site:** <https://curtishoffmann.com/human_infective_rna_viruses/>

Every record carries ICTV taxonomy, genome type and envelope status, the
transmission level, the documented transmission routes and arthropod vector,
the observed host range, where and when human infection was first reported, the
cited literature, and a SpillOver risk score where one exists. Search by name,
species, genus, family or country, and filter by family, genome type,
transmission route or transmission level.

The catalogue comes from Zhang and colleagues and is released under CC BY 4.0.
See [DATA.md](DATA.md) for the source, the checksum, and a full account of what
the build changes and why.

## How it works

```
fetch_data.py         Downloads the upstream workbook and verifies its checksum
build.py              Normalizes the workbook into data/ and renders index.html
src/template.html     The page, with placeholders for every computed number
data/raw/             The upstream workbook, committed unchanged
data/source.json      Provenance of that file: DOI, version, license, checksum
data/spillover.json   SpillOver risk scores, joined by ICTV species name
data/viruses.json     The normalized catalogue the page loads
data/meta.json        Counts, gaps and the normalization report, all computed
assets/styles.css     Stylesheet
assets/app.js         Search, filtering and the detail dialog
index.html            Build output; do not edit by hand
```

Standard library only, no build dependencies, no spreadsheet package and no
front-end framework. The page loads one stylesheet, one script and one JSON
file.

### Build

```bash
python3 build.py            # normalize and render
python3 build.py --report   # print the normalization report, write nothing
```

Every number the page prints is computed in `build.py` from the data: the
species, family, genus and country counts, the year range, the aggregate table,
the per-level counts and the list of what the data does not contain. Nothing
about the catalogue is typed into the template, so a later upstream release
cannot leave a stale figure behind.

### Refreshing from a new upstream release

```bash
python3 fetch_data.py --force
```

`fetch_data.py` refuses a file whose checksum does not match the version this
build was written against, and prints what it received. Check the figshare
record, update `EXPECTED_MD5`, `EXPECTED_SIZE` and `VERSION` in that script
along with the provenance block in `DATA.md`, then run `build.py` and commit
the regenerated `data/` and `index.html` together.

## Preview locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

A server is needed because the page fetches `data/viruses.json`.

## Licensing

Code is MIT. The catalogue is CC BY 4.0 from Zhang et al. and the risk scores
belong to the SpillOver project. [LICENSE](LICENSE) sets out which is which.
Anyone reusing the catalogue should cite Zhang et al. rather than this
repository.

## Sources

- **Zhang F, Lu L, Brierley L, Hietanen H, Woolhouse MEJ.** A complete catalogue of human-infective RNA viruses. *Scientific Data*. 2026;13:981. [doi:10.1038/s41597-026-07281-5](https://doi.org/10.1038/s41597-026-07281-5)
- **Zhang F, Lu L, Brierley L, Hietanen H, Woolhouse MEJ.** Human-infective RNA virus database [dataset]. figshare; version 2, 2026. [doi:10.6084/m9.figshare.30094726.v2](https://doi.org/10.6084/m9.figshare.30094726.v2)
- **SpillOver: Viral Risk Ranking.** [spillover.global/ranking-comparison](https://spillover.global/ranking-comparison/)
- **International Committee on Taxonomy of Viruses.** [ictv.global](https://ictv.global)

For research and teaching. The data may contain errors; confirm against the
cited literature before relying on it. Not medical advice, and not a statement
about any virus's current circulation or risk.
