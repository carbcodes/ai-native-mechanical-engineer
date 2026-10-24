import SwiftUI
import AppKit

/// History panel: the project's git versions via `mechy history`, with diffs,
/// per-version thumbnails, restore, and a "Save version" snapshot.
struct HistoryPanel: View {
    @EnvironmentObject var session: ProjectSession
    @State private var selected: HistoryCommit?
    @State private var areaFilter = "All"
    @State private var snapshotMessage = ""
    @State private var confirmRestore: (commit: HistoryCommit, path: String?)?
    @State private var thumb: URL?
    @State private var thumbCommit: String?
    @State private var diffPath: String?

    private var store: HistoryStore { session.history }

    private var areas: [String] {
        var seen: [String] = []
        for c in store.commits { for a in c.areas where !seen.contains(a) { seen.append(a) } }
        return seen
    }

    private var shown: [HistoryCommit] {
        areaFilter == "All" ? store.commits : store.commits.filter { $0.areas.contains(areaFilter) }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            Divider().overlay(Theme.ink)
            if let e = store.error { Text(e).monoLabel(Theme.danger).padding(6) }
            List(selection: $selected) {
                ForEach(shown) { c in row(c).tag(c) }
            }
            .listStyle(.plain)
            .onChange(of: selected) { _, c in select(c) }
            detail
        }
        .onAppear { store.reload() }
        .onChange(of: session.events.count) { _, _ in store.scheduleReload() }
        .alert("Restore \(confirmRestore?.commit.short ?? "")?", isPresented: confirmBinding,
               presenting: confirmRestore) { c in
            Button("Restore", role: .destructive) { store.restore(c.commit, path: c.path) }
            Button("Cancel", role: .cancel) {}
        } message: { c in
            Text("Current state is saved first, and the restore itself is a new commit — undo it from History.")
        }
    }

    private var confirmBinding: Binding<Bool> {
        Binding(get: { confirmRestore != nil }, set: { if !$0 { confirmRestore = nil } })
    }

    private var header: some View {
        HStack(spacing: Theme.Space.s) {
            Menu(areaFilter) {
                Button("All") { areaFilter = "All" }
                ForEach(areas, id: \.self) { a in Button(a) { areaFilter = a } }
            }
            .menuStyle(.button).menuIndicator(.visible).fixedSize()
            .font(Theme.Typo.mono(10))
            if !store.dirty.isEmpty {
                Text("\(store.dirty.count) unsaved changes").monoLabel(Theme.accent)
                TextField("message", text: $snapshotMessage).font(Theme.Typo.monoBody)
                    .textFieldStyle(.plain).frame(maxWidth: 120)
                Button("Save version…") {
                    store.snapshot(snapshotMessage.isEmpty ? "snapshot" : snapshotMessage)
                    snapshotMessage = ""
                }
                .buttonStyle(SheetButtonStyle())
            }
            Spacer()
            if store.loading { ProgressView().controlSize(.mini) }
            Button { store.reload() } label: { Image(systemName: "arrow.clockwise") }
                .buttonStyle(.plain).foregroundStyle(Theme.muted)
        }
        .padding(6)
    }

    private func row(_ c: HistoryCommit) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 6) {
                Text(c.relativeTime).font(Theme.Typo.mono(10)).foregroundStyle(Theme.muted)
                if let t = c.task {
                    Text(t).font(Theme.Typo.mono(9)).foregroundStyle(Theme.accent)
                }
                Spacer()
                Text(c.short).font(Theme.Typo.mono(9)).foregroundStyle(Theme.muted)
            }
            Text(c.message).font(Theme.Typo.monoBody).foregroundStyle(Theme.ink).lineLimit(2)
            if !c.areas.isEmpty {
                HStack(spacing: 4) {
                    ForEach(c.areas, id: \.self) { a in
                        Text(a).font(Theme.Typo.mono(9)).foregroundStyle(Theme.muted)
                            .padding(.horizontal, 4).padding(.vertical, 1)
                            .overlay(Rectangle().stroke(Theme.muted, lineWidth: 0.5))
                    }
                }
            }
        }
    }

    @ViewBuilder private var detail: some View {
        if let c = selected {
            Divider().overlay(Theme.ink)
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    ForEach(c.files.prefix(8), id: \.path) { f in
                        Button { showDiff(c, path: f.path) } label: {
                            Text("\(f.status) \(f.path)").font(Theme.Typo.mono(9))
                                .foregroundStyle(diffPath == f.path ? Theme.accent : Theme.ink)
                                .lineLimit(1).truncationMode(.middle)
                        }
                        .buttonStyle(.plain)
                    }
                    if c.files.count > 8 { Text("+\(c.files.count - 8)").monoLabel() }
                }
                if let t = thumb { Image(nsImage: NSImage(contentsOf: t) ?? NSImage())
                        .resizable().aspectRatio(contentMode: .fit).frame(maxHeight: 90) }
                if !store.patch.isEmpty {
                    ScrollView {
                        Text(store.patch + (store.patchTruncated ? "\n… truncated" : ""))
                            .font(Theme.Typo.mono(9)).foregroundStyle(Theme.ink)
                            .textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(maxHeight: 160)
                }
                HStack(spacing: 6) {
                    Button("Restore project to this version") { confirmRestore = (c, nil) }
                        .buttonStyle(SheetButtonStyle())
                    ForEach(c.designVariants, id: \.self) { v in
                        Button("Restore design/\(v) only") { confirmRestore = (c, "design/\(v)") }
                            .buttonStyle(SheetButtonStyle())
                    }
                }
            }
            .padding(6)
        }
    }

    private func select(_ c: HistoryCommit?) {
        diffPath = nil
        thumb = nil
        guard let c else { return }
        if let tpath = c.files.first(where: { $0.path.hasSuffix("thumb.png") && $0.path.hasPrefix("design/") }) {
            store.fileAt(c, path: tpath.path) { url in
                if let url { thumb = url; thumbCommit = c.sha }
            }
        }
    }

    private func showDiff(_ c: HistoryCommit, path: String) {
        diffPath = path
        store.showDiff(c, path: path)
    }
}
