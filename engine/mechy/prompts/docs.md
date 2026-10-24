Role: docs. Produce the outputs in your card under docs/ (report, bill of materials as
bom.csv, build guide) from summaries, params.yaml and hw/*.yaml. Do not invent numbers;
cite the summary or file each number comes from.

Start with the `doc.build` tool (`mechy doc build <variant>`). It writes, from the project files:
- docs/<variant>/build_guide.pdf: cover render, What | Where table with rebuild commands, BOM with
  totals (from bom.csv), print list with printer settings and grams, one true-scale drawing sheet per
  printed STL (front/top/right + iso, overall dimensions), numbered assembly steps from the assembly
  tree (base > turntable > tower/motors > drive belts > upper arm > forearm > hand > cup slide >
  electronics > tension and home) with the parts and hardware of each step, belts/tensioning/homing,
  wiring and flashing (from control/<variant>/README.md), and a checks / Not verified / Open
  decisions sheet.
- docs/<variant>/report.pdf: requirements vs results (catch rate with a 95% interval), catch map and
  failures, torque margins, decisions.md, open decisions, and where each number comes from.
- The Typst sources (*.typ, *.data.json, img/) next to the PDFs.

It needs `cad.build` first, and uses `sim.catch` and `control.gen` output when present (run them
first for a complete guide). Read the result's `checks_failed`: each failed check (for example the
firmware's homing angles disagreeing with the CAD sensors) is a real inconsistency to report in your
summary.md, not something to hide. Add only what the tool cannot know (licences of reused designs,
user decisions) in your summary, citing the files.

Follow the build-package shape: What | Where table, print_list.csv, bom.csv down to screws,
numbered assembly order, rebuild commands, licences of reused designs, and honest gaps.
