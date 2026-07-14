# Human Virus Database

A free, searchable, mobile- and desktop-friendly atlas of human-infective viruses.

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

## Data sources

- **Zhang et al.** — Human-infective RNA virus database (taxonomy, transmission, host range, discovery data)
- **SpillOver: Viral Risk Ranking** — [spillover.global](https://spillover.global) (spillover risk scores)
- **WHO** — Pathogens prioritization for research and development
- **CEPI 3.0 Strategy** — pandemic preparedness context

For research and educational use. Data is provided "as is" and may contain errors; confirm against primary literature before relying on it. Not medical advice.
