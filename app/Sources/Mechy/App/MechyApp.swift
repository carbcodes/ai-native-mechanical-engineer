import SwiftUI
import AppKit

@main
struct MechyApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var app = AppState()

    var body: some Scene {
        Window("Mechy", id: "main") {
            RootView()
                .environmentObject(app)
                .frame(minWidth: 980, minHeight: 620)
        }
        .defaultSize(width: 1440, height: 900)
        .commands { MechyCommands(app: app) }

        Settings {
            SettingsView().environmentObject(app)
        }
    }
}

/// Makes `swift run Mechy` behave like a normal app (Dock icon, key window).
final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
        AppearanceMode.current.apply()
        EngineLocator.warmUp()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

struct RootView: View {
    @EnvironmentObject var app: AppState

    var body: some View {
        Group {
            if let session = app.session {
                ProjectWindow(session: session, engine: app.engine)
                    .id(session.root)
            } else {
                StartView()
            }
        }
        .overlay {
            if app.creating {
                VStack(spacing: Theme.Space.s) {
                    ProgressView().controlSize(.small)
                    Text("Creating project").monoLabel(Theme.ink)
                }
                .padding(Theme.Space.l)
                .background(Theme.surface)
                .overlay(Rectangle().stroke(Theme.ink, lineWidth: 1))
            }
        }
        .alert(app.alert?.title ?? "", isPresented: Binding(
            get: { app.alert != nil },
            set: { if !$0 { app.alert = nil } }
        ), presenting: app.alert) { _ in
            Button("OK", role: .cancel) {}
        } message: { a in
            Text(a.message)
        }
    }
}

struct MechyCommands: Commands {
    @ObservedObject var app: AppState

    var body: some Commands {
        CommandGroup(replacing: .newItem) {
            Button("New Project…") { app.showStartComposer() }
                .keyboardShortcut("n")
            Button("Open Project…") { app.openProjectInteractive() }
                .keyboardShortcut("o")
            Menu("Open Recent") {
                ForEach(app.recent, id: \.self) { url in
                    Button(url.lastPathComponent) { app.open(url) }
                }
            }
            .disabled(app.recent.isEmpty)
            Divider()
            Button("Home") { app.closeProject() }
                .keyboardShortcut("h", modifiers: [.command, .shift])
                .disabled(app.session == nil)
            Button("Close Project") { app.closeProject() }
                .keyboardShortcut("w", modifiers: [.command, .shift])
                .disabled(app.session == nil)
        }
        CommandMenu("Engine") {
            Button("Build CAD") { app.session?.buildCAD() }
                .keyboardShortcut("b")
                .disabled(app.session?.activeVariant == nil)
            Button("Run Sim") { app.session?.runSim() }
                .keyboardShortcut("r", modifiers: [.command, .shift])
                .disabled(app.session?.activeVariant == nil)
            Button("Run Agents") { app.session?.runAgents() }
                .keyboardShortcut("r", modifiers: [.command, .option])
                .disabled(app.session == nil)
            Button("Stop Agents") { app.session?.stopAgents() }
                .keyboardShortcut(".", modifiers: [.command, .option])
                .disabled(app.session == nil)
            Button("Plan") { if let s = app.session { s.engine.plan(project: s.root) } }
                .disabled(app.session == nil)
            Divider()
            Button("Make It (CAD, Sim, Firmware, Docs)") { app.session?.makeIt() }
                .keyboardShortcut("m", modifiers: [.command, .shift])
                .disabled(app.session?.makeVariant == nil)
            Button("Build Docs") { app.session?.buildDocs() }
                .keyboardShortcut("d", modifiers: [.command, .shift])
                .disabled(app.session?.makeVariant == nil)
            Button("Build Print Docs") { app.session?.buildDocs(printVersion: true) }
                .disabled(app.session?.makeVariant == nil)
            Button("Generate Firmware") { app.session?.generateFirmware() }
                .disabled(app.session?.makeVariant == nil)
            Button("Digest Pending Inspiration") { app.session?.digestAllPending() }
                .disabled(app.session == nil)
        }
        CommandGroup(after: .toolbar) {
            Picker("Appearance", selection: $app.appearance) {
                ForEach(AppearanceMode.allCases) { mode in
                    Text(mode.title).tag(mode)
                }
            }
            Divider()
            Button("Zoom In") { app.session?.zoomIn() }
                .keyboardShortcut("=")
                .disabled(app.session == nil)
            Button("Zoom Out") { app.session?.zoomOut() }
                .keyboardShortcut("-")
                .disabled(app.session == nil)
            Button("Actual Size") { app.session?.setZoom(1) }
                .disabled(app.session == nil)
            Button("Fit All Panels") { app.session?.zoomToFit() }
                .keyboardShortcut("0")
                .disabled(app.session == nil)
            Divider()
        }
        CommandMenu("Sheet") {
            ForEach(PanelKind.allCases) { kind in
                Button("Add \(kind.title)") { app.session?.addPanel(kind) }
                    .disabled(app.session == nil)
            }
            Divider()
            Button("Reset Layout") { app.session?.resetLayout() }
                .disabled(app.session == nil)
        }
    }
}
