import SwiftUI
import AppKit

/// Tasks (tasks/*.yaml + *.status.json) as a compact live board. Pending work is
/// drawn dashed, live work in accent, finished work solid.
struct TasksPanel: View {
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        VStack(spacing: 0) {
            PanelStrip {
                ForEach([TaskState.running, .queued, .blocked, .done, .failed], id: \.self) { state in
                    let n = session.tasks.filter { $0.state == state }.count
                    if n > 0 {
                        HStack(spacing: 4) {
                            StateMark(state: state)
                            Text("\(n) \(state.rawValue)").monoLabel(state == .running ? Theme.accent : Theme.muted, size: 9)
                        }
                    }
                }
                Spacer(minLength: 0)
                AgentRunButton(engine: session.engine, compact: true)
            }
            AgentRunFeed(engine: session.engine)
            if session.tasks.isEmpty {
                EmptySheet(symbol: "checklist", label: "No tasks yet", actionTitle: "Plan") {
                    session.engine.plan(project: session.root)
                }
            } else {
                ScrollView {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: Theme.Space.s)],
                              spacing: Theme.Space.s) {
                        ForEach(session.tasks) { task in
                            TaskTile(task: task, progress: session.lastEvent(forTask: task.id))
                        }
                    }
                    .padding(Theme.Space.s)
                }
            }
        }
    }
}

struct TaskTile: View {
    let task: TaskCard
    let progress: EngineEvent?
    @EnvironmentObject var session: ProjectSession

    private var live: Bool { task.state == .running }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                StateMark(state: task.state)
                Text(Theme.tag(task.shortID)).font(Theme.Typo.mono(11, .medium)).foregroundStyle(live ? Theme.accent : Theme.ink)
                Spacer(minLength: 0)
                Image(systemName: task.roleSymbol).font(.system(size: 9)).foregroundStyle(Theme.muted)
            }
            Text(task.slugTitle).monoLabel(Theme.ink, size: 9).lineLimit(1)
            if live {
                if let f = progress?.fraction ?? session.lastProgress(forTask: task.id)?.fraction {
                    ProgressView(value: min(1, max(0, f))).progressViewStyle(.linear).tint(Theme.accent).controlSize(.mini)
                }
                // Latest line from the agent (progress message or streamed agent.output text).
                if let line = progress?.shortText, !line.isEmpty {
                    Text(line).font(Theme.Typo.mono(9)).foregroundStyle(Theme.muted).lineLimit(2)
                }
            } else if task.state == .failed, let e = task.status?.error {
                Text(e).font(Theme.Typo.mono(9)).foregroundStyle(Theme.danger).lineLimit(1)
            }
        }
        .padding(Theme.Space.s)
        .overlay(
            Rectangle().stroke(live ? Theme.accent : (task.state == .failed ? Theme.danger : Theme.ink),
                               style: task.state == .queued || task.state == .blocked || task.state == .unknown
                                   ? Theme.Stroke.dashed : StrokeStyle(lineWidth: 1))
        )
        .contentShape(Rectangle())
        .onTapGesture { openSummary() }
        .contextMenu {
            Button("Run this task") { session.runTask(task.id) }
            if let sim = session.simReports.first(where: { $0.id == task.id || task.outputs.contains("sim/\($0.id)/report.json") }),
               sim.replay != nil {
                Button("Replay sim \(sim.id)") { session.openReplay(sim.id) }
            }
            Button("Open card") { session.preview(session.url("tasks/\(task.id).yaml")) }
            if task.status?.summary != nil { Button("Open summary") { openSummary() } }
        }
        .help(task.goal ?? task.id)
    }

    private func openSummary() {
        if let s = task.status?.summary { session.preview(session.url(s)) }
    }
}

