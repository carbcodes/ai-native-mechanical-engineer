import Foundation
import Combine

/// One running (or finished) `mechy` command.
final class EngineRun: ObservableObject, Identifiable {
    enum State: Equatable {
        case running
        case succeeded
        case failed(String)
    }

    let id = UUID()
    let label: String
    let symbol: String
    let arguments: [String]
    /// Project the command runs against (nil for init/doctor).
    let project: URL?
    let started = Date()

    @Published var state: State = .running
    @Published var message: String?
    @Published var fraction: Double?
    @Published var finished: Date?
    /// The final `{"type": "result", ...}` object, if any.
    @Published var result: Loose?
    /// Last lines of output (stdout non-JSON and stderr) for diagnostics.
    @Published var log: [String] = []
    /// Last JSON events printed by this run (newest last).
    @Published var events: [EngineEvent] = []
    /// Set when the user pressed Stop; the run then ends as "Stopped", not as a failure.
    @Published fileprivate(set) var stopRequested = false

    fileprivate var process: Process?

    init(label: String, symbol: String, arguments: [String], project: URL?) {
        self.label = label
        self.symbol = symbol
        self.arguments = arguments
        self.project = project
    }

    var isRunning: Bool { state == .running }

    /// The engine subcommand, e.g. "run", "cad", "sim".
    var command: String? { arguments.first }

    var wasStopped: Bool {
        if case .failed(let why) = state { return why == EngineRun.stoppedReason }
        return false
    }

    static let stoppedReason = "Stopped"

    fileprivate func appendEvent(_ ev: EngineEvent) {
        events.append(ev)
        if events.count > 60 { events.removeFirst(events.count - 60) }
    }

    fileprivate func appendLog(_ line: String) {
        log.append(line)
        if log.count > 300 { log.removeFirst(log.count - 300) }
    }
}

/// Starts `mechy` engine commands (contracts §3) and parses their `--json` event lines.
final class EngineClient: ObservableObject {
    @Published private(set) var runs: [EngineRun] = []

    /// Called on the main queue for every JSON event line printed by a run.
    var onEvent: ((EngineEvent, EngineRun) -> Void)?

    private var cancellables: [UUID: AnyCancellable] = [:]
    private var terminateObserver: NSObjectProtocol?

    /// Parallel agent jobs for `mechy run`.
    static let agentJobs = 2

    init() {
        // Quitting the app must not leave agents (and their CLIs) running in the project.
        terminateObserver = NotificationCenter.default.addObserver(
            // = NSApplication.willTerminateNotification, by name to stay out of main-actor isolation.
            forName: Notification.Name("NSApplicationWillTerminateNotification"), object: nil, queue: nil
        ) { [weak self] _ in
            self?.terminateAllNow()
        }
    }

    deinit {
        if let terminateObserver { NotificationCenter.default.removeObserver(terminateObserver) }
    }

    var mechyURL: URL? { EngineLocator.mechy }

    var activeRuns: [EngineRun] { runs.filter(\.isRunning) }

    // MARK: Contract commands

    @discardableResult
    func initProject(at dir: URL, example: String? = "tennis-catcher", name: String? = nil,
                     goal: String? = nil,
                     completion: @escaping (EngineRun) -> Void) -> EngineRun {
        var args = ["init", dir.path]
        if let example { args += ["--example", example] }
        if let name, !name.isEmpty { args += ["--name", name] }
        if let goal, !goal.isEmpty { args += ["--goal", goal] }
        return run(args, project: nil, label: "Create project", symbol: "folder.badge.plus", completion: completion)
    }

    /// `mechy accounts status`: installed/version/login per provider CLI.
    @discardableResult
    func accountsStatus(completion: @escaping (EngineRun) -> Void) -> EngineRun {
        run(["accounts", "status"], project: nil, label: "Accounts", symbol: "person.badge.key",
            completion: completion)
    }

    /// `mechy history list [--path P] [--limit N]`.
    @discardableResult
    func historyList(project: URL, path: String? = nil, limit: Int = 100,
                     completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        var args = ["history", "list", "--limit", String(limit)]
        if let path { args += ["--path", path] }
        return run(args, project: project, label: "History", symbol: "clock.arrow.circlepath",
                   completion: completion)
    }

    /// `mechy history show <sha> <path> --out <file>`: file contents at a commit.
    @discardableResult
    func historyShow(_ sha: String, path: String, out: URL, project: URL,
                     completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        run(["history", "show", sha, path, "--out", out.path], project: project,
            label: "Show \(path)", symbol: "doc", completion: completion)
    }

    /// `mechy history diff <sha> [--path P]`: patch + stats for a commit vs its parent.
    @discardableResult
    func historyDiff(_ sha: String, path: String? = nil, project: URL,
                     completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        var args = ["history", "diff", sha]
        if let path { args += ["--path", path] }
        return run(args, project: project, label: "Diff", symbol: "doc.badge.gearshape",
                   completion: completion)
    }

