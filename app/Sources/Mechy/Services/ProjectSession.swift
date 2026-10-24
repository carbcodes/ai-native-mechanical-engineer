import Foundation
import AppKit
import UniformTypeIdentifiers

/// Everything the app knows about one open project folder.
///
/// It reads the contract files (contracts.md §1-6), refreshes when the folder
/// changes, tails the event log, owns the canvas layout, and performs the few
/// writes the app is allowed to make (answers, choices, feedback, inspiration,
/// inbox requests).
final class ProjectSession: ObservableObject {
    let root: URL
    let engine: EngineClient

    // MARK: Project contents
    @Published private(set) var name: String
    @Published private(set) var tree: [FileNode] = []
    @Published private(set) var variants: [DesignVariant] = []
    @Published private(set) var chosenVariant: String?
    @Published private(set) var optionSets: [OptionSetDoc] = []
    @Published private(set) var questions: [Question] = []
    @Published private(set) var tasks: [TaskCard] = []
    @Published private(set) var simReports: [SimReport] = []
    @Published private(set) var inspiration: [InspirationItem] = []
    @Published private(set) var docs: [URL] = []
    /// docs/<variant>/*.pdf per variant, then loose files at the top of docs/.
    @Published private(set) var docGroups: [DocGroup] = []
    /// Digested inspiration sources (inspiration/<slug>/source.json), newest first.
    @Published private(set) var digests: [InspirationDigest] = []
    /// `mechy intake add` runs started from the Inspiration panel (running or failed).
    @Published private(set) var intakeJobs: [IntakeJob] = []
    @Published private(set) var targetCatchRate: Double?
    /// "pick" when requirements.yaml has a `pick:` block (pick-and-place project), else "catch".
    @Published private(set) var simKind = "catch"
    /// hw/drivers.yaml + hw/motors.yaml (Electronics panel).
    @Published private(set) var hardware = HardwareSpec()
    /// Chat history: what the user asked Mechy (inbox/), newest last.
    @Published private(set) var requests: [UserRequest] = []
    @Published private(set) var events: [EngineEvent] = []
    /// What Mechy said while working (task summaries, pinned comments, questions), oldest first.
    @Published private(set) var notes: [WorkspaceNote] = []
    /// Notes the user closed on their panel (they stay in the chat).
    @Published private(set) var dismissedNotes: Set<String>
    /// Bumped after every reload; views use it to refresh thumbnails.
    @Published private(set) var revision = 0

    // MARK: Canvas
    @Published var layout: CanvasLayout
    /// Visible canvas size in points, reported by CanvasView.
    var viewportSize = CGSize(width: 1200, height: 800)
    /// False until the layout has been fitted to the real canvas size once (see `fitToViewportAtLaunch`).
    private(set) var didLaunchFit = false
    /// True when `layout` came from UserDefaults (and was arranged by the user) rather than a default.
    private let hasSavedLayout: Bool

    /// Variant the user is looking at in a CAD panel.
    @Published var focusedVariant: String?

    /// One-click "Make it" (CAD -> sim -> firmware -> docs) for the chosen variant.
    let pipeline = MakeItPipeline()
    /// `mechy history` state for the History panel (created on first use).
    lazy var history = HistoryStore(engine: engine, session: self)

    private var watcher: DirectoryWatcher?
    private let eventTail: EventTail
    private var pendingReload: DispatchWorkItem?
    /// When the project was opened; panels only carry comments from around this sitting.
    private let openedAt = Date()
    /// False until notes have been rebuilt from the event history after the first load.
    private var notesBuilt = false
    private let loadQueue = DispatchQueue(label: "mechy.project.load", qos: .userInitiated)

    init(root: URL, engine: EngineClient) {
        self.root = root.standardizedFileURL
        self.engine = engine
        self.name = root.lastPathComponent
        self.eventTail = EventTail(url: root.appendingPathComponent(".mechy/events.jsonl"))
        dismissedNotes = Set(UserDefaults.standard.stringArray(forKey: "mechy.dismissedNotes." + root.standardizedFileURL.path) ?? [])
        if let data = UserDefaults.standard.data(forKey: SettingsKey.layout(for: root)),
           let saved = try? JSONDecoder().decode(CanvasLayout.self, from: data) {
            layout = saved
            // The fixed pre-1.1 default ran off smaller windows; treat it as "never arranged".
            hasSavedLayout = !saved.isLegacyDefault
        } else {
            layout = .initial
            hasSavedLayout = false
        }
    }

    // MARK: Lifecycle

    func start() {
        reload()
        events = Array(eventTail.readRecent().suffix(200))
        // Live events from engine commands started by the app (stdout `--json` lines). The
        // same events are also appended to .mechy/events.jsonl; `ingest` drops duplicates.
        let rootPath = root.path
        engine.onEvent = { [weak self] ev, run in
            guard let self, run.project?.standardizedFileURL.path == rootPath else { return }
            self.ingest([ev])
        }
        let resolvedRoot = root.resolvingSymlinksInPath().path
        watcher = DirectoryWatcher(url: root) { [weak self] paths in
            self?.handleChanges(paths, resolvedRoot: resolvedRoot)
        }
        watcher?.start()
    }

