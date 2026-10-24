import SwiftUI
import AppKit
import UniformTypeIdentifiers

/// Inspiration board: drop images, videos or links. Links, images and videos are digested
/// right away with `mechy intake add <src>` (keyframes, contact sheet, transcript, note);
/// each digest shows as a card, and clicking a card opens its keyframes and note.
struct InspirationPanel: View {
    @EnvironmentObject var session: ProjectSession
    @State private var targeted = false
    @State private var linkText = ""

    /// Raw items (files, links, notes) that have no digest card, minus links being digested now.
    private var looseItems: [InspirationItem] {
        let busy = Set(session.intakeJobs.map(\.source))
        return session.inspiration.filter { !($0.kind == .link && busy.contains($0.url.absoluteString)) }
    }

    private var isEmpty: Bool {
        session.inspiration.isEmpty && session.digests.isEmpty && session.intakeJobs.isEmpty
    }

    var body: some View {
        VStack(spacing: 0) {
            ZStack {
                if isEmpty {
                    EmptySheet(symbol: "square.and.arrow.down", label: "Drop links, videos, images")
                } else {
                    ScrollView {
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 118), spacing: Theme.Space.s, alignment: .top)],
                                  alignment: .leading, spacing: Theme.Space.s) {
                            ForEach(session.intakeJobs) { job in
                                IntakeJobCard(job: job, run: job.run)
                            }
                            ForEach(Array(session.digests.enumerated()), id: \.element.id) { i, d in
                                DigestCard(digest: d, number: i + 1)
                            }
                            ForEach(Array(looseItems.enumerated()), id: \.element.id) { i, item in
                                InspirationTile(item: item, number: session.digests.count + i + 1)
                            }
                        }
                        .padding(Theme.Space.s)
                    }
                }
                if targeted {
                    Rectangle()
                        .stroke(Theme.accent, style: StrokeStyle(lineWidth: 1.5, dash: [4, 4]))
                        .background(Theme.accentWash)
                        .padding(Theme.Space.xs)
                        .allowsHitTesting(false)
                }
            }
            .onDrop(of: [.fileURL, .image, .url], isTargeted: $targeted) { providers in
                session.handleDrop(providers)
            }
            Hairline()
            HStack(spacing: Theme.Space.s) {
                Button {
                    pickFiles()
                } label: {
                    Image(systemName: "plus").font(.system(size: 10, weight: .medium))
                }
                .buttonStyle(SheetButtonStyle(compact: true))
                .help("Add images or videos (digested with mechy intake)")
                Image(systemName: "link").font(.system(size: 10)).foregroundStyle(Theme.muted)
                TextField("PASTE YOUTUBE / WEB LINK", text: $linkText)
                    .textFieldStyle(.plain)
                    .font(Theme.Typo.monoBody)
                    .onSubmit(addLink)
                DigestAllButton(engine: session.engine)
            }
            .padding(.horizontal, Theme.Space.s)
            .padding(.vertical, Theme.Space.xs + 1)
        }
    }

    private func addLink() {
        let t = linkText.trimmingCharacters(in: .whitespaces)
        guard let url = URL(string: t.contains("://") ? t : "https://" + t), url.host != nil else { return }
        session.addLink(url)
        linkText = ""
    }

    private func pickFiles() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.allowedContentTypes = [.image, .movie, .pdf, .plainText, .html]
        if panel.runModal() == .OK {
            panel.urls.forEach { session.ingestFile($0) }
        }
    }
}

/// `mechy intake all` (digest everything not digested yet), with a spinner while it runs.
private struct DigestAllButton: View {
    @ObservedObject var engine: EngineClient
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        let running = engine.activeRun(["intake", "all"], project: session.root) != nil
        Button {
            session.digestAllPending()
        } label: {
            HStack(spacing: 4) {
                if running { ProgressView().controlSize(.mini) }
                Text("Digest all")
            }
        }
        .buttonStyle(SheetButtonStyle(compact: true))
        .disabled(running)
        .help("mechy intake all: digest every link and media file here that has no note yet")
    }
}

// MARK: - Cards

/// Fixed card art size so the grid stays even.
private enum CardArt {
    static let height: CGFloat = 76
}

/// A source being digested (spinner + engine progress), or a failed one (red mono error line).
struct IntakeJobCard: View {
    let job: IntakeJob
    @ObservedObject var run: EngineRun
    @EnvironmentObject var session: ProjectSession

