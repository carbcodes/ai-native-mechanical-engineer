import SwiftUI
import AppKit
import Quartz
import PDFKit

/// Docs: docs/<variant>/*.pdf grouped by variant (PDFKit thumbnails), a PDF viewer with page
/// navigation, and the engine buttons Build docs (`mechy doc build <v>`), Print version
/// (`--print`) and Firmware (`mechy control gen <v>`, then control/<v>/ in Finder).
/// Any other file sent here (STL, YAML, markdown) is shown with QuickLook.
struct DocsPanel: View {
    let panel: PanelState
    @EnvironmentObject var session: ProjectSession
    /// Variant the buttons act on when the user picked one by its tag.
    @State private var pickedVariant: String?
    @State private var pageIndex = 0
    @State private var pageCount = 0

    private var fileURL: URL? {
        if let p = panel.param {
            let u = session.url(p)
            if FileIO.exists(u) { return u }
        }
        if let v = pickedVariant, let g = session.docGroups.first(where: { $0.variant == v }) {
            return Self.preferred(g.files)
        }
        return session.docGroups.first.flatMap { Self.preferred($0.files) } ?? session.docs.first
    }

    /// docs/<v>/... of the shown file, if it is in a variant folder.
    private var fileVariant: String? {
        guard let f = fileURL else { return nil }
        let parts = FileIO.relativePath(f, to: session.root).split(separator: "/")
        guard parts.count >= 3, parts[0] == "docs" else { return nil }
        let v = String(parts[1])
        return session.variants.contains(where: { $0.name == v }) ? v : nil
    }

    private var actionVariant: String? {
        if let v = pickedVariant, session.variants.contains(where: { $0.name == v }) { return v }
        return fileVariant ?? session.makeVariant
    }

    private var isPDF: Bool { fileURL?.pathExtension.lowercased() == "pdf" }

    var body: some View {
        VStack(spacing: 0) {
            PanelStrip {
                VariantTags(selected: actionVariant) { v in select(variant: v) }
                Spacer(minLength: 0)
                DocsActions(engine: session.engine, variant: actionVariant)
            }
            GeometryReader { geo in
                if geo.size.width >= 440 {
                    HStack(spacing: 0) {
                        docList(axis: .vertical)
                            .frame(width: 148)
                        Rectangle().fill(Theme.ink).frame(width: Theme.Stroke.frame)
                        preview
                    }
                } else {
                    VStack(spacing: 0) {
                        docList(axis: .horizontal)
                            .frame(height: 88)
                        Hairline()
                        preview
                    }
                }
            }
        }
        .onChange(of: fileURL) { _, _ in pageIndex = 0 }
    }

    // MARK: List

