import XCTest
@testable import Mechy

final class IntakeModelsTests: XCTestCase {
    private var root: URL!

    override func setUpWithError() throws {
        root = FileManager.default.temporaryDirectory.appendingPathComponent("mechy-intake-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: root.appendingPathComponent("inspiration/yt-abc/frames"),
                                                withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: root.appendingPathComponent("inspiration/notes"),
                                                withIntermediateDirectories: true)
    }

    override func tearDownWithError() throws {
        try? FileManager.default.removeItem(at: root)
    }

    private func touch(_ rel: String, _ text: String = "x") throws {
        try text.write(to: root.appendingPathComponent(rel), atomically: true, encoding: .utf8)
    }

    func testVideoDigestFromSourceJSON() throws {
        try touch("inspiration/yt-abc/frames/f000.jpg")
        try touch("inspiration/yt-abc/frames/f001.jpg")
        try touch("inspiration/yt-abc/contact.jpg")
        try touch("inspiration/yt-abc/transcript.txt", "[0:01] hello")
        try touch("inspiration/notes/yt-abc.md", "# Note")
        let json = """
        {"schema": 1, "kind": "youtube", "slug": "yt-abc", "title": "Robot arm catches ball",
         "url": "https://www.youtube.com/watch?v=abc", "duration_s": 247.4, "license": null,
         "frames": [{"t": 1.5, "path": "inspiration/yt-abc/frames/f000.jpg", "scene_score": 0.4},
                    {"t": 30.0, "path": "inspiration/yt-abc/frames/f001.jpg", "scene_score": 0.3},
                    {"t": 60.0, "path": "inspiration/yt-abc/frames/missing.jpg", "scene_score": 0.3}],
         "contact_sheet": "inspiration/yt-abc/contact.jpg",
         "transcript": {"path": "inspiration/yt-abc/transcript.txt", "origin": "captions"},
         "note": "inspiration/notes/yt-abc.md", "warnings": []}
        """
        try touch("inspiration/yt-abc/source.json", json)
        let d = try XCTUnwrap(InspirationDigest(dir: root.appendingPathComponent("inspiration/yt-abc"), root: root))
        XCTAssertEqual(d.kind, "youtube")
        XCTAssertEqual(d.title, "Robot arm catches ball")
        XCTAssertEqual(d.frames.count, 2)               // the missing frame is dropped
        XCTAssertEqual(d.frames.first?.t, 1.5)
        XCTAssertEqual(d.cover?.lastPathComponent, "contact.jpg")
        XCTAssertEqual(d.transcriptOrigin, "captions")
        XCTAssertEqual(d.tag, "2 frames · transcript")
        XCTAssertEqual(InspirationDigest.formatDuration(d.duration), "4:07")
        XCTAssertEqual(d.note?.lastPathComponent, "yt-abc.md")
        XCTAssertTrue(d.isVideo)
    }

    func testBrokenSourceJSONIsSkipped() throws {
        try touch("inspiration/yt-abc/source.json", "{not json")
        XCTAssertNil(InspirationDigest(dir: root.appendingPathComponent("inspiration/yt-abc"), root: root))
    }

    func testDurationFormatting() {
        XCTAssertNil(InspirationDigest.formatDuration(nil))
        XCTAssertNil(InspirationDigest.formatDuration(0))
        XCTAssertEqual(InspirationDigest.formatDuration(59.6), "1:00")
        XCTAssertEqual(InspirationDigest.formatDuration(3723), "1:02:03")
    }

    func testMarkdownBlocks() {
        let md = """
        ---
        source: x
        ---
        # Robot arm catches ball

        | What | Where |
        |---|:--:|
        | Keyframes | frames/ |

        - belt drive
          - two stages
        1. first
        Some **bold** text
        continues here.

        ```
        code line
        ```
        """
        let blocks = MarkdownBlock.parse(md)
        XCTAssertEqual(blocks.first, .heading(level: 1, text: "Robot arm catches ball"))
        XCTAssertTrue(blocks.contains(.table(rows: [["What", "Where"], ["Keyframes", "frames/"]])))
        XCTAssertTrue(blocks.contains(.bullet(text: "belt drive", indent: 0)))
        XCTAssertTrue(blocks.contains(.bullet(text: "two stages", indent: 1)))
        XCTAssertTrue(blocks.contains(.bullet(text: "1. first", indent: 0)))
        XCTAssertTrue(blocks.contains(.paragraph("Some **bold** text continues here.")))
        XCTAssertTrue(blocks.contains(.code("code line")))
    }

    func testIntakeJobTitle() {
        XCTAssertEqual(IntakeJob.title(for: "https://www.example.com/arm"), "example.com/arm")
        XCTAssertEqual(IntakeJob.title(for: "/Users/me/Desktop/clip.mov"), "clip.mov")
    }
}