    private var failure: String? {
        if case .failed(let why) = run.state { return run.wasStopped ? "Stopped" : why }
        return nil
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.xs) {
            ZStack {
                Theme.wash
                if run.isRunning {
                    VStack(spacing: Theme.Space.xs) {
                        ProgressView().controlSize(.small)
                        Text(run.message ?? "digesting").monoLabel(Theme.accent, size: 8).lineLimit(2)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, Theme.Space.xs)
                    }
                } else {
                    Image(systemName: failure != nil ? "exclamationmark.triangle" : "checkmark")
                        .font(.system(size: 16, weight: .ultraLight))
                        .foregroundStyle(failure != nil ? Theme.danger : Theme.ink)
                }
            }
            .frame(height: CardArt.height)
            .frame(maxWidth: .infinity)
            .overlay(Rectangle().stroke(failure != nil ? Theme.danger : Theme.accent,
                                        style: run.isRunning ? Theme.Stroke.dashed : StrokeStyle(lineWidth: 1)))
            Text(job.title).monoLabel(Theme.ink, size: 9).lineLimit(1)
            if let failure {
                Text(failure)
                    .font(Theme.Typo.mono(9))
                    .foregroundStyle(Theme.danger)
                    .lineLimit(3)
                    .textSelection(.enabled)
                HStack(spacing: Theme.Space.xs) {
                    Button("Retry") { session.retryIntake(job) }.buttonStyle(SheetButtonStyle(compact: true))
                    Button("×") { session.dismissIntake(job) }.buttonStyle(SheetButtonStyle(compact: true))
                        .help("Dismiss")
                }
            }
        }
        .contextMenu {
            if run.isRunning { Button("Stop") { session.dismissIntake(job) } }
            else { Button("Retry") { session.retryIntake(job) } }
            Button("Copy log") {
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(run.log.joined(separator: "\n"), forType: .string)
            }
        }
        .help("mechy intake add \(job.source)\n" + run.log.suffix(8).joined(separator: "\n"))
    }
}

/// A digested source: contact sheet (or first keyframe), title, duration, and a small tag.
struct DigestCard: View {
    let digest: InspirationDigest
    let number: Int
    @EnvironmentObject var session: ProjectSession
    @State private var showDetail = false

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.xs) {
            ZStack(alignment: .bottomTrailing) {
                if let cover = digest.cover {
                    FileThumb(url: cover)
                } else {
                    ZStack {
                        Theme.wash
                        Image(systemName: digest.isWeb ? "globe" : "film")
                            .font(.system(size: 18, weight: .ultraLight)).foregroundStyle(Theme.ink)
                    }
                }
                if let d = InspirationDigest.formatDuration(digest.duration) {
                    Text(d)
                        .font(Theme.Typo.mono(9, .medium))
                        .foregroundStyle(Theme.ink)
                        .padding(.horizontal, 3)
                        .background(Theme.surface)
                        .overlay(Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.hair))
                        .padding(3)
                }
            }
            .frame(height: CardArt.height)
            .frame(maxWidth: .infinity)
            .clipped()
            .overlay(Rectangle().stroke(showDetail ? Theme.accent : Theme.ink,
                                        lineWidth: showDetail ? 1 : Theme.Stroke.hair))
            HStack(spacing: Theme.Space.xs) {
                Text("[\(number)]").font(Theme.Typo.mono(9)).foregroundStyle(Theme.muted)
                Text(digest.title).font(Theme.Typo.mono(9, .medium)).foregroundStyle(Theme.ink).lineLimit(1)
            }
            Text(digest.tag)
                .font(Theme.Typo.mono(8, .medium))
                .tracking(0.6)
                .textCase(.uppercase)
                .foregroundStyle(Theme.muted)
                .padding(.horizontal, 3).padding(.vertical, 1)
                .overlay(Rectangle().stroke(Theme.muted, style: Theme.Stroke.dashedHair))
                .lineLimit(1)
        }
        .contentShape(Rectangle())
        .onTapGesture { showDetail = true }
        .popover(isPresented: $showDetail, arrowEdge: .trailing) {
            DigestDetail(digest: digest).environmentObject(session)
        }
        .contextMenu {
            Button("Open details") { showDetail = true }
            if let url = digest.url { Button("Open link") { NSWorkspace.shared.open(url) } }
            if let note = digest.note { Button("Open note on sheet") { session.preview(note) } }
            if !digest.frames.isEmpty { Button("Quick Look keyframes") { QuickLookPanel.show(digest.frames.map(\.url)) } }
            Button("Digest again") { session.redigest(digest) }
            Button("Reveal in Finder") { Finder.reveal(digest.dir) }
        }
        .help(digest.url?.absoluteString ?? digest.sourcePath ?? digest.slug)
    }
}

/// Popover: keyframe strip (click opens Quick Look), facts, and the note rendered from Markdown.
struct DigestDetail: View {
    let digest: InspirationDigest
    @EnvironmentObject var session: ProjectSession
    @State private var noteText: String?