/// Run agents / Stop: starts `mechy run --jobs 2` (provider from Settings), or stops it
/// and every agent process it started. Observes the engine so it flips immediately.
struct AgentRunButton: View {
    @ObservedObject var engine: EngineClient
    var compact = false
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        if let run = engine.agentsRun(for: session.root) {
            Button {
                session.stopAgents()
            } label: {
                HStack(spacing: 5) {
                    Rectangle().fill(run.stopRequested ? Theme.muted : Theme.danger).frame(width: 7, height: 7)
                    Text(run.stopRequested ? "Stopping" : "Stop agents")
                }
            }
            .buttonStyle(SheetButtonStyle(compact: compact))
            .disabled(run.stopRequested)
            .help("Stop mechy run and every agent it started")
        } else {
            Button {
                session.runAgents()
            } label: {
                HStack(spacing: 5) {
                    Image(systemName: "play.fill").font(.system(size: 7))
                    Text("Run agents")
                }
            }
            .buttonStyle(SheetButtonStyle(filled: !compact, compact: compact))
            .help("mechy run --jobs \(EngineClient.agentJobs) · provider \(AppSettings.provider.title)")
        }
    }
}

/// One-line status of the current (or just finished) agents run, plus its last events.
struct AgentRunFeed: View {
    @ObservedObject var engine: EngineClient
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        if let run = engine.latestAgentsRun(for: session.root) {
            AgentRunFeedBody(run: run)
        }
    }
}

private struct AgentRunFeedBody: View {
    @ObservedObject var run: EngineRun

    private var stateText: String {
        switch run.state {
        case .running: return run.stopRequested ? "stopping" : "running"
        case .succeeded: return "finished"
        case .failed(let why): return run.wasStopped ? "stopped" : why
        }
    }

    private var stateColor: Color {
        switch run.state {
        case .running: return Theme.accent
        case .succeeded: return Theme.ink
        case .failed: return run.wasStopped ? Theme.muted : Theme.danger
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 6) {
                if run.isRunning { Rectangle().fill(Theme.accent).frame(width: 6, height: 6) }
                Text("Agents · \(stateText)").monoLabel(stateColor, size: 9).lineLimit(1)
                Spacer(minLength: 0)
                TimelineView(.periodic(from: run.started, by: 1)) { ctx in
                    Text(Self.elapsed(from: run.started, to: run.finished ?? ctx.date)).monoLabel(size: 9)
                }
                Text("\(AppSettings.provider.title) · \(EngineClient.agentJobs) jobs").monoLabel(size: 9)
            }
            ForEach(run.events.filter { $0.type != "result" }.suffix(3)) { ev in
                HStack(spacing: 6) {
                    Text(ev.task.map { Theme.tag(String($0.split(separator: "-").first ?? "")) } ?? "·")
                        .font(Theme.Typo.mono(9, .medium))
                        .foregroundStyle(Theme.ink)
                        .frame(width: 34, alignment: .leading)
                    Text(ev.shortText)
                        .font(Theme.Typo.mono(9))
                        .foregroundStyle(ev.type == "task.failed" ? Theme.danger : Theme.muted)
                        .lineLimit(1)
                        .truncationMode(.tail)
                }
            }
            if run.events.isEmpty, let last = run.log.last {
                Text(last).font(Theme.Typo.mono(9)).foregroundStyle(Theme.muted).lineLimit(1)
            }
        }
        .padding(.horizontal, Theme.Space.s)
        .padding(.vertical, 5)
        .overlay(alignment: .bottom) { Hairline() }
        .contextMenu {
            Button("Copy log") {
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(run.log.joined(separator: "\n"), forType: .string)
            }
        }
        .help(run.log.suffix(12).joined(separator: "\n"))
    }

    static func elapsed(from a: Date, to b: Date) -> String {
        let s = max(0, Int(b.timeIntervalSince(a)))
        return s >= 3600 ? String(format: "%d:%02d:%02d", s / 3600, s / 60 % 60, s % 60)
                         : String(format: "%02d:%02d", s / 60, s % 60)
    }
}
