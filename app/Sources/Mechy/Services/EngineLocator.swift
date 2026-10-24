import Foundation

/// Finds the `mechy`, `claude` and `codex` executables.
///
/// Apps launched from Finder do not inherit the user's shell PATH, so besides the
/// process PATH we search common install folders and the PATH of a login shell.
enum EngineLocator {
    private static var home: String { NSHomeDirectory() }

    static var commonDirectories: [String] {
        [
            home + "/.local/bin",
            "/opt/homebrew/bin",
            "/usr/local/bin",
            home + "/.pyenv/shims",
            home + "/.cargo/bin",
            home + "/.npm-global/bin",
            home + "/.bun/bin",
            "/usr/bin",
            "/bin",
        ]
    }

    /// PATH reported by the user's login shell (computed once, in the background at launch).
    static let loginShellPATH: String? = {
        let shell = ProcessInfo.processInfo.environment["SHELL"] ?? "/bin/zsh"
        let p = Process()
        p.executableURL = URL(fileURLWithPath: shell)
        p.arguments = ["-l", "-c", "printf %s \"$PATH\""]
        let out = Pipe()
        p.standardOutput = out
        p.standardError = FileHandle.nullDevice
        p.standardInput = FileHandle.nullDevice
        let done = DispatchSemaphore(value: 0)
        p.terminationHandler = { _ in done.signal() }
        do { try p.run() } catch { return nil }
        if done.wait(timeout: .now() + 4) == .timedOut {
            p.terminate()
            return nil
        }
        let data = out.fileHandleForReading.readDataToEndOfFile()
        let s = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
        return (s?.isEmpty ?? true) ? nil : s
    }()

    /// Call at launch so the first engine command does not wait on the shell.
    static func warmUp() {
        DispatchQueue.global(qos: .utility).async { _ = loginShellPATH }
    }

    static var searchDirectories: [String] {
        var dirs: [String] = []
        let env = ProcessInfo.processInfo.environment["PATH"] ?? ""
        for d in env.split(separator: ":") + (loginShellPATH ?? "").split(separator: ":") {
            dirs.append(String(d))
        }
        dirs += commonDirectories
        var seen = Set<String>()
        return dirs.filter { !$0.isEmpty && seen.insert($0).inserted }
    }

    /// Resolve an executable: explicit setting first, then the search path.
    static func find(_ name: String, override: String? = nil) -> URL? {
        let fm = FileManager.default
        if let override, !override.isEmpty {
            return fm.isExecutableFile(atPath: override) ? URL(fileURLWithPath: override) : nil
        }
        for dir in searchDirectories {
            let candidate = (dir as NSString).appendingPathComponent(name)
            if fm.isExecutableFile(atPath: candidate) { return URL(fileURLWithPath: candidate) }
        }
        return nil
    }

    static var mechy: URL? { find("mechy", override: AppSettings.path(SettingsKey.mechyPath)) }

    /// Environment for engine child processes.
    ///
    /// MECHY_PROVIDER / MECHY_CLAUDE_BIN / MECHY_CODEX_BIN are proposed additions to
    /// contracts.md §3 (see app/README.md); an engine that ignores them still works.
    static func childEnvironment() -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        var dirs = searchDirectories
        for key in [SettingsKey.claudePath, SettingsKey.codexPath, SettingsKey.mechyPath] {
            if let p = AppSettings.path(key) { dirs.insert((p as NSString).deletingLastPathComponent, at: 0) }
        }
        env["PATH"] = dirs.joined(separator: ":")
        env["MECHY_PROVIDER"] = AppSettings.provider.rawValue
        if let c = AppSettings.path(SettingsKey.claudePath) { env["MECHY_CLAUDE_BIN"] = c }
        if let c = AppSettings.path(SettingsKey.codexPath) { env["MECHY_CODEX_BIN"] = c }
        env["PYTHONUNBUFFERED"] = "1"
        return env
    }
}
