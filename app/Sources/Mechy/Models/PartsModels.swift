import Foundation

// Variant parts lists (contracts §10): design/<v>/print_list.csv (printed parts) and
// design/<v>/bom.csv (purchased parts). Read leniently: column names are looked up
// by a few aliases, and a missing or malformed number just leaves that cell empty.

/// Minimal RFC 4180 CSV reader: quoted fields, doubled quotes, commas and newlines
/// inside quotes, CRLF or LF line ends. The first row is the header.
struct CSVTable {
    let header: [String]
    let rows: [[String: String]]

    init(header: [String], rows: [[String: String]]) {
        self.header = header
        self.rows = rows
    }

    init?(url: URL) {
        guard let text = try? String(contentsOf: url, encoding: .utf8) else { return nil }
        self.init(text: text)
    }

    init(text: String) {
        let records = CSVTable.parse(text)
        guard let first = records.first else {
            header = []
            rows = []
            return
        }
        let keys = first.map { $0.trimmingCharacters(in: .whitespaces).lowercased() }
        header = keys
        rows = records.dropFirst().compactMap { fields in
            if fields.allSatisfy({ $0.trimmingCharacters(in: .whitespaces).isEmpty }) { return nil }
            var row: [String: String] = [:]
            for (i, key) in keys.enumerated() where i < fields.count && !key.isEmpty {
                row[key] = fields[i].trimmingCharacters(in: .whitespaces)
            }
            return row
        }
    }

    static func parse(_ text: String) -> [[String]] {
        var records: [[String]] = []
        var record: [String] = []
        var field = ""
        var inQuotes = false
        var chars = Array(text)
        if chars.first == "\u{FEFF}" { chars.removeFirst() }   // UTF-8 BOM
        var i = 0
        while i < chars.count {
            let c = chars[i]
            if inQuotes {
                if c == "\"" {
                    if i + 1 < chars.count, chars[i + 1] == "\"" {
                        field.append("\"")
                        i += 1
                    } else {
                        inQuotes = false
                    }
                } else {
                    field.append(c)
                }
            } else {
                switch c {
                case "\"":
                    inQuotes = true
                case ",":
                    record.append(field)
                    field = ""
                case "\n", "\r", "\r\n":
                    // Swift treats CRLF as one Character ("\r\n").
                    record.append(field)
                    records.append(record)
                    record = []
                    field = ""
                    if c == "\r", i + 1 < chars.count, chars[i + 1] == "\n" { i += 1 }
                default:
                    field.append(c)
                }
            }
            i += 1
        }
        if !field.isEmpty || !record.isEmpty {
            record.append(field)
            records.append(record)
        }
        return records
    }
}

private extension Dictionary where Key == String, Value == String {
    /// First non-empty value among `keys`.
    func pick(_ keys: [String]) -> String? {
        for k in keys {
            if let v = self[k], !v.isEmpty { return v }
        }
        return nil
    }

    func number(_ keys: [String]) -> Double? {
        guard let s = pick(keys) else { return nil }
        let cleaned = s.replacingOccurrences(of: "$", with: "")
            .replacingOccurrences(of: "%", with: "")
            .replacingOccurrences(of: ",", with: "")
            .trimmingCharacters(in: .whitespaces)
        guard let d = Double(cleaned), d.isFinite else { return nil }
        return d
    }

    /// Whole count (never traps on odd input such as "nan" or 1e30).
    func whole(_ keys: [String]) -> Int? {
        guard let d = number(keys), abs(d) < 1e9 else { return nil }
        return Int(d.rounded())
    }
}

/// One printed part (print_list.csv row).
struct PrintPart: Identifiable {
    let id: Int
    let part: String
    let qty: Int
    let material: String?
    let orientation: String?
    let infill: String?
    let gramsEach: Double?
    let gramsTotal: Double?
    /// Project-relative to the variant folder, e.g. "stl/base_plate.stl".
    let stl: String?

    init(index: Int, _ r: [String: String]) {
        id = index
        part = r.pick(["part", "name", "ref", "item"]) ?? "part \(index + 1)"
        qty = r.whole(["qty", "quantity", "count"]) ?? 1
        material = r.pick(["material"])
        orientation = r.pick(["orientation", "print_orientation"])
        infill = r.pick(["infill"])
        let each = r.number(["est_grams", "grams", "mass_g", "g"])
        let count = r.whole(["qty", "quantity", "count"]) ?? 1
        gramsEach = each
        gramsTotal = r.number(["est_grams_total", "grams_total", "total_grams"])
            ?? each.map { $0 * Double(max(1, count)) }
        stl = r.pick(["stl", "file", "path"])
    }
}

/// One purchased line (bom.csv row).
struct BOMLine: Identifiable {
    let id: Int
    let item: String
    let qty: Int
    let spec: String?
    let usedFor: String?
    let source: String?
    let unitUSD: Double?
    let totalUSD: Double?

    init(index: Int, _ r: [String: String]) {
        id = index
        item = r.pick(["item", "part", "name", "description"]) ?? "item \(index + 1)"
        qty = r.whole(["qty", "quantity", "count"]) ?? 1
        spec = r.pick(["spec", "specification", "notes"])
        usedFor = r.pick(["used_for", "use", "for"])
        source = r.pick(["source", "vendor", "supplier"])
        let unit = r.number(["est_unit_usd", "unit_usd", "unit_cost_usd", "usd", "price_usd", "cost_usd"])
        let count = r.whole(["qty", "quantity", "count"]) ?? 1
        unitUSD = unit
        totalUSD = r.number(["est_total_usd", "total_usd", "line_usd"]) ?? unit.map { $0 * Double(count) }
    }
}

/// Both lists for one variant plus totals.
struct PartsList {
    var printed: [PrintPart] = []
    var purchased: [BOMLine] = []
    var hasPrintList = false
    var hasBOM = false

    /// Filament price used for the printed-material estimate (PETG/PLA, roughly 20 USD per kg).
    static let filamentUSDPerKg = 20.0

    static func load(_ variant: DesignVariant) -> PartsList {
        var list = PartsList()
        if let t = CSVTable(url: variant.printListCSV) {
            list.hasPrintList = true
            list.printed = t.rows.enumerated().map { PrintPart(index: $0.offset, $0.element) }
        }
        if let t = CSVTable(url: variant.bomCSV) {
            list.hasBOM = true
            list.purchased = t.rows.enumerated().map { BOMLine(index: $0.offset, $0.element) }
        }
        return list
    }

    var isEmpty: Bool { !hasPrintList && !hasBOM }

    var printedPieces: Int { printed.reduce(0) { $0 + $1.qty } }
    var printedGrams: Double { printed.reduce(0) { $0 + ($1.gramsTotal ?? 0) } }
    var purchasedUSD: Double { purchased.reduce(0) { $0 + ($1.totalUSD ?? 0) } }
    var filamentUSD: Double { printedGrams / 1000 * Self.filamentUSDPerKg }
    var totalUSD: Double { purchasedUSD + filamentUSD }
    /// Lines without a price (their cost is not in the totals).
    var unpricedLines: Int { purchased.filter { $0.totalUSD == nil }.count }
}
