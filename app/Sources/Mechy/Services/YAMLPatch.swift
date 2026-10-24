import Foundation

/// A YAML scalar the app writes back into a contract file.
enum YAMLScalar: Equatable {
    case string(String)
    case number(Double)
    case null

    /// YAML text for this scalar. Strings are always double-quoted with JSON-style
    /// escapes, which YAML 1.1 and 1.2 (PyYAML, Yams) read identically.
    var yaml: String {
        switch self {
        case .null: return "null"
        case .number(let d):
            if d.rounded() == d && abs(d) < 1e15 { return String(Int(d)) }
            return String(d)
        case .string(let s): return YAMLScalar.quote(s)
        }
    }

    static func quote(_ s: String) -> String {
        var out = "\""
        for scalar in s.unicodeScalars {
            switch scalar {
            case "\"": out += "\\\""
            case "\\": out += "\\\\"
            case "\n": out += "\\n"
            case "\r": out += "\\r"
            case "\t": out += "\\t"
            default:
                if scalar.value < 0x20 || scalar.value == 0x7F {
                    out += String(format: "\\u%04X", scalar.value)
                } else {
                    out.unicodeScalars.append(scalar)
                }
            }
        }
        return out + "\""
    }
}

/// Minimal, comment-preserving edits to top-level keys of a YAML file.
///
/// The app only ever writes `chosen`, `feedback` (options/*.yaml) and `answer`
/// (questions/*.yaml), all top-level scalars. Re-serialising the whole file would
/// drop the agents' comments and key order, so we replace just that key's line
/// (and any indented continuation lines of an old block value).
enum YAMLPatch {
    static func setTopLevel(_ key: String, to value: YAMLScalar, in text: String) -> String {
        var lines = text.components(separatedBy: "\n")
        let hadTrailingNewline = text.hasSuffix("\n")
        if hadTrailingNewline, lines.last == "" { lines.removeLast() }

        guard let i = lines.firstIndex(where: { isKeyLine($0, key) }) else {
            lines.append("\(key): \(value.yaml)")
            return lines.joined(separator: "\n") + "\n"
        }

        // Keep any trailing comment from the old line.
        let comment = trailingComment(String(lines[i].dropFirst(key.count + 1)))

        // Remove continuation lines of a previous block value.
        var j = i + 1
        while j < lines.count {
            let line = lines[j]
            if line.hasPrefix(" ") || line.hasPrefix("\t") || line == "-" || line.hasPrefix("- ") {
                j += 1
                continue
            }
            if line.trimmingCharacters(in: .whitespaces).isEmpty {
                // Blank line: part of the block only if more indented lines follow.
                var k = j + 1
                while k < lines.count, lines[k].trimmingCharacters(in: .whitespaces).isEmpty { k += 1 }
                if k < lines.count, lines[k].hasPrefix(" ") || lines[k].hasPrefix("\t") {
                    j = k
                    continue
                }
            }
            break
        }
        if j > i + 1 { lines.removeSubrange((i + 1)..<j) }

        lines[i] = "\(key): \(value.yaml)\(comment)"
        return lines.joined(separator: "\n") + "\n"
    }

    /// The `# ...` comment after a scalar value (skipping over a quoted string), as "  # ...".
    static func trailingComment(_ value: String) -> String {
        let chars = Array(value)
        var i = 0
        while i < chars.count, chars[i] == " " || chars[i] == "\t" { i += 1 }
        if i < chars.count, chars[i] == "#" { return "  " + String(chars[i...]) }
        if i < chars.count, chars[i] == "\"" || chars[i] == "'" {
            let q = chars[i]
            i += 1
            while i < chars.count {
                if q == "\"" && chars[i] == "\\" { i += 2; continue }
                if chars[i] == q {
                    if q == "'" && i + 1 < chars.count && chars[i + 1] == "'" { i += 2; continue }
                    i += 1
                    break
                }
                i += 1
            }
        }
        while i < chars.count {
            if chars[i] == "#" && i > 0 && (chars[i - 1] == " " || chars[i - 1] == "\t") {
                return "  " + String(chars[i...])
            }
            i += 1
        }
        return ""
    }

    static func isKeyLine(_ line: String, _ key: String) -> Bool {
        guard line.hasPrefix(key) else { return false }
        let rest = line.dropFirst(key.count)
        return rest.hasPrefix(":") && (rest.count == 1 || rest.dropFirst().first == " " || rest.dropFirst().first == "\t")
    }

    /// Read, patch and atomically write a file.
    static func apply(_ edits: [(String, YAMLScalar)], to url: URL) throws {
        var text = (try? String(contentsOf: url, encoding: .utf8)) ?? ""
        for (key, value) in edits {
            text = setTopLevel(key, to: value, in: text)
        }
        try text.write(to: url, atomically: true, encoding: .utf8)
    }
}