    private var stripURLs: [URL] {
        if !digest.frames.isEmpty { return digest.frames.map(\.url) }
        return digest.images
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.m) {
            HStack(alignment: .firstTextBaseline, spacing: Theme.Space.s) {
                Text(digest.kindLabel).monoLabel(Theme.ink, size: 9).boxed(padding: 1)
                Text(digest.title).font(Theme.Typo.title).foregroundStyle(Theme.ink).lineLimit(2)
                Spacer(minLength: 0)
            }
            HStack(spacing: Theme.Space.m) {
                if let d = InspirationDigest.formatDuration(digest.duration) { Annotation(label: "Length", value: d) }
                Annotation(label: "Has", value: digest.tag)
                if let l = digest.license, !l.isEmpty { Annotation(label: "Licence", value: l) }
            }
            if let url = digest.url {
                Button { NSWorkspace.shared.open(url) } label: {
                    Text(url.absoluteString).font(Theme.Typo.mono(10)).foregroundStyle(Theme.accent).lineLimit(1)
                        .truncationMode(.middle)
                }
                .buttonStyle(.plain)
                .help("Open in the browser")
            }

            if !stripURLs.isEmpty { keyframeStrip }

            if let contact = digest.contactSheet {
                Button { QuickLookPanel.show([contact]) } label: {
                    Text("Contact sheet").monoLabel(Theme.ink, size: 9)
                }
                .buttonStyle(SheetButtonStyle(compact: true))
            }

            Hairline()
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Space.s) {
                    if let noteText {
                        MarkdownNoteView(text: noteText, baseURL: digest.note?.deletingLastPathComponent())
                    } else {
                        Text(digest.note == nil ? "No note yet" : "Loading note…").monoLabel(size: 9)
                    }
                    ForEach(digest.warnings, id: \.self) { w in
                        Text(w).font(Theme.Typo.mono(9)).foregroundStyle(Theme.danger).lineLimit(3)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(minHeight: 120, maxHeight: 300)

            HStack(spacing: Theme.Space.s) {
                if let note = digest.note {
                    Button("Note on sheet") { session.preview(note) }.buttonStyle(SheetButtonStyle(compact: true))
                    Button("Edit note") { NSWorkspace.shared.open(note) }.buttonStyle(SheetButtonStyle(compact: true))
                }
                if let t = digest.transcript {
                    Button("Transcript") { QuickLookPanel.show([t]) }.buttonStyle(SheetButtonStyle(compact: true))
                }
                if let p = digest.page {
                    Button("Page text") { QuickLookPanel.show([p]) }.buttonStyle(SheetButtonStyle(compact: true))
                }
                Spacer(minLength: 0)
                Button("Folder") { Finder.reveal(digest.dir) }.buttonStyle(SheetButtonStyle(compact: true))
            }
        }
        .padding(Theme.Space.m)
        .frame(width: 460)
        .background(Theme.surface)
        .task(id: "\(digest.note?.path ?? "")#\(digest.modified.timeIntervalSince1970)") {
            if let note = digest.note { noteText = try? String(contentsOf: note, encoding: .utf8) }
        }
    }

    private var keyframeStrip: some View {
        ScrollView(.horizontal, showsIndicators: true) {
            HStack(spacing: Theme.Space.xs) {
                ForEach(Array(stripURLs.enumerated()), id: \.offset) { i, url in
                    Button { QuickLookPanel.show(stripURLs, index: i) } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            FileThumb(url: url)
                                .frame(width: 96, height: 56)
                                .overlay(Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.hair))
                            Text(frameLabel(i)).font(Theme.Typo.mono(9)).foregroundStyle(Theme.muted)
                        }
                    }
                    .buttonStyle(.plain)
                    .help("Quick Look (arrow keys page through)")
                }
            }
            .padding(.bottom, Theme.Space.xs)
        }
    }

    private func frameLabel(_ i: Int) -> String {
        if i < digest.frames.count, let t = digest.frames[i].t {
            let s = Int(t.rounded())
            return String(format: "%d:%02d", s / 60, s % 60)
        }
        return "[\(i + 1)]"
    }
}

/// Renders a short Markdown note block by block (headings, bullets, tables, paragraphs);
/// inline styles and links come from `AttributedString(markdown:)`.
struct MarkdownNoteView: View {
    let text: String
    var baseURL: URL? = nil

    var body: some View {
        let blocks = MarkdownBlock.parse(text)
        VStack(alignment: .leading, spacing: Theme.Space.s) {
            ForEach(Array(blocks.enumerated()), id: \.offset) { _, block in
                blockView(block)
            }
        }
        .textSelection(.enabled)
    }

