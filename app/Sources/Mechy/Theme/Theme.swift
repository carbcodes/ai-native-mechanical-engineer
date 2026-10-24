import SwiftUI
import AppKit

/// Every color, line, size and font the app uses lives here.
///
/// Source: docs/architecture/ui-style.md — an engineering-drawing sheet: monochrome
/// paper/graphite, hairlines, monospace uppercase labels, boxed labels, dashed lines
/// for predicted / unchosen / pending things, and Mechy blue only for selection and
/// live state. No gradients, no shadows, corner radius 0-2 pt.
enum Theme {
    // MARK: Colors (light "paper" / dark "graphite")
    // Dark ("graphite") follows the Architect Labs poster: near-black sheet, panels barely
    // lifted off it, light text, grey hairline frames.
    static let paper = dynamic(light: 0xECECEA, dark: 0x1A1A1A)       // canvas background
    static let surface = dynamic(light: 0xF5F5F3, dark: 0x1F1F1F)     // panels, bars
    static let ink = dynamic(light: 0x1C1C1C, dark: 0xEDEDED)         // lines, primary text
    static let muted = dynamic(light: 0x6B6B6B, dark: 0x8E8E8E)       // secondary text
    /// Panel frames and bar rules: ink on paper, a softer grey hairline on graphite.
    static let frame = dynamic(light: 0x1C1C1C, dark: 0x6A6A6A)
    static let gridLine = dynamic(light: 0x1C1C1C, dark: 0xFFFFFF, lightAlpha: 0.10, darkAlpha: 0.10)
    static let gridDot = dynamic(light: 0x1C1C1C, dark: 0xFFFFFF, lightAlpha: 0.12, darkAlpha: 0.12)
    /// Faint separators inside panels (dividers between rows).
    static let hairline = dynamic(light: 0x1C1C1C, dark: 0xFFFFFF, lightAlpha: 0.16, darkAlpha: 0.16)
    /// Subtle fill for hovered / sunken areas.
    static let wash = dynamic(light: 0x1C1C1C, dark: 0xFFFFFF, lightAlpha: 0.04, darkAlpha: 0.05)

    /// Mechy blue: selection and live state only.
    static let accent = Color(hex: 0x20A4F3)
    static let accentWash = Color(hex: 0x20A4F3, alpha: 0.10)
    /// Result charts only.
    static let good = Color(hex: 0x1E7F4F)
    static let danger = Color(hex: 0xC8102E)

    // MARK: Lines
    enum Stroke {
        static let hair: CGFloat = 0.5
        static let line: CGFloat = 1
        /// Panel frames, boxed labels.
        static let frame: CGFloat = 1
        /// Dashed: predicted, planned, pending, unchosen.
        static let dashed = StrokeStyle(lineWidth: 1, dash: [4, 4])
        static let dashedHair = StrokeStyle(lineWidth: 0.5, dash: [4, 4])
    }

    // MARK: Spacing (4-pt grid)
    enum Space {
        static let xxs: CGFloat = 2
        static let xs: CGFloat = 4
        static let s: CGFloat = 8
        static let m: CGFloat = 12
        static let l: CGFloat = 16
        static let xl: CGFloat = 24
        static let xxl: CGFloat = 32
    }

    // MARK: Corner radii (drawing sheet: square or nearly)
    enum Radius {
        static let panel: CGFloat = 0
        static let control: CGFloat = 2
    }

    // MARK: Canvas (drafting sheet)
    enum Canvas {
        static let gridUnit: CGFloat = 24        // dot spacing at zoom 1
        static let nodeEvery: Int = 8            // hollow square node every 8 grid units
        static let dotRadius: CGFloat = 0.9
        static let nodeSize: CGFloat = 5
        static let minZoom: CGFloat = 0.4
        static let maxZoom: CGFloat = 2.0
        static let panelMinWidth: CGFloat = 240
        static let panelMinHeight: CGFloat = 160
        static let titleBlockHeight: CGFloat = 22
        static let dragStripHeight: CGFloat = 10
    }


