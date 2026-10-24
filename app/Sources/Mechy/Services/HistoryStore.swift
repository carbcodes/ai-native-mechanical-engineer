import Foundation
import Combine

/// One commit from `mechy history list`.
struct HistoryCommit: Identifiable, Hashable {
    static func == (a: HistoryCommit, b: HistoryCommit) -> Bool { a.sha == b.sha }
    func hash(into h: inout Hasher) { h.combine(sha) }
    let sha: String
    let short: String
    let time: String
    let message: String
    let author: String
    let task: String?
    let files: [(path: String, status: String)]
    let areas: [String]

    var id: String { sha }

    init(_ d: Loose) {
        sha = d.string("sha") ?? ""
        short = d.string("short") ?? String(sha.prefix(7))
        time = d.string("time") ?? ""
        message = d.string("message") ?? ""
        author = d.string("author") ?? ""
        task = d.string("task")
        files = d.dicts("files").map { (path: $0.string("path") ?? "", status: $0.string("status") ?? "") }
        areas = d.strings("areas")
    }

    /// "2 h ago" style relative time from the ISO 8601 commit timestamp.
    var relativeTime: String {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        var date = f.date(from: time)
        if date == nil {
            f.formatOptions = [.withInternetDateTime]
            date = f.date(from: time)
        }
        guard let date else { return time }
        return RelativeDateTimeFormatter().localizedString(for: date, relativeTo: Date())
    }

    /// design/<v>/... paths this commit touched (variant names).
    var designVariants: [String] {
        var seen: [String] = []
        for f in files where f.path.hasPrefix("design/") {
            let v = f.path.split(separator: "/").dropFirst().first.map(String.init) ?? ""
            if !v.isEmpty && !seen.contains(v) { seen.append(v) }
        }
        return seen
    }
}

/// Project history: `mechy history` commands for the open project.
final class HistoryStore: ObservableObject {
    @Published private(set) var commits: [HistoryCommit] = []
    @Published private(set) var dirty: [String] = []
    @Published private(set) var loading = false
    @Published var error: String?
    /// Patch text shown in the detail pane for the selected commit.
    @Published var patch: String = ""
    @Published var patchTruncated = false

    private weak var engine: EngineClient?
    private weak var session: ProjectSession?
    private var debounce: AnyCancellable?

    init(engine: EngineClient, session: ProjectSession) {
        self.engine = engine
        self.session = session
    }

    var project: URL? { session?.root }

    func reload() {
        guard let engine, let project else { return }
        loading = true
        engine.historyList(project: project) { [weak self] run in
            guard let self else { return }
            self.loading = false
            guard let r = run.result, r.bool("ok") == true else {
                self.error = run.result?.string("error")
                if case .failed(let why) = run.state, self.error == nil { self.error = why }
                return
            }
            self.error = nil
            self.commits = r.dicts("commits").map(HistoryCommit.init)
            self.dirty = r.strings("dirty")
        }
    }

    /// Reload at most once per 2 s (task done / file events call this).
    func scheduleReload() {
        debounce?.cancel()
        debounce = Just(())
            .delay(for: .seconds(2), scheduler: DispatchQueue.main)
            .sink { [weak self] _ in self?.reload() }
    }

    func showDiff(_ commit: HistoryCommit, path: String? = nil) {
        guard let engine, let project else { return }
        patch = ""
        patchTruncated = false
        engine.historyDiff(commit.sha, path: path, project: project) { [weak self] run in
            guard let self, let r = run.result else { return }
            if r.bool("ok") == true {
                self.patch = r.string("patch") ?? ""
                self.patchTruncated = r.bool("truncated") ?? false
            } else {
                self.patch = r.string("error") ?? "diff failed"
            }
        }
    }

    /// Write a file's content at `sha` into .mechy/history-cache/ and return the URL.
    func fileAt(_ commit: HistoryCommit, path: String, completion: @escaping (URL?) -> Void) {
        guard let engine, let project else { completion(nil); return }
        let name = path.split(separator: "/").last.map(String.init) ?? "file"
        let out = project.appendingPathComponent(".mechy/history-cache/\(commit.short)-\(name)")
        engine.historyShow(commit.sha, path: path, out: out, project: project) { run in
            completion(run.result?.bool("ok") == true ? out : nil)
        }
    }

    func snapshot(_ message: String) {
        guard let engine, let project else { return }
        engine.historySnapshot(message, project: project) { [weak self] _ in self?.reload() }
    }

    func restore(_ commit: HistoryCommit, path: String? = nil) {
        guard let engine, let project else { return }
        error = nil
        engine.historyRestore(commit.sha, path: path, project: project) { [weak self] run in
            guard let self else { return }
            if run.result?.bool("ok") != true {
                self.error = run.result?.string("error") ?? "restore failed"
            }
            self.reload()
        }
    }
}
