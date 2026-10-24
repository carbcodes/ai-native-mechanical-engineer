import Foundation
import Yams

/// A forgiving view over a parsed YAML/JSON mapping.
///
/// The contract files are written by agents, so fields can be missing or have a
/// slightly different scalar type than expected (`id: 3` vs `id: "3"`). Instead of
/// strict Codable we parse into Foundation values and read them leniently.
struct Loose {
    let raw: [String: Any]

    init(_ raw: [String: Any]) { self.raw = raw }

    init?(any: Any?) {
        guard let d = Loose.asDict(any) else { return nil }
        self.raw = d
    }

    // MARK: Field access

    func string(_ key: String) -> String? { Loose.text(raw[key]) }

    func double(_ key: String) -> Double? { Loose.number(raw[key]) }

    func int(_ key: String) -> Int? { Loose.number(raw[key]).map { Int($0.rounded()) } }

    func bool(_ key: String) -> Bool? {
        if let n = raw[key] as? NSNumber { return n.boolValue }
        if let s = raw[key] as? String { return ["true", "yes", "on", "1"].contains(s.lowercased()) }
        return nil
    }

    func strings(_ key: String) -> [String] {
        if let arr = raw[key] as? [Any] { return arr.compactMap(Loose.text) }
        if let one = Loose.text(raw[key]) { return [one] }
        return []
    }

    func dict(_ key: String) -> Loose? { Loose(any: raw[key]) }

    func dicts(_ key: String) -> [Loose] {
        (raw[key] as? [Any])?.compactMap { Loose(any: $0) } ?? []
    }

    func isNull(_ key: String) -> Bool { raw[key] == nil || raw[key] is NSNull }

    // MARK: Conversions

    static func asDict(_ any: Any?) -> [String: Any]? {
        guard let any else { return nil }
        if let d = any as? [String: Any] { return d }
        if let d = any as? [AnyHashable: Any] {
            var out: [String: Any] = [:]
            for (k, v) in d { out[(k.base as? String) ?? String(describing: k.base)] = v }
            return out
        }
        return nil
    }

    static func isBoolNumber(_ n: NSNumber) -> Bool {
        CFGetTypeID(n) == CFBooleanGetTypeID()
    }

    /// Any scalar as display text; nil for null / missing / containers.
    static func text(_ value: Any?) -> String? {
        guard let value, !(value is NSNull) else { return nil }
        if let s = value as? String { return s }
        if let n = value as? NSNumber {
            if isBoolNumber(n) { return n.boolValue ? "true" : "false" }
            return formatNumber(n.doubleValue)
        }
        return nil
    }

    static func number(_ value: Any?) -> Double? {
        guard let value, !(value is NSNull) else { return nil }
        if let n = value as? NSNumber, !isBoolNumber(n) { return n.doubleValue }
        if let s = value as? String { return Double(s.trimmingCharacters(in: .whitespaces)) }
        return nil
    }

    static func formatNumber(_ d: Double) -> String {
        if d.rounded() == d && abs(d) < 1e15 { return String(Int(d)) }
        return String(d)
    }
}

/// File helpers used by the project loader.
enum FileIO {
    static let fm = FileManager.default

    static func loadYAML(_ url: URL) -> Loose? {
        guard let text = try? String(contentsOf: url, encoding: .utf8),
              let any = try? Yams.load(yaml: text) else { return nil }
        return Loose(any: any)
    }

    static func loadJSON(_ url: URL) -> Loose? {
        guard let data = try? Data(contentsOf: url),
              let any = try? JSONSerialization.jsonObject(with: data) else { return nil }
        return Loose(any: any)
    }

    static func parseJSONLine(_ line: String) -> Loose? {
        guard let data = line.data(using: .utf8),
              let any = try? JSONSerialization.jsonObject(with: data) else { return nil }
        return Loose(any: any)
    }

    static func isDirectory(_ url: URL) -> Bool {
        var isDir: ObjCBool = false
        return fm.fileExists(atPath: url.path, isDirectory: &isDir) && isDir.boolValue
    }

    static func exists(_ url: URL) -> Bool { fm.fileExists(atPath: url.path) }

    /// Non-hidden entries of a folder, sorted by name (natural order: v2 < v10).
    static func children(of dir: URL) -> [URL] {
        let items = (try? fm.contentsOfDirectory(at: dir, includingPropertiesForKeys: [.isDirectoryKey],
                                                  options: [.skipsHiddenFiles])) ?? []
        return items.sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }
    }

    static func files(in dir: URL, extensions: Set<String>) -> [URL] {
        children(of: dir).filter { !isDirectory($0) && extensions.contains($0.pathExtension.lowercased()) }
    }

    static func subdirectories(of dir: URL) -> [URL] {
        children(of: dir).filter { isDirectory($0) }
    }

    static func modified(_ url: URL) -> Date? {
        (try? fm.attributesOfItem(atPath: url.path))?[.modificationDate] as? Date
    }

    static func timestamp(_ date: Date = Date()) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyyMMdd-HHmmss"
        return f.string(from: date)
    }

    static func iso(_ date: Date = Date()) -> String {
        ISO8601DateFormatter().string(from: date)
    }

    /// `base/name.ext`, or `base/name-2.ext` etc. if taken.
    static func uniqueURL(in dir: URL, name: String) -> URL {
        var candidate = dir.appendingPathComponent(name)
        let stem = (name as NSString).deletingPathExtension
        let ext = (name as NSString).pathExtension
        var i = 2
        while exists(candidate) {
            candidate = dir.appendingPathComponent(ext.isEmpty ? "\(stem)-\(i)" : "\(stem)-\(i).\(ext)")
            i += 1
        }
        return candidate
    }

    /// Path of `url` relative to `root`, or the full path if outside.
    static func relativePath(_ url: URL, to root: URL) -> String {
        let r = root.standardizedFileURL.path
        let p = url.standardizedFileURL.path
        if p.hasPrefix(r + "/") { return String(p.dropFirst(r.count + 1)) }
        return p
    }
}