    // MARK: Typography
    enum Typo {
        /// Grotesk for titles and the few sentences (Inter if installed, else SF Pro).
        static func sans(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
            Font.custom("Inter", size: size).weight(weight)
        }
        /// Monospace for labels, numbers, annotations, buttons.
        static func mono(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
            Font.system(size: size, weight: weight, design: .monospaced)
        }
        static let hero = mono(52, .light)        // one big number (catch rate)
        static let number = mono(15, .regular)
        static let title = sans(14, .medium)
        static let body = sans(13)
        static let small = sans(12)
        static let label = mono(10, .medium)      // UPPERCASE tracked labels
        static let labelTracking: CGFloat = 1.1
        static let monoBody = mono(11)
    }

    // MARK: Helpers

    static func dynamic(light: UInt32, dark: UInt32, lightAlpha: CGFloat = 1, darkAlpha: CGFloat = 1) -> Color {
        Color(nsColor: NSColor(name: nil, dynamicProvider: { appearance in
            let isDark = appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua
            return isDark ? NSColor(hex: dark, alpha: darkAlpha) : NSColor(hex: light, alpha: lightAlpha)
        }))
    }

    /// Superscript-style tag: sup("V", "3") -> "V³", sup("T", "14") -> "T¹⁴".
    static func sup(_ base: String, _ tag: String) -> String {
        let map: [Character: Character] = [
            "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
            ".": "·", "-": "⁻", "+": "⁺",
        ]
        return base + String(tag.map { map[$0] ?? $0 })
    }

    /// "v3" -> "V³", "T014" -> "T¹⁴"; anything else upper-cased.
    static func tag(_ id: String) -> String {
        guard let first = id.first, first.isLetter else { return id.uppercased() }
        let digits = id.dropFirst()
        guard !digits.isEmpty, digits.allSatisfy(\.isNumber) else { return id.uppercased() }
        let trimmed = String(Int(digits) ?? 0)
        return sup(String(first).uppercased(), trimmed)
    }

    /// Ink for a task / run state. Accent only for live (running) work.
    static func stateColor(_ state: String) -> Color {
        switch state {
        case "running": return accent
        case "failed": return danger
        case "queued", "blocked", "unknown": return muted
        default: return ink
        }
    }

    static func percent(_ v: Double?) -> String {
        guard let v else { return "—" }
        return "\(Int((v * 100).rounded()))%"
    }
}

extension NSColor {
    convenience init(hex: UInt32, alpha: CGFloat = 1) {
        self.init(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255,
                  green: CGFloat((hex >> 8) & 0xFF) / 255,
                  blue: CGFloat(hex & 0xFF) / 255,
                  alpha: alpha)
    }
}

extension Color {
    init(hex: UInt32, alpha: Double = 1) {
        self.init(.sRGB,
                  red: Double((hex >> 16) & 0xFF) / 255,
                  green: Double((hex >> 8) & 0xFF) / 255,
                  blue: Double(hex & 0xFF) / 255,
                  opacity: alpha)
    }
}

// MARK: - Shared drawing-sheet styles

extension View {
    /// Small UPPERCASE monospace label with wide tracking.
    func monoLabel(_ color: Color = Theme.muted, size: CGFloat = 10) -> some View {
        self.font(Theme.Typo.mono(size, .medium))
            .tracking(Theme.Typo.labelTracking)
            .textCase(.uppercase)
            .foregroundStyle(color)
    }

    /// 1 pt rectangle around content (boxed label / frame). Dashed for pending/unchosen.
    func boxed(_ color: Color = Theme.ink, dashed: Bool = false, padding: CGFloat = Theme.Space.xs) -> some View {
        self.padding(.horizontal, padding + 2)
            .padding(.vertical, padding)
            .overlay(
                Rectangle().stroke(color, style: dashed ? Theme.Stroke.dashed : StrokeStyle(lineWidth: Theme.Stroke.frame))
            )
    }
}

/// Drawing-sheet button: mono uppercase text in a 1 pt box. `filled` = ink block (primary).
struct SheetButtonStyle: ButtonStyle {
    var filled = false
    var compact = false
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(Theme.Typo.mono(compact ? 10 : 11, .medium))
            .tracking(Theme.Typo.labelTracking)
            .textCase(.uppercase)
            .foregroundStyle(filled ? Theme.paper : Theme.ink)
            .padding(.horizontal, compact ? 6 : 10)
            .padding(.vertical, compact ? 3 : 5)
            .background(Rectangle().fill(filled ? Theme.ink : (configuration.isPressed ? Theme.wash : Color.clear)))
            .overlay(Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.frame))
            .opacity(configuration.isPressed ? 0.7 : 1)
            .contentShape(Rectangle())
    }
}
