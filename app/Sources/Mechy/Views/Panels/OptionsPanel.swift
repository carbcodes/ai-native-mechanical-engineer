import SwiftUI

/// Option sets (options/*.yaml): pick one card -> writes `chosen`; tweak -> writes `feedback`.
/// Unchosen options are drawn dashed, the chosen one solid with the accent.
struct OptionsPanel: View {
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        if session.optionSets.isEmpty {
            EmptySheet(symbol: "square.grid.2x2", label: "No options to pick yet")
        } else {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Space.l) {
                    // Open sets first.
                    ForEach(session.openOptionSets + session.optionSets.filter { !$0.isOpen }) { set in
                        OptionSetView(set: set)
                    }
                }
                .padding(Theme.Space.m)
            }
        }
    }
}

struct OptionSetView: View {
    let set: OptionSetDoc
    @EnvironmentObject var session: ProjectSession
    @State private var tweak = ""

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.s) {
            HStack(spacing: Theme.Space.s) {
                Text(set.prompt).font(Theme.Typo.title).foregroundStyle(Theme.ink)
                Spacer()
                Text(set.isOpen ? "Pick one" : "Chosen").monoLabel(set.isOpen ? Theme.accent : Theme.muted)
            }
            if set.options.isEmpty {
                Text("No options listed yet — \(set.fileURL.lastPathComponent)")
                    .monoLabel(size: 9)
                    .frame(maxWidth: .infinity, minHeight: 60)
                    .overlay(Rectangle().stroke(Theme.muted, style: Theme.Stroke.dashed))
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(alignment: .top, spacing: Theme.Space.m) {
                        ForEach(set.options) { option in
                            OptionCard(option: option, chosen: set.chosen == option.id, anyChosen: !set.isOpen)
                                .onTapGesture { session.choose(option, in: set) }
                        }
                    }
                    .padding(1)
                }
            }
            HStack(spacing: Theme.Space.s) {
                Image(systemName: "pencil.line").font(.system(size: 10)).foregroundStyle(Theme.muted)
                TextField("TWEAK — e.g. longer forearm", text: $tweak)
                    .textFieldStyle(.plain)
                    .font(Theme.Typo.monoBody)
                    .onSubmit(send)
                if !tweak.isEmpty {
                    Button("Send", action: send).buttonStyle(SheetButtonStyle(filled: true, compact: true))
                }
            }
            .padding(.horizontal, Theme.Space.s)
            .padding(.vertical, Theme.Space.xs + 1)
            .overlay(Rectangle().stroke(Theme.hairline, lineWidth: 1))
            if let fb = set.feedback, !fb.isEmpty {
                HStack(alignment: .top, spacing: Theme.Space.xs) {
                    Text("Sent").monoLabel()
                    Text(fb).font(Theme.Typo.small).foregroundStyle(Theme.muted).lineLimit(2)
                }
            }
        }
    }

    private func send() {
        session.sendFeedback(tweak, in: set)
        tweak = ""
    }
}

struct OptionCard: View {
    let option: OptionChoice
    let chosen: Bool
    let anyChosen: Bool
    @EnvironmentObject var session: ProjectSession

    static let width: CGFloat = 172

    /// The thumbnail named in the YAML exists on disk.
    private var hasImage: Bool {
        guard let img = option.image else { return false }
        return FileIO.exists(session.url(img))
    }

