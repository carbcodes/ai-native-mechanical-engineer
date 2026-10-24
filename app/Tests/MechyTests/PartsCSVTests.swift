import XCTest
@testable import Mechy

final class PartsCSVTests: XCTestCase {
    func testQuotedFieldsAndCRLF() {
        let text = "item,qty,spec,est_unit_usd\r\n"
            + "NEMA 17 stepper,4,\"1.7 A, ~0.45 N m\",9.0\r\n"
            + "Net,1,\"say \"\"hi\"\"\nsecond line\",4\r\n"
            + "\r\n"
        let t = CSVTable(text: text)
        XCTAssertEqual(t.header, ["item", "qty", "spec", "est_unit_usd"])
        XCTAssertEqual(t.rows.count, 2)
        XCTAssertEqual(t.rows[0]["spec"], "1.7 A, ~0.45 N m")
        XCTAssertEqual(t.rows[1]["spec"], "say \"hi\"\nsecond line")
        let line = BOMLine(index: 0, t.rows[0])
        XCTAssertEqual(line.qty, 4)
        XCTAssertEqual(line.totalUSD ?? 0, 36, accuracy: 1e-9)
    }

    func testPrintListTotals() {
        let text = """
        part,qty,material,orientation,est_grams,est_grams_total,infill,volume_cm3,stl
        base_plate,1,PETG,"flat, as installed",69.8,69.8,25%,104.9,stl/base_plate.stl
        tower_plate,2,PETG,flat on its side face,53.4,106.8,25%,84.7,stl/tower_plate.stl
        spacer,nan,PETG,end,3.1,,25%,3.9,stl/spacer.stl
        """
        let t = CSVTable(text: text)
        var list = PartsList()
        list.hasPrintList = true
        list.printed = t.rows.enumerated().map { PrintPart(index: $0.offset, $0.element) }
        XCTAssertEqual(list.printed.count, 3)
        XCTAssertEqual(list.printed[0].orientation, "flat, as installed")
        XCTAssertEqual(list.printed[2].qty, 1)               // "nan" falls back to 1, no trap
        XCTAssertEqual(list.printed[2].gramsTotal ?? 0, 3.1, accuracy: 1e-9)
        XCTAssertEqual(list.printedPieces, 4)
        XCTAssertEqual(list.printedGrams, 69.8 + 106.8 + 3.1, accuracy: 1e-9)
        XCTAssertEqual(list.printed[1].stl, "stl/tower_plate.stl")
    }

    func testPanelStateDecodesWithoutReplayField() throws {
        let json = #"{"id":"6B1C9A1E-8F7A-4C55-9C3B-2D4F1E0A9B11","kind":"cad","x":1,"y":2,"w":300,"h":200,"z":1,"param":"v1"}"#
        let p = try JSONDecoder().decode(PanelState.self, from: Data(json.utf8))
        XCTAssertNil(p.replay)
        XCTAssertEqual(p.param, "v1")
    }
}
