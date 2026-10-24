import SwiftUI
import AppKit

/// Parts for one variant (contracts §10): printed parts from print_list.csv and purchased
/// parts from bom.csv, with totals (cost, grams) and a button to open stl/ in Finder.
struct PartsPanel: View {
    let panel: PanelState
    @EnvironmentObject var session: ProjectSession
    @State private var parts = PartsList()

    private var variantName: String? {
        if let p = panel.param, session.variants.contains(where: { $0.name == p }) { return p }
        return session.activeVariant
    }

    private var variant: DesignVariant? { session.variants.first { $0.name == variantName } }

    /// Reload when the variant changes or the project reloads (files rewritten by a build).
    private var loadKey: String { "\(variantName ?? "-")#\(session.revision)" }

    var body: some View {
        VStack(spacing: 0) {
            PanelStrip {
                VariantTags(selected: variantName) { session.setParam(panel.id, $0) }
                Spacer(minLength: 0)
                if let v = variant {
                    Button("STL folder") { reveal(v.stlDir) }
                        .buttonStyle(SheetButtonStyle(compact: true))
                        .disabled(!FileIO.isDirectory(v.stlDir))
                        .help("Show \(v.name)/stl/ in Finder")
                }
            }
            content
        }
        .task(id: loadKey) {
            guard let v = variant else { parts = PartsList(); return }
            parts = PartsList.load(v)
        }
    }

    @ViewBuilder private var content: some View {
        if let v = variant {
            if parts.isEmpty {
                EmptySheet(symbol: "shippingbox", label: "No parts list for \(Theme.tag(v.name))",
                           actionTitle: "Build CAD") { session.buildCAD(v.name) }
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: Theme.Space.l) {
                        totals
                        if parts.hasPrintList { printedTable(v) }
                        if parts.hasBOM { purchasedTable(v) }
                    }
                    .padding(Theme.Space.m)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        } else {
            EmptySheet(symbol: "shippingbox", label: "No design variants")
        }
    }

    // MARK: Totals

    private var totals: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .top, spacing: Theme.Space.xl) { totalCells }
            VStack(alignment: .leading, spacing: Theme.Space.m) { totalCells }
        }
    }

    @ViewBuilder private var totalCells: some View {
        TotalCell(label: "Est. cost", value: Self.usd(parts.totalUSD),
                  note: parts.unpricedLines > 0 ? "\(parts.unpricedLines) lines unpriced" : "parts + filament")
        TotalCell(label: "Purchased", value: Self.usd(parts.purchasedUSD),
                  note: "\(parts.purchased.count) lines")
        TotalCell(label: "Printed", value: Self.grams(parts.printedGrams),
                  note: "\(parts.printedPieces) pcs · ≈\(Self.usd(parts.filamentUSD)) filament")
    }

    // MARK: Tables

    private func printedTable(_ v: DesignVariant) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            sectionHeader("Print list", trailing: "\(parts.printed.count) parts")
            tableHeader(["Part", "Qty", "Grams", "Material"], widths: [nil, 34, 62, 58])
            ForEach(parts.printed) { p in
                let stl = p.stl.map { v.dir.appendingPathComponent($0) }
                    ?? v.stlDir.appendingPathComponent("\(p.part).stl")
                let hasSTL = FileIO.exists(stl)
                PartsRow(cells: [p.part.replacingOccurrences(of: "_", with: " "),
                                 "\(p.qty)",
                                 p.gramsTotal.map { String(format: "%.0f", $0) } ?? "—",
                                 p.material ?? "—"],
                         widths: [nil, 34, 62, 58],
                         dashed: !hasSTL,
                         help: [p.orientation.map { "Print: \($0)" }, p.infill.map { "Infill \($0)" },
                                p.gramsEach.map { String(format: "%.1f g each", $0) },
                                hasSTL ? "Click to preview the STL" : "STL not found"]
                            .compactMap { $0 }.joined(separator: "\n"))
                    .onTapGesture { if hasSTL { session.preview(stl) } }
                    .contextMenu {
                        if hasSTL {
                            Button("Preview") { session.preview(stl) }
                            Button("Show in Finder") { NSWorkspace.shared.activateFileViewerSelecting([stl]) }
                        }
                    }
            }
            tableFooter(["Total", "\(parts.printedPieces)", String(format: "%.0f", parts.printedGrams), ""],
                        widths: [nil, 34, 62, 58])
        }
    }

    private func purchasedTable(_ v: DesignVariant) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            sectionHeader("Purchased", trailing: "\(parts.purchased.count) lines")
            tableHeader(["Item", "Qty", "Unit $", "Sum $"], widths: [nil, 34, 54, 58])
            ForEach(parts.purchased) { b in
                PartsRow(cells: [b.item, "\(b.qty)",
                                 b.unitUSD.map { Self.money($0) } ?? "—",
                                 b.totalUSD.map { Self.money($0) } ?? "—"],
                         widths: [nil, 34, 54, 58],
                         dashed: false,
                         help: [b.spec, b.usedFor.map { "Used for: \($0)" }, b.source.map { "Source: \($0)" }]
                            .compactMap { $0 }.joined(separator: "\n"))
            }
            tableFooter(["Total", "\(parts.purchased.reduce(0) { $0 + $1.qty })", "", Self.money(parts.purchasedUSD)],
                        widths: [nil, 34, 54, 58])
        }
    }

    private func sectionHeader(_ title: String, trailing: String) -> some View {
        HStack {
            Text(title).monoLabel(Theme.ink)
            Spacer(minLength: 0)
            Text(trailing).monoLabel(size: 9)
        }
        .padding(.bottom, Theme.Space.xs)
    }

    private func tableHeader(_ titles: [String], widths: [CGFloat?]) -> some View {
        VStack(spacing: 0) {
            Rectangle().fill(Theme.ink).frame(height: Theme.Stroke.frame)
            PartsCells(cells: titles, widths: widths, header: true)
            Rectangle().fill(Theme.ink).frame(height: Theme.Stroke.hair)
        }
    }

    private func tableFooter(_ cells: [String], widths: [CGFloat?]) -> some View {
        VStack(spacing: 0) {
            Rectangle().fill(Theme.ink).frame(height: Theme.Stroke.hair)
            PartsCells(cells: cells, widths: widths, header: false, bold: true)
            Rectangle().fill(Theme.ink).frame(height: Theme.Stroke.frame)
        }
    }

    private func reveal(_ dir: URL) {
        // Opens a Finder window showing the folder's contents (the STL files).
        if !NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: dir.path) {
            NSWorkspace.shared.activateFileViewerSelecting([dir])
        }
    }

    // MARK: Formatting

    static func usd(_ v: Double) -> String {
        v >= 100 ? String(format: "$%.0f", v) : String(format: "$%.2f", v)
    }

    static func money(_ v: Double) -> String { String(format: "%.2f", v) }

    static func grams(_ g: Double) -> String {
        g >= 1000 ? String(format: "%.2f kg", g / 1000) : String(format: "%.0f g", g)
    }
}

