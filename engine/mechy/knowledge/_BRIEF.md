# Brief for knowledge-base research agents

Mechy is an AI engineering app: LLM agents (planner, research, concept, cad, sim, controls, docs) design
buildable mechanisms (e.g. 3D-printed robot arms with belts, bearings, steppers). See
engine/mechy/prompts/_standards.md for how they work. You are building a reference file those agents
will read before designing. Make it the thing a senior engineer wishes a junior had memorised.

Rules:
1. Research the web broadly (standards bodies, university course notes like MIT OCW, manufacturer
   datasheets/app notes, respected handbooks and textbooks, engineering forums). Cross-check numbers
   across at least two sources when they drive design decisions.
2. Write in your own words. Do NOT paste copyrighted text or reproduce tables wholesale from books like
   Machinery's Handbook or Shigley; summarise principles, give typical values with the source cited.
   Freely licensed or public-domain data (government, open standards summaries, datasheets) can be
   tabulated with citation.
3. Optimise for an LLM agent acting on it: rules of thumb, formulas (with units and variable meanings),
   typical numeric values/ranges, decision tables ("use X when..."), checklists, common mistakes,
   and worked mini-examples. Prefer SI units. Label each number as typical/estimate and cite a source.
4. End with: "Canonical references" (books, free courses, standards, sites — with URLs, noting which are
   free) and "Gaps / not verified".
5. Output: ONE markdown file at the path given in your task, ~600–1500 lines, scannable headings.
   Do not edit any other files. Do not commit. Reply with a 5-line summary of what you covered.
