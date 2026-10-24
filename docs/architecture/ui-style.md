# Mechy app visual style

Distilled from the team's UI inspiration (four images: a Dyson-swarm orbital diagram poster, a "Sensorium" business card on a hairline grid, an "Architect Labs" dark spec poster, and an engineering dimension drawing of a phone). The images themselves are third-party and are not stored in the repo.

## The feel

An engineering drawing sheet, not a SaaS dashboard. Monochrome, hairline lines, monospace annotations, lots of empty paper. Pictures carry the meaning; text is small labels on the drawing.

## Tokens

| Token | Light ("paper") | Dark ("graphite") |
|---|---|---|
| background | `#ECECEA` warm light grey paper | `#222222` |
| surface (panel) | `#F5F5F3` | `#2A2A2A` |
| ink (lines, primary text) | `#1C1C1C` | `#EDEDED` |
| ink-muted | `#6B6B6B` | `#9A9A9A` |
| grid line | `#1C1C1C` at 10% | `#FFFFFF` at 10% |
| grid dot | `#1C1C1C` at 12% | `#FFFFFF` at 12% |
| accent (rare: selection, live state) | `#20A4F3` (Mechy blue) | `#20A4F3` |
| danger / good | `#C8102E` / `#1E7F4F`, used only in result charts | same |

- No gradients, no shadows, no rounded "cards". Corner radius 0 to 2 pt.
- Lines: 0.5 to 1 pt hairlines. Dashed lines (4/4) for predicted, planned or "ghost" things (predicted ball path, unchosen variants, pending tasks). Solid for actual.
- Arrowheads are small filled triangles.

## Type

- Labels, numbers, annotations, buttons: a monospace, uppercase for small labels with wide tracking (SF Mono / `.monospaced` design; JetBrains Mono or IBM Plex Mono if bundled later).
- Titles and the few sentences: a neutral grotesk (Inter, already used by the landing page, or SF Pro).
- Superscript-style tags like `R¹²`, `F¹⁵·⁸` for annotation of parameters and versions (e.g. `V³` for variant 3, `T¹⁴` for task 14).
- Boxed labels: text inside a thin 1 pt rectangle, used for panel titles and key callouts ("SUN" box in the inspo).

## Layout

- The canvas is a drafting sheet: a fine dot grid plus a coarser square-node grid (small hollow squares at intersections every 8 grid units, as in the orbital poster).
- Panels are frames on the sheet: 1 pt ink border, a title block strip at the bottom-right like a drawing's title block (panel name, variant, scale/date in mono), no window chrome beyond that.
- Dimension lines with values for key numbers on CAD and results (reach, link lengths, catch rate) instead of separate text tables where possible.
- Numbered note boxes (`[1] [2] [3]`) for agent notes and questions, like the NOTES list on the drawing.
- Dark mode follows the Architect Labs poster: graphite background, light hairlines, uppercase mono lists.

## 3D viewer

- Background = paper colour with the same grid; model rendered as flat light-grey surfaces with black edge outlines (three.js `EdgesGeometry` + `LineSegments`), like a technical illustration. Toggle to a shaded mode.
- Ghost/dashed rendering for alternative variants and predicted trajectories.
