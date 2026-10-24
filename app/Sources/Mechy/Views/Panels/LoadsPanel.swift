import SwiftUI

/// One joint of design/<v>/loads.json (written by `mechy cad build`).
struct JointLoad: Identifiable {
    var id: String { joint }
    let joint: String
    let gearRatio: Double
    let motor: String
    /// Worst-case gravity torque at the joint (N·m).
    let jointTorque: Double
    /// The same, at the motor shaft after the belt reduction (N·m).
    let motorTorque: Double
    let holding: Double
    let atSpeed: Double?
    let usableSpeedRPS: Double?
    let jointAvailable: Double?
    let sfStatic: Double?
    let sfAtSpeed: Double?
    let inertiaRatio: Double?

    init(_ d: Loose) {
        joint = d.string("joint") ?? "joint"
        gearRatio = d.double("gear_ratio") ?? 1
        motor = d.string("motor") ?? "motor"
        jointTorque = d.double("gravity_torque_joint_nm") ?? 0
        motorTorque = d.double("gravity_torque_motor_nm") ?? 0
        holding = d.double("holding_torque_nm") ?? 0
        atSpeed = d.double("torque_at_speed_nm")
        usableSpeedRPS = d.double("usable_speed_rps")
        jointAvailable = d.double("joint_torque_available_nm")
        sfStatic = d.double("safety_factor_static")
        sfAtSpeed = d.double("safety_factor_at_speed")
        if let load = d.double("load_inertia_motor_kgm2"), let rotor = d.double("rotor_inertia_kgm2"), rotor > 0 {
            inertiaRatio = load / rotor
        } else {
            inertiaRatio = nil
        }
    }

    /// Weakest margin we know of.
    var margin: Double? { [sfStatic, sfAtSpeed].compactMap { $0 }.min() }
}

struct LoadReport {
    var joints: [JointLoad] = []
    var note: String?
    var exists = false

    static func load(_ variant: DesignVariant) -> LoadReport {
        guard let d = FileIO.loadJSON(variant.dir.appendingPathComponent("loads.json")) else { return LoadReport() }
        return LoadReport(joints: d.dicts("joints").map(JointLoad.init), note: d.string("note"), exists: true)
    }
}

/// Load analysis: for each joint, the torque gravity puts on the motor (arm stretched out,
/// ball in the cup) against what the motor gives, as bars plus the safety factor.
struct LoadsPanel: View {
    let panel: PanelState
    @EnvironmentObject var session: ProjectSession
    @State private var report = LoadReport()

    private var variantName: String? {
        if let p = panel.param, session.variants.contains(where: { $0.name == p }) { return p }
        return session.activeVariant
    }
    private var variant: DesignVariant? { session.variants.first { $0.name == variantName } }
    private var loadKey: String { "\(variantName ?? "-")#\(session.revision)" }

    var body: some View {
        VStack(spacing: 0) {
            PanelStrip {
                VariantTags(selected: variantName) { session.setParam(panel.id, $0) }
                Spacer(minLength: 0)
                Button("Rebuild") { session.buildCAD(variantName) }
                    .buttonStyle(SheetButtonStyle(compact: true))
                    .disabled(variantName == nil)
                    .help("mechy cad build: recomputes loads.json from the solids")
            }
            content
        }
        .task(id: loadKey) {
            report = variant.map(LoadReport.load) ?? LoadReport()
        }
    }

    @ViewBuilder private var content: some View {
        if let v = variant {
            if !report.exists {
                EmptySheet(symbol: "scalemass", label: "No load analysis for \(Theme.tag(v.name))",
                           actionTitle: "Build CAD") { session.buildCAD(v.name) }
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: Theme.Space.l) {
                        verdict
                        VStack(spacing: Theme.Space.m) {
                            ForEach(report.joints) { j in row(j) }
                        }
                        legend
                        if let n = report.note {
                            Text(n).font(Theme.Typo.small).foregroundStyle(Theme.muted)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .padding(Theme.Space.m)
                }
            }
        } else {
            EmptySheet(symbol: "scalemass", label: "No design variants")
        }
    }

