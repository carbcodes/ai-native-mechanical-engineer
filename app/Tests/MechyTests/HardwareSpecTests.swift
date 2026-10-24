import XCTest
import SwiftUI
@testable import Mechy

final class HardwareSpecTests: XCTestCase {
    private func project(drivers: String, motors: String) throws -> URL {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("hw-\(UUID().uuidString)")
        let hw = root.appendingPathComponent("hw")
        try FileManager.default.createDirectory(at: hw, withIntermediateDirectories: true)
        try drivers.write(to: hw.appendingPathComponent("drivers.yaml"), atomically: true, encoding: .utf8)
        try motors.write(to: hw.appendingPathComponent("motors.yaml"), atomically: true, encoding: .utf8)
        return root
    }

    func testReadsUserHardware() throws {
        let root = try project(drivers: """
            drivers:
              - id: a4988
                count: 4
                microsteps: 16
                heatsinks: true
            controller: arduino-uno
            shield: cnc-shield-v3
            power_supply: {voltage_v: 24, current_a: 6}
            bulk_capacitor: {capacitance_uf: 100, voltage_v: 50}
            """, motors: """
            motors:
              - id: nema17
                model: 42SHDC3026-15B
                count: 4
                rated_current_a: 0.9
            """)
        let h = HardwareSpec.load(root: root)
        XCTAssertTrue(h.declared)
        XCTAssertEqual(h.controller, "Arduino Uno")
        XCTAssertEqual(h.shield, "CNC Shield V3")
        XCTAssertEqual(h.driver, "A4988")
        XCTAssertEqual(h.motorModel, "42SHDC3026-15B")
        XCTAssertEqual(h.supplyV, 24)
        XCTAssertEqual(h.capacitorUF, 100)
        XCTAssertEqual(h.microstepJumpers, "MS1 + MS2 + MS3")
        XCTAssertEqual(h.stepsPerRev, 3200)
        XCTAssertEqual(h.vref(senseOhm: 0.1)!, 0.72, accuracy: 1e-9)
        XCTAssertEqual(h.vref(senseOhm: 0.068)!, 0.4896, accuracy: 1e-9)
    }

    func testMissingFilesFallBackToDefaults() {
        let h = HardwareSpec.load(root: URL(fileURLWithPath: "/nonexistent-\(UUID().uuidString)"))
        XCTAssertFalse(h.declared)
        XCTAssertNil(h.driveCurrentA)
        XCTAssertEqual(h.driverCount, 4)
    }

    @MainActor func testRenderDiagram() throws {
        guard let out = ProcessInfo.processInfo.environment["MECHY_RENDER_DIAGRAM"] else { return }
        let h = HardwareSpec.load(root: URL(fileURLWithPath: ProcessInfo.processInfo.environment["MECHY_PROJECT"] ?? "/"))
        let r = ImageRenderer(content: WiringDiagram(hw: h).frame(width: 820, height: 470).background(Theme.surface))
        r.scale = 2
        let img = try XCTUnwrap(r.nsImage)
        let rep = NSBitmapImageRep(data: img.tiffRepresentation!)!
        try rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: out))
    }
}
