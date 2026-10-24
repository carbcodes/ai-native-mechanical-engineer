Mechy engineering standards (every agent follows these):

1. Start from what already works. Before inventing geometry, look for proven open-source
   designs (robot arm kits, published catchers, Thingiverse/Printables/GitHub projects) and
   adapt the closest one. Keep vendor files as untouched originals in research/<topic>/vendor/
   and edit copies. Credit the licence (e.g. CC BY 4.0, author) in the note.
2. Offer real alternatives, anchored on the conventional answer. The first option is the
   proven, conventional mechanism built on an open-source base (for an arm: a regular
   articulated or parallel-linkage robot arm). Add 1 to 2 genuinely different concepts only as
   alternatives, and compare all of them in a numbers-backed option table. Let the user pick
   before heavy CAD work; never commit to an unusual concept on your own.
3. Keep mass off moving distal links. Motors sit at the base and drive joints by belt or
   linkage; estimate the payload cost of any motor placed on a moving link.
4. Use real parts. Name bearings (608-2RS, F624ZZ, 51105 thrust...), shafts, belts (GT2 with
   tooth counts and closed-loop length), pulleys, extrusions (2020), fasteners (M3x10...),
   homing sensors, supply voltage and current. Every printed part gets a material and print
   orientation. Check torque budget = motor torque x ratio x safety factor (50%) per joint.
5. Verify before deciding. Any new analysis is checked against a closed-form or published
   result before it drives a decision, and the note contains a verification table:
   | Check | Expected | Got | PASS/FAIL |. Random-pose checks (e.g. 500 poses) beat one pose.
6. Label estimates. Every number is either measured, from a datasheet (cite it), computed
   (say how), or an estimate (say "estimate"). Placeholder data is labelled as such wherever
   it is shown, not only in a comment.
7. Be honest about gaps. Every summary ends with "Not verified" and "Open decisions" lists.
8. Make it buildable. A finished design has: STLs (one per printed part), print_list.csv
   (part, qty, material, orientation, est. grams), bom.csv (every purchased part incl.
   screws, with qty and a source), an assembly order, and a rebuild command for each artifact.
9. Write notes people can scan. Open each note/summary with a | What | Where | table of the
   files it produced, then the decision, then numbers. SI units internally; convert only at
   the user-facing boundary.
10. Always produce something the user can look at (a render, a GLB in the CAD viewer, a plot)
    with every design result, so they can judge it at a glance.
11. Treat short, blunt user feedback ("this looks bad, I want X") as a change of direction:
    record it in decisions.md, drop the rejected approach, and re-plan rather than patch.
