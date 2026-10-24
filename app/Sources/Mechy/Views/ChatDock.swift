import SwiftUI

/// The one strip under the sheet. In the middle, the conversation with Mechy: what you asked,
/// what Mechy did (each reply links to the panel it opened and commented on), one line saying
/// what it is doing now with a Stop button, and the composer. Sending writes inbox/<timestamp>.md,
/// plans and starts the agents (ProjectSession.sendRequest); there is no separate run step.
/// Engine jobs in flight sit on the left; Make it and the sheet zoom on the right.
struct ChatDock: View {
    @EnvironmentObject var session: ProjectSession
    @ObservedObject var engine: EngineClient
    @State private var draft = ""
    @State private var expanded = false
    @FocusState private var focused: Bool

    static let maxWidth: CGFloat = 760
    private let ticker = Timer.publish(every: 10, on: .main, in: .common).autoconnect()

    var body: some View {
        HStack(alignment: .bottom, spacing: Theme.Space.l) {
            jobs
                .frame(maxWidth: .infinity, alignment: .bottomLeading)
            VStack(spacing: Theme.Space.s) {
                thread
                status
                composer
            }
            .frame(maxWidth: Self.maxWidth)
            HStack(spacing: Theme.Space.s) {
                MakeItMenu(pipeline: session.pipeline).fixedSize()
                ZoomControls().fixedSize()
            }
            .frame(maxWidth: .infinity, alignment: .bottomTrailing)
        }
        .padding(.horizontal, Theme.Space.m)
        .padding(.top, Theme.Space.s)
        .padding(.bottom, Theme.Space.m)
        .background(Theme.paper)
        .overlay(alignment: .top) { Rectangle().fill(Theme.frame).frame(height: Theme.Stroke.frame) }
        .onReceive(ticker) { _ in engine.pruneFinished() }
    }

    // MARK: Engine jobs (left)

    /// Make it progress and single engine commands (CAD build, sim...). Agent runs are summed
    /// up by the status line instead of listed one by one.
    private var jobs: some View {
        VStack(alignment: .leading, spacing: Theme.Space.xs) {
            MakeItChips(pipeline: session.pipeline)
            ForEach(engine.runs.filter { !session.pipeline.runIDs.contains($0.id) && $0.command != "run" && $0.command != "plan" }) { run in
                RunChip(run: run)
            }
        }
    }

    // MARK: Conversation

    private enum Entry: Identifiable {
        case user(UserRequest)
        case mechy(WorkspaceNote)

        var id: String {
            switch self {
            case .user(let r): return r.fileURL.path
            case .mechy(let n): return n.id
            }
        }
        var date: Date {
            switch self {
            case .user(let r): return r.date ?? .distantPast
            case .mechy(let n): return n.date
            }
        }
    }

    private var entries: [Entry] {
        (session.requests.map(Entry.user) + session.notes.map(Entry.mechy))
            .sorted { $0.date < $1.date }
    }

