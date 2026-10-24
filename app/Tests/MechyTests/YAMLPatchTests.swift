import XCTest
import Yams
@testable import Mechy

final class YAMLPatchTests: XCTestCase {
    let option = """
    id: O002-arm-layout
    prompt: Pick an arm layout
    options:
      - id: v1
        title: Belt-driven, motors at base
        stats: {catch_rate: 0.74, reach_m: 0.48, cost_usd: 35}
    chosen: null                 # app writes the chosen option id
    feedback: null               # app writes free-text tweak requests

    """

    func testChosenKeepsCommentAndOtherKeys() throws {
        let out = YAMLPatch.setTopLevel("chosen", to: .string("v1"), in: option)
        XCTAssertTrue(out.contains("chosen: \"v1\"  # app writes the chosen option id"))
        XCTAssertTrue(out.contains("feedback: null"))
        let again = YAMLPatch.setTopLevel("chosen", to: .string("v2"), in: out)
        XCTAssertTrue(again.contains("chosen: \"v2\"  # app writes the chosen option id"))
        let parsed = try XCTUnwrap(Loose(any: try Yams.load(yaml: again)))
        XCTAssertEqual(parsed.string("chosen"), "v2")
        XCTAssertEqual(parsed.dicts("options").count, 1)
    }

    func testFeedbackEscapesQuotesAndNewlines() throws {
        let text = "Make it \"lighter\"\nand # cheaper: please"
        let out = YAMLPatch.setTopLevel("feedback", to: .string(text), in: option)
        let parsed = try XCTUnwrap(Loose(any: try Yams.load(yaml: out)))
        XCTAssertEqual(parsed.string("feedback"), text)
    }

    func testReplacesBlockValueAndAppendsMissingKey() throws {
        let q = "id: Q1\ntext: How high?\nanswer: |\n  old\n  text\nkind: text\n"
        let out = YAMLPatch.setTopLevel("answer", to: .number(1.5), in: q)
        XCTAssertEqual(out, "id: Q1\ntext: How high?\nanswer: 1.5\nkind: text\n")
        let added = YAMLPatch.setTopLevel("answer", to: .string("x"), in: "id: Q2\n")
        XCTAssertEqual(added, "id: Q2\nanswer: \"x\"\n")
    }

    func testKeyLineDoesNotMatchLongerKeys() {
        XCTAssertFalse(YAMLPatch.isKeyLine("chosen_by: x", "chosen"))
        XCTAssertTrue(YAMLPatch.isKeyLine("chosen: x", "chosen"))
        XCTAssertTrue(YAMLPatch.isKeyLine("chosen:", "chosen"))
    }

    func testQuestionModel() throws {
        let yaml = """
        id: Q003-throw-height
        text: How high will the ball be when it's thrown?
        kind: choice
        choices: [Underhand from waist, Overhand from shoulder, Not sure]
        answer: null
        """
        let d = try XCTUnwrap(Loose(any: try Yams.load(yaml: yaml)))
        let q = Question(fileURL: URL(fileURLWithPath: "/tmp/q.yaml"), d)
        XCTAssertEqual(q.kind, .choice)
        XCTAssertEqual(q.choices.count, 3)
        XCTAssertFalse(q.isAnswered)
    }

    func testTags() {
        XCTAssertEqual(Theme.tag("v3"), "V³")
        XCTAssertEqual(Theme.tag("T014"), "T¹⁴")
        XCTAssertEqual(Theme.tag("tennis"), "TENNIS")
    }
}
