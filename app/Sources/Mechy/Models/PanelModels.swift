import Foundation
import CoreGraphics

/// The kinds of panel the canvas can hold.
enum PanelKind: String, Codable, CaseIterable, Identifiable {
    case inspiration, cad, options, questions, sim, tasks, docs, parts, electronics, loads, manufacturing, history

    var id: String { rawValue }

    var title: String {
        switch self {
        case .inspiration: return "Inspiration"
        case .cad: return "CAD"
        case .options: return "Options"
        case .questions: return "Questions"
        case .sim: return "Simulation"
        case .tasks: return "Tasks"
        case .docs: return "Docs"
        case .parts: return "BOM"
        case .electronics: return "Electronics"
        case .loads: return "Loads"
        case .manufacturing: return "Manufacturing"
        case .history: return "History"
        }
    }

    var symbol: String {
        switch self {
        case .inspiration: return "photo.on.rectangle.angled"
        case .cad: return "cube"
        case .options: return "square.grid.2x2"
        case .questions: return "questionmark.bubble"
        case .sim: return "chart.bar.xaxis"
        case .tasks: return "checklist"
        case .docs: return "doc.richtext"
        case .parts: return "shippingbox"
        case .electronics: return "bolt.horizontal"
        case .loads: return "scalemass"
        case .manufacturing: return "printer"
        case .history: return "clock.arrow.circlepath"
        }
    }

    var defaultSize: CGSize {
        switch self {
        case .inspiration: return CGSize(width: 340, height: 300)
        case .cad: return CGSize(width: 560, height: 420)
        case .options: return CGSize(width: 560, height: 320)
        case .questions: return CGSize(width: 340, height: 340)
        case .sim: return CGSize(width: 420, height: 480)
        case .tasks: return CGSize(width: 420, height: 260)
        case .docs: return CGSize(width: 460, height: 520)
        case .parts: return CGSize(width: 480, height: 460)
        case .electronics: return CGSize(width: 640, height: 520)
        case .loads: return CGSize(width: 520, height: 420)
        case .manufacturing: return CGSize(width: 560, height: 560)
        case .history: return CGSize(width: 460, height: 460)
        }
    }

    /// Name in the sidebar's view list.
    var sidebarTitle: String {
        switch self {
        case .cad: return "3D Design"
        case .sim: return "Simulation"
        case .loads: return "Load analysis"
        case .parts: return "Bill of materials"
        default: return title
        }
    }

    /// The sidebar's view list, grouped: making the thing, then the conversation.
    static let designViews: [PanelKind] = [.cad, .sim, .loads, .electronics, .parts, .manufacturing, .docs]
    static let projectViews: [PanelKind] = [.inspiration, .options, .questions, .tasks]
}

/// One panel on the canvas, in canvas coordinates (zoom 1).
struct PanelState: Identifiable, Codable, Equatable {
    var id = UUID()
    var kind: PanelKind
    var x: Double
    var y: Double
    var w: Double
    var h: Double
    var z: Double = 0
    /// Per-panel parameter: CAD / Parts variant name, Docs file path (project-relative), Sim report id.
    var param: String?
    /// CAD panels only: sim task id whose sim/<task>/replay.json is playing in the viewer.
    /// Optional, so layouts saved before it existed still decode.
    var replay: String? = nil
}

/// The whole canvas: panels plus the viewport transform.
struct CanvasLayout: Codable, Equatable {
    var panels: [PanelState]
    var panX: Double = 0
    var panY: Double = 0
    var zoom: Double = 1

    /// Default sheet for an unknown canvas size (1200 x 800 points).
    static var initial: CanvasLayout { initial(fitting: CGSize(width: 1200, height: 800)) }

    /// Width and height (in canvas points at zoom 1) the default three-column sheet needs
    /// before it starts to zoom out instead of shrinking panels further.
    static let designMinimum = CGSize(width: 1120, height: 660)

