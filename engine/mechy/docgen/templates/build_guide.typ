// Build guide. Data: build_guide.data.json (written by `mechy doc build`). Compile from this folder with
// `typst compile build_guide.typ` (or re-run `mechy doc build <variant>`).
#import "mechy_sheet.typ": *
#let d = json("build_guide.data.json")
#show: setup.with(d.meta)

// ------------------------------------------------------------------ cover
#sheet("Build guide " + upper(d.meta.variant), tag: d.cover.subtitle, first: true)[
  #grid(columns: (172mm, 1fr), column-gutter: 7mm,
    image(d.cover.image, width: 172mm),
    {
      text(font: sans, size: 22pt, weight: "medium", d.cover.title)
      v(1mm)
      lbl(d.cover.subtitle)
      v(5mm)
      for s in d.cover.stats { stat(s.l, s.v, note: s.at("note", default: none)) }
      v(2mm)
      section("notes")
      notes(d.cover.notes)
    })
]

// ------------------------------------------------------------------ contents + what/where
#sheet("Contents and files")[
  #grid(columns: (1fr, 1.45fr), column-gutter: 8mm,
    {
      section("contents")
      context {
        let seen = ()
        let rows = ()
        for m in query(<sheet>) {
          let t = m.value.title
          let key = t + repr(m.value.at("tag", default: none))
          if key in seen { continue }
          seen.push(key)
          rows.push((str(m.location().page()), t))
        }
        dtable(columns: (12mm, 1fr), header: ("sheet", "title"), rows: rows, size: 6.3pt)
      }
    },
    {
      section("what | where")
      dtable(columns: (40mm, 1fr, 48mm), header: ("what", "where", "rebuild"),
        rows: d.what_where.map(r => (r.what, r.where, raw(r.rebuild))), size: 6.3pt)
      section("how to read this guide")
      notes(d.reading_notes)
    })
]

// ------------------------------------------------------------------ BOM
#sheet("Bill of materials", tag: d.bom.source + " · total = sum of qty x unit price")[
  #dtable(columns: (7mm, 52mm, 9mm, 1fr, 30mm, 13mm, 14mm),
    header: ("#", "item", "qty", "spec", "source", "usd ea", "usd"),
    aligns: (right, left, right, left, left, right, right),
    rows: d.bom.rows.map(r => (str(r.line), r.item, str(r.qty), r.spec, r.source, fmt(r.unit_usd), fmt(r.ext_usd))),
    footer: ("", "TOTAL: " + str(d.bom.lines) + " LINES", str(d.bom.pieces), "pieces incl. spares; prices are estimates",
      "", "", fmt(d.bom.total_usd)),
    size: 5.9pt)
]

// ------------------------------------------------------------------ print list
#sheet("Print list", tag: d.print.source)[
  #grid(columns: (1fr, 62mm), column-gutter: 7mm,
    dtable(columns: (32mm, 9mm, 13mm, 1fr, 13mm, 15mm, 11mm),
      header: ("part", "qty", "material", "orientation", "g ea", "g total", "sheet"),
      aligns: (left, right, left, left, right, right, right),
      rows: d.print.rows.map(r => (r.part, str(r.qty), r.material, r.orientation, fmt(r.grams, d: 1),
        fmt(r.grams_total, d: 1), [#context {
          let q = query(selector(<sheet>)).filter(m => m.value.at("tag", default: none) == "part " + r.part)
          if q.len() > 0 { str(q.first().location().page()) } else { "-" } }])),
      footer: ("TOTAL", str(d.print.pieces), "", str(d.print.stls) + " STL files", "", fmt(d.print.grams, d: 1), ""),
      size: 6.2pt),
    {
      section("printer settings")
      dtable(columns: (24mm, 1fr), header: ("setting", "value"),
        rows: d.print.settings.map(s => (s.k, s.v)), size: 6.2pt)
      v(2mm)
      notes(d.print.notes)
    })
]

// ------------------------------------------------------------------ parts
#for p in d.parts [
  #sheet("Part " + p.ref, scale: p.scale, tag: "part " + p.ref)[
    #grid(columns: (190mm, 1fr), column-gutter: 6mm,
      image(p.drawing, width: 190mm),
      {
        section("part data")
        dtable(columns: (22mm, 1fr), header: ("field", "value"), rows: (
          ("file", p.stl), ("qty", str(p.qty)), ("material", p.material), ("infill", p.infill),
          ("orientation", p.orientation), ("size x y z", p.dims_mm.map(x => fmt(x, d: 1)).join(" x ") + " mm"),
          ("volume", fmt(p.volume_cm3, d: 1) + " cm3"), ("mass ea", fmt(p.grams, d: 1) + " g (estimate)"),
          ("scale", p.scale + " on A4"), ("used in", "step " + str(p.step) + ": " + p.step_title),
        ), size: 6.2pt)
        section("notes")
        notes(p.notes)
      })
  ]
]

