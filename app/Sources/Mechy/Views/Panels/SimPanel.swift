import SwiftUI
import AVKit

/// Simulation results (sim/*/report.json): catch rate as one big number with a
/// dimension line to the target, failure breakdown chart, plots, and video.
struct SimPanel: View {
    let panel: PanelState
    @EnvironmentObject var session: ProjectSession

    private var report: SimReport? {
        if let p = panel.param, let r = session.simReports.first(where: { $0.id == p }) { return r }
        return session.simReports.first
    }

    var body: some View {
        VStack(spacing: 0) {
            PanelStrip {
                if session.simReports.count > 1 {
                    Menu {
                        ForEach(session.simReports) { r in
                            Button("\(r.id)  \(r.variant.map(Theme.tag) ?? "")\(r.replay != nil ? "  ▸ replay" : "")") {
                                session.setParam(panel.id, r.id)
                            }
                        }
                    } label: {
                        Text(report?.id ?? "Report").monoLabel(Theme.ink)
                    }
                    .menuStyle(.button)
                    .buttonStyle(.plain)
                    .fixedSize()
                } else {
                    Text(report?.id ?? "No report").monoLabel(Theme.ink)
                }
                Spacer(minLength: 0)
                if let report {
                    Button("▶ Replay") { session.openReplay(report.id) }
                        .buttonStyle(SheetButtonStyle(compact: true))
                        .disabled(report.replay == nil)
                        .help(report.replay == nil
                              ? "No replay.json in sim/\(report.id)/ yet. Re-run the sim to record one"
                              : "Play the recorded motion of \(report.id) on the arm in the CAD panel")
                }
                Button("Run sim") { session.runSim(report?.variant, kind: report?.kind) }
                    .buttonStyle(SheetButtonStyle(compact: true))
                    .disabled(session.activeVariant == nil)
            }
            if let report {
                ScrollView { SimReportView(report: report, target: session.targetCatchRate) }
            } else {
                EmptySheet(symbol: "chart.bar.xaxis", label: "No simulation yet",
                           actionTitle: session.simKind == "pick" ? "Run pick sim" : "Run catch sim") {
                    session.runSim()
                }
            }
        }
    }
}

