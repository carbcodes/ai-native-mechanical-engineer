import SwiftUI
import AppKit
import QuickLookThumbnailing
import Quartz
import PDFKit

// Small drawing-sheet building blocks shared by the panels.

/// A key/value annotation: `REACH  0.48 M`.
struct Annotation: View {
    let label: String
    let value: String
    var body: some View {
        HStack(spacing: Theme.Space.xs) {
            Text(label).monoLabel()
            Text(value).font(Theme.Typo.monoBody).foregroundStyle(Theme.ink)
        }
    }
}

/// Numbered note box `[1]` used for questions and agent notes.
struct NoteNumber: View {
    let n: Int
    var active = true
    var body: some View {
        Text("\(n)")
            .font(Theme.Typo.mono(10, .medium))
            .foregroundStyle(active ? Theme.ink : Theme.muted)
            .frame(minWidth: 16, minHeight: 16)
            .overlay(Rectangle().stroke(active ? Theme.ink : Theme.muted,
                                        style: active ? StrokeStyle(lineWidth: 1) : Theme.Stroke.dashed))
    }
}

/// Horizontal dimension line with filled-triangle arrowheads and a centred value:
/// |◀──── 74% ────▶|
struct DimensionLine: View {
    let value: String
    var color: Color = Theme.ink
    var body: some View {
        ZStack {
            GeometryReader { geo in
                let w = geo.size.width, y = geo.size.height / 2
                Path { p in
                    p.move(to: CGPoint(x: 0.5, y: y - 5)); p.addLine(to: CGPoint(x: 0.5, y: y + 5))
                    p.move(to: CGPoint(x: w - 0.5, y: y - 5)); p.addLine(to: CGPoint(x: w - 0.5, y: y + 5))
                    p.move(to: CGPoint(x: 0, y: y)); p.addLine(to: CGPoint(x: w, y: y))
                }
                .stroke(color, lineWidth: Theme.Stroke.hair)
                Path { p in
                    p.move(to: CGPoint(x: 0, y: y)); p.addLine(to: CGPoint(x: 6, y: y - 2.5)); p.addLine(to: CGPoint(x: 6, y: y + 2.5)); p.closeSubpath()
                    p.move(to: CGPoint(x: w, y: y)); p.addLine(to: CGPoint(x: w - 6, y: y - 2.5)); p.addLine(to: CGPoint(x: w - 6, y: y + 2.5)); p.closeSubpath()
                }
                .fill(color)
            }
            Text(value)
                .font(Theme.Typo.monoBody)
                .foregroundStyle(color)
                .padding(.horizontal, 4)
                .background(Theme.surface)
        }
        .frame(height: 14)
    }
}

/// Centered placeholder for an empty panel: a dashed box with a label and optional action.
struct EmptySheet: View {
    let symbol: String
    let label: String
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        VStack(spacing: Theme.Space.m) {
            Image(systemName: symbol)
                .font(.system(size: 22, weight: .ultraLight))
                .foregroundStyle(Theme.muted)
            Text(label).monoLabel()
            if let actionTitle, let action {
                Button(actionTitle, action: action).buttonStyle(SheetButtonStyle())
            }
        }
        .padding(Theme.Space.xl)
        .overlay(Rectangle().stroke(Theme.hairline, style: Theme.Stroke.dashed))
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

/// State mark for tasks/runs: solid square = done, dashed = pending, accent = live, × = failed.
struct StateMark: View {
    let state: TaskState
    var body: some View {
        ZStack {
            switch state {
            case .done:
                Rectangle().fill(Theme.ink)
            case .running:
                Rectangle().fill(Theme.accent)
            case .failed:
                Rectangle().stroke(Theme.danger, lineWidth: 1)
                Image(systemName: "xmark").font(.system(size: 6, weight: .bold)).foregroundStyle(Theme.danger)
            case .blocked:
                Rectangle().stroke(Theme.ink, lineWidth: 1)
                Rectangle().fill(Theme.ink).frame(width: 4, height: 1)
            default:
                Rectangle().stroke(Theme.muted, style: StrokeStyle(lineWidth: 1, dash: [2, 2]))
            }
        }
        .frame(width: 9, height: 9)
    }
}

/// Thumbnail for any file (images, videos, PDFs, markdown) via QuickLook thumbnails.
struct FileThumb: View {
    let url: URL
    var contentMode: ContentMode = .fill
    @State private var image: NSImage?

    private var key: String {
        let m = FileIO.modified(url)?.timeIntervalSince1970 ?? 0
        return "\(url.path)#\(m)"
    }

    var body: some View {
        ZStack {
            Theme.wash
            if let image {
                Image(nsImage: image)
                    .resizable()
                    .aspectRatio(contentMode: contentMode)
            } else {
                Image(systemName: "photo").font(.system(size: 14, weight: .ultraLight)).foregroundStyle(Theme.muted)
            }
        }
        .clipped()
        .task(id: key) { image = await ThumbnailCache.shared.thumbnail(for: url, key: key) }
    }
}

final class ThumbnailCache {
    static let shared = ThumbnailCache()
    private let cache = NSCache<NSString, NSImage>()

