import Foundation

/// Something Mechy said while working in the workspace: a finished task's summary, a comment an
/// agent pinned on a panel (`workspace.note`), a question, options to pick, or a problem.
/// Each shows as a reply in the chat; notes about a panel are also pinned on that panel.
struct WorkspaceNote: Identifiable, Equatable {
    enum Kind: Equatable { case note, question, options, failure }

    let id: String
    let kind: Kind
    let text: String
    let date: Date
    /// Panel the note is about (nil: chat only).
    let panel: PanelKind?
    /// What that panel should show: variant (CAD/BOM/...), sim task id, docs path.
    let target: String?
    /// Task card that produced it, when known.
    let task: String?
    /// Whether Mechy should bring the panel up when the note arrives.
    let opens: Bool

    /// Notes for the events Mechy "says"; nil for everything else (progress, file writes...).
    /// `role` maps a task id to its card's role (cad, sim, ...).
    static func from(_ ev: EngineEvent, root: URL, role: (String) -> String?,
                     questions: [Question], optionSets: [OptionSetDoc]) -> WorkspaceNote? {
        let id = ev.dedupeKey ?? ev.id.uuidString
        let date = ev.ts.flatMap(Self.parseDate) ?? Date()
        switch ev.type {
        case "workspace.note":
            guard let text = ev.text, !text.isEmpty else { return nil }
            return WorkspaceNote(id: id, kind: .note, text: text, date: date,
                                 panel: ev.raw.string("panel").flatMap(PanelKind.init(rawValue:)),
                                 target: ev.raw.string("target"), task: ev.task,
                                 opens: ev.raw.bool("open") ?? true)
        case "task.done":
            guard let task = ev.task, let rel = ev.raw.string("summary"),
                  let text = Self.gist(of: root.appendingPathComponent(rel)) else { return nil }
            let panel = task == "intake" ? .inspiration : role(task).flatMap(PanelKind.forRole)
            return WorkspaceNote(id: id, kind: .note, text: text, date: date, panel: panel,
                                 target: panel == .sim ? task : nil, task: task, opens: panel != nil)
        case "question.asked":
            let q = questions.first { $0.id == ev.refID }
            return WorkspaceNote(id: id, kind: .question, text: q?.text ?? "I have a question for you.", date: date,
                                 panel: .questions, target: nil, task: ev.task, opens: true)
        case "options.presented":
            let set = optionSets.first { $0.id == ev.refID }
            return WorkspaceNote(id: id, kind: .options, text: set?.prompt ?? "Pick one of these options.", date: date,
                                 panel: .options, target: nil, task: ev.task, opens: true)
        case "task.failed":
            let why = ev.error ?? "failed"
            let what = ev.task.map { "\($0): " } ?? ""
            return WorkspaceNote(id: id, kind: .failure, text: what + why, date: date,
                                 panel: nil, target: nil, task: ev.task, opens: false)
        default:
            return nil
        }
    }

    /// The opening sentence of a summary.md (its first paragraph, without headings, bullets
    /// or markdown marks), for a one-line chat reply and panel comment.
    static func gist(of file: URL, limit: Int = 180) -> String? {
        guard let raw = try? String(contentsOf: file, encoding: .utf8) else { return nil }
        var paragraph: [String] = []
        for line in raw.components(separatedBy: .newlines) {
            var l = line.trimmingCharacters(in: .whitespaces)
            if l.hasPrefix("#") || l.hasPrefix("---") || l.hasPrefix("|") { continue }
            if l.isEmpty { if paragraph.isEmpty { continue } else { break } }
            if l.hasPrefix("- ") || l.hasPrefix("* ") {
                if !paragraph.isEmpty { break }
                l.removeFirst(2)
            }
            paragraph.append(l)
        }
        let text = paragraph.joined(separator: " ")
            .replacingOccurrences(of: "**", with: "")
            .replacingOccurrences(of: "`", with: "")
        guard !text.isEmpty else { return nil }
        var out = text
        text.enumerateSubstrings(in: text.startIndex..., options: .bySentences) { s, _, _, stop in
            if let s { out = s.trimmingCharacters(in: .whitespaces) }
            stop = true
        }
        if out.count > limit { out = String(out.prefix(limit - 1)).trimmingCharacters(in: .whitespaces) + "…" }
        return out
    }

    private static func parseDate(_ s: String) -> Date? {
        let f = ISO8601DateFormatter()
        if let d = f.date(from: s) { return d }
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f.date(from: s)
    }
}

extension PanelKind {
    /// Panel an agent role's finished work is about.
    static func forRole(_ role: String) -> PanelKind? {
        switch role {
        case "cad": return .cad
        case "sim": return .sim
        case "research": return .inspiration
        case "concept": return .options
        case "docs": return .docs
        case "controls": return .electronics
        default: return nil
        }
    }
}
