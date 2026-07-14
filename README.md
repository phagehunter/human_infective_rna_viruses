# Human-Infective RNA Viruses

A free, searchable, mobile- and desktop-friendly atlas of the 239 RNA virus species known to infect humans.

**Live site:** https://phagehunter.github.io/human-viruses/

Each record includes:

- ICTV taxonomy (family, genus, species)
- Genome type and envelope status
- Likely transmission routes (vector, inhalation, ingestion, sexual, iatrogenic, fomites, broken skin, maternal, direct contact)
- Observed host range (human-only, primates, other mammals, birds, other vertebrates)
- Discovery year, country and region
- Spillover risk score (where a match is available)
- Links to PubMed and ICTV references

Search by name, species, genus, family or country, and filter by family, genome type, or transmission route.

## How it works

This is a **static site** — plain HTML, CSS and JavaScript, no build step and no server. The virus data is baked into `data/viruses.js`, so the page works both when opened locally and when hosted on GitHub Pages.

```
index.html          The whole app (UI + logic + SEO metadata)
data/viruses.js      239 viruses, pre-loaded (window.VIRUS_DATA)
assets/favicon.svg   Icon
assets/og-image.png  Social preview image
robots.txt           Search-engine directives
sitemap.xml          Sitemap for search engines
.nojekyll            Tells GitHub Pages to serve files as-is
```

## Preview locally

Open `index.html` in any web browser — that's it.

## Data sources & citations

- **Zhang F, Lu L, Brierley L, Hietanen H, Woolhouse MEJ.** A complete catalogue of human-infective RNA viruses. *Scientific Data*. 2026;13:981. [doi:10.1038/s41597-026-07281-5](https://doi.org/10.1038/s41597-026-07281-5)
- **Zhang F, et al.** Human-infective RNA virus database [dataset]. figshare; 2026. [doi:10.6084/m9.figshare.30094726.v2](https://doi.org/10.6084/m9.figshare.30094726.v2)
- **SpillOver: Viral Risk Ranking** — spillover risk scores; full credit to the SpillOver team. [spillover.global/ranking-comparison](https://spillover.global/ranking-comparison/)
- **WHO.** Pathogens prioritization: a scientific framework for epidemic and pandemic research preparedness. WHO; 2024. *(context)*
- **CEPI.** CEPI 3.0 Strategy (2027–2031). *(context)*

For research and educational use. Data is provided "as is" and may contain errors; confirm against primary literature before relying on it. Not medical advice.