    @ViewBuilder private func blockView(_ block: MarkdownBlock) -> some View {
        switch block {
        case .heading(let level, let t):
            if level <= 1 {
                Text(inline(t)).font(Theme.Typo.title).foregroundStyle(Theme.ink)
            } else {
                Text(inline(t)).monoLabel(Theme.ink, size: 10).padding(.top, Theme.Space.xs)
            }
        case .bullet(let t, let indent):
            HStack(alignment: .firstTextBaseline, spacing: Theme.Space.xs) {
                Text("–").font(Theme.Typo.mono(10)).foregroundStyle(Theme.muted)
                Text(inline(t)).font(Theme.Typo.small).foregroundStyle(Theme.ink)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(.leading, CGFloat(indent) * 12)
        case .table(let rows):
            VStack(alignment: .leading, spacing: 0) {
                ForEach(Array(rows.enumerated()), id: \.offset) { r, cells in
                    HStack(alignment: .top, spacing: Theme.Space.s) {
                        ForEach(Array(cells.enumerated()), id: \.offset) { c, cell in
                            Text(inline(cell))
                                .font(Theme.Typo.mono(9, r == 0 ? .medium : .regular))
                                .foregroundStyle(r == 0 ? Theme.muted : Theme.ink)
                                .frame(maxWidth: c == 0 ? CGFloat(120) : CGFloat.infinity, alignment: .leading)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .padding(.vertical, 2)
                    Rectangle().fill(r == 0 ? Theme.ink : Theme.hairline).frame(height: Theme.Stroke.hair)
                }
            }
        case .paragraph(let t):
            Text(inline(t)).font(Theme.Typo.small).foregroundStyle(Theme.ink)
                .fixedSize(horizontal: false, vertical: true)
        case .code(let t):
            Text(t).font(Theme.Typo.mono(9)).foregroundStyle(Theme.ink)
                .padding(Theme.Space.xs)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Theme.wash)
        case .rule:
            Hairline()
        }
    }

    private func inline(_ s: String) -> AttributedString {
        let options = AttributedString.MarkdownParsingOptions(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        if let a = try? AttributedString(markdown: s, options: options, baseURL: baseURL) { return a }
        return AttributedString(s)
    }
}

// MARK: - Raw items (not digested: PDFs, text, links/files whose intake has not run)

struct InspirationTile: View {
    let item: InspirationItem
    let number: Int
    @EnvironmentObject var session: ProjectSession

    private var canDigest: Bool { item.kind == .link || item.kind == .image || item.kind == .video }

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.xs) {
            ZStack {
                switch item.kind {
                case .link:
                    ZStack {
                        Theme.wash
                        Image(systemName: "globe").font(.system(size: 18, weight: .ultraLight)).foregroundStyle(Theme.ink)
                    }
                default:
                    FileThumb(url: item.url)
                }
                if item.kind == .video {
                    Image(systemName: "play.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(Theme.ink)
                        .frame(width: 22, height: 22)
                        .background(Theme.surface)
                        .overlay(Rectangle().stroke(Theme.ink, lineWidth: 1))
                }
            }
            .frame(height: CardArt.height)
            .frame(maxWidth: .infinity)
            .clipped()
            .overlay(Rectangle().stroke(Theme.ink, style: canDigest ? Theme.Stroke.dashedHair : StrokeStyle(lineWidth: Theme.Stroke.hair)))
            HStack(spacing: Theme.Space.xs) {
                Text("[\(number)]").font(Theme.Typo.mono(9)).foregroundStyle(Theme.muted)
                Text(item.title).monoLabel(Theme.ink, size: 9).lineLimit(1)
            }
            if canDigest {
                Text("Not digested").font(Theme.Typo.mono(8, .medium)).textCase(.uppercase).foregroundStyle(Theme.muted)
            }
        }
        .contentShape(Rectangle())
        .onTapGesture(count: 2) { open() }
        .contextMenu {
            Button("Open") { open() }
            if canDigest { Button("Digest (mechy intake add)") { digest() } }
            if item.kind != .link {
                Button("Preview on sheet") { session.preview(item.url) }
                Button("Reveal in Finder") { NSWorkspace.shared.activateFileViewerSelecting([item.url]) }
            }
        }
        .help(item.kind == .link ? item.url.absoluteString : item.url.lastPathComponent)
    }

    private func digest() {
        if item.kind == .link {
            session.startIntake(item.url.absoluteString)
        } else {
            session.startIntake(FileIO.relativePath(item.url, to: session.root), title: item.url.lastPathComponent)
        }
    }

    private func open() {
        if item.kind == .link { NSWorkspace.shared.open(item.url) } else { session.preview(item.url) }
    }
}
