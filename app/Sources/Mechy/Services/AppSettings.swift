import Foundation
import AppKit

/// Which agent CLI the engine should drive.
enum AgentProvider: String, CaseIterable, Identifiable {
    case auto, claude, codex
    var id: String { rawValue }
    var title: String {
        switch self {
        case .auto: return "Auto"
        case .claude: return "Claude"
        case .codex: return "Codex"
        }
    }
}

/// App appearance: follow the system, or force the light "paper" or dark "graphite" sheet
/// (docs/architecture/ui-style.md tokens). Applied app-wide through `NSApp.appearance`,
/// which every Theme colour (dynamic NSColor) and the CAD web view follow.
enum AppearanceMode: String, CaseIterable, Identifiable {
    case system, paper, graphite
    var id: String { rawValue }

    var title: String {
        switch self {
        case .system: return "System"
        case .paper: return "Paper (light)"
        case .graphite: return "Graphite (dark)"
        }
    }

    /// nil = follow the system setting.
    var nsAppearance: NSAppearance? {
        switch self {
        case .system: return nil
        case .paper: return NSAppearance(named: .aqua)
        case .graphite: return NSAppearance(named: .darkAqua)
        }
    }

    /// Value passed to the three.js viewer page (`window.mechy.setTheme`).
    var webTheme: String {
        switch self {
        case .system: return "system"
        case .paper: return "light"
        case .graphite: return "dark"
        }
    }

    static var current: AppearanceMode {
        AppearanceMode(rawValue: UserDefaults.standard.string(forKey: SettingsKey.appearance) ?? "") ?? .system
    }

    /// Set the whole app (all windows, menus, sheets) to this appearance.
    func apply() {
        NSApp?.appearance = nsAppearance
    }
}

/// UserDefaults keys (shared with @AppStorage in SettingsView).
enum SettingsKey {
    static let provider = "provider"
    static let mechyPath = "mechyPath"
    static let claudePath = "claudePath"
    static let codexPath = "codexPath"
    static let recentProjects = "recentProjects"
    static let lastProject = "lastProject"
    static let appearance = "appearance"
    static func layout(for root: URL) -> String { "layout:" + root.standardizedFileURL.path }
}

enum AppSettings {
    static var defaults: UserDefaults { .standard }

    static var provider: AgentProvider {
        AgentProvider(rawValue: defaults.string(forKey: SettingsKey.provider) ?? "") ?? .auto
    }

    static func path(_ key: String) -> String? {
        let s = defaults.string(forKey: key)?.trimmingCharacters(in: .whitespaces) ?? ""
        return s.isEmpty ? nil : (s as NSString).expandingTildeInPath
    }
}