    func stop() {
        engine.onEvent = nil
        watcher?.stop()
        watcher = nil
        saveLayout()
    }

    private func handleChanges(_ paths: [String], resolvedRoot: String) {
        var needsReload = false
        for p in paths {
            if p.hasSuffix("/.mechy/events.jsonl") {
                ingest(eventTail.readNew())
                continue
            }
            if p.contains("/.git/") || p.hasSuffix("/.git") || p.contains("/.mechy/") { continue }
            needsReload = true
        }
        if needsReload { scheduleReload() }
    }

    func scheduleReload() {
        pendingReload?.cancel()
        let work = DispatchWorkItem { [weak self] in self?.reload() }
        pendingReload = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15, execute: work)
    }

    /// Add events from the log tail or a live run, skipping ones already seen (the engine
    /// writes each event to both stdout and events.jsonl).
    func ingest(_ new: [EngineEvent]) {
        guard !new.isEmpty else { return }
        var recent = Set(events.suffix(300).compactMap(\.dedupeKey))
        var added = false
        for ev in new {
            if let key = ev.dedupeKey {
                if recent.contains(key) { continue }
                recent.insert(key)
            }
            events.append(ev)
            added = true
            // Live: Mechy says something, and brings up the panel it is about.
            if notesBuilt, let note = makeNote(ev), !notes.contains(where: { $0.id == note.id }) {
                notes.append(note)
                if notes.count > 100 { notes.removeFirst(notes.count - 100) }
                if note.opens { reveal(note) }
            }
        }
        guard added else { return }
        if events.count > 200 { events.removeFirst(events.count - 200) }
        // Task states live in tasks/*.status.json; a task event means one probably changed.
        let stateChanges: Set<String> = ["task.started", "task.done", "task.failed"]
        if new.contains(where: { stateChanges.contains($0.type) }) { scheduleReload() }
    }

    /// Re-read all contract files on a background queue, then publish.
    func reload() {
        let root = self.root
        loadQueue.async {
            let snap = Snapshot.load(root: root)
            DispatchQueue.main.async { self.apply(snap) }
        }
    }

    private func apply(_ s: Snapshot) {
        name = s.name
        tree = s.tree
        variants = s.variants
        chosenVariant = s.chosenVariant
        optionSets = s.optionSets
        questions = s.questions
        tasks = s.tasks
        simReports = s.simReports
        inspiration = s.inspiration
        docs = s.docs
        docGroups = s.docGroups
        digests = s.digests
        targetCatchRate = s.targetCatchRate
        simKind = s.simKind
        if hardware != s.hardware { hardware = s.hardware }
        if requests != s.requests { requests = s.requests }
        // A finished intake's card gives way to its digest once the files are loaded.
        intakeJobs.removeAll { $0.run.state == .succeeded }
        revision += 1
        if !notesBuilt {
            notesBuilt = true
            notes = events.compactMap(makeNote)
        }
    }

    // MARK: Mechy in the workspace

    private func makeNote(_ ev: EngineEvent) -> WorkspaceNote? {
        let tasks = self.tasks
        return WorkspaceNote.from(ev, root: root, role: { id in tasks.first { $0.id == id }?.role },
                                  questions: questions, optionSets: optionSets)
    }

    /// The comment pinned on a panel kind: the newest note about it the user has not closed,
    /// from this sitting (older ones stay in the chat only). Questions and options are not
    /// pinned: their own panels already show them.
    func pinnedNote(for kind: PanelKind) -> WorkspaceNote? {
        let since = openedAt.addingTimeInterval(-30 * 60)
        return notes.last { $0.panel == kind && $0.kind == .note && $0.date > since && !dismissedNotes.contains($0.id) }
    }

    func dismiss(_ note: WorkspaceNote) {
        dismissedNotes.insert(note.id)
        UserDefaults.standard.set(Array(dismissedNotes.suffix(300)), forKey: "mechy.dismissedNotes." + root.standardizedFileURL.path)
    }

    /// Bring up the panel a note is about, showing its target (variant, sim run, document).
    func reveal(_ note: WorkspaceNote) {
        guard let kind = note.panel else { return }
        switch kind {
        case .cad where note.target.map { t in variants.contains { $0.name == t } } == true:
            showVariant(note.target!)
        case .docs where note.target != nil:
            preview(url(note.target!))
        default:
            focus(kind)
            if let t = note.target, [.sim, .parts, .loads, .manufacturing].contains(kind),
               let p = layout.panels.filter({ $0.kind == kind }).max(by: { $0.z < $1.z }) {
                setParam(p.id, t)
            }
        }
    }

    // MARK: Derived

    /// The variant toolbar actions apply to.
    var activeVariant: String? {
        if let f = focusedVariant, variants.contains(where: { $0.name == f }) { return f }
        if let c = chosenVariant, variants.contains(where: { $0.name == c }) { return c }
        return variants.last?.name ?? chosenVariant
    }

    var openQuestions: [Question] { questions.filter { !$0.isAnswered } }
    var openOptionSets: [OptionSetDoc] { optionSets.filter(\.isOpen) }

    func url(_ relative: String) -> URL { root.appendingPathComponent(relative) }

    /// Latest event for a task id.
    func lastEvent(forTask task: String) -> EngineEvent? {
        events.last { $0.task == task }
    }

    /// Latest event for a task id that carries a progress fraction.
    func lastProgress(forTask task: String) -> EngineEvent? {
        events.last { $0.task == task && $0.fraction != nil }
    }

    // MARK: Engine actions

    func buildCAD(_ variant: String? = nil) {
        guard let v = variant ?? activeVariant else { return }
        engine.buildCAD(variant: v, project: root)
    }

    func runCatchSim(_ variant: String? = nil) {
        guard let v = variant ?? activeVariant else { return }
        engine.runCatchSim(variant: v, project: root)
    }

    func runPickSim(_ variant: String? = nil) {
        guard let v = variant ?? activeVariant else { return }
        engine.runPickSim(variant: v, project: root)
    }

    /// The sim this project runs: pick-and-place when its requirements say so, else the catch sweep.
    func runSim(_ variant: String? = nil, kind: String? = nil) {
        if (kind ?? simKind) == "pick" { runPickSim(variant) } else { runCatchSim(variant) }
    }

    /// Start the scheduler (`mechy run --jobs 2`), unless it is already running here.
    func runAgents() {
        if engine.agentsRun(for: root) != nil { return }
        engine.runAgents(project: root)
    }

    /// The running `mechy run` for this project, if any.
    var agentsRun: EngineRun? { engine.agentsRun(for: root) }

    /// Stop the planner, the scheduler and every agent process it started.
    func stopAgents() {
        for run in engine.runs where run.isRunning && ["plan", "run"].contains(run.command ?? "")
            && run.project?.standardizedFileURL.path == root.path {
            engine.cancel(run)
        }
    }

    func runTask(_ id: String) { engine.runTask(id, project: root) }

    /// Variant "Make it" and the docs/firmware buttons default to: design/chosen, else the active one.
    var makeVariant: String? {
        if let c = chosenVariant, variants.contains(where: { $0.name == c }) { return c }
        return activeVariant
    }

    /// `mechy doc build <v> [--print]`; when it finishes, the newest PDF of docs/<v>/ is shown.
    func buildDocs(_ variant: String? = nil, printVersion: Bool = false, showWhenDone: Bool = true) {
        guard let v = variant ?? makeVariant else { return }
        engine.docBuild(variant: v, printVersion: printVersion, project: root) { [weak self] run in
            guard let self, run.state == .succeeded else { return }
            self.reload()
            if showWhenDone { self.showNewestDoc(of: v, preferPrint: printVersion) }
        }
    }

    /// `mechy control gen <v> [--board b]`, then reveal control/<v>/ in Finder.
    func generateFirmware(_ variant: String? = nil, board: String? = nil, revealWhenDone: Bool = true) {
        guard let v = variant ?? makeVariant else { return }
        engine.controlGen(variant: v, board: board, project: root) { [weak self] run in
            guard let self, run.state == .succeeded else { return }
            if revealWhenDone { Finder.reveal(self.url("control/\(v)")) }
        }
    }

    /// Show the newest PDF in docs/<v>/ in a Docs panel (the print version if asked for and present).
    func showNewestDoc(of variant: String, preferPrint: Bool = false) {
        let dir = url("docs/\(variant)")
        let pdfs = FileIO.files(in: dir, extensions: ["pdf"])
        let pool = preferPrint ? pdfs.filter { $0.lastPathComponent.lowercased().contains("print") } : []
        let pick = (pool.isEmpty ? pdfs : pool).max { (FileIO.modified($0) ?? .distantPast) < (FileIO.modified($1) ?? .distantPast) }
        if let pick { preview(pick) }
    }

    /// Build CAD -> run sim -> generate firmware -> build docs for one variant, stopping at the
    /// first failure. When every step passed, the build guide opens in a Docs panel.
    func makeIt(_ variant: String? = nil) {
        guard let v = variant ?? makeVariant else { return }
        pipeline.start(variant: v, project: root, engine: engine) { [weak self] v in
            guard let self else { return }
            self.reload()
            let guide = self.url("docs/\(v)/build_guide.pdf")
            if FileIO.exists(guide) { self.preview(guide) } else { self.showNewestDoc(of: v) }
        }
    }

    /// Chat request: write inbox/<timestamp>.md, run the planner, then start the agents on
    /// the cards it wrote. One message is all it takes; there is no separate "run" step.
    /// (`inbox/` is a proposed contract addition, see app/README.md.)
    func sendRequest(_ text: String) {
        let body = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !body.isEmpty else { return }
        let inbox = url("inbox")
        do {
            try FileManager.default.createDirectory(at: inbox, withIntermediateDirectories: true)
            let file = FileIO.uniqueURL(in: inbox, name: FileIO.timestamp() + ".md")
            let content = "---\nfrom: user\ncreated: \(FileIO.iso())\n---\n\n\(body)\n"
            try content.write(to: file, atomically: true, encoding: .utf8)
            engine.plan(project: root) { [weak self] run in
                guard let self, run.state == .succeeded else { return }
                self.reload()
                self.runAgents()
            }
            scheduleReload()
        } catch {
            NSSound.beep()
        }
    }

    // MARK: Writes to contract files

    func choose(_ option: OptionChoice, in set: OptionSetDoc) {
        try? YAMLPatch.apply([("chosen", .string(option.id))], to: set.fileURL)
        // An option named after a design/<id>/ folder picks that variant: write design/chosen
        // (contracts §1) and show it in the CAD panel.
        if FileIO.isDirectory(url("design/\(option.id)")) {
            setChosenVariant(option.id)
        }
        scheduleReload()
    }

    /// Write design/chosen and show the variant in the front-most CAD panel.
    func setChosenVariant(_ variant: String) {
        do {
            try FileManager.default.createDirectory(at: url("design"), withIntermediateDirectories: true)
            try (variant + "\n").write(to: url("design/chosen"), atomically: true, encoding: .utf8)
            chosenVariant = variant
        } catch {
            NSSound.beep()
        }
        showVariant(variant)
    }

    func sendFeedback(_ text: String, in set: OptionSetDoc) {
        let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return }
        try? YAMLPatch.apply([("feedback", .string(t))], to: set.fileURL)
        scheduleReload()
    }

    func answer(_ question: Question, with value: YAMLScalar) {
        try? YAMLPatch.apply([("answer", value)], to: question.fileURL)
        scheduleReload()
    }

    /// Copy an image chosen for an `image` question into inspiration/ and answer with its path.
    func answer(_ question: Question, withImageAt source: URL) {
        if let copied = importFile(source) {
            answer(question, with: .string(FileIO.relativePath(copied, to: root)))
        }
    }

    // MARK: Inspiration

    @discardableResult
    func importFile(_ source: URL) -> URL? {
        let dir = url("inspiration")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        if source.standardizedFileURL.path.hasPrefix(dir.path + "/") { return source }
        let dest = FileIO.uniqueURL(in: dir, name: source.lastPathComponent)
        do {
            try FileManager.default.copyItem(at: source, to: dest)
            scheduleReload()
            return dest
        } catch {
            return nil
        }
    }

    func importImageData(_ data: Data, ext: String) {
        let dir = url("inspiration")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let dest = FileIO.uniqueURL(in: dir, name: "dropped-\(FileIO.timestamp()).\(ext)")
        do {
            try data.write(to: dest)
            startIntake(FileIO.relativePath(dest, to: root), title: dest.lastPathComponent)
        } catch {
            NSSound.beep()
        }
        scheduleReload()
    }

    /// A file dropped on (or picked for) the inspiration board. Images and videos are digested
    /// with `mechy intake add`; anything else is copied into inspiration/.
    /// - Image from outside the project: the engine keeps only an EXIF-free copy, so the original
    ///   (with its GPS/camera data) is not copied in. If the intake fails, it is copied as before.
    /// - Video: copied into inspiration/ first (the digest refers to it), then digested.
    func ingestFile(_ source: URL) {
        let kind = InspirationItem.classify(source)
        let inside = source.standardizedFileURL.path.hasPrefix(root.standardizedFileURL.path + "/")
        switch kind {
        case .image:
            let arg = inside ? FileIO.relativePath(source, to: root) : source.standardizedFileURL.path
            startIntake(arg, title: source.lastPathComponent) { [weak self] run in
                if !inside, run.state != .succeeded, !run.wasStopped { self?.importFile(source) }
            }
        case .video:
            guard let copied = importFile(source) else { NSSound.beep(); return }
            startIntake(FileIO.relativePath(copied, to: root), title: copied.lastPathComponent)
        case _ where ["html", "htm"].contains(source.pathExtension.lowercased()):
            // A saved web page: digested like a link (page.txt, images/).
            guard let copied = importFile(source) else { NSSound.beep(); return }
            startIntake(FileIO.relativePath(copied, to: root), title: copied.lastPathComponent)
        default:
            importFile(source)
        }
    }

    /// Run `mechy intake add <source>` and show a card for it until the digest appears.
    func startIntake(_ source: String, title: String? = nil, completion: ((EngineRun) -> Void)? = nil) {
        if intakeJobs.contains(where: { $0.source == source && $0.run.isRunning }) { return }
        intakeJobs.removeAll { $0.source == source }
        let run = engine.intakeAdd(source, project: root) { [weak self] run in
            completion?(run)
            self?.reload()
        }
        intakeJobs.append(IntakeJob(source: source, title: title ?? IntakeJob.title(for: source), run: run))
    }

    func retryIntake(_ job: IntakeJob) {
        startIntake(job.source, title: job.title)
    }

    func dismissIntake(_ job: IntakeJob) {
        if job.run.isRunning { engine.cancel(job.run) }
        intakeJobs.removeAll { $0.id == job.id }
    }

    /// Re-digest a source (e.g. after the engine learned something new).
    func redigest(_ d: InspirationDigest) {
        let source = d.url?.absoluteString ?? d.input ?? d.sourcePath
        if let source { startIntake(source, title: d.title) }
    }

    /// `mechy intake all`: every link and media file in inspiration/ without a digest.
    func digestAllPending() {
        if engine.activeRun(["intake", "all"], project: root) != nil { return }
        engine.intakeAll(project: root) { [weak self] _ in self?.reload() }
    }

    /// Append a link to inspiration/links.yaml as `links: [{url, title, added}]`, then digest it
    /// (`mechy intake add <url>`), unless `digest` is false.
    func addLink(_ link: URL, title: String? = nil, digest: Bool = true) {
        guard let scheme = link.scheme?.lowercased(), scheme == "http" || scheme == "https" else { return }
        let file = url("inspiration/links.yaml")
        var entries: [[String: Any]] = []
        if let d = FileIO.loadYAML(file) {
            for item in (d.raw["links"] as? [Any]) ?? [] {
                if let s = item as? String { entries.append(["url": s]) }
                else if let l = Loose(any: item) { entries.append(l.raw) }
            }
        }
        if entries.contains(where: { Loose.text($0["url"]) == link.absoluteString }) {
            // Already on the board: digest it if that has not happened yet.
            if digest, !digests.contains(where: { $0.url?.absoluteString == link.absoluteString }) {
                startIntake(link.absoluteString)
            }
            return
        }
        var entry: [String: Any] = ["url": link.absoluteString, "added": FileIO.iso()]
        if let title, !title.isEmpty { entry["title"] = title }
        entries.append(entry)
        var text = "links:\n"
        for e in entries {
            let keys = ["url", "title", "added"] + e.keys.filter { !["url", "title", "added"].contains($0) }.sorted()
            var first = true
            for k in keys {
                guard let v = Loose.text(e[k]) else { continue }
                text += (first ? "  - " : "    ") + "\(k): \(YAMLScalar.quote(v))\n"
                first = false
            }
        }
        try? FileManager.default.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? text.write(to: file, atomically: true, encoding: .utf8)
        scheduleReload()
        if digest { startIntake(link.absoluteString) }
    }

    /// Handle a drop of files, images or links onto the inspiration board.
    func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        var handled = false
        for provider in providers {
            if provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) {
                handled = true
                provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                    guard let url = ProjectSession.url(from: item) else { return }
                    DispatchQueue.main.async { self.ingestFile(url) }
                }
            } else if let imageType = provider.registeredTypeIdentifiers.first(where: {
                UTType($0)?.conforms(to: .image) == true
            }) {
                handled = true
                let ext = UTType(imageType)?.preferredFilenameExtension ?? "png"
                _ = provider.loadDataRepresentation(forTypeIdentifier: imageType) { data, _ in
                    guard let data else { return }
                    DispatchQueue.main.async { self.importImageData(data, ext: ext) }
                }
            } else if provider.hasItemConformingToTypeIdentifier(UTType.url.identifier) {
                handled = true
                provider.loadItem(forTypeIdentifier: UTType.url.identifier, options: nil) { item, _ in
                    guard let url = ProjectSession.url(from: item) else { return }
                    DispatchQueue.main.async {
                        if url.isFileURL { self.ingestFile(url) } else { self.addLink(url) }
                    }
                }
            }
        }
        return handled
    }

    private static func url(from item: NSSecureCoding?) -> URL? {
        if let u = item as? URL { return u }
        if let u = item as? NSURL { return u as URL }
        if let d = item as? Data { return URL(dataRepresentation: d, relativeTo: nil) }
        if let s = item as? String { return URL(string: s) }
        return nil
    }

    // MARK: Canvas layout

    func saveLayout() {
        if let data = try? JSONEncoder().encode(layout) {
            UserDefaults.standard.set(data, forKey: SettingsKey.layout(for: root))
        }
    }

    /// Lay the default panels out to fill the visible canvas.
    func resetLayout() {
        layout = .initial(fitting: viewportSize)
        saveLayout()
    }

    /// Called once by CanvasView when the canvas has its real size: a new project gets the
    /// default sheet laid out for that size; a saved layout that runs off the window
    /// (e.g. saved in a bigger window) is zoomed and panned so every panel is visible.
    func fitToViewportAtLaunch(_ size: CGSize) {
        guard !didLaunchFit, size.width > 100, size.height > 100 else { return }
        didLaunchFit = true
        viewportSize = size
        if !hasSavedLayout {
            resetLayout()
        } else if !layout.allPanelsVisible(in: size) {
            zoomToFit()
        }
    }

    @discardableResult
    func addPanel(_ kind: PanelKind, param: String? = nil) -> UUID {
        let size = kind.defaultSize
        let z = layout.zoom
        // Centre of the visible area, in canvas coordinates, nudged so stacked adds stay visible.
        let cx = (viewportSize.width / 2 - layout.panX) / z
        let cy = (viewportSize.height / 2 - layout.panY) / z
        let nudge = Double(layout.panels.count % 5) * 24
        let panel = PanelState(kind: kind,
                               x: cx - size.width / 2 + nudge,
                               y: cy - size.height / 2 + nudge,
                               w: size.width, h: size.height,
                               z: layout.topZ + 1, param: param)
        layout.panels.append(panel)
        saveLayout()
        return panel.id
    }

    /// Bring an existing panel of this kind to the front (scrolling the sheet to it), or add one.
    func focus(_ kind: PanelKind) {
        if let p = layout.panels.filter({ $0.kind == kind }).max(by: { $0.z < $1.z }) {
            bringToFront(p.id)
            scrollIntoView(p.id)
        } else {
            addPanel(kind)
        }
    }

    /// Pan the sheet so the panel is fully on screen (centred when it was off screen).
    func scrollIntoView(_ id: UUID) {
        guard let p = layout.panels.first(where: { $0.id == id }) else { return }
        let z = layout.zoom
        let minX = p.x * z + layout.panX, minY = p.y * z + layout.panY
        let maxX = minX + p.w * z, maxY = minY + p.h * z
        let vw = Double(viewportSize.width), vh = Double(viewportSize.height)
        guard minX < 0 || minY < 0 || maxX > vw || maxY > vh else { return }
        layout.panX = vw / 2 - (p.x + p.w / 2) * z
        layout.panY = vh / 2 - (p.y + p.h / 2) * z
        saveLayout()
    }

    func bringToFront(_ id: UUID) {
        guard let i = layout.panels.firstIndex(where: { $0.id == id }) else { return }
        let top = layout.topZ
        if layout.panels[i].z == top { return }
        layout.panels[i].z = top + 1
        saveLayout()
    }

    func closePanel(_ id: UUID) {
        layout.panels.removeAll { $0.id == id }
        saveLayout()
    }

    func movePanel(_ id: UUID, dx: Double, dy: Double) {
        guard let i = layout.panels.firstIndex(where: { $0.id == id }) else { return }
        layout.panels[i].x += dx
        layout.panels[i].y += dy
        saveLayout()
    }

    func resizePanel(_ id: UUID, w: Double, h: Double) {
        guard let i = layout.panels.firstIndex(where: { $0.id == id }) else { return }
        layout.panels[i].w = max(Double(Theme.Canvas.panelMinWidth), w)
        layout.panels[i].h = max(Double(Theme.Canvas.panelMinHeight), h)
        saveLayout()
    }

    func setParam(_ id: UUID, _ param: String?) {
        guard let i = layout.panels.firstIndex(where: { $0.id == id }) else { return }
        layout.panels[i].param = param
        saveLayout()
    }

    /// Show a file in a Docs panel (reusing the front-most one).
    func preview(_ fileURL: URL) {
        let rel = FileIO.relativePath(fileURL, to: root)
        if let p = layout.panels.filter({ $0.kind == .docs }).max(by: { $0.z < $1.z }) {
            setParam(p.id, rel)
            bringToFront(p.id)
        } else {
            addPanel(.docs, param: rel)
        }
    }

    /// Show a variant in the front-most CAD panel.
    func showVariant(_ variant: String) {
        focusedVariant = variant
        if let p = layout.panels.filter({ $0.kind == .cad }).max(by: { $0.z < $1.z }) {
            setParam(p.id, variant)
            bringToFront(p.id)
        } else {
            addPanel(.cad, param: variant)
        }
    }

    // MARK: Sim replay (contracts §11)

    /// Play sim/<task>/replay.json in the front-most CAD panel (adds one if there is none),
    /// showing the variant the sim ran on.
    func openReplay(_ taskID: String) {
        guard let report = simReports.first(where: { $0.id == taskID }), report.replay != nil else { return }
        let variant = report.variant.flatMap { v in variants.contains(where: { $0.name == v }) ? v : nil }
        if let v = variant { focusedVariant = v }
        let id: UUID
        if let p = layout.panels.filter({ $0.kind == .cad }).max(by: { $0.z < $1.z }) {
            id = p.id
            if let v = variant { setParam(id, v) }
            bringToFront(id)
        } else {
            id = addPanel(.cad, param: variant)
        }
        setReplay(id, taskID)
    }

    func setReplay(_ id: UUID, _ taskID: String?) {
        guard let i = layout.panels.firstIndex(where: { $0.id == id }) else { return }
        layout.panels[i].replay = taskID
        saveLayout()
    }

    // MARK: Zoom

    func setZoom(_ newZoom: Double, around point: CGPoint? = nil) {
        let clamped = min(Double(Theme.Canvas.maxZoom), max(Double(Theme.Canvas.minZoom), newZoom))
        let anchor = point ?? CGPoint(x: viewportSize.width / 2, y: viewportSize.height / 2)
        // Keep the canvas point under `anchor` fixed.
        let cx = (Double(anchor.x) - layout.panX) / layout.zoom
        let cy = (Double(anchor.y) - layout.panY) / layout.zoom
        layout.zoom = clamped
        layout.panX = Double(anchor.x) - cx * clamped
        layout.panY = Double(anchor.y) - cy * clamped
        saveLayout()
    }

    func zoomIn() { setZoom(layout.zoom * 1.2) }
    func zoomOut() { setZoom(layout.zoom / 1.2) }

    /// Fit all panels into the viewport.
    func zoomToFit() {
        guard !layout.panels.isEmpty else { return }
        let minX = layout.panels.map(\.x).min()!, minY = layout.panels.map(\.y).min()!
        let maxX = layout.panels.map { $0.x + $0.w }.max()!, maxY = layout.panels.map { $0.y + $0.h }.max()!
        let margin = 32.0
        let w = maxX - minX, h = maxY - minY
        let zx = (Double(viewportSize.width) - 2 * margin) / max(w, 1)
        let zy = (Double(viewportSize.height) - 2 * margin) / max(h, 1)
        let z = min(Double(Theme.Canvas.maxZoom), max(Double(Theme.Canvas.minZoom), min(zx, zy, 1.0)))
        layout.zoom = z
        layout.panX = (Double(viewportSize.width) - w * z) / 2 - minX * z
        layout.panY = (Double(viewportSize.height) - h * z) / 2 - minY * z
        saveLayout()
    }
}