/// Variant tags (V¹ V² …) used by the Parts panel strip.
struct VariantTags: View {
    let selected: String?
    let onSelect: (String) -> Void
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: Theme.Space.xs) {
                ForEach(session.variants) { v in
                    let isSel = v.name == selected
                    let chosen = v.name == session.chosenVariant
                    Button { onSelect(v.name) } label: {
                        Text(Theme.tag(v.name))
                            .font(Theme.Typo.mono(11, isSel ? .semibold : .regular))
                            .foregroundStyle(isSel ? Theme.accent : Theme.ink)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .overlay(Rectangle().stroke(isSel ? Theme.accent : (chosen ? Theme.ink : Theme.muted),
                                                        style: chosen || isSel ? StrokeStyle(lineWidth: 1) : Theme.Stroke.dashed))
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .help(chosen ? "\(v.name) (chosen)" : v.name)
                }
            }
            .padding(1)
        }
    }
}

/// One big total: label, value, small note.
struct TotalCell: View {
    let label: String
    let value: String
    let note: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).monoLabel()
            Text(value).font(Theme.Typo.mono(20, .light)).foregroundStyle(Theme.ink)
            Text(note).monoLabel(size: 9).lineLimit(1)
        }
        .fixedSize()
    }
}

/// A row of mono cells: the first column flexes, the others have fixed widths (right aligned).
struct PartsCells: View {
    let cells: [String]
    let widths: [CGFloat?]
    var header = false
    var bold = false

    var body: some View {
        HStack(spacing: Theme.Space.s) {
            ForEach(Array(cells.enumerated()), id: \.offset) { i, text in
                let w = i < widths.count ? widths[i] : nil
                let label = Text(text)
                    .lineLimit(1)
                    .truncationMode(.tail)
                if header {
                    label.monoLabel(size: 9)
                        .frame(width: w, alignment: i == 0 ? .leading : .trailing)
                        .frame(maxWidth: w == nil ? CGFloat.infinity : nil, alignment: .leading)
                } else {
                    label.font(Theme.Typo.mono(10, bold ? .semibold : .regular))
                        .foregroundStyle(Theme.ink)
                        .frame(width: w, alignment: i == 0 ? .leading : .trailing)
                        .frame(maxWidth: w == nil ? CGFloat.infinity : nil, alignment: .leading)
                }
            }
        }
        .padding(.vertical, 3)
    }
}

/// A table body row with a faint separator; dashed when the row's file is missing.
struct PartsRow: View {
    let cells: [String]
    let widths: [CGFloat?]
    let dashed: Bool
    let help: String
    @State private var hover = false

    var body: some View {
        VStack(spacing: 0) {
            PartsCells(cells: cells, widths: widths)
                .opacity(dashed ? 0.6 : 1)
            Rectangle().fill(Theme.hairline).frame(height: Theme.Stroke.hair)
        }
        .background(hover ? Theme.wash : Color.clear)
        .contentShape(Rectangle())
        .onHover { hover = $0 }
        .help(help)
    }
}
