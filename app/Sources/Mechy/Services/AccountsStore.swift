import Foundation
import AppKit

/// One provider's account status from `mechy accounts status`.
struct AccountStatus {
    let installed: Bool
    let bin: String?
    let version: String?
    let loggedIn: Bool?
    let method: String?
    let detail: String?

    init(_ d: Loose) {
        installed = d.bool("installed") ?? false
        bin = d.string("bin")
        version = d.string("version")
        loggedIn = d.isNull("logged_in") ? nil : d.bool("logged_in")
        method = d.string("method")
        detail = d.string("detail")
    }

    /// One-line status for the chip, e.g. "Connected · API key".
    var label: String {
        guard installed else {
            return "Not installed"
        }
        guard loggedIn == true else { return loggedIn == false ? "Not signed in" : "Sign-in unknown" }
        let m = method.map { $0 == "api_key" ? "API key" : $0 } ?? "signed in"
        return "Connected · \(m)"
    }

    func installHint(_ provider: String) -> String {
        "npm i -g " + (provider == "codex" ? "@openai/codex" : "@anthropic-ai/claude-code")
    }
}

/// Loads and watches `mechy accounts status`; the Connect button opens a Terminal
/// login script (we never run `claude auth login` / `codex login` inside the app).
final class AccountsStore: ObservableObject {
    @Published private(set) var accounts: [String: AccountStatus] = [:]
    @Published private(set) var loading = false
    /// Provider currently being connected (polling is faster while non-nil).
    @Published private(set) var connecting: String?

    private weak var engine: EngineClient?
    private var timer: Timer?
    private var deadline: Date?
    /// Status when Connect was pressed: a switch (e.g. API key -> ChatGPT) ends polling too.
    private var connectingFrom: AccountStatus?

    init(engine: EngineClient) { self.engine = engine }

    func refresh() {
        guard let engine else { return }
        loading = true
        engine.accountsStatus { [weak self] run in
            self?.loading = false
            guard let accounts = run.result?.dict("accounts") else { return }
            var out: [String: AccountStatus] = [:]
            for p in ["claude", "codex"] {
                if let d = accounts.dict(p) { out[p] = AccountStatus(d) }
            }
            self?.accounts = out
            if let c = self?.connecting, let now = out[c], now.loggedIn == true,
               now.method != self?.connectingFrom?.method || self?.connectingFrom?.loggedIn != true {
                self?.stopPolling()
            }
        }
    }

    /// Write a temp .command that runs the provider's login in Terminal, then open it.
    func connect(_ provider: String) {
        guard let status = accounts[provider], let bin = status.bin ?? EngineLocator.find(provider)?.path
        else { return }
        let login = provider == "codex" ? "login" : "auth login"
        let quoted = "'" + bin.replacingOccurrences(of: "'", with: "'\\''") + "'"
        let script = "#!/bin/zsh\n\(quoted) \(login)\necho\necho \"You can close this window.\"\n"
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("mechy-\(provider)-login.command")
        do {
            try script.write(to: url, atomically: true, encoding: .utf8)
            try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: url.path)
            NSWorkspace.shared.open(url)
        } catch {
            return
        }
        connecting = provider
        connectingFrom = status
        deadline = Date().addingTimeInterval(180)
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { [weak self] _ in
            guard let self else { return }
            if let d = self.deadline, Date() > d { self.stopPolling(); return }
            self.refresh()
        }
    }

    func stopPolling() {
        timer?.invalidate()
        timer = nil
        connecting = nil
        connectingFrom = nil
        deadline = nil
    }
}
