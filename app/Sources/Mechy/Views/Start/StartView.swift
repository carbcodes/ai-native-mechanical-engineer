import SwiftUI
import AppKit

/// Shown whenever no project is open: recent project tiles, the new-project composer,
/// and an engine/accounts status strip at the bottom.
struct StartView: View {
    @EnvironmentObject var app: AppState
    @State private var mechyPath: String?

    var body: some View {
        ZStack {
            SheetGrid(zoom: 1, pan: .zero)
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Space.xl) {
                    VStack(alignment: .leading, spacing: Theme.Space.xs) {
                        Text("MECHY").font(Theme.Typo.mono(30, .light)).tracking(8).foregroundStyle(Theme.ink)
                        Text("What do you want to make?").font(Theme.Typo.mono(18, .regular)).foregroundStyle(Theme.ink).padding(.top, Theme.Space.s)
                    }
                    HStack(spacing: Theme.Space.m) {
                        Button { app.openProjectInteractive() } label: {
                            Label("Open…", systemImage: "folder")
                        }
                        .buttonStyle(SheetButtonStyle())
                    }
                    NewProjectComposer()
                    if !app.recent.isEmpty {
                        VStack(alignment: .leading, spacing: Theme.Space.s) {
                            Text("Recent").monoLabel()
                            LazyVGrid(columns: [GridItem(.adaptive(minimum: 200), spacing: Theme.Space.m)],
                                      alignment: .leading, spacing: Theme.Space.m) {
                                ForEach(Array(app.recent.enumerated()), id: \.element) { i, url in
                                    Button { app.open(url) } label: { RecentTile(url: url, number: i + 1) }
                                        .buttonStyle(.plain)
                                        .contextMenu {
                                            Button("Reveal in Finder") {
                                                NSWorkspace.shared.activateFileViewerSelecting([url])
                                            }
                                            Button("Remove from recents") { app.removeRecent(url) }
                                        }
                                }
                            }
                        }
                    }
                    bottomStrip
                }
                .padding(Theme.Space.xxl)
                .frame(maxWidth: 860, alignment: .leading)
                .background(Theme.surface)
                .overlay(Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.frame))
                .padding(Theme.Space.xxl)
            }
        }
        .background(Theme.paper)
        .task {
            mechyPath = await Task.detached { EngineLocator.mechy?.path }.value
            app.accounts.refresh()
        }
    }

    private var bottomStrip: some View {
        HStack(spacing: Theme.Space.m) {
            HStack(spacing: Theme.Space.s) {
                Rectangle().fill(mechyPath == nil ? Theme.danger : Theme.ink).frame(width: 6, height: 6)
                Text(mechyPath.map { "Engine " + $0 } ?? "Engine not found").monoLabel()
                if mechyPath == nil {
                    SettingsLink { Text("Settings").monoLabel(Theme.accent) }.buttonStyle(.plain)
                }
            }
            ForEach(["claude", "codex"], id: \.self) { p in
                AccountChip(accounts: app.accounts, provider: p)
            }
            Spacer()
        }
    }
}

/// Small account status chip shared by the start screen and Settings.
struct AccountChip: View {
    @ObservedObject var accounts: AccountsStore
    let provider: String

    private var status: AccountStatus? { accounts.accounts[provider] }

    var body: some View {
        HStack(spacing: 4) {
            Rectangle().fill(dot).frame(width: 6, height: 6)
            Text("\(provider): \(status?.label ?? "…")").monoLabel()
            if let status, status.installed, status.loggedIn != true {
                Button("Connect") { accounts.connect(provider) }
                    .buttonStyle(.plain).foregroundStyle(Theme.accent).font(Theme.Typo.mono(10))
            }
        }
    }

    private var dot: Color {
        guard let status, status.installed else { return Theme.danger }
        return status.loggedIn == true ? Theme.ink : Theme.accent
    }
}

/// Recent project tile: thumbnail (design/<chosen>/thumb.png, else any design/*/thumb.png,
/// else the name), name, ~-abbreviated path, last modified.
struct RecentTile: View {
    let url: URL
    let number: Int

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.xs) {
            if let t = Self.thumb(url), let img = NSImage(contentsOf: t) {
                Image(nsImage: img).resizable().aspectRatio(contentMode: .fit)
                    .frame(maxHeight: 90).frame(maxWidth: .infinity)
                    .overlay(Rectangle().stroke(Theme.muted, lineWidth: Theme.Stroke.hair))
            } else {
                HStack {
                    Spacer()
                    Text(url.lastPathComponent).font(Theme.Typo.mono(20, .light)).foregroundStyle(Theme.muted)
                    Spacer()
                }
                .frame(height: 60)
                .overlay(Rectangle().stroke(Theme.muted, style: Theme.Stroke.dashed))
            }
            HStack {
                Text(name).font(Theme.Typo.title).foregroundStyle(Theme.ink).lineLimit(1)
                Spacer()
                Text("[\(number)]").font(Theme.Typo.mono(10)).foregroundStyle(Theme.muted)
            }
            Text(path).font(Theme.Typo.mono(10)).foregroundStyle(Theme.muted)
                .lineLimit(1).truncationMode(.middle)
            Text(modified).font(Theme.Typo.mono(9)).foregroundStyle(Theme.muted)
        }
        .padding(Theme.Space.m)
        .frame(maxWidth: .infinity, alignment: .leading)
        .overlay(Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.hair))
        .contentShape(Rectangle())
    }

    private var name: String {
        let meta = url.appendingPathComponent(".mechy/project.json")
        if let d = FileIO.loadJSON(meta), let n = d.string("name"), !n.isEmpty { return n }
        return url.lastPathComponent
    }

    private var path: String {
        url.deletingLastPathComponent().path.replacingOccurrences(of: NSHomeDirectory(), with: "~")
    }

    private var modified: String {
        guard let d = FileIO.modified(url) else { return "" }
        return RelativeDateTimeFormatter().localizedString(for: d, relativeTo: Date())
    }

    static func thumb(_ url: URL) -> URL? {
        let design = url.appendingPathComponent("design")
        let chosen = (try? String(contentsOf: design.appendingPathComponent("chosen"),
                                  encoding: .utf8))?.trimmingCharacters(in: .whitespacesAndNewlines)
        var candidates: [URL] = []
        if let chosen, !chosen.isEmpty {
            candidates.append(design.appendingPathComponent("\(chosen)/thumb.png"))
        }
        if let subs = try? FileManager.default.contentsOfDirectory(
            at: design, includingPropertiesForKeys: nil, options: .skipsHiddenFiles) {
            candidates += subs.sorted { $0.lastPathComponent < $1.lastPathComponent }
                .filter { $0.hasDirectoryPath }
                .map { $0.appendingPathComponent("thumb.png") }
        }
        return candidates.first(where: { FileIO.exists($0) })
    }
}
