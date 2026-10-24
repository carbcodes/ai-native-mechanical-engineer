// Design report. Data: report.data.json (written by `mechy doc build`). Compile from this folder with
// `typst compile report.typ`.
#import "mechy_sheet.typ": *
#let d = json("report.data.json")
#show: setup.with(d.meta)

#sheet("Design report " + upper(d.meta.variant), tag: d.meta.project, first: true)[
  #grid(columns: (150mm, 1fr), column-gutter: 8mm,
    {
      image(d.cover_image, width: 150mm)
    },
    {
      text(font: sans, size: 20pt, weight: "medium", d.title)
      v(5mm)
      if d.headline != none {
        let hl = d.headline
        lbl("catch rate (" + str(hl.throws) + " simulated throws, seed " + str(hl.seed) + ")")
        linebreak()
        text(font: mono, size: 30pt, pct(hl.catch_rate, d: 1))
        h(3mm)
        status(hl.status)
        linebreak()
        text(font: mono, size: 6.5pt, fill: muted)[95% interval #pct(hl.ci_low, d: 0) – #pct(hl.ci_high, d: 0) (Wilson, computed) · target #pct(hl.target, d: 0)]
        v(5mm)
      } else if d.pick != none {
        let pk = d.pick
        lbl("payload in the work zone (pick-and-place study " + pk.task + ")")
        linebreak()
        text(font: mono, size: 30pt, fmt(pk.payload_g, d: 0) + " g")
        h(3mm)
        if pk.meets { status("PASS") } else { status("FAIL") }
        linebreak()
        text(font: mono, size: 6.5pt, fill: muted)[cycle #fmt(pk.cycle_s, d: 2) s with #fmt(pk.design_g, d: 0) g · #fmt(pk.picks_per_min, d: 0) picks/min · peak motor load #pct(pk.peak, d: 0) of pull-out]
        v(5mm)
      } else {
        notes(("No catch simulation for this variant yet: run `mechy sim catch " + d.meta.variant + "`.",))
      }
      for s in d.stats { stat(s.l, s.v, note: s.at("note", default: none)) }
      section("findings")
      notes(d.findings)
    })
]

#sheet("Requirements vs results")[
  #dtable(columns: (48mm, 34mm, 1fr, 16mm, 50mm), header: ("requirement", "target", "result", "status", "source"),
    rows: d.requirements.map(r => (r.req, r.target, r.result, status(r.status), r.source)), size: 6.3pt)
  #if d.sims.len() > 0 {
    section("catch simulations of this variant")
    dtable(columns: (30mm, 14mm, 12mm, 16mm, 16mm, 20mm, 18mm, 1fr),
      header: ("task", "throws", "seed", "catch", "reach", "skip impact", "usteps", "failures"),
      aligns: (left, right, right, right, right, right, right, left),
      rows: d.sims.map(s => (s.task, str(s.throws), str(s.seed), pct(s.catch_rate), pct(s.reach_rate),
        pct(s.skip_on_impact_rate), str(s.microsteps), s.failures)), size: 6.3pt)
  }
]

#if d.headline != none [
  #sheet("Catch map and failures", tag: d.headline.task)[
    #grid(columns: (178mm, 1fr), column-gutter: 6mm,
      image(d.figs.catch_map, width: 178mm),
      {
        section("outcomes")
        image(d.figs.failures, width: 100%)
        section("how to read")
        notes(d.catch_notes)
      })
  ]
]

#if d.pick != none [
  #sheet("Pick-and-place study", tag: d.pick.task)[
    #grid(columns: (1fr, 1fr), column-gutter: 6mm,
      image(d.figs.pick_workspace, width: 100%),
      {
        image(d.figs.pick_cycle, width: 100%)
        section("estimates")
        notes(d.pick.notes)
      })
  ]
  #sheet("Payload against reach", tag: d.pick.task)[
    #image(d.figs.pick_payload_budget, width: 100%)
  ]
]

#sheet("Torque margins", tag: "standards rule 4: holding x ratio x 50%")[
  #grid(columns: (125mm, 1fr), column-gutter: 8mm,
    {
      image(d.figs.torque, width: 125mm)
    },
    {
      dtable(columns: (16mm, 11mm, 18mm, 18mm, 15mm, 1fr),
        header: ("motor", "ratio", "static nm", "budget nm", "margin", "max deg/s"),
        aligns: (left, right, right, right, right, right),
        rows: d.torque.map(t => (t.joint, fmt(t.ratio, d: 1), fmt(t.gravity_nm, d: 3), fmt(t.budget_50pct_nm, d: 3),
          if t.margin == none { "-" } else { fmt(t.margin, d: 2) + "x" }, fmt(t.max_joint_speed_dps, d: 0))), size: 6.3pt)
      section("notes")
      notes(d.torque_notes)
    })
]

#sheet("Decisions", tag: "decisions.md")[
  #dtable(columns: (18mm, 1fr, 1fr, 34mm), header: ("date", "decision", "why", "evidence"),
    rows: d.decisions.map(x => (x.date, x.text, x.why, x.evidence)), size: 6pt)
]

#sheet("Open decisions and gaps")[
  #grid(columns: (1fr, 1fr), column-gutter: 7mm,
    {
      section("open decisions")
      notes(d.open_decisions.map(x => [#x.text #text(fill: muted, size: 6pt, font: mono)[(#x.source)]]))
    },
    {
      section("not verified")
      notes(d.not_verified.map(x => [#x.text #text(fill: muted, size: 6pt, font: mono)[(#x.source)]]))
    })
]

#sheet("Where the numbers come from")[
  #dtable(columns: (52mm, 32mm, 24mm, 1fr), header: ("quantity", "value", "label", "source"),
    rows: d.estimates.map(e => (e.quantity, e.value, status(upper(e.label)), e.source)), size: 6.3pt)
  #v(2mm)
  #notes(d.estimate_notes)
]
