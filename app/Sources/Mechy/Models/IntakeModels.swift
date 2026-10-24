import Foundation

// Inspiration digests written by `mechy intake add <src>` (engine/mechy/intake):
//   inspiration/<slug>/source.json   {kind, slug, title, url, duration_s, license, frames: [{t, path}],
//                                     contact_sheet, transcript: {path, origin}, images, note, warnings, input, path}
//   inspiration/<slug>/frames/*.jpg, contact.jpg, transcript.txt, page.txt, images/, image.jpg, thumb.jpg
//   inspiration/notes/<slug>.md      the note (skeleton, then completed by the research agent)
// Paths inside source.json are project-relative (absolute when the source lives outside the project).

/// One keyframe of a digested video.
struct DigestFrame: Identifiable, Hashable {
    var id: String { url.path }
    let url: URL
    /// Seconds into the video, when known.
    let t: Double?
}

/// One digested inspiration source (inspiration/<slug>/source.json).
struct InspirationDigest: Identifiable {
    var id: String { slug }
    let slug: String
    let dir: URL
    /// youtube | video_url | video | image | image_url | web
    let kind: String
    let title: String
    /// Source URL for links; nil for local files.
    let url: URL?
    /// What was passed to `mechy intake add` (URL or path), and the project-relative path of a local source.
    let input: String?
    let sourcePath: String?
    let duration: Double?
    let license: String?
    let frames: [DigestFrame]
    let contactSheet: URL?
    let transcript: URL?
    let transcriptOrigin: String?
    let page: URL?
    let images: [URL]
    let note: URL?
    let warnings: [String]
    let modified: Date

    var isVideo: Bool { ["youtube", "video_url", "video"].contains(kind) }
    var isWeb: Bool { kind == "web" }
    var isImage: Bool { kind == "image" || kind == "image_url" }

    /// Contact sheet, else first keyframe, else the clean image copy / first page image.
    var cover: URL? { contactSheet ?? frames.first?.url ?? images.first }

    /// "12 frames · transcript", "6 images · page", "image".
    var tag: String {
        var parts: [String] = []
        if !frames.isEmpty { parts.append("\(frames.count) frame\(frames.count == 1 ? "" : "s")") }
        if transcript != nil { parts.append("transcript") }
        if isWeb {
            if !images.isEmpty { parts.append("\(images.count) image\(images.count == 1 ? "" : "s")") }
            if page != nil { parts.append("page") }
        }
        if parts.isEmpty { parts.append(isImage ? "image" : kind) }
        return parts.joined(separator: " · ")
    }

    var kindLabel: String {
        switch kind {
        case "youtube": return "YouTube"
        case "video_url", "video": return "Video"
        case "image", "image_url": return "Image"
        case "web": return "Web"
        default: return kind
        }
    }

    init?(dir: URL, root: URL) {
        let sj = dir.appendingPathComponent("source.json")
        guard let d = FileIO.loadJSON(sj) else { return nil }
        self.init(dir: dir, root: root, d, modified: FileIO.modified(sj) ?? .distantPast)
    }

    init(dir: URL, root: URL, _ d: Loose, modified: Date) {
        func resolve(_ rel: String?) -> URL? {
            guard let rel, !rel.isEmpty else { return nil }
            let u = rel.hasPrefix("/") ? URL(fileURLWithPath: rel) : root.appendingPathComponent(rel)
            return FileIO.exists(u) ? u : nil
        }
        func existing(_ name: String) -> URL? {
            let u = dir.appendingPathComponent(name)
            return FileIO.exists(u) ? u : nil
        }
        self.dir = dir
        self.modified = modified
        slug = d.string("slug") ?? dir.lastPathComponent
        kind = d.string("kind") ?? "web"
        let link = d.string("url").flatMap { URL(string: $0) }.flatMap { $0.scheme == nil ? nil : $0 }
        url = link
        input = d.string("input")
        sourcePath = d.string("path")
        title = d.string("title").flatMap { $0.isEmpty ? nil : $0 } ?? link?.host ?? slug
        duration = d.double("duration_s") ?? d.double("duration")
        license = d.string("license") ?? d.string("licence")

        // Keyframes: [{t, path}] (or plain path strings); fall back to frames/*.jpg on disk.
        var frames: [DigestFrame] = []
        if let list = d.raw["frames"] as? [Any] {
            for item in list {
                if let f = Loose(any: item), let u = resolve(f.string("path")) {
                    frames.append(DigestFrame(url: u, t: f.double("t")))
                } else if let u = resolve(Loose.text(item)) {
                    frames.append(DigestFrame(url: u, t: nil))
                }
            }
        }
        if frames.isEmpty {
            frames = FileIO.files(in: dir.appendingPathComponent("frames"), extensions: ["jpg", "jpeg", "png"])
                .map { DigestFrame(url: $0, t: nil) }
        }
        self.frames = frames
        contactSheet = resolve(d.string("contact_sheet")) ?? existing("contact.jpg")

        // transcript: {path, origin} or a plain path
        if let t = d.dict("transcript") {
            transcript = resolve(t.string("path")) ?? existing("transcript.txt")
            transcriptOrigin = t.string("origin")
        } else {
            transcript = resolve(d.string("transcript")) ?? existing("transcript.txt")
            transcriptOrigin = nil
        }
        page = existing("page.txt")

        // Images: the clean copy of an image source, then page images (images/ folder).
        var imgs: [URL] = []
        for name in ["image.jpg", "image.png", "thumb.jpg"] {
            if let u = existing(name) { imgs.append(u); break }
        }
        if let list = d.raw["images"] as? [Any] {
            for item in list {
                let rel = Loose(any: item)?.string("path") ?? Loose.text(item)
                if let u = resolve(rel), !imgs.contains(u) { imgs.append(u) }
            }
        }
        for u in FileIO.files(in: dir.appendingPathComponent("images"), extensions: ["jpg", "jpeg", "png", "webp", "gif"])
            where !imgs.contains(u) {
            imgs.append(u)
        }
        images = imgs
        note = resolve(d.string("note")) ?? {
            let u = root.appendingPathComponent("inspiration/notes/\(dir.lastPathComponent).md")
            return FileIO.exists(u) ? u : nil
        }()
        warnings = d.strings("warnings")
    }

