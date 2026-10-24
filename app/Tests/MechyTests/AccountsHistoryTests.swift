import XCTest
@testable import Mechy

final class AccountsHistoryTests: XCTestCase {

    private func json(_ s: String) -> Loose {
        Loose(try! JSONSerialization.jsonObject(with: Data(s.utf8)) as! [String: Any])
    }

    func testAccountStatusParsing() {
        let claude = AccountStatus(json("""
            {"installed": true, "bin": "/opt/homebrew/bin/claude", "version": "2.1.296",
             "logged_in": true, "method": "claude.ai", "detail": null}
            """))
        XCTAssertTrue(claude.installed)
        XCTAssertEqual(claude.loggedIn, true)
        XCTAssertEqual(claude.label, "Connected · claude.ai")

        let codex = AccountStatus(json("""
            {"installed": true, "bin": "/opt/homebrew/bin/codex", "version": "codex-cli 0.163.0",
             "logged_in": true, "method": "api_key", "detail": "Logged in using an API key"}
            """))
        XCTAssertEqual(codex.label, "Connected · API key")

        let out = AccountStatus(json("""
            {"installed": true, "bin": "codex", "version": "codex-cli 0.163.0",
             "logged_in": false, "method": null, "detail": "Not logged in"}
            """))
        XCTAssertEqual(out.label, "Not signed in")

        let missing = AccountStatus(json("""
            {"installed": false, "bin": "codex", "version": null,
             "logged_in": null, "method": null, "detail": "not installed"}
            """))
        XCTAssertFalse(missing.installed)
        XCTAssertEqual(missing.label, "Not installed")
    }

    func testHistoryCommitParsing() {
        let c = HistoryCommit(json("""
            {"sha": "abc123def", "short": "abc123d", "time": "2026-10-24T13:30:17-04:00",
             "message": "T012-arms: add v1", "author": "Mechy", "task": "T012-arms",
             "files": [{"path": "design/v1/params.yaml", "status": "A"},
                       {"path": "design/v1/thumb.png", "status": "M"}],
             "areas": ["design/v1"]}
            """))
        XCTAssertEqual(c.task, "T012-arms")
        XCTAssertEqual(c.files.count, 2)
        XCTAssertEqual(c.designVariants, ["v1"])
        XCTAssertFalse(c.relativeTime.isEmpty)
        XCTAssertEqual(HistoryCommit(json("{\"sha\":\"x\",\"message\":\"m\"}")).task, nil)
    }

    func testSplitLinks() {
        let links = NewProjectComposer.splitLinks("""
            https://youtube.com/watch?v=abc
            not a link
            https://example.com/page
            https://youtu.be/xyz
            """)
        XCTAssertEqual(links.count, 3)
        XCTAssertTrue(links[0].video && links[2].video)
        XCTAssertFalse(links[1].video)
        XCTAssertTrue(NewProjectComposer.splitLinks("no links here").isEmpty)
    }
}
