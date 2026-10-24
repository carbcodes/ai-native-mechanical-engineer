import SwiftUI
import AppKit
import UniformTypeIdentifiers

/// The "New project" composer on the start screen: name, goal, starting point,
/// an inspiration tray (files, links, pasted text, sketches) and a location.
struct NewProjectComposer: View {
    @EnvironmentObject var app: AppState

    @State private var name = ""
    @State private var goal = ""
    @State private var startFrom: StartFrom = .blank
    @State private var staged: [StagedItem] = []
    @State private var linkField = ""
    @State private var locationParent: URL = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Mechy Projects")
    @State private var planAfter = true
    @State private var planTouched = false
    @State private var sketching = false
    @State private var error: String?
    @State private var dropTargeted = false

    enum StartFrom: String, CaseIterable, Identifiable {
        case blank, arm, pick, drone
        var id: String { rawValue }
        var example: String? {
            switch self {
            case .blank: return nil
            case .arm: return "tennis-catcher"
            case .pick: return "bam-arm"
            case .drone: return "drone"
            }
        }
        var title: String {
            switch self {
            case .blank: return "Blank"
            case .arm: return "Robot arm (catcher)"
            case .pick: return "Pick-and-place arm"
            case .drone: return "Drone (quadcopter)"
            }
        }
        var symbol: String {
            switch self {
            case .blank: return "doc"
            case .arm: return "tent"
            case .pick: return "arrow.up.and.down.and.arrow.left.and.right"
            case .drone: return "fan"
            }
        }
    }

    struct StagedItem: Identifiable {
        enum Kind { case file, link, sketch }
        let id = UUID()
        let kind: Kind
        /// file: source URL to copy · link: the URL string · sketch: PNG data
        let url: URL?
        let link: String?
        let data: Data?
        let label: String
        var symbol: String {
            switch kind {
            case .link: return "link"
            case .sketch: return "pencil.and.scribble"
            default:
                let ext = url?.pathExtension.lowercased() ?? ""
                if ["jpg", "jpeg", "png", "gif", "webp", "heic"].contains(ext) { return "photo" }
                if ["mp4", "mov", "webm", "mkv"].contains(ext) { return "video" }
                if ext == "pdf" { return "doc.richtext" }
                if ["stl", "step", "stp", "3mf", "obj", "dxf", "svg"].contains(ext) { return "cube" }
                return "doc"
            }
        }
    }

    private var slug: String {
        let s = name.lowercased()
            .replacingOccurrences(of: "[^a-z0-9]+", with: "-", options: .regularExpression)
            .trimmingCharacters(in: CharacterSet(charactersIn: "-"))
        return s.isEmpty ? "untitled" : s
    }

    private var projectURL: URL { locationParent.appendingPathComponent(slug) }

