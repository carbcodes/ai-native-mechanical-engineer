import SwiftUI
import AppKit

/// A status chip: tiny state mark + mono uppercase text in a 1 pt box.
struct Chip: View {
    let symbol: String
    let text: String
    var live = false
    var emphasized = false
    var failed = false

    var body: some View {
        HStack(spacing: 5) {
            if live {
                Rectangle().fill(Theme.accent).frame(width: 6, height: 6)
            }
            Image(systemName: symbol).font(.system(size: 9, weight: .medium))
            Text(text).lineLimit(1)
        }
        .font(Theme.Typo.mono(10, .medium))
        .tracking(0.6)
        .textCase(.uppercase)
        .foregroundStyle(failed ? Theme.danger : (live ? Theme.accent : Theme.ink))
        .padding(.horizontal, 6)
        .padding(.vertical, 3)
        .frame(maxWidth: 260)
        .overlay(Rectangle().stroke(failed ? Theme.danger : (live ? Theme.accent : Theme.ink),
                                    style: emphasized || live || failed ? StrokeStyle(lineWidth: 1) : Theme.Stroke.dashedHair))
    }
}

struct RunChip: View {
    @ObservedObject var run: EngineRun
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        let text: String = {
            switch run.state {
            case .running: return "\(run.label) \(run.message ?? "…")"
            case .succeeded: return "\(run.label) done"
            case .failed: return "\(run.label) \(run.message ?? "failed")"
            }
        }()
        HStack(spacing: 4) {
            Chip(symbol: run.state == .succeeded ? "checkmark" : run.symbol, text: text,
                 live: run.isRunning, failed: isFailed)
            if run.isRunning, let f = run.fraction {
                Text(Theme.percent(f)).font(Theme.Typo.mono(9)).foregroundStyle(Theme.accent)
            }
        }
        .help(run.log.suffix(12).joined(separator: "\n"))
        .contextMenu {
            if run.isRunning { Button("Stop") { session.engine.cancel(run) } }
            Button("Copy log") {
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(run.log.joined(separator: "\n"), forType: .string)
            }
        }
    }

    private var isFailed: Bool {
        if case .failed = run.state { return true }
        return false
    }
}

/// "Make it" menu: Build CAD -> Run sim -> Generate firmware -> Build docs for the chosen
/// variant (design/chosen, else the one on screen), plus each step on its own.
struct MakeItMenu: View {
    @ObservedObject var pipeline: MakeItPipeline
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        let v = session.makeVariant
        let tag = v.map(Theme.tag) ?? "—"
        Menu {
            if pipeline.isRunning {
                Button("Stop Make it") { pipeline.cancel() }
            } else {
                Button("Make it \(tag): CAD → sim → firmware → docs") { session.makeIt() }
                    .disabled(v == nil)
            }
            Divider()
            Button("Build CAD \(tag)") { session.buildCAD(v) }.disabled(v == nil)
            Button(session.simKind == "pick" ? "Run pick sim \(tag)" : "Run catch sim \(tag)") { session.runSim(v) }.disabled(v == nil)
            Button("Generate firmware \(tag)") { session.generateFirmware(v) }.disabled(v == nil)
            Button("Build docs \(tag)") { session.buildDocs(v) }.disabled(v == nil)
            Button("Build print docs \(tag)") { session.buildDocs(v, printVersion: true) }.disabled(v == nil)
            Divider()
            Button("Digest pending inspiration") { session.digestAllPending() }
            if pipeline.isActive && !pipeline.isRunning {
                Button("Clear Make it chips") { pipeline.dismiss() }
            }
        } label: {
            HStack(spacing: 5) {
                Image(systemName: pipeline.isRunning ? "hammer.fill" : "hammer")
                Text(pipeline.isRunning ? "Making \(pipeline.variant.map(Theme.tag) ?? "")" : "Make it")
            }
            .font(Theme.Typo.mono(10, .medium))
            .textCase(.uppercase)
        }
        .menuStyle(.button)
        .buttonStyle(.plain)
        .menuIndicator(.visible)
        .padding(.horizontal, 6)
        .padding(.vertical, 3)
        .overlay(Rectangle().stroke(pipeline.isRunning ? Theme.accent : Theme.ink, lineWidth: Theme.Stroke.frame))
        .help(v.map { "Make it: mechy cad build \($0) → sim catch → control gen → doc build" } ?? "No design variant yet")
    }
}

/// Progress chips of a "Make it" run: done solid with a check, running in accent with its
/// message, pending dashed, failed red (the rest are skipped).
struct MakeItChips: View {
    @ObservedObject var pipeline: MakeItPipeline
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        if pipeline.isActive {
            HStack(spacing: 4) {
                Text("Make \(pipeline.variant.map(Theme.tag) ?? "")")
                    .font(Theme.Typo.mono(10, .semibold))
                    .textCase(.uppercase)
                    .foregroundStyle(pipeline.failedStep != nil ? Theme.danger : (pipeline.isRunning ? Theme.accent : Theme.ink))
                ForEach(pipeline.steps) { step in
                    MakeItStepChip(step: step, variant: pipeline.variant ?? "")
                }
                if pipeline.isRunning {
                    Button { pipeline.cancel() } label: {
                        Image(systemName: "stop.fill").font(.system(size: 8))
                    }
                    .buttonStyle(SheetButtonStyle(compact: true))
                    .help("Stop Make it")
                } else {
                    if pipeline.succeeded, let v = pipeline.variant {
                        Button("Docs") { session.showNewestDoc(of: v) }
                            .buttonStyle(SheetButtonStyle(compact: true))
                    }
                    Button { pipeline.dismiss() } label: {
                        Image(systemName: "xmark").font(.system(size: 8, weight: .semibold))
                    }
                    .buttonStyle(SheetButtonStyle(compact: true))
                    .help("Clear")
                }
            }
            .fixedSize()
        }
    }
}

private struct MakeItStepChip: View {
    let step: MakeItPipeline.Step
    let variant: String

    var body: some View {
        switch step.state {
        case .pending:
            Chip(symbol: step.kind.symbol, text: step.kind.title)
                .opacity(0.8)
                .help(step.kind.command(variant))
        case .running:
            if let run = step.run {
                MakeItRunningChip(step: step, run: run)
            } else {
                Chip(symbol: step.kind.symbol, text: step.kind.title, live: true)
            }
        case .done:
            Chip(symbol: "checkmark", text: step.kind.title, emphasized: true)
                .help(step.kind.command(variant) + ": done")
        case .failed(let why):
            Chip(symbol: "xmark", text: "\(step.kind.title) \(why)", failed: true)
                .help(step.kind.command(variant) + " failed:\n" + (step.run?.log.suffix(12).joined(separator: "\n") ?? why))
                .contextMenu {
                    Button("Copy log") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(step.run?.log.joined(separator: "\n") ?? why, forType: .string)
                    }
                }
        case .skipped:
            Chip(symbol: step.kind.symbol, text: step.kind.title)
                .opacity(0.4)
                .help(step.skipReason ?? "Skipped")
        }
    }
}

private struct MakeItRunningChip: View {
    let step: MakeItPipeline.Step
    @ObservedObject var run: EngineRun

    var body: some View {
        HStack(spacing: 4) {
            Chip(symbol: step.kind.symbol, text: "\(step.kind.title) \(run.message ?? "…")", live: true)
            if let f = run.fraction {
                Text(Theme.percent(f)).font(Theme.Typo.mono(9)).foregroundStyle(Theme.accent)
            }
        }
        .help(run.log.suffix(12).joined(separator: "\n"))
    }
}