    /// "4:07", "1:02:03"; nil when unknown.
    static func formatDuration(_ s: Double?) -> String? {
        guard let s, s.isFinite, s > 0 else { return nil }
        let total = Int(s.rounded())
        let h = total / 3600, m = total / 60 % 60, sec = total % 60
        return h > 0 ? String(format: "%d:%02d:%02d", h, m, sec) : String(format: "%d:%02d", m, sec)
    }
}

/// A `mechy intake add <src>` started from the app, shown as a card until its digest appears.
struct IntakeJob: Identifiable {
    let id = UUID()
    /// What was passed to the engine (URL string or file path).
    let source: String
    /// Short card title (host or file name).
    let title: String
    let run: EngineRun

    static func title(for source: String) -> String {
        if let u = URL(string: source), let host = u.host {
            let path = u.path == "/" ? "" : u.path
            return host.replacingOccurrences(of: "www.", with: "") + path
        }
        return (source as NSString).lastPathComponent
    }
}

/// docs/<variant>/*.pdf, or the loose files at the top of docs/ (`variant == nil`).
struct DocGroup: Identifiable, Equatable {
    var id: String { variant ?? "_docs" }
    let variant: String?
    let files: [URL]
}

/// Tiny line-based Markdown renderer input: notes are short (<= 300 words), written by the
/// intake skeleton and the research agent: headings, lists, tables, paragraphs.
enum MarkdownBlock: Equatable {
    case heading(level: Int, text: String)
    case bullet(text: String, indent: Int)
    case table(rows: [[String]])
    case paragraph(String)
    case code(String)
    case rule

    /// Splits note text into blocks. YAML front matter (--- ... ---) is dropped.
    static func parse(_ text: String) -> [MarkdownBlock] {
        var lines = text.replacingOccurrences(of: "\r\n", with: "\n").components(separatedBy: "\n")
        if lines.first?.trimmingCharacters(in: .whitespaces) == "---",
           let end = lines.dropFirst().firstIndex(where: { $0.trimmingCharacters(in: .whitespaces) == "---" }) {
            lines.removeSubrange(0...end)
        }
        var blocks: [MarkdownBlock] = []
        var para: [String] = []
        var table: [[String]] = []
        var code: [String]? = nil

        func flushPara() {
            if !para.isEmpty { blocks.append(.paragraph(para.joined(separator: " "))); para = [] }
        }
        func flushTable() {
            if !table.isEmpty { blocks.append(.table(rows: table)); table = [] }
        }

        for raw in lines {
            let line = raw.trimmingCharacters(in: .whitespaces)
            if code != nil {
                if line.hasPrefix("```") {
                    blocks.append(.code(code!.joined(separator: "\n")))
                    code = nil
                } else {
                    code!.append(raw)
                }
                continue
            }
            if line.hasPrefix("```") { flushPara(); flushTable(); code = []; continue }
            if line.isEmpty { flushPara(); flushTable(); continue }
            if line.hasPrefix("|") {
                flushPara()
                var cells = line.split(separator: "|", omittingEmptySubsequences: false)
                    .map { $0.trimmingCharacters(in: .whitespaces) }
                if cells.first == "" { cells.removeFirst() }
                if cells.last == "" { cells.removeLast() }
                // Skip the |---|:---:| separator row.
                let isSeparator = !cells.isEmpty && cells.allSatisfy { c in
                    !c.isEmpty && c.allSatisfy { $0 == "-" || $0 == ":" }
                }
                if !isSeparator { table.append(cells) }
                continue
            }
            flushTable()
            if line.hasPrefix("#") {
                flushPara()
                let level = line.prefix(while: { $0 == "#" }).count
                let text = line.dropFirst(level).trimmingCharacters(in: .whitespaces)
                blocks.append(.heading(level: min(level, 6), text: text))
            } else if line == "---" || line == "***" || line == "___" {
                flushPara()
                blocks.append(.rule)
            } else if line.hasPrefix("- ") || line.hasPrefix("* ") || line.hasPrefix("+ ") {
                flushPara()
                let indent = raw.prefix(while: { $0 == " " }).count / 2
                blocks.append(.bullet(text: String(line.dropFirst(2)), indent: indent))
            } else if let dot = line.firstIndex(of: "."), line[line.startIndex..<dot].allSatisfy(\.isNumber),
                      dot != line.startIndex, line[line.index(after: dot)...].hasPrefix(" ") {
                flushPara()
                blocks.append(.bullet(text: line, indent: 0))
            } else {
                para.append(line)
            }
        }
        if let code { blocks.append(.code(code.joined(separator: "\n"))) }
        flushPara()
        flushTable()
        return blocks
    }
}