    private var providerConnected: Bool {
        app.accounts.accounts.values.contains { $0.loggedIn == true }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.m) {
            Text("New project").monoLabel()
            TextField("Name", text: $name)
                .font(Theme.Typo.title).textFieldStyle(.plain)
                .onChange(of: goal) { _, _ in
                    if !planTouched { planAfter = !goal.isEmpty && providerConnected }
                }
            Text("What do you want to build?").monoLabel()
            TextEditor(text: $goal)
                .font(Theme.Typo.monoBody).foregroundStyle(Theme.ink)
                .scrollContentBackground(.hidden)
                .frame(minHeight: 52, maxHeight: 90)
                .overlay(Rectangle().stroke(Theme.muted, lineWidth: Theme.Stroke.hair))
            HStack(spacing: Theme.Space.m) {
                ForEach(StartFrom.allCases) { s in
                    Button { startFrom = s } label: {
                        VStack(spacing: 4) {
                            Image(systemName: s.symbol).font(.system(size: 16))
                            Text(s.title).font(Theme.Typo.mono(10))
                        }
                        .foregroundStyle(startFrom == s ? Theme.accent : Theme.ink)
                        .frame(maxWidth: .infinity).frame(height: 58)
                        .overlay(Rectangle().stroke(startFrom == s ? Theme.accent : Theme.muted,
                                                    lineWidth: Theme.Stroke.hair))
                    }
                    .buttonStyle(.plain)
                }
            }
            inspirationTray
            stagedList
            locationRow
            HStack(spacing: Theme.Space.m) {
                Toggle("Start planning after import", isOn: Binding(
                    get: { planAfter },
                    set: { planAfter = $0; planTouched = true }))
                .toggleStyle(.checkbox).font(Theme.Typo.mono(11)).foregroundStyle(Theme.ink)
                Spacer()
                Button { create() } label: { Label("Create project", systemImage: "plus") }
                    .buttonStyle(SheetButtonStyle(filled: true))
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty || app.creating)
            }
        }
        .sheet(isPresented: $sketching) {
            SketchPad { data in
                sketching = false
                staged.append(StagedItem(kind: .sketch, url: nil, link: nil, data: data,
                                         label: "sketch-\(staged.filter { $0.kind == .sketch }.count + 1).png"))
            } onCancel: { sketching = false }
        }
    }

    // MARK: Inspiration tray

    private var inspirationTray: some View {
        VStack(alignment: .leading, spacing: Theme.Space.s) {
            Text("Inspiration").monoLabel()
            HStack(spacing: Theme.Space.s) {
                Button("Add files…") { addFiles() }.buttonStyle(SheetButtonStyle())
                TextField("Paste link", text: $linkField)
                    .font(Theme.Typo.monoBody).textFieldStyle(.plain)
                    .onSubmit { addLinks(linkField); linkField = "" }
                    .frame(maxWidth: 220)
                    .overlay(Rectangle().stroke(Theme.muted, lineWidth: Theme.Stroke.hair).padding(-3))
                Button("Draw sketch") { sketching = true }.buttonStyle(SheetButtonStyle())
            }
            Text("Drop files, images, PDFs, STL/STEP, or paste links — one per line")
                .font(Theme.Typo.small).foregroundStyle(Theme.muted)
        }
        .padding(Theme.Space.m)
        .overlay(Rectangle().stroke(dropTargeted ? Theme.accent : Theme.muted,
                                    style: dropTargeted ? StrokeStyle(lineWidth: 1) : Theme.Stroke.dashed))
        .onDrop(of: [UTType.fileURL.identifier, UTType.url.identifier, UTType.plainText.identifier],
                isTargeted: $dropTargeted) { providers in
            for provider in providers {
                if provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) {
                    provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier) { item, _ in
                        guard let url = Self.droppedURL(item) else { return }
                        DispatchQueue.main.async {
                            staged.append(StagedItem(kind: .file, url: url, link: nil, data: nil,
                                                     label: url.lastPathComponent))
                        }
                    }
                } else {
                    provider.loadItem(forTypeIdentifier: UTType.plainText.identifier) { item, _ in
                        guard let text = item as? String ?? (item as? Data).flatMap({
                            String(data: $0, encoding: .utf8) }) else { return }
                        DispatchQueue.main.async { addLinks(text) }
                    }
                }
            }
            return true
        }
    }

    private var stagedList: some View {
        Group {
            if !staged.isEmpty {
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(staged) { item in
                        HStack(spacing: 6) {
                            Image(systemName: item.symbol).font(.system(size: 9)).foregroundStyle(Theme.muted)
                            Text(item.label).font(Theme.Typo.mono(10)).foregroundStyle(Theme.ink).lineLimit(1)
                            Spacer()
                            Button { staged.removeAll { $0.id == item.id } } label: {
                                Image(systemName: "xmark").font(.system(size: 8))
                            }
                            .buttonStyle(.plain).foregroundStyle(Theme.muted)
                        }
                    }
                }
            }
        }
    }

    private var locationRow: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: Theme.Space.s) {
                Text("Location").monoLabel()
                Text(projectURL.path.replacingOccurrences(of: NSHomeDirectory(), with: "~"))
                    .font(Theme.Typo.monoBody).foregroundStyle(Theme.ink).lineLimit(1).truncationMode(.middle)
                Button("Change…") {
                    let panel = NSOpenPanel()
                    panel.canChooseDirectories = true
                    panel.canChooseFiles = false
                    panel.prompt = "Choose parent folder"
                    if panel.runModal() == .OK, let url = panel.url { locationParent = url }
                }
                .buttonStyle(SheetButtonStyle())
            }
            if let e = error { Text(e).monoLabel(Theme.danger) }
        }
    }

    // MARK: Staging

    private func addFiles() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.allowsMultipleSelection = true
        if panel.runModal() == .OK {
            for url in panel.urls {
                staged.append(StagedItem(kind: .file, url: url, link: nil, data: nil,
                                         label: url.lastPathComponent))
            }
        }
    }

    static func droppedURL(_ item: NSSecureCoding?) -> URL? {
        if let u = item as? URL { return u }
        if let u = item as? NSURL { return u as URL }
        if let d = item as? Data { return URL(dataRepresentation: d, relativeTo: nil) }
        if let s = item as? String { return URL(string: s) }
        return nil
    }

    /// Paste/link text may hold several URLs, one per line (YouTube lines labelled video).
    static func splitLinks(_ text: String) -> [(url: String, video: Bool)] {
        text.components(separatedBy: .whitespacesAndNewlines)
            .compactMap { piece -> (String, Bool)? in
                let s = piece.trimmingCharacters(in: .whitespaces)
                guard let u = URL(string: s), let scheme = u.scheme?.lowercased(),
                      scheme == "http" || scheme == "https" else { return nil }
                let host = (u.host ?? "").lowercased()
                let video = host.contains("youtube.com") || host.contains("youtu.be")
                    || host.contains("vimeo.com") || host.contains("tiktok.com")
                return (s, video)
            }
    }

    private func addLinks(_ text: String) {
        for l in Self.splitLinks(text) {
            staged.append(StagedItem(kind: .link, url: nil, link: l.url, data: nil,
                                     label: l.video ? "video: \(l.url)" : l.url))
        }
    }

    // MARK: Create

    private func create() {
        error = nil
        let dest = projectURL
        var isDir: ObjCBool = false
        if FileManager.default.fileExists(atPath: dest.path, isDirectory: &isDir),
           let contents = try? FileManager.default.contentsOfDirectory(atPath: dest.path),
           !contents.filter({ $0 != ".DS_Store" }).isEmpty {
            error = "\(dest.lastPathComponent) already exists and is not empty"
            return
        }
        let goalText = goal.trimmingCharacters(in: .whitespacesAndNewlines)
        let items = staged
        let wantPlan = planAfter
        app.creating = true
        app.engine.initProject(at: dest, example: startFrom.example,
                               name: name.trimmingCharacters(in: .whitespaces),
                               goal: goalText.isEmpty ? nil : goalText) { [self] run in
            guard run.state == .succeeded
                    || FileIO.exists(dest.appendingPathComponent(".mechy/project.json")) else {
                self.app.creating = false
                if case .failed(let why) = run.state { error = why } else { error = "init failed" }
                return
            }
            // Stage files/links into the fresh project, then open it and start the planner
            // (which digests pending inspiration first) or a plain intake pass.
            let insp = dest.appendingPathComponent("inspiration")
            try? FileManager.default.createDirectory(at: insp, withIntermediateDirectories: true)
            for item in items {
                switch item.kind {
                case .file:
                    if let src = item.url {
                        let to = FileIO.uniqueURL(in: insp, name: src.lastPathComponent)
                        try? FileManager.default.copyItem(at: src, to: to)
                    }
                case .sketch:
                    if let data = item.data {
                        let to = FileIO.uniqueURL(in: insp, name: item.label)
                        try? data.write(to: to)
                    }
                case .link:
                    break   // handled through session.addLink after open
                }
            }
            app.open(dest)
            guard let session = app.session else { app.creating = false; return }
            for item in items where item.kind == .link {
                if let s = item.link, let u = URL(string: s) {
                    session.addLink(u, digest: false)
                }
            }
            app.creating = false
            if wantPlan {
                session.engine.plan(project: session.root)
            } else {
                session.engine.intakeAll(project: session.root)
            }
        }
    }
}
