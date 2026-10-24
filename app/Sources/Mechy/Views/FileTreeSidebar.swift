import SwiftUI
import AppKit

/// Sidebar: the project's views (click to open one on the sheet, or jump to it), each with
/// a pulse while an agent works on it and a dot when it is on the sheet; then the project
/// folder as a tree. Selecting a file previews it on the sheet.
struct FileTreeSidebar: View {
    @EnvironmentObject var session: ProjectSession
    @State private var selection: URL?

    var body: some View {
        List(selection: $selection) {
            Section {
                ForEach(PanelKind.designViews) { ViewRow(kind: $0, engine: session.engine) }
            } header: {
                Text("Design").monoLabel(Theme.muted, size: 9)
            }
            Section {
                ForEach(PanelKind.projectViews) { ViewRow(kind: $0, engine: session.engine) }
            } header: {
                Text("Project").monoLabel(Theme.muted, size: 9)
            }
            Section {
                OutlineGroup(session.tree, children: \.children) { node in
                    Label {
                        Text(node.name).font(Theme.Typo.mono(11)).foregroundStyle(Theme.ink).lineLimit(1)
                    } icon: {
                        Image(systemName: node.symbol).font(.system(size: 10)).foregroundStyle(Theme.muted)
                    }
                    .tag(node.url)
                    .contextMenu {
                        if !node.isDirectory { Button("Preview on sheet") { session.preview(node.url) } }
                        Button("Open") { NSWorkspace.shared.open(node.url) }
                        Button("Reveal in Finder") { NSWorkspace.shared.activateFileViewerSelecting([node.url]) }
                    }
                }
            } header: {
                Text("Files · \(session.name)").monoLabel(Theme.muted, size: 9)
            }
        }
        .listStyle(.sidebar)
        .onChange(of: selection) { _, url in
            guard let url, !FileIO.isDirectory(url) else { return }
            if ["arm.glb", "model.glb"].contains(url.lastPathComponent) {
                session.showVariant(url.deletingLastPathComponent().lastPathComponent)
            } else {
                session.preview(url)
            }
        }
    }
}

/// One view in the sidebar: icon, name, live/open state. Click opens it (or brings it forward);
/// the context menu can open a second copy or close it.
private struct ViewRow: View {
    let kind: PanelKind
    @ObservedObject var engine: EngineClient
    @EnvironmentObject var session: ProjectSession
    @State private var hover = false

    var body: some View {
        let open = session.layout.panels.contains { $0.kind == kind }
        let live = session.activity(for: kind) != nil
        let badge = badgeText
        Button { session.focus(kind) } label: {
            HStack(spacing: Theme.Space.s) {
                Image(systemName: kind.symbol)
                    .font(.system(size: 11))
                    .frame(width: 16)
                    .foregroundStyle(live ? Theme.accent : (open ? Theme.ink : Theme.muted))
                Text(kind.sidebarTitle)
                    .font(Theme.Typo.sans(13, open ? .medium : .regular))
                    .foregroundStyle(open ? Theme.ink : Theme.muted)
                    .lineLimit(1)
                Spacer(minLength: 0)
                if let badge {
                    Text(badge).monoLabel(Theme.accent, size: 9)
                }
                if live {
                    LivePulse()
                } else if open {
                    Rectangle().fill(Theme.ink).frame(width: 5, height: 5)
                }
            }
            .padding(.vertical, 2)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .help(live ? "\(kind.sidebarTitle): an agent is working on it" : (open ? "Show \(kind.sidebarTitle)" : "Open \(kind.sidebarTitle)"))
        .contextMenu {
            Button("Open another") { session.addPanel(kind) }
            if open {
                Button("Close") {
                    for p in session.layout.panels where p.kind == kind { session.closePanel(p.id) }
                }
            }
        }
    }

    /// Small count of things waiting on the user.
    private var badgeText: String? {
        switch kind {
        case .questions: return session.openQuestions.isEmpty ? nil : "\(session.openQuestions.count)"
        case .options: return session.openOptionSets.isEmpty ? nil : "\(session.openOptionSets.count)"
        default: return nil
        }
    }
}
