# Where the data comes from and what was done to it

The catalogue on this site is not typed by hand and not edited by hand. It is
derived from one upstream release by one script, and every number printed on
the page is computed from that derivation at build time.

## The source

| | |
|---|---|
| Dataset | Zhang et al. — Human-infective RNA virus database |
| Authors | Feifei Zhang, Lu Lu, Liam Brierley, Helmi Hietanen, Mark E.J. Woolhouse |
| DOI | [10.6084/m9.figshare.30094726.v2](https://doi.org/10.6084/m9.figshare.30094726.v2) |
| Version | 2, published 19 February 2026 |
| License | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| File | `Zhang et al. - Human-infective RNA virus database.xlsx`, 150,945 bytes |
| MD5 | `4364e74b65441d18d2318ece3cd0267e` |
| Retrieved | 24 October 2026 |

Companion paper: Zhang F, Lu L, Brierley L, Hietanen H, Woolhouse MEJ. A
complete catalogue of human-infective RNA viruses. *Scientific Data*.
2026;13:981. [doi:10.1038/s41597-026-07281-5](https://doi.org/10.1038/s41597-026-07281-5)

The workbook is committed unchanged at
`data/raw/zhang-human-infective-rna-viruses-v2.xlsx`. CC BY 4.0 permits that,
and a 147 KB file makes the build reproducible without a network round trip.
`fetch_data.py` re-downloads it and refuses to proceed if the checksum has
moved, which is what a new upstream version looks like.

Risk scores in `data/spillover.json` come from the SpillOver: Viral Risk
Ranking project and are joined to the catalogue by ICTV species name. SpillOver
ranks a different set of viruses, so most species here carry no score. The date
those scores were retrieved was not recorded by the earlier version of this
site, so it is not claimed.

## What the build changes, and why

`build.py` reads the workbook and writes `data/viruses.json`. Every change it
makes is counted and reported, and the counts are written to
`data/meta.json` under `normalization` so they can be checked against this
file.

| Change | Records |
|---|---|
| Leading or trailing whitespace trimmed from the common name | 71 |
| Whitespace trimmed from the vector order | 55 |
| Left-to-right mark (U+200E) removed from the vector order | 13 |
| Whitespace trimmed from the ICTV species | 2 |
| Whitespace trimmed from the discovery country | 1 |

These are artifacts of the upstream spreadsheet, not errors in the science. The
underlying values are untouched.

The literal strings `None`, `NA` and empty cells all become a real absence, so
that a missing value reads as missing everywhere rather than as the word
"None".

## The asterisk

The source marks some cells with a trailing asterisk: transmission levels,
vector flags, vector orders, transmission routes and host categories. It
appears on both yes and no values, and the dataset does not define what it
means.

This site reads the underlying value as it stands and keeps the mark alongside
it. Each record lists the marked fields in `sourceMarked`, the detail panel
prints an asterisk beside those values, and a note says the mark is not
interpreted. 48 of the 239 species carry at least one.

This matters because the previous version of this site did the opposite. It
treated an asterisked value as unreadable and stored zero, which had three
visible consequences:

- **45 species showed no transmission route at all.** Their only recorded
  routes were marked ones, so every route was zeroed. Achimota virus 2, for
  one, records inhalation and direct contact in the source and showed neither.
- **9 species showed no host category** for the same reason.
- **60 species had their transmission level stored as `0`.** Levels `4a` and
  `4b` both collapsed to zero, which inverted the scale: the viruses that
  transmit most readily between people looked like the ones that transmit
  least. Nothing on the old page displayed the field, so the error was
  invisible on screen and wrong in the data file.

## Transmission level

The level says how far a virus is known to travel between people. It is not a
severity scale. A level 2 virus can be lethal and a level 4b virus can be mild.

| Level | Meaning | Species |
|---|---|---|
| 2 | Limited onward transmission between humans | 147 |
| 3 | Longer chains of transmission between humans | 32 |
| 4a | Sustained human-to-human transmission, with an animal reservoir | 36 |
| 4b | Sustained human-to-human transmission, no animal reservoir needed | 24 |

## What is absent

Counted from the data at build time and printed on the page:

- 32 of 239 records carry no reference sequence accession.
- 206 have no SpillOver risk score, because SpillOver covers a different set.
- 48 carry at least one asterisked cell.
- 65 sit on coordinates shared with at least one other record.

Latitude and longitude are kept in `data/viruses.json` because the source
carries them, and are not plotted. They are the locality of first report, and
with 65 records sharing points, a map of them would imply a precision the data
does not have.

A blank transmission route or host category means the source recorded no
evidence, not that none exists.

## Rebuilding

```bash
python3 fetch_data.py       # only to pick up a later upstream version
python3 build.py            # normalize the data and render index.html
python3 build.py --report   # print the normalization report, write nothing
```

Standard library only. The workbook is read by a small reader inside
`build.py`; no spreadsheet package is required.