    @ViewBuilder private var thread: some View {
        let all = entries
        let shown = expanded ? Array(all.suffix(40)) : Array(all.suffix(3))
        if !all.isEmpty {
            VStack(alignment: .leading, spacing: Theme.Space.xs) {
                if all.count > 3 {
                    HStack {
                        Spacer()
                        Button(expanded ? "Show less" : "Earlier (\(all.count - 3))") { expanded.toggle() }
                            .buttonStyle(.plain)
                            .font(Theme.Typo.mono(9, .medium))
                            .textCase(.uppercase)
                            .foregroundStyle(Theme.muted)
                    }
                }
                ScrollViewReader { proxy in
                    ScrollView {
                        VStack(alignment: .leading, spacing: Theme.Space.s) {
                            ForEach(shown) { entry in
                                row(entry).id(entry.id)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(maxHeight: expanded ? 320 : 132)
                    .fixedSize(horizontal: false, vertical: !expanded)
                    .onAppear { proxy.scrollTo(shown.last?.id, anchor: .bottom) }
                    .onChange(of: all.count) { _, _ in
                        withAnimation { proxy.scrollTo(entries.last?.id, anchor: .bottom) }
                    }
                }
            }
        }
    }

    @ViewBuilder private func row(_ entry: Entry) -> some View {
        switch entry {
        case .user(let r):
            HStack(alignment: .firstTextBaseline, spacing: Theme.Space.s) {
                Text("You").monoLabel(Theme.muted, size: 9).frame(width: 46, alignment: .leading)
                Text(r.text)
                    .font(Theme.Typo.body)
                    .foregroundStyle(Theme.ink)
                    .lineLimit(expanded ? nil : 2)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
                if r.pending { Text("Queued").monoLabel(Theme.muted, size: 8) }
            }
        case .mechy(let n):
            HStack(alignment: .firstTextBaseline, spacing: Theme.Space.s) {
                Text("Mechy").monoLabel(n.kind == .failure ? Theme.danger : Theme.ink, size: 9)
                    .frame(width: 46, alignment: .leading)
                Text(n.text)
                    .font(Theme.Typo.body)
                    .foregroundStyle(n.kind == .failure ? Theme.danger : Theme.ink)
                    .lineLimit(expanded ? nil : 2)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
                if let kind = n.panel {
                    Button { session.reveal(n) } label: {
                        HStack(spacing: 3) {
                            Text(linkTitle(n, kind))
                            Image(systemName: "arrow.up.right").font(.system(size: 8, weight: .semibold))
                        }
                    }
                    .buttonStyle(SheetButtonStyle(compact: true))
                    .help("Bring up \(kind.title)")
                }
            }
        }
    }

    private func linkTitle(_ n: WorkspaceNote, _ kind: PanelKind) -> String {
        switch n.kind {
        case .question: return "Answer"
        case .options: return "Pick"
        default: return kind.title
        }
    }

    // MARK: What Mechy is doing

    private var status: some View {
        let areas = session.workingAreas
        let busy = session.agentsBusy || !areas.isEmpty
        return HStack(spacing: Theme.Space.s) {
            if busy { LivePulse(size: 7, color: Theme.ink) } else { Rectangle().stroke(Theme.ink, lineWidth: 1).frame(width: 7, height: 7) }
            Text(statusText(busy: busy, areas: areas))
                .font(Theme.Typo.small)
                .foregroundStyle(busy ? Theme.ink : Theme.muted)
                .lineLimit(1)
                .truncationMode(.tail)
            Spacer(minLength: 0)
            if session.agentsBusy {
                Button { session.stopAgents() } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "stop.fill").font(.system(size: 8))
                        Text("Stop")
                    }
                }
                .buttonStyle(SheetButtonStyle(compact: true))
                .help("Stop Mechy and every agent it started")
            }
        }
    }

    private func statusText(busy: Bool, areas: [String]) -> String {
        let working = session.tasks.filter { $0.state == .running }.count
        if !areas.isEmpty {
            let who = working > 1 ? " (\(working) agents)" : ""
            return "Working on " + Self.list(areas) + who + "…"
        }
        if busy { return "Thinking…" }
        if !session.openQuestions.isEmpty { return "Waiting for your answer." }
        if !session.openOptionSets.isEmpty { return "Waiting for you to pick an option." }
        return session.requests.isEmpty ? "Describe what to build. Mechy works on the sheet with you." : "Ready for the next change."
    }

    static func list(_ items: [String]) -> String {
        switch items.count {
        case 0: return ""
        case 1: return items[0]
        default: return items.dropLast().joined(separator: ", ") + " and " + items.last!
        }
    }

    // MARK: Composer

    private var composer: some View {
        HStack(alignment: .bottom, spacing: Theme.Space.s) {
            ZStack(alignment: .topLeading) {
                if draft.isEmpty {
                    Text("Ask Mechy — e.g. make the forearm lighter, or use a 24 V supply")
                        .font(Theme.Typo.sans(14))
                        .foregroundStyle(Theme.muted)
                        .padding(.top, 1)
                        .padding(.leading, 5)
                        .allowsHitTesting(false)
                }
                TextEditor(text: $draft)
                    .font(Theme.Typo.sans(14))
                    .scrollContentBackground(.hidden)
                    .focused($focused)
                    .onKeyPress(.return, phases: .down) { press in
                        // Return sends; Shift-Return adds a line.
                        if press.modifiers.contains(.shift) { return .ignored }
                        send()
                        return .handled
                    }
            }
            .frame(minHeight: 36, maxHeight: 120)
            .fixedSize(horizontal: false, vertical: true)

            Button(action: send) {
                HStack(spacing: 6) {
                    Text("Send")
                    Image(systemName: "arrow.up").font(.system(size: 11, weight: .semibold))
                }
            }
            .buttonStyle(SheetButtonStyle(filled: true))
            .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .help("Send (Return). Shift-Return for a new line.")
        }
        .padding(.horizontal, Theme.Space.m)
        .padding(.vertical, Theme.Space.s)
        .background(Theme.surface)
        .overlay(Rectangle().stroke(Theme.ink, lineWidth: focused ? 1.5 : 1))
        .contentShape(Rectangle())
        .onTapGesture { focused = true }
    }

    private func send() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        session.sendRequest(text)
        draft = ""
    }
}