    @ViewBuilder private func docList(axis: Axis) -> some View {
        if session.docGroups.isEmpty {
            VStack(spacing: Theme.Space.xs) {
                Text("No docs yet").monoLabel(size: 9)
                Text(actionVariant.map { "Build docs for \(Theme.tag($0))" } ?? "").monoLabel(size: 8)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if axis == .vertical {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Space.s) {
                    ForEach(session.docGroups) { group in
                        groupHeader(group)
                        ForEach(group.files, id: \.self) { doc in docRow(doc, compact: false) }
                    }
                }
                .padding(Theme.Space.s)
            }
        } else {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(alignment: .top, spacing: Theme.Space.s) {
                    ForEach(session.docGroups) { group in
                        VStack(alignment: .leading, spacing: 2) {
                            groupHeader(group)
                            HStack(spacing: Theme.Space.xs) {
                                ForEach(group.files, id: \.self) { doc in docRow(doc, compact: true) }
                            }
                        }
                    }
                }
                .padding(Theme.Space.xs)
            }
        }
    }

    private func groupHeader(_ group: DocGroup) -> some View {
        HStack(spacing: Theme.Space.xs) {
            Text(group.variant.map(Theme.tag) ?? "docs/").font(Theme.Typo.mono(11, .medium)).foregroundStyle(Theme.ink)
            if let v = group.variant, v == session.chosenVariant { Text("chosen").monoLabel(size: 8) }
        }
    }

    private func docRow(_ doc: URL, compact: Bool) -> some View {
        let selected = doc == fileURL
        let pdf = doc.pathExtension.lowercased() == "pdf"
        return Button {
            pickedVariant = nil
            session.setParam(panel.id, FileIO.relativePath(doc, to: session.root))
        } label: {
            VStack(alignment: .leading, spacing: 2) {
                Group {
                    if pdf { PDFThumb(url: doc) } else { FileThumb(url: doc, contentMode: .fit) }
                }
                .frame(width: compact ? 64 : 128, height: compact ? 44 : 90)
                .overlay(Rectangle().stroke(selected ? Theme.accent : Theme.ink,
                                            lineWidth: selected ? 1.5 : Theme.Stroke.hair))
                Text(doc.deletingPathExtension().lastPathComponent.replacingOccurrences(of: "_", with: " "))
                    .monoLabel(selected ? Theme.accent : Theme.ink, size: 8)
                    .lineLimit(1)
                    .frame(width: compact ? 64 : 128, alignment: .leading)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .contextMenu {
            Button("Open in Preview") { NSWorkspace.shared.open(doc) }
            Button("Print…") { PDFPrint.run(doc) }.disabled(!pdf)
            Button("Reveal in Finder") { Finder.reveal(doc) }
        }
        .help(FileIO.relativePath(doc, to: session.root))
    }

    private func select(variant v: String) {
        pickedVariant = v
        if let g = session.docGroups.first(where: { $0.variant == v }), let f = Self.preferred(g.files) {
            session.setParam(panel.id, FileIO.relativePath(f, to: session.root))
        } else {
            session.setParam(panel.id, nil)
        }
    }

    /// The build guide first, then the report, then whatever is there.
    static func preferred(_ files: [URL]) -> URL? {
        files.first { $0.lastPathComponent == "build_guide.pdf" }
            ?? files.first { $0.lastPathComponent == "report.pdf" }
            ?? files.first
    }

    // MARK: Preview

    @ViewBuilder private var preview: some View {
        if let fileURL {
            if isPDF {
                VStack(spacing: 0) {
                    PDFKitView(url: fileURL, stamp: FileIO.modified(fileURL), pageIndex: $pageIndex, pageCount: $pageCount)
                    Hairline()
                    pageBar(fileURL)
                }
            } else {
                VStack(spacing: 0) {
                    QuickLookView(url: fileURL, stamp: FileIO.modified(fileURL))
                    Hairline()
                    HStack(spacing: Theme.Space.s) {
                        Text(fileURL.lastPathComponent).monoLabel(size: 9).lineLimit(1)
                        Spacer(minLength: 0)
                        Button("Open") { NSWorkspace.shared.open(fileURL) }.buttonStyle(SheetButtonStyle(compact: true))
                    }
                    .padding(.horizontal, Theme.Space.s)
                    .padding(.vertical, Theme.Space.xs)
                }
            }
        } else {
            EmptySheet(symbol: "doc.richtext", label: "No docs yet",
                       actionTitle: actionVariant.map { "Build docs \(Theme.tag($0))" }) {
                session.buildDocs(actionVariant)
            }
        }
    }

    private func pageBar(_ url: URL) -> some View {
        HStack(spacing: Theme.Space.s) {
            Button { pageIndex = max(0, pageIndex - 1) } label: {
                Image(systemName: "chevron.left").font(.system(size: 9, weight: .semibold))
            }
            .buttonStyle(SheetButtonStyle(compact: true))
            .disabled(pageIndex <= 0)
            .keyboardShortcut(.leftArrow, modifiers: [.command])
            Text(pageCount > 0 ? "Sheet \(pageIndex + 1) / \(pageCount)" : "—")
                .font(Theme.Typo.mono(10, .medium))
                .foregroundStyle(Theme.ink)
                .frame(minWidth: 90)
            Button { pageIndex = min(max(0, pageCount - 1), pageIndex + 1) } label: {
                Image(systemName: "chevron.right").font(.system(size: 9, weight: .semibold))
            }
            .buttonStyle(SheetButtonStyle(compact: true))
            .disabled(pageIndex >= pageCount - 1)
            .keyboardShortcut(.rightArrow, modifiers: [.command])
            Spacer(minLength: 0)
            Button("Print") { PDFPrint.run(url) }.buttonStyle(SheetButtonStyle(compact: true))
                .help("Print at 100% (sheets are drawn true to scale)")
            Button("Open") { NSWorkspace.shared.open(url) }.buttonStyle(SheetButtonStyle(compact: true))
            Button("Reveal") { Finder.reveal(url) }.buttonStyle(SheetButtonStyle(compact: true))
        }
        .padding(.horizontal, Theme.Space.s)
        .padding(.vertical, Theme.Space.xs)
    }
}

/// Build docs / Print version / Firmware buttons; each shows a spinner while its command runs.
private struct DocsActions: View {
    @ObservedObject var engine: EngineClient
    let variant: String?
    @EnvironmentObject var session: ProjectSession

    private func running(_ prefix: [String]) -> Bool {
        engine.activeRun(prefix, project: session.root) != nil
    }

    var body: some View {
        let v = variant ?? ""
        let docsBusy = running(["doc", "build", v])
        let fwBusy = running(["control", "gen", v])
        HStack(spacing: Theme.Space.xs) {
            Button { session.buildDocs(variant) } label: { busyLabel("Build docs", busy: docsBusy) }
                .buttonStyle(SheetButtonStyle(compact: true))
                .disabled(variant == nil || docsBusy)
                .help("mechy doc build \(v): build_guide.pdf + report.pdf")
            Button { session.buildDocs(variant, printVersion: true) } label: { Text("Print version") }
                .buttonStyle(SheetButtonStyle(compact: true))
                .disabled(variant == nil || docsBusy)
                .help("mechy doc build \(v) --print: a version for home printers")
            Button { session.generateFirmware(variant) } label: { busyLabel("Firmware", busy: fwBusy) }
                .buttonStyle(SheetButtonStyle(compact: true))
                .disabled(variant == nil || fwBusy)
                .help("mechy control gen \(v), then show control/\(v)/ in Finder. Right-click for the board")
                .contextMenu {
                    Button("Arduino Uno + CNC shield") { session.generateFirmware(variant, board: "uno_cnc") }
                    Button("Arduino Mega + RAMPS") { session.generateFirmware(variant, board: "mega_ramps") }
                    Divider()
                    Button("Show control/\(v)/") { Finder.reveal(session.url("control/\(v)")) }
                }
        }
        .fixedSize()
    }

    private func busyLabel(_ title: String, busy: Bool) -> some View {
        HStack(spacing: 4) {
            if busy { ProgressView().controlSize(.mini) }
            Text(title)
        }
    }
}

/// Print a PDF through the system print panel, at 100% scale.
enum PDFPrint {
    static func run(_ url: URL) {
        guard let doc = PDFDocument(url: url) else { NSSound.beep(); return }
        let info = NSPrintInfo.shared.copy() as? NSPrintInfo ?? NSPrintInfo.shared
        guard let op = doc.printOperation(for: info, scalingMode: .pageScaleNone, autoRotate: true) else {
            NSSound.beep()
            return
        }
        op.showsPrintPanel = true
        op.showsProgressPanel = true
        op.run()
    }
}

/// PDFView with page navigation: `pageIndex` follows scrolling, and setting it jumps to that page.
struct PDFKitView: NSViewRepresentable {
    let url: URL
    let stamp: Date?
    @Binding var pageIndex: Int
    @Binding var pageCount: Int

    final class Coordinator: NSObject {
        var parent: PDFKitView
        var url: URL?
        var stamp: Date?
        /// Last page index the view reported (or was sent to), so scrolling and buttons do not fight.
        var reported = 0
        weak var view: PDFView?

        init(_ parent: PDFKitView) { self.parent = parent }

        @objc func pageChanged(_ note: Notification) {
            guard let view, let doc = view.document, let page = view.currentPage else { return }
            let i = doc.index(for: page)
            reported = i
            let binding = parent.$pageIndex
            DispatchQueue.main.async {
                if binding.wrappedValue != i { binding.wrappedValue = i }
            }
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeNSView(context: Context) -> PDFView {
        let view = PDFView(frame: .zero)
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.displaysPageBreaks = true
        view.backgroundColor = NSColor(Theme.paper)
        context.coordinator.view = view
        NotificationCenter.default.addObserver(context.coordinator, selector: #selector(Coordinator.pageChanged(_:)),
                                               name: Notification.Name.PDFViewPageChanged, object: view)
        load(view, context.coordinator)
        return view
    }

    func updateNSView(_ view: PDFView, context: Context) {
        context.coordinator.parent = self
        let c = context.coordinator
        if c.url != url || c.stamp != stamp {
            load(view, c)
            return
        }
        // A page change asked for by the buttons (not one the view just reported).
        if pageIndex != c.reported, let doc = view.document, pageIndex >= 0, pageIndex < doc.pageCount,
           let page = doc.page(at: pageIndex) {
            c.reported = pageIndex
            view.go(to: page)
        }
    }

    private func load(_ view: PDFView, _ c: Coordinator) {
        let sameFile = c.url == url
        c.url = url
        c.stamp = stamp
        let keep = sameFile ? pageIndex : 0
        let doc = PDFDocument(url: url)
        view.document = doc
        let count = doc?.pageCount ?? 0
        let target = min(keep, max(0, count - 1))
        if let page = doc?.page(at: target) { view.go(to: page) }
        c.reported = target
        let countBinding = $pageCount, indexBinding = $pageIndex
        DispatchQueue.main.async {
            countBinding.wrappedValue = count
            if indexBinding.wrappedValue != target { indexBinding.wrappedValue = target }
        }
    }

    static func dismantleNSView(_ view: PDFView, coordinator: Coordinator) {
        NotificationCenter.default.removeObserver(coordinator)
    }
}

/// QLPreviewView hosted in a plain container view.
struct QuickLookView: NSViewRepresentable {
    let url: URL
    let stamp: Date?

    final class Coordinator {
        var preview: QLPreviewView?
        var url: URL?
        var stamp: Date?
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> NSView {
        let container = NSView(frame: .zero)
        if let preview = QLPreviewView(frame: .zero, style: .normal) {
            preview.autostarts = true
            preview.shouldCloseWithWindow = false
            preview.autoresizingMask = [.width, .height]
            preview.frame = container.bounds
            container.addSubview(preview)
            context.coordinator.preview = preview
        }
        update(context.coordinator)
        return container
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        update(context.coordinator)
    }

    private func update(_ c: Coordinator) {
        guard let preview = c.preview else { return }
        if c.url != url {
            preview.previewItem = url as NSURL
            c.url = url
            c.stamp = stamp
        } else if c.stamp != stamp {
            preview.refreshPreviewItem()
            c.stamp = stamp
        }
    }

    static func dismantleNSView(_ nsView: NSView, coordinator: Coordinator) {
        coordinator.preview?.close()
    }
}
