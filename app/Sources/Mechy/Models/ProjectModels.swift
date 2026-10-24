import Foundation
import UniformTypeIdentifiers

// Swift mirrors of the project folder contract (docs/architecture/contracts.md).
// All are built leniently from `Loose` so a half-written file never crashes the UI.

// MARK: - Tasks (contracts §2)

enum TaskState: String, CaseIterable {
    case queued, running, done, failed, blocked, unknown

    var symbol: String {
        switch self {
        case .queued: return "circle.dotted"
        case .running: return "arrow.triangle.2.circlepath"
        case .done: return "checkmark.circle.fill"
        case .failed: return "xmark.octagon.fill"
        case .blocked: return "pause.circle.fill"
        case .unknown: return "circle"
        }
    }
}

struct TaskStatus {
    var state: TaskState
    var started: String?
    var finished: String?
    var summary: String?
    var error: String?

    init(_ d: Loose) {
        state = TaskState(rawValue: d.string("state") ?? "") ?? .unknown
        started = d.string("started")
        finished = d.string("finished")
        summary = d.string("summary")
        error = d.string("error") ?? d.dict("error")?.string("message")
    }
}

struct TaskCard: Identifiable {
    let id: String
    var role: String
    var provider: String?
    var goal: String?
    var dependsOn: [String]
    var outputs: [String]
    var status: TaskStatus?

    init(id: String, card: Loose?, status: TaskStatus?) {
        self.id = card?.string("id") ?? id
        role = card?.string("role") ?? "task"
        provider = card?.string("provider")
        goal = card?.string("goal")
        dependsOn = card?.strings("depends_on") ?? []
        outputs = card?.strings("outputs") ?? []
        self.status = status
    }

    var state: TaskState { status?.state ?? .queued }

    /// "T014" from "T014-shoulder-torque".
    var shortID: String { String(id.split(separator: "-").first ?? Substring(id)) }

    /// "shoulder torque" from "T014-shoulder-torque".
    var slugTitle: String {
        let parts = id.split(separator: "-")
        guard parts.count > 1 else { return id }
        return parts.dropFirst().joined(separator: " ")
    }

    var roleSymbol: String { TaskCard.symbol(forRole: role) }

    static func symbol(forRole role: String) -> String {
        switch role {
        case "planner": return "map"
        case "research": return "magnifyingglass"
        case "cad": return "cube"
        case "sim": return "waveform.path.ecg"
        case "controls": return "slider.horizontal.3"
        case "docs": return "doc.text"
        default: return "circle.grid.2x2"
        }
    }
}

// MARK: - Questions (contracts §4)

enum QuestionKind: String {
    case choice, number, text, image
}

struct Question: Identifiable {
    let id: String
    let fileURL: URL
    var askedBy: String?
    var text: String
    var kind: QuestionKind
    var choices: [String]
    var image: String?
    var answer: String?

    init(fileURL: URL, _ d: Loose) {
        let qid = d.string("id") ?? fileURL.deletingPathExtension().lastPathComponent
        let qchoices = d.strings("choices")
        self.fileURL = fileURL
        id = qid
        askedBy = d.string("asked_by")
        text = d.string("text") ?? qid
        choices = qchoices
        kind = QuestionKind(rawValue: d.string("kind") ?? "") ?? (qchoices.isEmpty ? .text : .choice)
        image = d.string("image")
        answer = d.string("answer")
    }

    var isAnswered: Bool { !(answer ?? "").isEmpty }
}

// MARK: - Option sets (contracts §5)

struct StatValue: Identifiable {
    var id: String { key }
    let key: String
    let value: Any
}

struct FailureCount: Identifiable {
    var id: String { name }
    let name: String
    let count: Int

    var label: String { name.replacingOccurrences(of: "_", with: " ") }
}

struct OptionChoice: Identifiable {
    let id: String
    var title: String
    var image: String?
    var model: String?
    var stats: [StatValue]
    /// Free-text `summary` / `description` fields of the option entry (agents write either).
    var notes: [String]

    init(_ d: Loose, index: Int) {
        let oid = d.string("id") ?? "option-\(index + 1)"
        id = oid
        title = d.string("title") ?? oid
        image = d.string("image")
        model = d.string("model")
        var texts: [String] = []
        for key in ["summary", "description"] {
            if let t = d.string(key)?.trimmingCharacters(in: .whitespacesAndNewlines), !t.isEmpty, !texts.contains(t) {
                texts.append(t)
            }
        }
        notes = texts
        let raw = d.dict("stats")?.raw ?? [:]
        stats = raw.map { StatValue(key: $0.key, value: $0.value) }
            .sorted { OptionChoice.order($0.key) < OptionChoice.order($1.key) }
    }