// MARK: - Snapshot loading (background queue)

private struct Snapshot {
    var name = ""
    var tree: [FileNode] = []
    var variants: [DesignVariant] = []
    var chosenVariant: String?
    var optionSets: [OptionSetDoc] = []
    var questions: [Question] = []
    var tasks: [TaskCard] = []
    var simReports: [SimReport] = []
    var inspiration: [InspirationItem] = []
    var docs: [URL] = []
    var docGroups: [DocGroup] = []
    var digests: [InspirationDigest] = []
    var targetCatchRate: Double?
    var simKind = "catch"
    var hardware = HardwareSpec()
    var requests: [UserRequest] = []

    static let yamlExt: Set<String> = ["yaml", "yml"]

    static func load(root: URL) -> Snapshot {
        var s = Snapshot()
        let u = { (rel: String) in root.appendingPathComponent(rel) }

        s.name = FileIO.loadJSON(u(".mechy/project.json"))?.string("name") ?? root.lastPathComponent
        s.tree = FileTree.build(root)

        // design/
        s.variants = FileIO.subdirectories(of: u("design")).map(DesignVariant.init(dir:))
        if let chosen = try? String(contentsOf: u("design/chosen"), encoding: .utf8) {
            let c = chosen.trimmingCharacters(in: .whitespacesAndNewlines)
            s.chosenVariant = c.isEmpty ? nil : c
        }

        // options/, questions/
        s.optionSets = FileIO.files(in: u("options"), extensions: yamlExt).compactMap { f in
            FileIO.loadYAML(f).map { OptionSetDoc(fileURL: f, $0) }
        }
        s.questions = FileIO.files(in: u("questions"), extensions: yamlExt).compactMap { f in
            FileIO.loadYAML(f).map { Question(fileURL: f, $0) }
        }

        // tasks/ (cards + status files; a status without a card still shows)
        var ids = Set<String>()
        var cards: [String: Loose] = [:]
        var statuses: [String: TaskStatus] = [:]
        for f in FileIO.children(of: u("tasks")) where !FileIO.isDirectory(f) {
            let n = f.lastPathComponent
            if n.hasSuffix(".status.json") {
                let id = String(n.dropLast(".status.json".count))
                ids.insert(id)
                if let d = FileIO.loadJSON(f) { statuses[id] = TaskStatus(d) }
            } else if yamlExt.contains(f.pathExtension.lowercased()) {
                let id = f.deletingPathExtension().lastPathComponent
                ids.insert(id)
                cards[id] = FileIO.loadYAML(f)
            }
        }
        s.tasks = ids.sorted { $0.localizedStandardCompare($1) == .orderedAscending }
            .map { TaskCard(id: $0, card: cards[$0], status: statuses[$0]) }

        // sim/
        s.simReports = FileIO.subdirectories(of: u("sim")).compactMap { dir in
            FileIO.loadJSON(dir.appendingPathComponent("report.json")).map { SimReport(dir: dir, $0) }
        }.sorted { $0.modified > $1.modified }

        // inspiration/<slug>/source.json digests (mechy intake), newest first
        s.digests = FileIO.subdirectories(of: u("inspiration"))
            .filter { $0.lastPathComponent != "notes" }
            .compactMap { InspirationDigest(dir: $0, root: root) }
            .sorted { $0.modified > $1.modified }
        // Sources already digested are shown by their digest card, not as raw files / links / notes.
        var digestedPaths = Set<String>()
        var digestedURLs = Set<String>()
        for d in s.digests {
            for p in [d.input, d.sourcePath].compactMap({ $0 }) {
                digestedPaths.insert(p.hasPrefix("/") ? URL(fileURLWithPath: p).standardizedFileURL.path
                                                      : u(p).standardizedFileURL.path)
            }
            if let link = d.url?.absoluteString { digestedURLs.insert(link) }
            if let i = d.input, i.contains("://") { digestedURLs.insert(i) }
        }
        let digestSlugs = Set(s.digests.map(\.slug))

        // inspiration/
        var items: [InspirationItem] = []
        for f in FileIO.children(of: u("inspiration")) where !FileIO.isDirectory(f) {
            if f.lastPathComponent == "links.yaml" { continue }
            if digestedPaths.contains(f.standardizedFileURL.path) { continue }
            let kind = InspirationItem.classify(f)
            items.append(InspirationItem(id: f.path, kind: kind, url: f, title: f.deletingPathExtension().lastPathComponent))
        }
        for note in FileIO.files(in: u("inspiration/notes"), extensions: ["md"]) {
            if digestSlugs.contains(note.deletingPathExtension().lastPathComponent) { continue }
            items.append(InspirationItem(id: note.path, kind: .note, url: note, title: note.deletingPathExtension().lastPathComponent))
        }
        if let links = FileIO.loadYAML(u("inspiration/links.yaml")) {
            for item in (links.raw["links"] as? [Any]) ?? [] {
                let d = Loose(any: item)
                guard let link = d?.string("url") ?? Loose.text(item), let url = URL(string: link) else { continue }
                if d?.string("digested") != nil || digestedURLs.contains(link) { continue }
                items.append(InspirationItem(id: link, kind: .link, url: url, title: d?.string("title") ?? url.host ?? link))
            }
        }
        s.inspiration = items

        // docs/: PDFs of each docs/<variant>/ (the .typ / .data.json / img/ sources are left out),
        // then the loose files at the top of docs/.
        var groups: [DocGroup] = []
        var loose: [URL] = []
        for f in FileIO.children(of: u("docs")) {
            if FileIO.isDirectory(f) {
                let pdfs = FileIO.files(in: f, extensions: ["pdf"])
                if !pdfs.isEmpty { groups.append(DocGroup(variant: f.lastPathComponent, files: pdfs)) }
            } else {
                loose.append(f)
            }
        }
        if !loose.isEmpty { groups.append(DocGroup(variant: nil, files: loose)) }
        s.docGroups = groups
        s.docs = groups.flatMap(\.files)

        // requirements.yaml
        let req = FileIO.loadYAML(u("requirements.yaml"))
        s.targetCatchRate = req?.dict("catch")?.double("target_catch_rate")
        s.simKind = req?.dict("pick") != nil && req?.dict("catch") == nil ? "pick" : "catch"
        s.hardware = HardwareSpec.load(root: root)
        s.requests = UserRequest.load(root: root)
        return s
    }
}

private enum FileTree {
    static let skip: Set<String> = [".git", "node_modules", "__pycache__", ".build"]

    static func build(_ root: URL) -> [FileNode] {
        var budget = 3000
        return children(root, depth: 0, budget: &budget)
    }

    private static func children(_ dir: URL, depth: Int, budget: inout Int) -> [FileNode] {
        guard depth < 8, budget > 0 else { return [] }
        let items = FileIO.children(of: dir).filter { !skip.contains($0.lastPathComponent) }
        let dirs = items.filter(FileIO.isDirectory)
        let files = items.filter { !FileIO.isDirectory($0) }
        var nodes: [FileNode] = []
        for d in dirs {
            budget -= 1
            nodes.append(FileNode(url: d, name: d.lastPathComponent, isDirectory: true,
                                  children: children(d, depth: depth + 1, budget: &budget)))
        }
        for f in files {
            budget -= 1
            if budget < 0 { break }
            nodes.append(FileNode(url: f, name: f.lastPathComponent, isDirectory: false, children: nil))
        }
        return nodes
    }
}
