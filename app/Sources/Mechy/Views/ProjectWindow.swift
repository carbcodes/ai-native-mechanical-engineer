import SwiftUI

/// The project window: file tree sidebar, the drafting-sheet canvas, and one strip under it
/// for working with Mechy (ChatDock). The toolbar only holds Home, appearance and Add panel;
/// building and simulating happen from the panels, Make it, or by asking Mechy.
struct ProjectWindow: View {
    @ObservedObject var session: ProjectSession
    @ObservedObject var engine: EngineClient
    @EnvironmentObject var app: AppState
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        NavigationSplitView {
            FileTreeSidebar()
                .navigationSplitViewColumnWidth(min: 180, ideal: 230, max: 360)
        } detail: {
            VStack(spacing: 0) {
                CanvasView()
                ChatDock(engine: engine)
            }
            .background(Theme.paper)
        }
        .navigationTitle(session.name)
        .navigationSubtitle(session.activeVariant.map { "Variant \(Theme.tag($0))" } ?? "")
        .toolbar { toolbar }
        .environmentObject(session)
    }

    @ToolbarContentBuilder private var toolbar: some ToolbarContent {
        ToolbarItem(placement: .navigation) {
            Button { app.closeProject() } label: { Label("Home", systemImage: "house") }
                .help("Back to the home screen (⇧⌘H)")
        }
        ToolbarItemGroup(placement: .primaryAction) {
            Button {
                app.appearance = colorScheme == .dark ? .paper : .graphite
            } label: {
                Label(colorScheme == .dark ? "Paper" : "Graphite",
                      systemImage: colorScheme == .dark ? "sun.max" : "moon")
            }
            .help(colorScheme == .dark ? "Switch to Paper (light)" : "Switch to Graphite (dark)")

            Menu {
                ForEach(PanelKind.allCases) { kind in
                    Button { session.addPanel(kind) } label: { Label(kind.title, systemImage: kind.symbol) }
                }
                Divider()
                Button("Fit all panels") { session.zoomToFit() }
                Button("Reset layout") { session.resetLayout() }
            } label: {
                Label("Add panel", systemImage: "plus.rectangle.on.rectangle")
            }
            .help("Add a panel to the sheet")
        }
    }
}