    private var verdict: some View {
        let weakest = report.joints.filter { $0.margin != nil }.min { ($0.margin ?? 0) < ($1.margin ?? 0) }
        let ok = (weakest?.margin ?? 99) >= 1.5
        return HStack(alignment: .firstTextBaseline, spacing: Theme.Space.m) {
            Text(weakest?.margin.map { String(format: "%.1f×", $0) } ?? "—")
                .font(Theme.Typo.mono(34, .light))
                .foregroundStyle(ok ? Theme.ink : Theme.danger)
            VStack(alignment: .leading, spacing: 2) {
                Text("Lowest safety factor").monoLabel(Theme.muted, size: 9)
                Text(weakest.map { "\($0.joint.capitalizedFirst): \(ok ? "holds the arm with margin" : "too close; raise the gear ratio or current")" }
                     ?? "No joint carries gravity load")
                    .font(Theme.Typo.small).foregroundStyle(Theme.ink)
            }
        }
    }

    private func row(_ j: JointLoad) -> some View {
        let scale = max(j.holding, j.motorTorque, 0.001)
        let sf = j.margin
        let color: Color = sf == nil ? Theme.muted : (sf! < 1 ? Theme.danger : (sf! < 1.5 ? Theme.accent : Theme.good))
        return VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .firstTextBaseline) {
                Text(j.joint).monoLabel(Theme.ink)
                Text("\(fmt(j.gearRatio)):1").monoLabel(Theme.muted, size: 9)
                Spacer()
                Text(sf.map { String(format: "SF %.1f", $0) } ?? "no gravity load").monoLabel(color, size: 10)
            }
            // Bars on one scale: need (solid) vs holding torque (outline) vs at speed (dashed tick).
            GeometryReader { geo in
                let w = geo.size.width
                ZStack(alignment: .leading) {
                    Rectangle().stroke(Theme.frame, lineWidth: 1)
                        .frame(width: w * CGFloat(j.holding / scale), height: 12)
                    Rectangle().fill(color.opacity(0.85))
                        .frame(width: max(1, w * CGFloat(j.motorTorque / scale)), height: 12)
                    if let s = j.atSpeed {
                        Rectangle().fill(Theme.ink).frame(width: 1.5, height: 18)
                            .offset(x: w * CGFloat(s / scale) - 0.75)
                    }
                }
            }
            .frame(height: 18)
            HStack(spacing: Theme.Space.m) {
                stat("Need", "\(fmt(j.motorTorque, 3)) N·m")
                stat("Motor", "\(fmt(j.holding)) N·m")
                if let s = j.atSpeed { stat("At \(fmt(j.usableSpeedRPS ?? 0)) rev/s", "\(fmt(s)) N·m") }
                stat("Joint", "\(fmt(j.jointTorque)) / \(fmt(j.jointAvailable ?? 0)) N·m")
                // Steppers lose steps accelerating loads much over ~10x their rotor inertia.
                if let r = j.inertiaRatio { stat("Inertia", "\(Int(r.rounded())):1", warn: r > 10) }
            }
        }
        .padding(.bottom, Theme.Space.xs)
        .overlay(alignment: .bottom) { Hairline() }
    }

    private var legend: some View {
        HStack(spacing: Theme.Space.m) {
            HStack(spacing: 4) { Rectangle().fill(Theme.good).frame(width: 14, height: 8); Text("Gravity need") }
            HStack(spacing: 4) { Rectangle().stroke(Theme.frame).frame(width: 14, height: 8); Text("Holding torque") }
            HStack(spacing: 4) { Rectangle().fill(Theme.ink).frame(width: 1.5, height: 10); Text("Torque at usable speed") }
        }
        .font(Theme.Typo.mono(9))
        .foregroundStyle(Theme.muted)
    }

    private func stat(_ label: String, _ value: String, warn: Bool = false) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(label).monoLabel(warn ? Theme.danger : Theme.muted, size: 8)
            Text(value).font(Theme.Typo.mono(10)).foregroundStyle(warn ? Theme.danger : Theme.ink)
        }
        .help(warn ? "Load inertia over 10× the rotor's: the motor will struggle to accelerate it and may skip steps" : "")
    }

    private func fmt(_ v: Double, _ digits: Int = 2) -> String {
        var s = String(format: "%.\(digits)f", v)
        if s.contains(".") { while s.hasSuffix("0") { s.removeLast() }; if s.hasSuffix(".") { s.removeLast() } }
        return s
    }
}
