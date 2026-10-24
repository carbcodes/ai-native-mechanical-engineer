import SwiftUI

/// Electronics: a wiring diagram of the arm's control box (supply -> bulk capacitor -> CNC
/// shield on the Uno -> four drivers -> four motors, plus USB and limit switches), drawn from
/// hw/drivers.yaml and hw/motors.yaml, then the numbers to set (Vref, microstep jumpers) and
/// a short bring-up checklist.
struct ElectronicsPanel: View {
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        let hw = session.hardware
        VStack(spacing: 0) {
            PanelStrip {
                Text("\(hw.controller) · \(hw.shield) · \(hw.driverCount)× \(hw.driver)").monoLabel(Theme.ink, size: 9)
                    .lineLimit(1)
                Spacer(minLength: 0)
                if !hw.declared {
                    Text("No hw/ files: defaults").monoLabel(Theme.muted, size: 9)
                }
                Button("Firmware") { session.generateFirmware(session.makeVariant) }
                    .buttonStyle(SheetButtonStyle(compact: true))
                    .disabled(session.makeVariant == nil)
                    .help("mechy control gen: Arduino sketch + pin map for this wiring")
            }
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Space.l) {
                    WiringDiagram(hw: hw)
                        .aspectRatio(WiringDiagram.size.width / WiringDiagram.size.height, contentMode: .fit)
                        .frame(maxWidth: .infinity)
                    settings(hw)
                    checklist(hw)
                }
                .padding(Theme.Space.m)
            }
        }
    }

    // MARK: Numbers to set

    private func settings(_ hw: HardwareSpec) -> some View {
        let rows: [(String, String)] = [
            ("Motor", "\(hw.motorModel) · \(hw.ratedCurrentA.map { fmt($0, "A") } ?? "? A")/phase"
                + (hw.holdingTorqueNm.map { " · \(fmt($0, "N·m")) hold" } ?? "")),
            ("Driver current", hw.driveCurrentA.map { fmt($0, "A") } ?? "set motors.yaml rated_current_a"),
            ("Vref (R100 clone)", hw.vref(senseOhm: 0.100).map { fmt($0, "V", digits: 2) } ?? "—"),
            ("Vref (R068 Pololu)", hw.vref(senseOhm: 0.068).map { fmt($0, "V", digits: 2) } ?? "—"),
            ("Microsteps", "1/\(hw.microsteps) · jumpers \(hw.microstepJumpers) · \(hw.stepsPerRev) steps/rev"),
            ("Supply", [hw.supplyV.map { fmt($0, "V") }, hw.supplyA.map { fmt($0, "A") }].compactMap { $0 }.joined(separator: " · ")
                + (hw.estimatedSupplyA.map { " · expect ≈ \(fmt($0, "A", digits: 1)) draw (est.)" } ?? "")),
            ("Bulk capacitor", hw.capacitorUF.map { "\(fmt($0, "µF")) / \(hw.capacitorV.map { fmt($0, "V") } ?? "?") across motor power in" }
                ?? "add ≥ 100 µF across motor power in"),
        ]
        return VStack(alignment: .leading, spacing: 0) {
            Text("Settings").monoLabel(Theme.ink)
                .padding(.bottom, Theme.Space.xs)
            ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                HStack(alignment: .firstTextBaseline, spacing: Theme.Space.s) {
                    Text(row.0).monoLabel(Theme.muted, size: 9).frame(width: 130, alignment: .leading)
                    Text(row.1).font(Theme.Typo.monoBody).foregroundStyle(Theme.ink)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(.vertical, 4)
                .overlay(alignment: .bottom) { Hairline() }
            }
        }
    }

    private func checklist(_ hw: HardwareSpec) -> some View {
        let steps = [
            "Set each \(hw.driver)'s Vref with the shield powered and motors unplugged (meter between the trim pot and GND).",
            "Fit microstep jumpers \(hw.microstepJumpers) under every driver socket.",
            "Seat drivers with the EN pin toward the shield's EN label; a reversed driver dies on power-up.",
            "Capacitor: + leg to V+, striped leg to GND, as close to the shield's power terminal as possible.",
            "Pair motor wires by coil (a multimeter beeps across a coil); wire colors differ between makers.",
            "Never plug or unplug a motor while the \(hw.supplyV.map { fmt($0, "V") } ?? "motor") supply is on.",
            "USB powers the Uno logic only; the motors need the DC supply as well.",
        ]
        return VStack(alignment: .leading, spacing: Theme.Space.xs) {
            Text("Bring-up").monoLabel(Theme.ink)
                .padding(.bottom, Theme.Space.xxs)
            ForEach(Array(steps.enumerated()), id: \.offset) { i, s in
                HStack(alignment: .firstTextBaseline, spacing: Theme.Space.s) {
                    NoteNumber(n: i + 1)
                    Text(s).font(Theme.Typo.small).foregroundStyle(Theme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private func fmt(_ v: Double, _ unit: String, digits: Int = 2) -> String {
        let s = String(format: "%.\(digits)f", v)
        var t = s
        if t.contains(".") {
            while t.hasSuffix("0") { t.removeLast() }
            if t.hasSuffix(".") { t.removeLast() }
        }
        return "\(t) \(unit)"
    }
}

/// The wiring diagram, drawn in a fixed 820 x 470 sheet and scaled to fit.
struct WiringDiagram: View {
    let hw: HardwareSpec
    static let size = CGSize(width: 820, height: 470)

    /// Semantic wire colors (the one place the sheet uses color beyond accent: wires must be told apart).
    static let vPlus = Color(hex: 0xC8102E)
    static let coilA = Color(hex: 0x2F7FD1)
    static let coilB = Color(hex: 0x2F9A6E)
    static let signal = Color(hex: 0xD3A12B)

    var body: some View {
        Canvas { ctx, size in
            let k = min(size.width / Self.size.width, size.height / Self.size.height)
            ctx.scaleBy(x: k, y: k)
            draw(&ctx)
        }
    }

    // MARK: Layout (sheet coordinates)

    private let psu = CGRect(x: 10, y: 30, width: 150, height: 92)
    private let shield = CGRect(x: 300, y: 20, width: 290, height: 330)
    private let uno = CGRect(x: 300, y: 372, width: 290, height: 70)
    private let terminal = CGRect(x: 312, y: 40, width: 74, height: 40)
    private func socket(_ i: Int) -> CGRect { CGRect(x: 420, y: 40 + CGFloat(i) * 74, width: 120, height: 62) }
    private func motor(_ i: Int) -> CGRect { CGRect(x: 690, y: 34 + CGFloat(i) * 74, width: 120, height: 54) }

    private func draw(_ ctx: inout GraphicsContext) {
        let ink = Theme.ink, muted = Theme.muted

        // Supply
        box(&ctx, psu)
        label(&ctx, "DC SUPPLY", at: CGPoint(x: psu.minX + 10, y: psu.minY + 14), size: 9, color: muted)
        let v = hw.supplyV.map { "\(Int($0)) V" } ?? "12–24 V"
        let a = hw.supplyA.map { "\(Int($0)) A" } ?? ""
        label(&ctx, "\(v)  \(a)", at: CGPoint(x: psu.minX + 10, y: psu.minY + 36), size: 16, weight: .medium, color: ink)
        // Connector, one option per line so it stays inside the box.
        let connector = (hw.supplyConnector ?? "barrel / terminal").uppercased()
            .components(separatedBy: "/").map { $0.trimmingCharacters(in: .whitespaces) }.prefix(2)
        for (i, line) in connector.enumerated() {
            label(&ctx, i == 0 && connector.count > 1 ? line + " /" : line,
                  at: CGPoint(x: psu.minX + 10, y: psu.minY + 58 + CGFloat(i) * 11), size: 7, color: muted)
        }
        pin(&ctx, CGPoint(x: psu.maxX, y: psu.minY + 30), "+", Self.vPlus)
        pin(&ctx, CGPoint(x: psu.maxX, y: psu.minY + 70), "−", ink)

        // Power rails: supply -> capacitor -> shield terminal
        let vy = psu.minY + 30, gy = psu.minY + 70
        let tPlus = CGPoint(x: terminal.minX, y: terminal.minY + 12), tGnd = CGPoint(x: terminal.minX, y: terminal.minY + 30)
        wire(&ctx, [CGPoint(x: psu.maxX, y: vy), CGPoint(x: 270, y: vy), CGPoint(x: 270, y: tPlus.y), tPlus], Self.vPlus, width: 2)
        wire(&ctx, [CGPoint(x: psu.maxX, y: gy), CGPoint(x: 282, y: gy), CGPoint(x: 282, y: tGnd.y), tGnd], ink, width: 2)
        // Capacitor across the rails, near the terminal
        let cx: CGFloat = 225
        wire(&ctx, [CGPoint(x: cx, y: vy), CGPoint(x: cx, y: vy + 12)], Self.vPlus)
        wire(&ctx, [CGPoint(x: cx, y: gy - 12), CGPoint(x: cx, y: gy)], ink)
        var plate = Path()
        plate.move(to: CGPoint(x: cx - 11, y: vy + 12)); plate.addLine(to: CGPoint(x: cx + 11, y: vy + 12))
        ctx.stroke(plate, with: .color(ink), lineWidth: 2)
        var curved = Path()
        curved.move(to: CGPoint(x: cx - 11, y: gy - 9))
        curved.addQuadCurve(to: CGPoint(x: cx + 11, y: gy - 9), control: CGPoint(x: cx, y: gy - 16))
        ctx.stroke(curved, with: .color(ink), lineWidth: 2)
        dot(&ctx, CGPoint(x: cx, y: vy), Self.vPlus); dot(&ctx, CGPoint(x: cx, y: gy), ink)
        label(&ctx, "+", at: CGPoint(x: cx - 18, y: vy + 6), size: 9, weight: .bold, color: Self.vPlus)
        let cap = hw.capacitorUF.map { "\(Int($0)) µF" } ?? "100 µF"
        let capV = hw.capacitorV.map { "\(Int($0)) V" } ?? "≥ 2× supply"
        label(&ctx, cap, at: CGPoint(x: cx + 16, y: vy + 15), size: 9, weight: .medium, color: ink)
        label(&ctx, capV, at: CGPoint(x: cx + 16, y: vy + 27), size: 8, color: muted)

        // Shield + Uno
        box(&ctx, shield)
        label(&ctx, hw.shield.uppercased(), at: CGPoint(x: shield.minX + 10, y: shield.maxY - 14), size: 9, weight: .semibold, color: ink)
        box(&ctx, terminal)
        label(&ctx, "POWER IN", at: CGPoint(x: terminal.minX + 6, y: terminal.minY - 8), size: 7, color: muted)
        label(&ctx, "+", at: CGPoint(x: terminal.minX + 8, y: terminal.minY + 12), size: 9, weight: .bold, color: Self.vPlus)
        label(&ctx, "GND", at: CGPoint(x: terminal.minX + 8, y: terminal.minY + 30), size: 8, color: ink)
        dashedBox(&ctx, uno)
        label(&ctx, hw.controller.uppercased(), at: CGPoint(x: uno.minX + 10, y: uno.minY + 16), size: 10, weight: .semibold, color: ink)
        label(&ctx, "UNDER THE SHIELD · STEP / DIR / EN VIA HEADERS", at: CGPoint(x: uno.minX + 10, y: uno.minY + 34), size: 7, color: muted)
        label(&ctx, "EN = D8 (ALL DRIVERS)", at: CGPoint(x: uno.minX + 10, y: uno.minY + 50), size: 7, color: muted)
        // stacking arrows shield <-> uno
        wire(&ctx, [CGPoint(x: shield.midX, y: shield.maxY), CGPoint(x: shield.midX, y: uno.minY)], muted, dash: [3, 3])

        // USB to computer
        let usb = CGRect(x: 10, y: 388, width: 150, height: 40)
        box(&ctx, usb)
        label(&ctx, "COMPUTER", at: CGPoint(x: usb.minX + 10, y: usb.minY + 14), size: 9, weight: .medium, color: ink)
        label(&ctx, "SERIAL 115200", at: CGPoint(x: usb.minX + 10, y: usb.minY + 28), size: 7, color: muted)
        wire(&ctx, [CGPoint(x: usb.maxX, y: usb.midY), CGPoint(x: uno.minX, y: usb.midY)], Self.signal, width: 2)
        label(&ctx, "USB-B · LOGIC POWER", at: CGPoint(x: usb.maxX + 14, y: usb.midY - 8), size: 7, color: muted)

        // Drivers, motors and their coil wires
        for i in 0..<4 {
            let s = socket(i), m = motor(i)
            let slot = HardwareSpec.unoSlots[i]
            box(&ctx, s, color: i < hw.driverCount ? ink : muted)
            label(&ctx, slot.socket, at: CGPoint(x: s.minX + 8, y: s.minY + 14), size: 14, weight: .semibold, color: Theme.accent)
            label(&ctx, hw.driver, at: CGPoint(x: s.minX + 30, y: s.minY + 13), size: 9, weight: .medium, color: ink)
            label(&ctx, "STEP \(slot.step) · DIR \(slot.dir)", at: CGPoint(x: s.minX + 8, y: s.minY + 32), size: 7, color: muted)
            if let vr = hw.vref(senseOhm: 0.100) {
                label(&ctx, String(format: "VREF %.2f V", vr), at: CGPoint(x: s.minX + 8, y: s.minY + 46), size: 7, color: muted)
            }
            if hw.heatsinks { heatsink(&ctx, CGRect(x: s.maxX - 26, y: s.minY + 6, width: 18, height: 18)) }
            // Supply rail into each driver (VMOT), drawn as a short stub from the terminal bus
            wire(&ctx, [CGPoint(x: 400, y: s.midY), CGPoint(x: s.minX, y: s.midY)], Self.vPlus.opacity(0.55))

            // 4 coil wires: A1 A2 (coil A), B1 B2 (coil B)
            let names = ["2B", "2A", "1A", "1B"]
            let colors = [Self.coilB, Self.coilB, Self.coilA, Self.coilA]
            for w in 0..<4 {
                let y0 = s.minY + 12 + CGFloat(w) * 12
                let y1 = m.minY + 9 + CGFloat(w) * 12
                let x0 = s.maxX, x1 = m.minX
                wire(&ctx, [CGPoint(x: x0, y: y0), CGPoint(x: 615 + CGFloat(w) * 6, y: y0),
                            CGPoint(x: 615 + CGFloat(w) * 6, y: y1), CGPoint(x: x1, y: y1)], colors[w], width: 1.4)
                if i == 0 {
                    label(&ctx, names[w], at: CGPoint(x: x0 + 3, y: y0 - 4), size: 6, color: muted)
                }
            }
            // Motor
            box(&ctx, m)
            var shaft = Path()
            shaft.addEllipse(in: CGRect(x: m.maxX - 30, y: m.midY - 10, width: 20, height: 20))
            ctx.stroke(shaft, with: .color(ink), lineWidth: 1)
            ctx.fill(Path(ellipseIn: CGRect(x: m.maxX - 23, y: m.midY - 3, width: 6, height: 6)), with: .color(ink))
            label(&ctx, HardwareSpec.joints[i].uppercased(), at: CGPoint(x: m.minX + 8, y: m.minY + 14), size: 9, weight: .semibold, color: ink)
            label(&ctx, hw.motorModel.uppercased(), at: CGPoint(x: m.minX + 8, y: m.minY + 29), size: 6, color: muted)
            label(&ctx, hw.ratedCurrentA.map { String(format: "%.1f A/PH", $0) } ?? "", at: CGPoint(x: m.minX + 8, y: m.minY + 42),
                  size: 6, color: muted)
        }
        // VMOT bus from the power terminal down past every socket
        wire(&ctx, [CGPoint(x: terminal.maxX, y: terminal.minY + 12), CGPoint(x: 400, y: terminal.minY + 12),
                    CGPoint(x: 400, y: socket(3).midY)], Self.vPlus.opacity(0.55))

        // Limit switches
        let sw = CGRect(x: 690, y: 372, width: 120, height: 70)
        box(&ctx, sw)
        label(&ctx, "LIMIT SWITCHES", at: CGPoint(x: sw.minX + 8, y: sw.minY + 14), size: 8, weight: .semibold, color: ink)
        let pins = HardwareSpec.unoSlots.map { "\($0.socket) \($0.limit)" }.joined(separator: " · ")
        label(&ctx, pins, at: CGPoint(x: sw.minX + 8, y: sw.minY + 30), size: 6, color: muted)
        label(&ctx, "NO CONTACT TO GND", at: CGPoint(x: sw.minX + 8, y: sw.minY + 44), size: 6, color: muted)
        wire(&ctx, [CGPoint(x: sw.minX, y: sw.midY), CGPoint(x: shield.maxX, y: sw.midY), CGPoint(x: shield.maxX, y: shield.maxY - 20),
                    CGPoint(x: shield.maxX - 20, y: shield.maxY - 20)], Self.signal, dash: [4, 3])

        // Legend
        let ly: CGFloat = 196
        legend(&ctx, CGPoint(x: 14, y: ly), Self.vPlus, "MOTOR POWER +")
        legend(&ctx, CGPoint(x: 14, y: ly + 16), ink, "GROUND")
        legend(&ctx, CGPoint(x: 14, y: ly + 32), Self.coilA, "COIL A (1A / 1B)")
        legend(&ctx, CGPoint(x: 14, y: ly + 48), Self.coilB, "COIL B (2A / 2B)")
        legend(&ctx, CGPoint(x: 14, y: ly + 64), Self.signal, "LOGIC / SIGNAL")
    }

    // MARK: Primitives

    private func box(_ ctx: inout GraphicsContext, _ r: CGRect, color: Color = Theme.ink) {
        ctx.fill(Path(r), with: .color(Theme.surface))
        ctx.stroke(Path(r), with: .color(color), lineWidth: 1)
    }

    private func dashedBox(_ ctx: inout GraphicsContext, _ r: CGRect) {
        ctx.fill(Path(r), with: .color(Theme.surface))
        ctx.stroke(Path(r), with: .color(Theme.ink), style: StrokeStyle(lineWidth: 1, dash: [4, 4]))
    }

    private func wire(_ ctx: inout GraphicsContext, _ pts: [CGPoint], _ color: Color, width: CGFloat = 1, dash: [CGFloat] = []) {
        var p = Path()
        p.addLines(pts)
        ctx.stroke(p, with: .color(color), style: StrokeStyle(lineWidth: width, lineCap: .square, lineJoin: .miter, dash: dash))
    }

    private func dot(_ ctx: inout GraphicsContext, _ c: CGPoint, _ color: Color) {
        ctx.fill(Path(ellipseIn: CGRect(x: c.x - 2.5, y: c.y - 2.5, width: 5, height: 5)), with: .color(color))
    }

    private func pin(_ ctx: inout GraphicsContext, _ c: CGPoint, _ text: String, _ color: Color) {
        ctx.fill(Path(CGRect(x: c.x - 3, y: c.y - 3, width: 6, height: 6)), with: .color(color))
        label(&ctx, text, at: CGPoint(x: c.x - 14, y: c.y), size: 10, weight: .bold, color: color)
    }

    private func heatsink(_ ctx: inout GraphicsContext, _ r: CGRect) {
        ctx.stroke(Path(r), with: .color(Theme.muted), lineWidth: 0.5)
        var fins = Path()
        var x = r.minX + 3
        while x < r.maxX { fins.move(to: CGPoint(x: x, y: r.minY)); fins.addLine(to: CGPoint(x: x, y: r.maxY)); x += 3 }
        ctx.stroke(fins, with: .color(Theme.muted), lineWidth: 0.5)
    }

    private func legend(_ ctx: inout GraphicsContext, _ p: CGPoint, _ color: Color, _ text: String) {
        wire(&ctx, [p, CGPoint(x: p.x + 22, y: p.y)], color, width: 2)
        label(&ctx, text, at: CGPoint(x: p.x + 30, y: p.y), size: 7, color: Theme.muted)
    }

    private func label(_ ctx: inout GraphicsContext, _ text: String, at p: CGPoint, size: CGFloat,
                       weight: Font.Weight = .regular, color: Color) {
        ctx.draw(Text(text).font(Theme.Typo.mono(size, weight)).foregroundColor(color), at: p, anchor: .leading)
    }
}
