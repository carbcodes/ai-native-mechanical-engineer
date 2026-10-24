# reference_designs

A catalogue of open-source mechanisms that Mechy agents can adapt (see `prompts/_standards.md` rule 1).
Compiled on 2026-10-23. Each licence was read from the repository's actual LICENSE file through the GitHub API, not from GitHub's SPDX guess.

## Files

| File | Contents |
|---|---|
| `designs.csv` | 43 rows, one per design, 37 columns (listed below). |
| `designs/<id>.json` | 43 files. Same fields as the CSV, plus GitHub SPDX, a count of file extensions in the repo tree, the repo description and a `units` map. |
| `raw/<id>/` | Small BOMs, URDF/xacro and MJCF files (each under 100 kB), with the project's LICENSE file next to them. Only taken from licences that allow redistribution: MIT, Apache-2.0, BSD-3, GPL, CERN-OHL or CC BY-SA. |
| `raw/_github_meta/*.json` | Snapshots of GitHub metadata: stars, forks, last push, SPDX, the first 600 characters of the licence, the file-extension histogram and key files. |
| `build_catalogue.py` | Regenerates the CSV and JSONs from the hand-compiled records plus `_github_meta`. The records live in this script, so edit them here. |
| `check.py` | Validator (stdlib only). Run `python3 -I check.py`; it prints PASS or FAIL. |

Columns: id, name, category, repo_url, docs_url, licence, licence_file, licence_notes, reuse, dof, reach_mm,
payload_claimed_kg, payload_measured_kg, mass_kg, repeatability_mm, payload_note, motors, drivers, reductions, bearings,
materials, bom_cost_value, bom_cost_currency, bom_cost_note, cad_formats, urdf, mjcf, github_stars, github_forks, last_push,
maturity, known_weaknesses, mechy_use, raw_files, source_url, value_type, checked_date.

Categories: robot_arm (10), gripper (5), legged (5), actuator_* (12: qdd, driver, cycloidal, capstan, planetary, harmonic),
motion_corexy/cartesian/cnc (7), pan_tilt (1), launcher (1), catcher (1), conveyor (1 gap row).

`reuse` flags:
- `yes_permissive`: MIT, Apache-2.0, BSD or CC BY.
- `yes_copyleft`: GPL or CERN-OHL-S. Derivatives must keep the same licence.
- `yes_sharealike`: CC BY-SA.
- `non_commercial_only`: Yale OpenHand (CC BY-NC 3.0) and MPCNC (CC BY-NC-SA 4.0).
- `reference_only`: no LICENSE file, which means all rights reserved. Do not copy these files.
- `software_only`: only the code is open.

`value_type`:
- `datasheet`: the numbers were read from the project's own repo or docs in this session.
- `estimate`: the row contains numbers from the compiler's memory, or derived numbers. Fields that hold such numbers say "(from memory)".

## Licence findings worth knowing
- **Faze4**: the LICENSE file is CERN-OHL-S-2.0, but the README says MIT. Treat it as CERN-OHL-S.
- **AR4**: the download page states no licence, and "AR4" is a trademark. Only the community ROS2 driver/URDF (MIT) is clearly reusable.
- **Arctos**: the full CAD is sold. Only the ROS packages, URDF and meshes are MIT.
- **OpenTorque**: GitHub shows NOASSERTION, but the file is CC BY-SA 4.0. **Voron Trident**: the API shows no licence, but the file is GPL-3.0.
- **Prusa i3 MK3S**: the repo's LICENSE file is GPL v2.
- **Mini Cheetah**: only the software (MIT) is released. There is no official mechanical CAD.
- **No licence (reference only)**: Aaed Musa's cycloidal and capstan drives, both printed strain-wave repos, SimpleCore, the Stanford Pupper docs repo, and the BJR hardware.

## Sources
GitHub repos (the URLs are in the CSV), anninrobotics.com, docs.openarm.dev, thor.angel-lm.com (BOM, FAQ), arctosrobotics.com,
the PAROL-docs GitHub repo, the Faze4 docs `.rst` files on GitHub, pupper.readthedocs.io and open-dynamic-robot-initiative.github.io.
docs.source-robotics.com was blocked by the network, so the GitHub docs repo was used instead.

## Gaps / not verified
- **Conveyors**: no reputable open design was found (GitHub has only 0-1 star student projects). That row is a placeholder.
- **Catchers and launchers**: there are only small research repos (AIMY, BJR). Mechy will mostly need its own design here.
- **Harmonic drives**: no well-licensed printed strain-wave design was found.
- **Measured payloads**: these are rare. Only Thor (750 g, by the author), the pan-tilt (~1 kg) and WOLF (90 Nm tested peak) report tested values. Every other payload is a vendor claim or is missing.
- **Numbers from memory, not checked this session**: Solo12 mass and actuator (MN4004, 9:1 belt), Mini Cheetah (9 kg, 6:1), moteus/ODrive ratings, Voron/Prusa build volumes and parts, and PrintNC parts. All are marked `estimate`.
- **Not read**: AR4 per-axis ratios and bearings (in the build manual PDF), Thor bearings, OpenArm reach and mass (shown only in images), the SSG-48 motor model and the PAROL6 kit price.
- **BOM costs**: these are from the projects' own pages and change over time. There is no currency normalisation (USD and EUR are both used).
- **Stars and activity**: a snapshot on 2026-10-23.
