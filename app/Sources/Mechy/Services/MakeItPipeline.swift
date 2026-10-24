import Foundation
import Combine

/// "Make it": Build CAD -> Run sim -> Generate firmware -> Build docs for one variant,
/// one engine command after the other, stopping at the first failure.
final class MakeItPipeline: ObservableObject {
    enum StepKind: String, CaseIterable, Identifiable {
        case cad, sim, firmware, docs
        var id: String { rawValue }

        var title: String {
            switch self {
            case .cad: return "CAD"
            case .sim: return "Sim"
            case .firmware: return "Firmware"
            case .docs: return "Docs"
            }
        }

        var symbol: String {
            switch self {
            case .cad: return "cube"
            case .sim: return "waveform.path.ecg"
            case .firmware: return "cpu"
            case .docs: return "doc.richtext"
            }
        }

        func command(_ variant: String) -> String {
            switch self {
            case .cad: return "mechy cad build \(variant)"
            case .sim: return "mechy sim catch \(variant)"
            case .firmware: return "mechy control gen \(variant)"
            case .docs: return "mechy doc build \(variant)"
            }
        }
    }

    enum StepState: Equatable {
        case pending, running, done, failed(String), skipped
    }

    struct Step: Identifiable {
        let kind: StepKind
        var state: StepState = .pending
        var run: EngineRun?
        /// Why this step was skipped (e.g. "not available for drones yet").
        var skipReason: String?
        var id: String { kind.rawValue }
    }

    @Published private(set) var variant: String?
    @Published private(set) var steps: [Step] = []
    @Published private(set) var isRunning = false
    @Published private(set) var finished: Date?

    private weak var engine: EngineClient?
    private var project: URL?
    private var cancelled = false
    private var onSuccess: ((String) -> Void)?

    var isActive: Bool { !steps.isEmpty }
    var succeeded: Bool { !steps.isEmpty && steps.allSatisfy { $0.state == .done || $0.state == .skipped } }
    var failedStep: Step? {
        steps.first { if case .failed = $0.state { return true } else { return false } }
    }

    /// Engine runs started by the pipeline (the agent bar hides their separate chips).
    var runIDs: Set<UUID> { Set(steps.compactMap { $0.run?.id }) }

    var currentRun: EngineRun? { steps.first { $0.state == .running }?.run }

    func start(variant: String, project: URL, engine: EngineClient, onSuccess: ((String) -> Void)? = nil) {
        guard !isRunning else { return }
        self.variant = variant
        self.project = project
        self.engine = engine
        self.onSuccess = onSuccess
        cancelled = false
        finished = nil
        steps = StepKind.allCases.map { Step(kind: $0) }
        // A quad_frame (drone) variant has no sim/firmware/docs yet: CAD only.
        let paramsFile = project.appendingPathComponent("design/\(variant)/params.yaml")
        if FileIO.loadYAML(paramsFile)?.string("style") == "quad_frame" {
            for i in steps.indices where steps[i].kind != .cad {
                steps[i].state = .skipped
                steps[i].skipReason = "not available for drones yet"
            }
        }
        isRunning = true
        runStep(0)
    }

    func cancel() {
        guard isRunning else { return }
        cancelled = true
        if let run = currentRun { engine?.cancel(run) }
    }

    /// Clear the chips after a finished pipeline.
    func dismiss() {
        guard !isRunning else { return }
        steps = []
        variant = nil
        finished = nil
    }

    private func runStep(_ i: Int) {
        var i = i
        while i < steps.count, steps[i].state == .skipped { i += 1 }
        guard let engine = self.engine, let project = self.project, let variant = self.variant else { return finish() }
        guard i < steps.count else { return finish() }
        if cancelled {
            for j in i..<steps.count { steps[j].state = .skipped }
            return finish()
        }
        steps[i].state = .running
        let done: (EngineRun) -> Void = { [weak self] run in
            // The completion may run synchronously (mechy not found); hop so `steps[i].run` is set first.
            DispatchQueue.main.async { self?.stepFinished(i, run) }
        }
        let run: EngineRun
        switch steps[i].kind {
        case .cad: run = engine.buildCAD(variant: variant, project: project, completion: done)
        case .sim: run = engine.runSim(variant: variant, project: project, completion: done)
        case .firmware: run = engine.controlGen(variant: variant, project: project, completion: done)
        case .docs: run = engine.docBuild(variant: variant, project: project, completion: done)
        }
        steps[i].run = run
    }

    private func stepFinished(_ i: Int, _ run: EngineRun) {
        guard i < steps.count else { return }
        switch run.state {
        case .succeeded:
            steps[i].state = .done
            runStep(i + 1)
        case .failed(let why):
            steps[i].state = .failed(run.wasStopped ? "stopped" : why)
            for j in (i + 1)..<steps.count { steps[j].state = .skipped }
            finish()
        case .running:
            break
        }
    }

    private func finish() {
        isRunning = false
        finished = Date()
        if succeeded, let variant { onSuccess?(variant) }
    }
}