    /// Nothing to show yet: no thumbnail and no stats (the engine has not built it).
    private var isPlaceholder: Bool { !hasImage && option.stats.isEmpty }

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.s) {
            ZStack(alignment: .topLeading) {
                if hasImage, let img = option.image {
                    FileThumb(url: session.url(img), contentMode: .fit)
                } else {
                    notBuiltArt
                }
                Text(Theme.tag(option.id))
                    .font(Theme.Typo.mono(11, .medium))
                    .foregroundStyle(chosen ? Theme.accent : Theme.ink)
                    .boxed(chosen ? Theme.accent : Theme.ink, padding: 2)
                    .background(Theme.surface)
                    .padding(Theme.Space.xs)
            }
            .frame(width: Self.width, height: 112)
            .clipped()
            Text(option.title)
                .font(Theme.Typo.small)
                .foregroundStyle(Theme.ink)
                .lineLimit(2)
                .frame(width: Self.width, alignment: .leading)
            if chosen, option.id == session.chosenVariant {
                Text("design/chosen = \(option.id)").monoLabel(Theme.accent, size: 8)
                    .frame(width: Self.width, alignment: .leading)
                    .help("This option picked the variant the toolbar, Make it and the docs act on")
            }
            ForEach(option.notes, id: \.self) { note in
                Text(note)
                    .font(Theme.Typo.mono(10))
                    .foregroundStyle(Theme.muted)
                    .lineLimit(5)
                    .frame(width: Self.width, alignment: .leading)
                    .help(note)
            }
            if option.stats.isEmpty {
                Text(isPlaceholder ? "Not built yet" : "No stats yet")
                    .monoLabel(size: 9)
                    .frame(width: Self.width, alignment: .leading)
            } else {
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(option.stats) { stat in
                        HStack {
                            Text(OptionStat.label(stat.key)).monoLabel(size: 9)
                            Spacer(minLength: 4)
                            Text(OptionStat.value(stat.key, stat.value))
                                .font(Theme.Typo.monoBody)
                                .foregroundStyle(Theme.ink)
                        }
                    }
                }
                .frame(width: Self.width)
            }
            if option.variant != nil {
                Button(isPlaceholder ? "Build" : "View 3D") {
                    guard let v = option.variant else { return }
                    if isPlaceholder { session.buildCAD(v) } else { session.showVariant(v) }
                }
                .buttonStyle(SheetButtonStyle(compact: true))
                .help(isPlaceholder ? "mechy cad build \(option.variant ?? "")" : "Show in the CAD panel")
            }
        }
        .padding(Theme.Space.s)
        .background(chosen ? Theme.accentWash : Color.clear)
        .overlay(
            Rectangle().stroke(chosen ? Theme.accent : Theme.ink,
                               style: chosen ? StrokeStyle(lineWidth: 1.5)
                                   : (anyChosen || isPlaceholder ? Theme.Stroke.dashed : StrokeStyle(lineWidth: 1)))
        )
        .opacity(anyChosen && !chosen ? 0.6 : 1)
        .contentShape(Rectangle())
        .help(chosen ? "Chosen" : "Click to choose")
    }

    /// Dashed placeholder drawn where the thumbnail will go.
    private var notBuiltArt: some View {
        ZStack {
            Theme.wash
            Rectangle()
                .stroke(Theme.muted, style: Theme.Stroke.dashedHair)
                .padding(Theme.Space.xs)
            VStack(spacing: Theme.Space.xs) {
                Image(systemName: "cube.transparent")
                    .font(.system(size: 20, weight: .ultraLight))
                    .foregroundStyle(Theme.muted)
                Text("Not built yet").monoLabel(size: 9)
            }
        }
    }
}

/// Formatting for option stats keys like catch_rate, reach_m, cost_usd.
enum OptionStat {
    static func label(_ key: String) -> String {
        var k = key
        if let suffix = ["_usd", "_mm", "_nm", "_kg", "_m", "_s"].first(where: { k.hasSuffix($0) }) {
            k = String(k.dropLast(suffix.count))
        }
        return k.replacingOccurrences(of: "_", with: " ")
    }

    static func value(_ key: String, _ raw: Any) -> String {
        guard let d = Loose.number(raw) else { return Loose.text(raw) ?? "—" }
        if key.hasSuffix("_rate") || key.hasSuffix("_frac") { return Theme.percent(d) }
        if key.hasSuffix("_usd") { return "$" + Loose.formatNumber((d * 100).rounded() / 100) }
        let units: [(String, String)] = [("_mm", "mm"), ("_m", "m"), ("_kg", "kg"), ("_s", "s"), ("_nm", "N·m")]
        for (suffix, unit) in units where key.hasSuffix(suffix) {
            return String(format: "%.3g", d) + " " + unit
        }
        return Loose.formatNumber((d * 1000).rounded() / 1000)
    }
}
