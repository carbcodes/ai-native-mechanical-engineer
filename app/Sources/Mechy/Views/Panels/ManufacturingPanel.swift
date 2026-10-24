import SwiftUI
import AppKit

/// How to make the chosen variant: print settings, every printed part (STL preview, material,
/// orientation, grams, time), what to buy, and the assembly order. Reads print_list.csv and
/// bom.csv (contracts §10); the build guide PDF comes from `mechy doc build`.
struct ManufacturingPanel: View {
    let panel: PanelState
    @EnvironmentObject var session: ProjectSession
    @State private var parts = PartsList()

    /// Typical FDM throughput on a 0.4 mm nozzle at 0.2 mm layers.
    static let gramsPerHour = 12.0

    private var variantName: String? {
        if let p = panel.param, session.variants.contains(where: { $0.name == p }) { return p }
        return session.activeVariant
    }
    private var variant: DesignVariant? { session.variants.first { $0.name == variantName } }
    private var loadKey: String { "\(variantName ?? "-")#\(session.revision)" }

    var body: some View {
        VStack(spacing: 0) {
            PanelStrip {
                VariantTags(selected: variantName) { session.setParam(panel.id, $0) }
                Spacer(minLength: 0)
                if let v = variant {
                    Button("STL folder") { NSWorkspace.shared.activateFileViewerSelecting([v.stlDir]) }
                        .buttonStyle(SheetButtonStyle(compact: true))
                        .disabled(!FileIO.isDirectory(v.stlDir))
                    Button("Build guide") { session.buildDocs(v.name) }
                        .buttonStyle(SheetButtonStyle(compact: true))
                        .help("mechy doc build: printable build guide PDF")
                }
            }
            content
        }
        .task(id: loadKey) { parts = variant.map(PartsList.load) ?? PartsList() }
    }