    /// `mechy history snapshot -m <msg>`: commit all current changes.
    @discardableResult
    func historySnapshot(_ message: String, project: URL,
                         completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        run(["history", "snapshot", "-m", message], project: project,
            label: "Save version", symbol: "checkmark.circle", completion: completion)
    }

    /// `mechy history restore <sha> [--path P]`: restore files (always a new commit).
    @discardableResult
    func historyRestore(_ sha: String, path: String? = nil, project: URL,
                        completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        var args = ["history", "restore", sha]
        if let path { args += ["--path", path] }
        return run(args, project: project, label: "Restore", symbol: "arrow.uturn.backward",
                   completion: completion)
    }

    @discardableResult
    func buildCAD(variant: String, project: URL, completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        run(["cad", "build", variant], project: project, label: "CAD \(variant)", symbol: "cube",
            completion: completion)
    }

    @discardableResult
    func runCatchSim(variant: String, project: URL, throwsCount: Int = 200,
                     completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        run(["sim", "catch", variant, "--throws", String(throwsCount)], project: project,
            label: "Sim \(variant)", symbol: "waveform.path.ecg", completion: completion)
    }

    /// `mechy sim pick <variant>`: payload map, cycle time and motor load of a pick-and-place arm.
    @discardableResult
    func runPickSim(variant: String, project: URL, completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        run(["sim", "pick", variant], project: project,
            label: "Pick sim \(variant)", symbol: "waveform.path.ecg", completion: completion)
    }

    /// The project's own sim: pick-and-place when requirements.yaml has a `pick:` block and no `catch:`.
    @discardableResult
    func runSim(variant: String, project: URL, completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        let req = FileIO.loadYAML(project.appendingPathComponent("requirements.yaml"))
        if req?.dict("pick") != nil && req?.dict("catch") == nil {
            return runPickSim(variant: variant, project: project, completion: completion)
        }
        return runCatchSim(variant: variant, project: project, completion: completion)
    }

    /// `mechy intake add <src>`: digest a link, video or image into inspiration/<slug>/ and
    /// inspiration/notes/<slug>.md. `source` is a URL or a file path.
    @discardableResult
    func intakeAdd(_ source: String, project: URL, completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        run(["intake", "add", source], project: project, label: "Intake", symbol: "square.and.arrow.down",
            completion: completion)
    }

    /// `mechy intake all`: digest every link / media file in inspiration/ that has no digest yet.
    @discardableResult
    func intakeAll(project: URL, completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        run(["intake", "all"], project: project, label: "Intake all", symbol: "square.and.arrow.down",
            completion: completion)
    }

    /// `mechy doc build <variant> [--print]`: docs/<variant>/build_guide.pdf and report.pdf.
    @discardableResult
    func docBuild(variant: String, printVersion: Bool = false, project: URL,
                  completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        var args = ["doc", "build", variant]
        if printVersion { args.append("--print") }
        return run(args, project: project, label: printVersion ? "Print docs \(variant)" : "Docs \(variant)",
                   symbol: "doc.richtext", completion: completion)
    }

    /// `mechy control gen <variant> [--board uno_cnc|mega_ramps]`: control/<variant>/{firmware, host, README.md}.
    @discardableResult
    func controlGen(variant: String, board: String? = nil, project: URL,
                    completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        var args = ["control", "gen", variant]
        if let board { args += ["--board", board] }
        return run(args, project: project, label: "Firmware \(variant)", symbol: "cpu", completion: completion)
    }

    /// A running command whose arguments start with `prefix` (e.g. ["doc", "build", "v2"]) in `project`.
    func activeRun(_ prefix: [String], project: URL) -> EngineRun? {
        let path = project.standardizedFileURL.path
        return runs.last { r in
            r.isRunning && r.project?.standardizedFileURL.path == path
                && r.arguments.count >= prefix.count && Array(r.arguments.prefix(prefix.count)) == prefix
        }
    }

    /// `mechy run --jobs 2 --project <p> --json`: the scheduler runs every ready task card.
    /// MECHY_PROVIDER comes from Settings (EngineLocator.childEnvironment).
    @discardableResult
    func runAgents(project: URL, jobs: Int = EngineClient.agentJobs) -> EngineRun {
        run(["run", "--jobs", String(jobs)], project: project, label: "Agents", symbol: "sparkles")
    }

    /// The running `mechy run` scheduler for a project, if any.
    func agentsRun(for project: URL) -> EngineRun? {
        let path = project.standardizedFileURL.path
        return runs.last { $0.isRunning && $0.command == "run" && $0.project?.standardizedFileURL.path == path }
    }