    private static let preferred = ["catch_rate", "reach_m", "cost_usd", "mass_kg"]
    private static func order(_ key: String) -> String {
        if let i = preferred.firstIndex(of: key) { return "0\(i)" }
        return "1" + key
    }

    /// Variant folder name if `model` points into design/<variant>/.
    var variant: String? {
        guard let model else { return nil }
        let parts = model.split(separator: "/")
        if parts.count >= 2, parts[0] == "design" { return String(parts[1]) }
        return nil
    }
}

struct OptionSetDoc: Identifiable {
    let id: String
    let fileURL: URL
    var prompt: String
    var options: [OptionChoice]
    var chosen: String?
    var feedback: String?

    init(fileURL: URL, _ d: Loose) {
        let sid = d.string("id") ?? fileURL.deletingPathExtension().lastPathComponent
        self.fileURL = fileURL
        id = sid
        prompt = d.string("prompt") ?? sid
        options = d.dicts("options").enumerated().map { OptionChoice($0.element, index: $0.offset) }
        chosen = d.string("chosen")
        feedback = d.string("feedback")
    }

    var isOpen: Bool { (chosen ?? "").isEmpty }
}

// MARK: - Sim reports (contracts §3.2)

/// The one big number of a sim report that is not a catch rate (pick-and-place: payload in g).
struct SimHeadline {
    var label: String
    var value: Double
    var unit: String
    var target: Double?
    var meets: Bool
}

struct SimMetric: Identifiable {
    var id: String { label }
    var label: String
    var value: String
    var meets: Bool?
}

struct SimReport: Identifiable {
    let id: String            // task-id folder name
    let dir: URL
    var modified: Date
    var variant: String?
    /// `pick` for `mechy sim pick`; nil for the catch sim.
    var kind: String?
    var headline: SimHeadline?
    var metrics: [SimMetric]
    var throwsCount: Int?
    var catchRate: Double?
    var reachRate: Double?
    var skippedStepRate: Double?
    var meanMarginS: Double?
    var failures: [FailureCount]
    var worstJoint: String?
    var plots: [URL]
    var video: URL?
    /// sim/<task>/replay.json (contracts §11), if the sim wrote one.
    var replay: URL?
    var replayModified: Date?

    init(dir: URL, _ d: Loose) {
        self.dir = dir
        id = dir.lastPathComponent
        modified = FileIO.modified(dir.appendingPathComponent("report.json")) ?? .distantPast
        variant = d.string("variant")
        kind = d.string("kind")
        if let h = d.dict("headline"), let v = h.double("value") {
            headline = SimHeadline(label: h.string("label") ?? "Result", value: v, unit: h.string("unit") ?? "",
                                   target: h.double("target"), meets: h.bool("meets") ?? true)
        }
        metrics = d.dicts("metrics").compactMap { m in
            m.string("label").flatMap { l in m.string("value").map { SimMetric(label: l, value: $0, meets: m.bool("meets")) } }
        }
        throwsCount = d.int("throws")
        catchRate = d.double("catch_rate")
        reachRate = d.double("reach_rate")
        skippedStepRate = d.double("skipped_step_rate")
        meanMarginS = d.double("mean_margin_s")
        let f = d.dict("failures")?.raw ?? [:]
        failures = f.compactMap { k, v in Loose.number(v).map { FailureCount(name: k, count: Int($0)) } }
            .sorted { $0.count > $1.count }
        worstJoint = d.string("worst_joint")
        plots = d.strings("plots").map { dir.appendingPathComponent($0) }.filter { FileIO.exists($0) }
        if let v = d.string("video") {
            let u = dir.appendingPathComponent(v)
            video = FileIO.exists(u) ? u : nil
        } else {
            let u = dir.appendingPathComponent("video.mp4")
            video = FileIO.exists(u) ? u : nil
        }
        let r = dir.appendingPathComponent("replay.json")
        replay = FileIO.exists(r) ? r : nil
        replayModified = replay.flatMap(FileIO.modified)
    }
}

// MARK: - Design variants (contracts §1 design/v<N>/)

struct DesignVariant: Identifiable, Equatable {
    var id: String { name }
    let name: String
    let dir: URL
    var glb: URL?
    var glbModified: Date?
    var thumb: URL?

    init(dir: URL) {
        self.dir = dir
        name = dir.lastPathComponent
        let g = dir.appendingPathComponent("arm.glb")
        let m = dir.appendingPathComponent("model.glb")
        // arm.glb (animatable arm) wins; model.glb (e.g. quad_frame) is the fallback.
        let best = FileIO.exists(g) ? g : (FileIO.exists(m) ? m : nil)
        glb = best
        glbModified = best.flatMap(FileIO.modified)
        let t = dir.appendingPathComponent("thumb.png")
        thumb = FileIO.exists(t) ? t : nil
    }

