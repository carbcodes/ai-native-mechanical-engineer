import SwiftUI

/// What an agent (or engine command) is doing to one panel's contents right now.
struct PanelActivity: Equatable {
    /// "CAD agent", "Sim", ...
    let who: String
    /// Latest short status line ("building forearm", "42%").
    let detail: String
    let fraction: Double?
}

extension PanelKind {
    /// Agent roles (contracts: task card `role`) whose work shows up in this panel.
    var agentRoles: Set<String> {
        switch self {
        case .cad, .parts, .manufacturing: return ["cad"]
        case .sim, .loads: return ["sim"]
        case .inspiration: return ["research"]
        case .options: return ["concept"]
        case .docs: return ["docs"]
        case .electronics: return ["controls"]
        case .questions, .tasks: return ["planner"]
        case .history: return []
        }
    }

    /// `mechy <command>` runs whose output lands in this panel.
    var engineCommands: Set<String> {
        switch self {
        case .cad, .parts, .manufacturing, .loads: return ["cad"]
        case .sim: return ["sim"]
        case .inspiration: return ["intake"]
        case .docs: return ["doc"]
        case .electronics: return ["control"]
        case .questions, .tasks: return ["plan"]
        case .options, .history: return []
        }
    }

    /// Plain name for the area, used when Mechy says what it is working on.
    var areaName: String {
        switch self {
        case .cad: return "CAD"
        case .sim: return "simulation"
        case .inspiration: return "research"
        case .options: return "options"
        case .docs: return "docs"
        case .electronics: return "electronics"
        case .parts: return "the BOM"
        case .loads: return "load analysis"
        case .manufacturing: return "manufacturing"
        case .questions, .tasks: return "the plan"
        case .history: return "history"
        }
    }
}

extension ProjectSession {
    /// The live activity for a panel kind: a running task of a matching role first, else a
    /// running engine command that writes there. One line, never a list of subagents.
    func activity(for kind: PanelKind) -> PanelActivity? {
        let running = tasks.filter { $0.state == .running && kind.agentRoles.contains($0.role) }
        if let task = running.first {
            let detail = lastEvent(forTask: task.id)?.shortText ?? task.slugTitle
            let who = running.count > 1 ? "\(running.count) agents" : "\(kind.areaName.capitalizedFirst) agent"
            return PanelActivity(who: who, detail: detail.isEmpty ? "working" : detail, fraction: nil)
        }
        if let run = engine.runs.first(where: { $0.isRunning && kind.engineCommands.contains($0.command ?? "") }) {
            return PanelActivity(who: run.label, detail: run.message ?? "working", fraction: run.fraction)
        }
        return nil
    }

    /// Areas with work in progress, in sheet order, for the chat's "working on" line.
    var workingAreas: [String] {
        var seen: [String] = []
        for kind in PanelKind.allCases where ![.tasks, .parts, .loads, .manufacturing].contains(kind) && activity(for: kind) != nil {
            if !seen.contains(kind.areaName) { seen.append(kind.areaName) }
        }
        return seen
    }

    /// True while any agent task or the agent scheduler is running.
    var agentsBusy: Bool {
        tasks.contains { $0.state == .running } || engine.agentsRun(for: root) != nil
            || engine.runs.contains { $0.isRunning && $0.command == "plan" }
    }
}

extension String {
    var capitalizedFirst: String { prefix(1).uppercased() + dropFirst() }
}

/// Pulsing accent square: "something is happening here".
struct LivePulse: View {
    var size: CGFloat = 6
    var color: Color = Theme.accent
    @State private var on = false
    var body: some View {
        Rectangle()
            .fill(color)
            .frame(width: size, height: size)
            .opacity(on ? 1 : 0.25)
            .animation(.easeInOut(duration: 0.7).repeatForever(autoreverses: true), value: on)
            .onAppear { on = true }
    }
}
