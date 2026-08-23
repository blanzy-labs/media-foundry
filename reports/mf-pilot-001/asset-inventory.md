# MF-PILOT-001 Asset Inventory

## Discovery scope

Read-only discovery covered the Media Foundry repository, sibling project repositories under `/home/blanzy/projects`, and clearly named local files in `/home/blanzy/Downloads`. Arbitrary web retrieval was not used.

## Books

Discovered authentic cover candidates:

- `Dark Signal Upscale 1.png` — 1920×2571, visible title “Dark Signal,” Book Two of The Second Presence Trilogy, Robert Blanzy.
- `Final Override Upscale 1.png` — 1920×2571.
- `Unknown Process Cover (2).png` — 2048×3072.

Selected: **Dark Signal**, because its cover visibly establishes the real title, series, book number, and author while remaining readable in contain mode.

Imported copy: `media/images/books-dark-signal.png`
SHA-256: `4546678c906bb0a6065c25a5d61da76a5bd89bfcd02e3fa13b2a0aebb0ce7af5`

## Turd Burglar

The `/home/blanzy/projects/turd-burglar` repository contains source code/scenes but no committed PNG/JPEG/WebP/video assets. No local gameplay clip was found.

A clearly named local `tburgs.png` asset was discovered at 1672×941. Visual inspection confirmed Turd Burglar branding, gameplay environment, player character, HUD, objective, score, controls, and in-world action.

Selected: **tburgs.png**, as the best available authentic gameplay promotional screenshot.

Imported copy: `media/screenshots/turd-burglar-gameplay.png`
SHA-256: `c88faab6a331679b62c344b08a7e84f067965d38e5601e4e1a30c1c744967abe`

## Mythadis

The local `mythadis-site` repository contains authentic current-state, proof, field-report, homepage, design-study, mobile, desktop, and social-card screenshots. No exported Mission Control, Operator, or application screenshot was found.

Candidates inspected included the Current State page, Field Report 001, and `public/mythadis-social-card.png`. The long website captures became too dense or misleading when reduced to the media slot.

Selected: **mythadis-social-card.png** (1200×630), because it is approved project artwork, remains recognizable at phone scale, and contains the established wording “coordinate intelligence—not just computation.” It is explicitly described as approved project artwork, not an application screenshot.

Imported copy: `media/screenshots/mythadis-social-card.png`
SHA-256: `5a05967c156a0e11945554dc10d33e02310882d4219e7dfbe3132e75595c7fb1`

## Preservation

Original sources were not overwritten. Imported copies are byte-identical to the selected originals, as shown by matching SHA-256 values. Each production fixture records `project_asset` provenance and its source hash.