    /// Purchased parts (contracts §10).
    var bomCSV: URL { dir.appendingPathComponent("bom.csv") }
    /// Printed parts (contracts §10).
    var printListCSV: URL { dir.appendingPathComponent("print_list.csv") }
    /// Per-part STLs (contracts §10).
    var stlDir: URL { dir.appendingPathComponent("stl", isDirectory: true) }
}

// MARK: - Inspiration board

enum InspirationKind { case image, video, link, note, other }

struct InspirationItem: Identifiable {
    let id: String
    let kind: InspirationKind
    let url: URL
    let title: String

    static func classify(_ url: URL) -> InspirationKind {
        guard let type = UTType(filenameExtension: url.pathExtension.lowercased()) else { return .other }
        if type.conforms(to: .image) { return .image }
        if type.conforms(to: .movie) || type.conforms(to: .audiovisualContent) { return .video }
        if type.conforms(to: .text) { return .note }
        return .other
    }
}

// MARK: - Events (contracts §6)

struct EngineEvent: Identifiable {
    let id = UUID()
    let ts: String?
    let type: String
    let task: String?
    let message: String?
    let fraction: Double?
    let path: String?
    let refID: String?
    let text: String?
    let error: String?
    let raw: Loose

    init?(_ d: Loose) {
        guard let type = d.string("type") else { return nil }
        self.type = type
        ts = d.string("ts")
        task = d.string("task")
        message = d.string("message")
        fraction = d.double("fraction")
        path = d.string("path")
        refID = d.string("id")
        text = d.string("text")
        error = d.string("error")
        raw = d
    }

    /// Identity for de-duplicating the same event seen on stdout and in events.jsonl.
    /// nil (never de-duplicated) when the event has no timestamp.
    var dedupeKey: String? {
        guard let ts else { return nil }
        let f = fraction.map { String($0) }
        let parts: [String?] = [ts, type, task, message, f, path, refID, text, error]
        return parts.map { $0 ?? "" }.joined(separator: "\u{1F}")
    }

    /// Short human line for a status chip.
    var shortText: String {
        switch type {
        case "task.started": return "started"
        case "task.progress": return message ?? "working"
        case "task.done": return "done"
        case "task.failed": return error ?? "failed"
        case "file.written": return path.map { ($0 as NSString).lastPathComponent } ?? "file"
        case "question.asked": return "question"
        case "options.presented": return "options"
        case "agent.output": return text ?? ""
        default: return type
        }
    }
}

// MARK: - File tree

struct FileNode: Identifiable, Hashable {
    var id: URL { url }
    let url: URL
    let name: String
    let isDirectory: Bool
    var children: [FileNode]?

    var symbol: String {
        if isDirectory { return "folder" }
        switch InspirationItem.classify(url) {
        case .image: return "photo"
        case .video: return "film"
        default: break
        }
        switch url.pathExtension.lowercased() {
        case "yaml", "yml", "json", "jsonl": return "curlybraces"
        case "md": return "doc.text"
        case "glb", "stl", "step", "stp": return "cube"
        case "py", "cpp", "h", "ino": return "chevron.left.forwardslash.chevron.right"
        case "pdf": return "doc.richtext"
        case "csv": return "tablecells"
        default: return "doc"
        }
    }
}

// MARK: - Requests (inbox/*.md, handled ones in inbox/done/)

/// A message the user sent Mechy from the chat (app/README.md: `inbox/` proposal).
struct UserRequest: Identifiable, Equatable {
    var id: URL { fileURL }
    let fileURL: URL
    let text: String
    /// Still in inbox/ (the planner has not picked it up yet).
    let pending: Bool

    /// When it was sent, from the inbox file name (yyyyMMdd-HHmmss...).
    var date: Date? {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyyMMdd-HHmmss"
        return f.date(from: String(fileURL.lastPathComponent.prefix(15)))
    }

    /// Newest last; front matter stripped.
    static func load(root: URL, limit: Int = 30) -> [UserRequest] {
        let inbox = root.appendingPathComponent("inbox")
        let files = FileIO.children(of: inbox).filter { $0.pathExtension == "md" }.map { ($0, true) }
            + FileIO.children(of: inbox.appendingPathComponent("done")).filter { $0.pathExtension == "md" }.map { ($0, false) }
        let sorted = files.sorted { $0.0.lastPathComponent < $1.0.lastPathComponent }.suffix(limit)
        return sorted.compactMap { url, pending in
            guard var text = try? String(contentsOf: url, encoding: .utf8) else { return nil }
            if text.hasPrefix("---"), let end = text.range(of: "\n---", range: text.index(text.startIndex, offsetBy: 3)..<text.endIndex) {
                text = String(text[end.upperBound...])
            }
            let body = text.trimmingCharacters(in: .whitespacesAndNewlines)
            return body.isEmpty ? nil : UserRequest(fileURL: url, text: body, pending: pending)
        }
    }
}