    @ViewBuilder private var content: some View {
        if let v = variant {
            if !parts.hasPrintList {
                EmptySheet(symbol: "printer", label: "No print list for \(Theme.tag(v.name)): rebuild CAD",
                           actionTitle: "Build CAD") { session.buildCAD(v.name) }
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: Theme.Space.l) {
                        summary
                        settings
                        printed(v)
                        assembly
                    }
                    .padding(Theme.Space.m)
                }
            }
        } else {
            EmptySheet(symbol: "printer", label: "No design variants")
        }
    }

    private var summary: some View {
        let hours = parts.printedGrams / Self.gramsPerHour
        return HStack(spacing: Theme.Space.l) {
            big("\(parts.printedPieces)", "printed parts")
            big(String(format: "%.0f g", parts.printedGrams), "filament (est.)")
            big(String(format: "%.0f h", hours), "print time (est.)")
            big("\(parts.purchased.reduce(0) { $0 + $1.qty })", "bought items")
        }
    }

    private func big(_ value: String, _ label: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value).font(Theme.Typo.mono(22, .light)).foregroundStyle(Theme.ink)
            Text(label).monoLabel(Theme.muted, size: 8)
        }
    }

    private var settings: some View {
        let materials = Set(parts.printed.compactMap(\.material))
        var rows: [(String, String)] = [
            ("Printer", "Any FDM, 0.4 mm nozzle, bed ≥ 220 × 220 mm"),
            ("Layers", "0.2 mm, 3 walls, 4 top / 4 bottom, 20 % gyroid"),
        ]
        if materials.contains("PLA") { rows.append(("PLA", "210 °C nozzle, 60 °C bed: links, towers, cup")) }
        if materials.contains("PETG") { rows.append(("PETG", "240 °C nozzle, 80 °C bed: base, turntable, pulleys (stiffer under belt load)")) }
        rows.append(("Inserts", "Heat-set M3 inserts at 220 °C after printing"))
        return section("Print settings") {
            ForEach(Array(rows.enumerated()), id: \.offset) { _, r in
                HStack(alignment: .firstTextBaseline, spacing: Theme.Space.s) {
                    Text(r.0).monoLabel(Theme.muted, size: 9).frame(width: 70, alignment: .leading)
                    Text(r.1).font(Theme.Typo.small).foregroundStyle(Theme.ink)
                }
            }
        }
    }

    private func printed(_ v: DesignVariant) -> some View {
        section("Print these") {
            ForEach(parts.printed) { p in
                let stl = p.stl.map { v.dir.appendingPathComponent($0) }
                HStack(spacing: Theme.Space.m) {
                    Group {
                        if let stl, FileIO.exists(stl) {
                            FileThumb(url: stl, contentMode: .fit)
                        } else {
                            Theme.wash
                        }
                    }
                    .frame(width: 56, height: 56)
                    .overlay(Rectangle().stroke(Theme.hairline))
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: Theme.Space.xs) {
                            Text(p.part.replacingOccurrences(of: "_", with: " ")).font(Theme.Typo.title).foregroundStyle(Theme.ink)
                            if p.qty > 1 { Text("×\(p.qty)").monoLabel(Theme.muted, size: 9) }
                        }
                        Text([p.material, p.infill.map { "\($0) infill" }].compactMap { $0 }.joined(separator: " · "))
                            .font(Theme.Typo.mono(10)).foregroundStyle(Theme.muted)
                        if let o = p.orientation {
                            Text("Orient: \(o)").font(Theme.Typo.small).foregroundStyle(Theme.ink)
                        }
                    }
                    Spacer(minLength: 0)
                    VStack(alignment: .trailing, spacing: 2) {
                        Text(p.gramsTotal.map { String(format: "%.0f g", $0) } ?? "—").font(Theme.Typo.mono(11)).foregroundStyle(Theme.ink)
                        Text(p.gramsTotal.map { String(format: "%.1f h", $0 / Self.gramsPerHour) } ?? "").font(Theme.Typo.mono(9)).foregroundStyle(Theme.muted)
                    }
                }
                .padding(.vertical, 4)
                .overlay(alignment: .bottom) { Hairline() }
                .contentShape(Rectangle())
                .onTapGesture { if let stl, FileIO.exists(stl) { session.preview(stl) } }
                .help("Click to preview the STL")
            }
        }
    }

    /// Assembly order follows the arm from the table up, then the electronics.
    private var assembly: some View {
        let steps = [
            "Press heat-set inserts into every printed screw boss.",
            "Base: mount the base motor and its 20T pulley in the base housing; fit the thrust bearing.",
            "Turntable: fit the big base pulley and belt, set the turntable on the thrust bearing, tension the belt.",
            "Towers: bolt both towers to the turntable with the shoulder, elbow and wrist motors between them.",
            "Shoulder: slide the 8 mm shaft through the towers, bearings and upper arm with its joint pulley.",
            "Elbow and wrist: repeat with the forearm and hand; route each belt from its motor pulley.",
            "Cup: screw the cup to the hand.",
            "Electronics: wire as in the Electronics view, set Vref, then flash the firmware and home each joint.",
        ]
        return section("Assembly order") {
            ForEach(Array(steps.enumerated()), id: \.offset) { i, s in
                HStack(alignment: .firstTextBaseline, spacing: Theme.Space.s) {
                    NoteNumber(n: i + 1)
                    Text(s).font(Theme.Typo.small).foregroundStyle(Theme.ink).fixedSize(horizontal: false, vertical: true)
                }
            }
            Button("Open the BOM") { session.focus(.parts) }
                .buttonStyle(SheetButtonStyle(compact: true))
                .padding(.top, Theme.Space.xs)
        }
    }

    private func section<C: View>(_ title: String, @ViewBuilder _ c: () -> C) -> some View {
        VStack(alignment: .leading, spacing: Theme.Space.xs) {
            Text(title).monoLabel(Theme.ink)
            c()
        }
    }
}