struct SimReportView: View {
    let report: SimReport
    let target: Double?
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.l) {
            headline
            if !report.failures.isEmpty { failures }
            if !report.plots.isEmpty { plots }
            if let video = report.video {
                SimVideo(url: video)
                    .frame(height: 200)
                    .overlay(Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.hair))
            }
        }
        .padding(Theme.Space.m)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var meetsTarget: Bool {
        guard let c = report.catchRate, let t = target else { return true }
        return c >= t
    }

    /// Side by side when the panel is wide enough, stacked when it is narrow.
    private var headline: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .top, spacing: Theme.Space.l) {
                bigBlock
                statsBlock
            }
            VStack(alignment: .leading, spacing: Theme.Space.m) {
                bigBlock
                statsBlock
            }
        }
    }

    @ViewBuilder private var bigBlock: some View {
        if let h = report.headline { headlineBlock(h) } else { rateBlock }
    }

    /// Non-catch reports (pick-and-place): the headline number in g/s/..., bar to the target.
    private func headlineBlock(_ h: SimHeadline) -> some View {
        let good = h.meets
        let scale = max(h.value, h.target ?? 0) * 1.25
        return VStack(alignment: .leading, spacing: Theme.Space.xs) {
            Text(h.label).monoLabel()
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(String(format: "%.0f", h.value))
                    .font(Theme.Typo.hero)
                    .foregroundStyle(Theme.ink)
                Text(h.unit).font(Theme.Typo.mono(14, .medium)).foregroundStyle(Theme.muted)
            }
            GeometryReader { geo in
                let w = geo.size.width
                ZStack(alignment: .leading) {
                    Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.hair)
                    Rectangle()
                        .fill(good ? Theme.good : Theme.danger)
                        .frame(width: scale > 0 ? w * CGFloat(min(1, h.value / scale)) : 0)
                    if let t = h.target, scale > 0 {
                        Path { p in
                            p.move(to: CGPoint(x: w * CGFloat(t / scale), y: -4))
                            p.addLine(to: CGPoint(x: w * CGFloat(t / scale), y: 12))
                        }
                        .stroke(Theme.ink, style: Theme.Stroke.dashed)
                    }
                }
            }
            .frame(height: 8)
            if let t = h.target {
                HStack(spacing: Theme.Space.xs) {
                    Text("Target").monoLabel()
                    Text(String(format: "%.0f %@", t, h.unit)).font(Theme.Typo.monoBody).foregroundStyle(Theme.ink)
                }
            }
        }
        .frame(minWidth: 150, maxWidth: 200)
    }

    private var rateBlock: some View {
        VStack(alignment: .leading, spacing: Theme.Space.xs) {
            Text("Catch rate").monoLabel()
            Text(Theme.percent(report.catchRate))
                .font(Theme.Typo.hero)
                .foregroundStyle(Theme.ink)
            // Bar to scale: actual (solid) vs target (dashed tick), 0-100 %.
            GeometryReader { geo in
                let w = geo.size.width
                ZStack(alignment: .leading) {
                    Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.hair)
                    Rectangle()
                        .fill(meetsTarget ? Theme.good : Theme.danger)
                        .frame(width: w * CGFloat(min(1, max(0, report.catchRate ?? 0))))
                    if let t = target {
                        Path { p in
                            p.move(to: CGPoint(x: w * CGFloat(t), y: -4))
                            p.addLine(to: CGPoint(x: w * CGFloat(t), y: 12))
                        }
                        .stroke(Theme.ink, style: Theme.Stroke.dashed)
                    }
                }
            }
            .frame(height: 8)
            if let t = target {
                HStack(spacing: Theme.Space.xs) {
                    Text("Target").monoLabel()
                    Text(Theme.percent(t)).font(Theme.Typo.monoBody).foregroundStyle(Theme.ink)
                }
            }
        }
        .frame(minWidth: 150, maxWidth: 200)
    }

    private var statsBlock: some View {
        VStack(alignment: .leading, spacing: 6) {
            if report.headline != nil {
                if let v = report.variant { Annotation(label: "Variant", value: Theme.tag(v)) }
                ForEach(report.metrics) { m in
                    Annotation(label: m.label, value: m.value)
                }
            } else {
                if let v = report.variant { Annotation(label: "Variant", value: Theme.tag(v)) }
                if let n = report.throwsCount { Annotation(label: "Throws", value: "\(n)") }
                Annotation(label: "Reach", value: Theme.percent(report.reachRate))
                Annotation(label: "Skipped", value: Theme.percent(report.skippedStepRate))
                if let m = report.meanMarginS { Annotation(label: "Margin", value: String(format: "%.3f s", m)) }
                if let j = report.worstJoint { Annotation(label: "Worst", value: j.uppercased()) }
            }
        }
        .fixedSize()
    }

    /// Failure breakdown as hand-drawn horizontal bars. Bars are scaled to the widest
    /// count with room reserved for the value label, so the count is always visible and
    /// nothing overflows the panel at any width.
    private var failures: some View {
        let maxCount = max(1, report.failures.map(\.count).max() ?? 1)
        return VStack(alignment: .leading, spacing: Theme.Space.s) {
            HStack(spacing: Theme.Space.xs) {
                Text("Failures").monoLabel()
                Spacer(minLength: 0)
                if let n = report.throwsCount { Text("of \(n) throws").monoLabel(size: 9) }
            }
            VStack(alignment: .leading, spacing: 6) {
                ForEach(report.failures) { f in
                    FailureBar(label: f.label, count: f.count, maxCount: maxCount)
                }
            }
            .overlay(alignment: .leading) {
                // Zero line of the bars (after the label column).
                Rectangle().fill(Theme.ink).frame(width: Theme.Stroke.hair)
                    .padding(.leading, FailureBar.labelWidth + Theme.Space.s)
            }
        }
    }

    private var plots: some View {
        VStack(alignment: .leading, spacing: Theme.Space.s) {
            Text("Plots").monoLabel()
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: Theme.Space.s) {
                    ForEach(report.plots, id: \.self) { url in
                        VStack(alignment: .leading, spacing: 2) {
                            FileThumb(url: url, contentMode: .fit)
                                .frame(width: 160, height: 110)
                                .overlay(Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.hair))
                            Text(url.deletingPathExtension().lastPathComponent).monoLabel(size: 9)
                        }
                        .onTapGesture { session.preview(url) }
                        .help("Open on sheet")
                    }
                }
            }
        }
    }
}

struct SimVideo: View {
    let url: URL
    @State private var player: AVPlayer?

    var body: some View {
        VideoPlayer(player: player)
            .onAppear { if player == nil { player = AVPlayer(url: url) } }
            .onChange(of: url) { _, new in player = AVPlayer(url: new) }
            .onDisappear { player?.pause() }
    }
}

/// One row of the failure chart: label | bar scaled to `maxCount` | count.
struct FailureBar: View {
    static let labelWidth: CGFloat = 100
    /// Width kept free after the longest bar for the count text.
    static let valueWidth: CGFloat = 40

    let label: String
    let count: Int
    let maxCount: Int

    var body: some View {
        HStack(spacing: Theme.Space.s) {
            Text(label)
                .monoLabel(size: 9)
                .lineLimit(1)
                .truncationMode(.tail)
                .frame(width: Self.labelWidth, alignment: .leading)
            GeometryReader { geo in
                let track = max(0, geo.size.width - Self.valueWidth)
                let frac = maxCount > 0 ? CGFloat(count) / CGFloat(maxCount) : 0
                HStack(spacing: Theme.Space.xs) {
                    Rectangle()
                        .fill(Theme.ink)
                        .frame(width: count > 0 ? max(1, track * frac) : 0, height: 9)
                    Text("\(count)")
                        .font(Theme.Typo.mono(10, .medium))
                        .foregroundStyle(Theme.ink)
                        .lineLimit(1)
                        .fixedSize()
                    Spacer(minLength: 0)
                }
                .frame(width: geo.size.width, height: geo.size.height, alignment: .leading)
            }
            .frame(height: 14)
        }
        .help("\(label): \(count)")
    }
}