// ------------------------------------------------------------------ assembly
#for s in d.steps [
  #sheet("Step " + str(s.n) + "  " + s.title, tag: "assembly " + str(s.n) + " / " + str(d.steps.len()))[
    #grid(columns: (if s.image != none { 148mm } else { 0mm }, 1fr), column-gutter: if s.image != none { 7mm } else { 0mm },
      if s.image != none {
        image(s.image, width: 148mm)
        v(-2mm)
        text(font: mono, size: 5.5pt, fill: muted, s.caption)
      },
      {
        if s.printed.len() > 0 {
          section("printed parts")
          dtable(columns: (1fr, 10mm), header: ("part", "qty"), aligns: (left, right),
            rows: s.printed.map(r => (r.at(0), str(r.at(1)))), size: 6.2pt)
        }
        if s.hardware.len() > 0 {
          section("hardware (screws, bearings, bought parts)")
          dtable(columns: (1fr, 10mm), header: ("item", "qty"), aligns: (left, right),
            rows: s.hardware.map(r => (r.at(0), str(r.at(1)))), size: 6.2pt)
        }
        section("do")
        steps-list(s.instructions)
      })
  ]
]

// ------------------------------------------------------------------ belts and homing
#sheet("Belts, tensioning and homing", tag: "mass_props.json")[
  #grid(columns: (1fr, 1fr), column-gutter: 7mm,
    {
      section("belts (pitch lengths, computed)")
      dtable(columns: (20mm, 18mm, 15mm, 17mm, 14mm, 1fr), header: ("stage", "pulleys", "centre", "computed", "stock", "tension"),
        aligns: (left, left, right, right, right, left),
        rows: d.belts.map(b => (b.joint, b.pulleys, fmt(b.centre_mm, d: 1), fmt(b.computed_mm, d: 1), str(b.standard_mm), b.note)),
        size: 6pt)
      section("tensioning")
      notes(d.tension_notes)
      if d.slide != none {
        section("sprung cup slide")
        dtable(columns: (30mm, 1fr), header: ("item", "value"), rows: d.slide, size: 6pt)
      }
    },
    {
      section("homing sensors (one per joint)")
      dtable(columns: (15mm, 25mm, 1fr, 32mm), header: ("joint", "sensor", "where / trigger", "homes"),
        rows: d.homing.map(h => (h.joint, h.sensor, h.mount + "; " + h.trigger, h.homes)), size: 6pt)
      section("homing order")
      text(font: mono, size: 7pt, d.homing_order.join("  >  "))
      section("joint to motor mapping")
      notes(d.motor_notes)
    })
]

// ------------------------------------------------------------------ wiring and flashing
#sheet("Wiring and flashing", tag: if d.control.present { d.control.source } else { "control not generated" })[
  #if not d.control.present [
    #notes(("No control/" + d.meta.variant + "/README.md yet. Run `" + d.control.command +
      "` to generate the firmware, host code and wiring tables, then rebuild this guide.",))
  ] else [
    #lbl(d.control.title)
    #if d.control.wiring != none {
      section("wiring")
      dtable(header: d.control.wiring.header, rows: d.control.wiring.rows, size: 5.9pt,
        columns: d.control.wiring.header.map(_ => auto))
    }
    #grid(columns: (1fr, 1fr), column-gutter: 7mm,
      {
        section("wiring notes")
        notes(d.control.wiring_notes)
        if d.control.vref != none {
          section("driver current (vref)")
          dtable(header: d.control.vref.header, rows: d.control.vref.rows, size: 6pt,
            columns: d.control.vref.header.map(_ => 24mm))
        }
      },
      {
        section("flashing")
        notes(d.control.flashing)
        for c in d.control.code { block(width: 100%, stroke: hair-muted, inset: 2mm, raw(c, lang: "bash")) }
      })
  ]
]
#if d.control.present and d.control.calibration.len() > 0 [
  #sheet("Calibration", tag: d.control.source)[
    #steps-list(d.control.calibration)
  ]
]

// ------------------------------------------------------------------ checks and gaps
#sheet("Checks, not verified, open decisions")[
  #section("checks run while building this guide")
  #dtable(columns: (70mm, 1fr, 1fr, 14mm), header: ("check", "expected", "got", "status"),
    rows: d.checks.map(c => (c.check, c.expected, c.got, status(c.status))), size: 6pt)
  #grid(columns: (1fr, 1fr), column-gutter: 7mm,
    {
      section("not verified")
      notes(d.not_verified.map(x => [#x.text #text(fill: muted, size: 6pt, font: mono)[(#x.source)]]))
    },
    {
      section("open decisions")
      notes(d.open_decisions.map(x => [#x.text #text(fill: muted, size: 6pt, font: mono)[(#x.source)]]))
    })
]
