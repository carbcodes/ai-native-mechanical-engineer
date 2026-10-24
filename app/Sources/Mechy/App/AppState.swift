import SwiftUI
import AppKit

struct AppAlert: Identifiable {
    let id = UUID()
    let title: String
    let message: String
}

/// App-wide state: the open project, recent projects, and the shared engine client.
final class AppState: ObservableObject {
    @Published private(set) var session: ProjectSession?
    @Published private(set) var recent: [URL] = []
    @Published var alert: AppAlert?
    @Published var creating = false
    /// System / Paper / Graphite. Persisted in UserDefaults and applied app-wide on change.
    @Published var appearance: AppearanceMode = AppearanceMode.current {
        didSet {
            UserDefaults.standard.set(appearance.rawValue, forKey: SettingsKey.appearance)
            appearance.apply()
        }
    }

    let engine = EngineClient()
    /// Provider account status for Settings and the start screen chips.
    lazy var accounts = AccountsStore(engine: engine)

    /// File ▸ New Project: close the project and show the start screen (composer).
    func showStartComposer() {
        closeProject()
    }

    init() {
        recent = (UserDefaults.standard.stringArray(forKey: SettingsKey.recentProjects) ?? [])
            .map { URL(fileURLWithPath: $0) }
            .filter { FileIO.isDirectory($0) }
        // Dev/demo: `MECHY_OPEN_PROJECT=<dir> swift run Mechy` opens that project at launch.
        if let path = ProcessInfo.processInfo.environment["MECHY_OPEN_PROJECT"], !path.isEmpty {
            DispatchQueue.main.async { self.open(URL(fileURLWithPath: path)) }
        }
    }

    /// Reopen the last project at launch, if it still exists.
    func restoreLastProject() {
        guard session == nil,
              let path = UserDefaults.standard.string(forKey: SettingsKey.lastProject) else { return }
        let url = URL(fileURLWithPath: path)
        if FileIO.isDirectory(url) { open(url) }
    }

    // MARK: Open / close

    func open(_ url: URL) {
        guard FileIO.isDirectory(url) else {
            alert = AppAlert(title: "Folder not found", message: url.path)
            removeRecent(url)
            return
        }
        session?.stop()
        let s = ProjectSession(root: url, engine: engine)
        s.start()
        session = s
        addRecent(url)
        UserDefaults.standard.set(url.path, forKey: SettingsKey.lastProject)
    }

    func closeProject() {
        session?.stop()
        session = nil
        UserDefaults.standard.removeObject(forKey: SettingsKey.lastProject)
    }

    func openProjectInteractive() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        panel.prompt = "Open Project"
        panel.message = "Choose a Mechy project folder"
        if panel.runModal() == .OK, let url = panel.url {
            if !FileIO.exists(url.appendingPathComponent(".mechy/project.json")) {
                // Still open it: the user may be pointing at a folder the engine will initialise later.
                alert = AppAlert(title: "Not a Mechy project yet",
                                 message: "\(url.lastPathComponent) has no .mechy/project.json. Use New Project to create one.")
            }
            open(url)
        }
    }

    /// Ask for a new folder, then run `mechy init <dir> --example tennis-catcher`.
    func createProjectInteractive() {
        let panel = NSSavePanel()
        panel.title = "New Mechy Project"
        panel.prompt = "Create"
        panel.nameFieldLabel = "Project:"
        panel.nameFieldStringValue = "tennis-catcher"
        panel.canCreateDirectories = true
        guard panel.runModal() == .OK, let url = panel.url else { return }
        creating = true
        engine.initProject(at: url) { [weak self] run in
            guard let self else { return }
            self.creating = false
            if run.state == .succeeded || FileIO.exists(url.appendingPathComponent(".mechy/project.json")) {
                self.open(url)
            } else {
                let why: String
                if case .failed(let reason) = run.state { why = reason } else { why = "Unknown error" }
                self.alert = AppAlert(title: "Could not create project", message: why)
            }
        }
    }

    // MARK: Recents

    private func addRecent(_ url: URL) {
        var list = recent.filter { $0.standardizedFileURL != url.standardizedFileURL }
        list.insert(url, at: 0)
        recent = Array(list.prefix(10))
        saveRecent()
    }

    func removeRecent(_ url: URL) {
        recent.removeAll { $0.standardizedFileURL == url.standardizedFileURL }
        saveRecent()
    }

    private func saveRecent() {
        UserDefaults.standard.set(recent.map(\.path), forKey: SettingsKey.recentProjects)
    }
}
