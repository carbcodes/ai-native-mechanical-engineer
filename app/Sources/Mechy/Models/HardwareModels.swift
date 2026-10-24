import Foundation

/// The arm's electronics as declared in hw/drivers.yaml and hw/motors.yaml (read leniently;
/// anything missing falls back to the Uno + CNC Shield V3 + A4988 + NEMA 17 defaults).
struct HardwareSpec: Equatable {
    var controller = "Arduino Uno"
    var shield = "CNC Shield V3"
    var driver = "A4988"
    var driverCount = 4
    var driverMaxCurrentA = 2.0
    var heatsinks = true
    var microsteps = 16
    var motorModel = "NEMA 17"
    var motorCount = 4
    var ratedCurrentA: Double?
    var holdingTorqueNm: Double?
    var stepAngleDeg = 1.8
    var supplyV: Double?
    var supplyA: Double?
    var supplyConnector: String?
    var capacitorUF: Double?
    var capacitorV: Double?
    /// True when hw/ had at least one of the two files.
    var declared = false

    /// Joints in socket order X, Y, Z, A (engine/mechy/control/config.py assigns them by index).
    static let joints = ["Base", "Shoulder", "Elbow", "Wrist"]

    /// Uno + CNC Shield V3 slots, mirroring engine/mechy/control/boards.py `uno_cnc`.
    struct Slot { let socket: String; let step: String; let dir: String; let limit: String }
    static let unoSlots = [
        Slot(socket: "X", step: "D2", dir: "D5", limit: "D9"),
        Slot(socket: "Y", step: "D3", dir: "D6", limit: "D10"),
        Slot(socket: "Z", step: "D4", dir: "D7", limit: "D11"),
        Slot(socket: "A", step: "D12", dir: "D13", limit: "A0"),
    ]

    static func load(root: URL) -> HardwareSpec {
        var h = HardwareSpec()
        let drivers = FileIO.loadYAML(root.appendingPathComponent("hw/drivers.yaml"))
        let motors = FileIO.loadYAML(root.appendingPathComponent("hw/motors.yaml"))
        h.declared = drivers != nil || motors != nil
        if let d = drivers {
            if let c = d.string("controller") { h.controller = Self.pretty(c) }
            if let s = d.string("shield") { h.shield = Self.pretty(s) }
            if let drv = d.dicts("drivers").first {
                if let id = drv.string("id") { h.driver = id.uppercased() }
                h.driverCount = drv.int("count") ?? h.driverCount
                h.driverMaxCurrentA = drv.double("max_current_a") ?? h.driverMaxCurrentA
                h.microsteps = drv.int("microsteps") ?? h.microsteps
                h.heatsinks = drv.bool("heatsinks") ?? h.heatsinks
            }
            if let psu = d.dict("power_supply") {
                h.supplyV = psu.double("voltage_v")
                h.supplyA = psu.double("current_a")
                h.supplyConnector = psu.string("connector")
            }
            if let cap = d.dict("bulk_capacitor") {
                h.capacitorUF = cap.double("capacitance_uf")
                h.capacitorV = cap.double("voltage_v")
            }
        }
        if let m = motors?.dicts("motors").first {
            h.motorModel = m.string("model") ?? (m.string("id").map(Self.pretty) ?? h.motorModel)
            h.motorCount = m.int("count") ?? h.motorCount
            h.ratedCurrentA = m.double("rated_current_a")
            h.holdingTorqueNm = m.double("holding_torque_nm")
            h.stepAngleDeg = m.double("step_angle_deg") ?? h.stepAngleDeg
        }
        return h
    }

    /// "arduino-uno" -> "Arduino Uno", "cnc-shield-v3" -> "CNC Shield V3".
    static func pretty(_ id: String) -> String {
        let known = ["cnc": "CNC", "v3": "V3", "nema17": "NEMA 17", "a4988": "A4988", "drv8825": "DRV8825",
                     "tmc2209": "TMC2209", "ramps": "RAMPS"]
        return id.split(whereSeparator: { $0 == "-" || $0 == "_" || $0 == " " }).map { w in
            known[w.lowercased()] ?? w.prefix(1).uppercased() + w.dropFirst()
        }.joined(separator: " ")
    }

    /// Current the driver should be set to: the motor rating, capped by the driver
    /// (A4988 ~1.2 A per coil without forced cooling), as the firmware generator does.
    var driveCurrentA: Double? {
        guard let r = ratedCurrentA else { return nil }
        return min(r, driverMaxCurrentA, driver == "A4988" ? 1.2 : driverMaxCurrentA)
    }

    /// A4988 Vref = I * 8 * Rs, for the two common sense resistors (Pololu 0.068 Ω, clones 0.100 Ω).
    func vref(senseOhm: Double) -> Double? { driveCurrentA.map { $0 * 8 * senseOhm } }

    /// Which of MS1/MS2/MS3 jumpers to fit under each driver (A4988 table).
    var microstepJumpers: String {
        switch microsteps {
        case 1: return "none"
        case 2: return "MS1"
        case 4: return "MS2"
        case 8: return "MS1 + MS2"
        case 16: return "MS1 + MS2 + MS3"
        default: return "see A4988 datasheet"
        }
    }

    var stepsPerRev: Int { Int((360 / stepAngleDeg).rounded()) * microsteps }

    /// Rough draw from the motor supply: chopper drivers pull far less than the phase current.
    /// Assumes ~3.5 Ω coils and two energised coils per motor, plus 20 % driver loss.
    var estimatedSupplyA: Double? {
        guard let i = driveCurrentA, let v = supplyV, v > 0 else { return nil }
        let watts = Double(motorCount) * 2 * i * i * 3.5 * 1.2
        return watts / v
    }
}