    /// Default sheet laid out to fill a visible canvas of `size` points: three columns
    /// (inspiration + questions | CAD + options | sim + electronics). When the canvas is smaller
    /// than `designMinimum`, the sheet is laid out at that size and zoomed out to fit, so
    /// every panel is visible at launch.
    static func initial(fitting size: CGSize) -> CanvasLayout {
        let vw = Double(max(size.width, 200)), vh = Double(max(size.height, 200))
        let zx = vw / Double(designMinimum.width), zy = vh / Double(designMinimum.height)
        let zoom = max(Double(Theme.Canvas.minZoom), min(1.0, zx, zy))
        // Logical (zoom 1) size of the visible canvas.
        let w = vw / zoom, h = vh / zoom
        let margin = 24.0, gap = 16.0
        let usableW = max(3 * 240.0, w - 2 * margin - 2 * gap)
        let usableH = max(2 * 160.0, h - 2 * margin - gap)
        let leftW = (usableW * 0.27).rounded()
        let midW = (usableW * 0.40).rounded()
        let rightW = usableW - leftW - midW
        let x0 = margin, x1 = x0 + leftW + gap, x2 = x1 + midW + gap
        func split(_ topFrac: Double) -> (Double, Double) {
            let top = max(160, (usableH * topFrac).rounded())
            return (top, max(160, usableH - top))
        }
        let (inspH, qH) = split(0.46)
        let (cadH, optH) = split(0.56)
        let (simH, elecH) = split(0.45)
        func p(_ k: PanelKind, _ x: Double, _ y: Double, _ pw: Double, _ ph: Double, _ z: Double) -> PanelState {
            PanelState(kind: k, x: x, y: y, w: pw, h: ph, z: z)
        }
        let y0 = margin
        return CanvasLayout(panels: [
            p(.inspiration, x0, y0, leftW, inspH, 1),
            p(.questions, x0, y0 + inspH + gap, leftW, qH, 2),
            p(.cad, x1, y0, midW, cadH, 3),
            p(.options, x1, y0 + cadH + gap, midW, optH, 4),
            p(.sim, x2, y0, rightW, simH, 5),
            p(.electronics, x2, y0 + simH + gap, rightW, elecH, 6),
        ], panX: 0, panY: 0, zoom: zoom)
    }

    /// True when the panels are still exactly the old fixed default sheet (absolute positions
    /// up to x = 1376), which overflowed windows narrower than ~1400 points.
    var isLegacyDefault: Bool {
        let legacy: [(PanelKind, Double, Double)] = [
            (.inspiration, 24, 24), (.questions, 24, 340), (.cad, 380, 24),
            (.options, 380, 460), (.sim, 956, 24), (.tasks, 956, 520),
        ]
        guard panels.count == legacy.count else { return false }
        for (kind, x, y) in legacy {
            guard let p = panels.first(where: { $0.kind == kind }),
                  p.x == x, p.y == y,
                  p.w == Double(kind.defaultSize.width), p.h == Double(kind.defaultSize.height) else { return false }
        }
        return true
    }

    /// Bounding box of all panels in canvas coordinates, or nil when the sheet is empty.
    var panelBounds: CGRect? {
        guard let first = panels.first else { return nil }
        var r = CGRect(x: first.x, y: first.y, width: first.w, height: first.h)
        for p in panels.dropFirst() { r = r.union(CGRect(x: p.x, y: p.y, width: p.w, height: p.h)) }
        return r
    }

    /// True when every panel lies inside a viewport of `size` points (with a small slack).
    func allPanelsVisible(in size: CGSize) -> Bool {
        guard let b = panelBounds else { return true }
        let slack = 4.0
        let minX = Double(b.minX) * zoom + panX, minY = Double(b.minY) * zoom + panY
        let maxX = Double(b.maxX) * zoom + panX, maxY = Double(b.maxY) * zoom + panY
        return minX >= -slack && minY >= -slack
            && maxX <= Double(size.width) + slack && maxY <= Double(size.height) + slack
    }

    var topZ: Double { panels.map(\.z).max() ?? 0 }
}