    /// The latest `mechy run` for a project (running or recently finished).
    func latestAgentsRun(for project: URL) -> EngineRun? {
        let path = project.standardizedFileURL.path
        return runs.last { $0.command == "run" && $0.project?.standardizedFileURL.path == path }
    }

    @discardableResult
    func runTask(_ taskID: String, project: URL) -> EngineRun {
        run(["agent", "run", taskID], project: project, label: taskID, symbol: "play")
    }

    @discardableResult
    func plan(project: URL, completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        run(["plan"], project: project, label: "Planner", symbol: "map", completion: completion)
    }

    @discardableResult
    func doctor(completion: @escaping (EngineRun) -> Void) -> EngineRun {
        run(["doctor"], project: nil, label: "Doctor", symbol: "stethoscope", completion: completion)
    }

    /// Stop a run and every process it started (agent CLIs, their tools): SIGTERM to the
    /// whole tree, then SIGKILL to whatever is still alive after a grace period.
    func cancel(_ run: EngineRun) {
        guard run.isRunning else { return }
        run.stopRequested = true
        run.message = "stopping…"
        guard let process = run.process, process.isRunning else { return }
        ProcessTree.terminate(root: process.processIdentifier)
    }

    /// Synchronous best-effort SIGTERM of every running tree (app is quitting).
    private func terminateAllNow() {
        for run in runs where run.isRunning {
            guard let p = run.process, p.isRunning else { continue }
            ProcessTree.signalTree(root: p.processIdentifier, signal: SIGTERM)
        }
    }

    /// Drop finished runs older than `age` seconds from the list.
    func pruneFinished(olderThan age: TimeInterval = 30) {
        let now = Date()
        runs.removeAll { r in
            guard let f = r.finished else { return false }
            return now.timeIntervalSince(f) > age
        }
    }

    // MARK: Process plumbing

    /// Run `mechy <args> [--project <dir>] --json`. Always returns a run; if `mechy`
    /// cannot be found the run is already failed with an explanation.
    @discardableResult
    func run(_ args: [String], project: URL?, label: String, symbol: String,
             completion: ((EngineRun) -> Void)? = nil) -> EngineRun {
        var full = args
        if let project { full += ["--project", project.path] }
        full.append("--json")
        let run = EngineRun(label: label, symbol: symbol, arguments: full, project: project)
        runs.append(run)
        // Re-publish when a child run changes, so views observing the client refresh.
        cancellables[run.id] = run.objectWillChange.sink { [weak self] _ in self?.objectWillChange.send() }

        guard let exe = mechyURL else {
            finish(run, status: -1, reason: "mechy not found. Set its path in Settings.", completion: completion)
            return run
        }

        let process = Process()
        process.executableURL = exe
        process.arguments = full
        process.environment = EngineLocator.childEnvironment()
        if let project { process.currentDirectoryURL = project }
        process.standardInput = FileHandle.nullDevice
        let out = Pipe()
        let err = Pipe()
        process.standardOutput = out
        process.standardError = err
        run.process = process

        let stdoutLines = LineBuffer { [weak self, weak run] line in
            guard let self, let run else { return }
            DispatchQueue.main.async { self.handleStdout(line, run: run) }
        }
        let stderrLines = LineBuffer { [weak run] line in
            DispatchQueue.main.async { run?.appendLog(line) }
        }
        out.fileHandleForReading.readabilityHandler = { h in
            let data = h.availableData
            if data.isEmpty { h.readabilityHandler = nil } else { stdoutLines.append(data) }
        }
        err.fileHandleForReading.readabilityHandler = { h in
            let data = h.availableData
            if data.isEmpty { h.readabilityHandler = nil } else { stderrLines.append(data) }
        }

        process.terminationHandler = { [weak self] proc in
            // Drain whatever the readability handlers have not delivered yet.
            out.fileHandleForReading.readabilityHandler = nil
            err.fileHandleForReading.readabilityHandler = nil
            stdoutLines.append(out.fileHandleForReading.readDataToEndOfFile())
            stderrLines.append(err.fileHandleForReading.readDataToEndOfFile())
            stdoutLines.flush()
            stderrLines.flush()
            let status = proc.terminationStatus
            DispatchQueue.main.async {
                self?.finish(run, status: status, reason: nil, completion: completion)
            }
        }

        do {
            try process.run()
        } catch {
            finish(run, status: -1, reason: "Could not start mechy: \(error.localizedDescription)", completion: completion)
        }
        return run
    }

    private func handleStdout(_ line: String, run: EngineRun) {
        let trimmed = line.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { return }
        guard trimmed.hasPrefix("{"), let d = FileIO.parseJSONLine(trimmed), let ev = EngineEvent(d) else {
            run.appendLog(trimmed)
            run.message = String(trimmed.prefix(80))
            return
        }
        switch ev.type {
        case "result":
            run.result = d
            if let m = d.string("message") ?? d.string("summary") { run.message = m }
        case "task.progress":
            run.message = ev.message
            run.fraction = ev.fraction
        case "task.failed":
            run.message = ev.error
        default:
            run.message = ev.shortText
        }
        run.appendLog(trimmed)
        run.appendEvent(ev)
        onEvent?(ev, run)
    }