    func thumbnail(for url: URL, key: String, size: CGSize = CGSize(width: 360, height: 360)) async -> NSImage? {
        if let hit = cache.object(forKey: key as NSString) { return hit }
        let request = QLThumbnailGenerator.Request(fileAt: url, size: size, scale: 2,
                                                   representationTypes: .thumbnail)
        let image: NSImage? = await withCheckedContinuation { cont in
            QLThumbnailGenerator.shared.generateBestRepresentation(for: request) { rep, _ in
                cont.resume(returning: rep?.nsImage)
            }
        }
        if let image { cache.setObject(image, forKey: key as NSString) }
        return image
    }
}

/// Wrapping row of choice buttons etc.
struct WrapGrid<Content: View>: View {
    var minWidth: CGFloat = 110
    @ViewBuilder var content: () -> Content
    var body: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: minWidth), spacing: Theme.Space.s, alignment: .leading)],
                  alignment: .leading, spacing: Theme.Space.s, content: content)
    }
}

/// Horizontal hairline divider.
struct Hairline: View {
    var body: some View { Rectangle().fill(Theme.hairline).frame(height: Theme.Stroke.hair) }
}

/// Tiny toolbar strip at the top of a panel's content (mono controls).
struct PanelStrip<Content: View>: View {
    @ViewBuilder var content: () -> Content
    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: Theme.Space.s, content: content)
                .padding(.horizontal, Theme.Space.s)
                .padding(.vertical, Theme.Space.xs + 1)
            Hairline()
        }
    }
}

/// Finder helpers.
enum Finder {
    /// Open a Finder window showing a folder's contents (or select a file in its folder).
    static func reveal(_ url: URL) {
        if FileIO.isDirectory(url) {
            if !NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: url.path) {
                NSWorkspace.shared.activateFileViewerSelecting([url])
            }
        } else if FileIO.exists(url) {
            NSWorkspace.shared.activateFileViewerSelecting([url])
        } else {
            NSSound.beep()
        }
    }
}

/// The system QuickLook panel (space-bar preview) for a list of files, opened at `index`.
///
/// The panel normally asks the responder chain for a controller; the app has none, so this
/// object sets itself as the data source directly (the panel then pages with the arrow keys).
final class QuickLookPanel: NSObject, QLPreviewPanelDataSource, QLPreviewPanelDelegate {
    static let shared = QuickLookPanel()
    private var urls: [URL] = []

    static func show(_ urls: [URL], index: Int = 0) {
        // Typed as Optional so this compiles whether the SDK imports shared() as IUO or non-optional.
        let shared_: QLPreviewPanel? = QLPreviewPanel.shared()
        guard !urls.isEmpty, let panel = shared_ else { return }
        shared.urls = urls
        panel.dataSource = shared
        panel.delegate = shared
        panel.reloadData()
        panel.currentPreviewItemIndex = max(0, min(index, urls.count - 1))
        if panel.isVisible {
            panel.refreshCurrentPreviewItem()
        } else {
            panel.makeKeyAndOrderFront(nil)
        }
    }

    func numberOfPreviewItems(in panel: QLPreviewPanel!) -> Int { urls.count }

    func previewPanel(_ panel: QLPreviewPanel!, previewItemAt index: Int) -> QLPreviewItem! {
        urls[max(0, min(index, urls.count - 1))] as NSURL
    }
}

/// First page of a PDF, rendered with PDFKit (cached by path + modification date).
struct PDFThumb: View {
    let url: URL
    @State private var image: NSImage?

    private var key: String {
        "\(url.path)#\(FileIO.modified(url)?.timeIntervalSince1970 ?? 0)"
    }

    var body: some View {
        ZStack {
            Theme.wash
            if let image {
                Image(nsImage: image).resizable().aspectRatio(contentMode: .fit)
            } else {
                Image(systemName: "doc.richtext").font(.system(size: 14, weight: .ultraLight)).foregroundStyle(Theme.muted)
            }
        }
        .clipped()
        .task(id: key) { image = await PDFThumbCache.shared.thumbnail(for: url, key: key) }
    }
}

final class PDFThumbCache {
    static let shared = PDFThumbCache()
    private let cache = NSCache<NSString, NSImage>()

    func thumbnail(for url: URL, key: String, size: CGSize = CGSize(width: 240, height: 180)) async -> NSImage? {
        if let hit = cache.object(forKey: key as NSString) { return hit }
        let image: NSImage? = await withCheckedContinuation { cont in
            DispatchQueue.global(qos: .userInitiated).async {
                let img = PDFDocument(url: url)?.page(at: 0)?.thumbnail(of: size, for: .mediaBox)
                cont.resume(returning: img)
            }
        }
        if let image { cache.setObject(image, forKey: key as NSString) }
        return image
    }
}