    private func finish(_ run: EngineRun, status: Int32, reason: String?, completion: ((EngineRun) -> Void)?) {
        guard run.state == .running else { return }
        let resultOK = run.result?.bool("ok") ?? true
        if run.stopRequested {
            run.state = .failed(EngineRun.stoppedReason)
            run.message = "stopped"
            run.appendLog("Stopped by user")
        } else if status == 0 && resultOK {
            run.state = .succeeded
            run.fraction = 1
        } else {
            let why = reason
                ?? run.result?.string("error")
                ?? run.log.last
                ?? "exit code \(status)"
            run.state = .failed(why)
            run.message = why
            if let reason { run.appendLog(reason) }
        }
        run.finished = Date()
        run.process = nil
        completion?(run)
    }
}

/// Finds and signals a process and all its descendants (macOS `ps` snapshot).
///
/// `Process` cannot put the child in its own process group, so killing the tree means
/// walking it: freeze the root (SIGSTOP) so it cannot start new children while we look,
/// snapshot the descendants, SIGTERM everyone, let the root run again to handle SIGTERM,
/// and SIGKILL whatever is still alive after `grace` seconds.
enum ProcessTree {
    static func descendants(of root: pid_t) -> [pid_t] {
        let ps = Process()
        ps.executableURL = URL(fileURLWithPath: "/bin/ps")
        ps.arguments = ["-A", "-o", "pid=,ppid="]
        let pipe = Pipe()
        ps.standardOutput = pipe
        ps.standardError = FileHandle.nullDevice
        ps.standardInput = FileHandle.nullDevice
        do { try ps.run() } catch { return [] }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        ps.waitUntilExit()
        var children: [pid_t: [pid_t]] = [:]
        for line in String(decoding: data, as: UTF8.self).split(separator: "\n") {
            let parts = line.split(separator: " ", omittingEmptySubsequences: true)
            guard parts.count >= 2, let pid = pid_t(parts[0]), let ppid = pid_t(parts[1]) else { continue }
            children[ppid, default: []].append(pid)
        }
        var out: [pid_t] = []
        var queue: [pid_t] = [root]
        var seen: Set<pid_t> = [root]
        while !queue.isEmpty {
            let p = queue.removeFirst()
            for c in children[p] ?? [] where seen.insert(c).inserted {
                out.append(c)
                queue.append(c)
            }
        }
        return out
    }

    /// Signal the root and its current descendants (deepest first, root last).
    static func signalTree(root: pid_t, signal: Int32) {
        for pid in descendants(of: root).reversed() { kill(pid, signal) }
        kill(root, signal)
    }

    static func isAlive(_ pid: pid_t) -> Bool { kill(pid, 0) == 0 }

    static func terminate(root: pid_t, grace: TimeInterval = 3) {
        DispatchQueue.global(qos: .userInitiated).async {
            kill(root, SIGSTOP)
            let tree = ProcessTree.descendants(of: root)
            for pid in tree.reversed() { kill(pid, SIGTERM) }
            kill(root, SIGTERM)
            kill(root, SIGCONT)
            DispatchQueue.global(qos: .userInitiated).asyncAfter(deadline: .now() + grace) {
                // Children started by survivors in the meantime, too.
                var all = Set(tree)
                all.insert(root)
                for pid in all where ProcessTree.isAlive(pid) {
                    for d in ProcessTree.descendants(of: pid) { all.insert(d) }
                }
                for pid in all where ProcessTree.isAlive(pid) { kill(pid, SIGKILL) }
            }
        }
    }
}

/// Splits a byte stream into UTF-8 lines. Thread-safe.
private final class LineBuffer {
    private var buffer = Data()
    private let lock = NSLock()
    private let onLine: (String) -> Void

    init(onLine: @escaping (String) -> Void) { self.onLine = onLine }

    func append(_ data: Data) {
        guard !data.isEmpty else { return }
        var lines: [String] = []
        lock.lock()
        buffer.append(data)
        while let nl = buffer.firstIndex(of: 0x0A) {
            let lineData = buffer[buffer.startIndex..<nl]
            lines.append(String(decoding: lineData, as: UTF8.self))
            buffer.removeSubrange(buffer.startIndex...nl)
        }
        lock.unlock()
        lines.forEach(onLine)
    }

    func flush() {
        lock.lock()
        let rest = buffer
        buffer.removeAll()
        lock.unlock()
        if !rest.isEmpty { onLine(String(decoding: rest, as: UTF8.self)) }
    }
}
