import SwiftUI
import WebKit

/// CAD viewer: three.js page in a WKWebView showing design/<variant>/arm.glb.
struct CADPanel: View {
    let panel: PanelState
    @EnvironmentObject var session: ProjectSession
    @State private var shaded = false
    /// Motion sim in the viewer: the arm runs a demo routine and the joints get sliders.
    @State private var moving = false
    /// Mirrors AppState.appearance (same UserDefaults key) so the viewer page follows it.
    @AppStorage(SettingsKey.appearance) private var appearanceRaw = AppearanceMode.system.rawValue

    private var variantName: String? {
        if let p = panel.param, session.variants.contains(where: { $0.name == p }) { return p }
        return session.activeVariant
    }

    private var variant: DesignVariant? {
        session.variants.first { $0.name == variantName }
    }

    /// Sim report whose replay.json plays in this panel (contracts §11), if any.
    private var replayReport: SimReport? {
        guard let id = panel.replay else { return nil }
        return session.simReports.first { $0.id == id && $0.replay != nil }
    }

    var body: some View {
        VStack(spacing: 0) {
            PanelStrip {
                variantPicker
                Spacer(minLength: 0)
                if let r = replayReport { replayTag(r) }
                Button {
                    moving.toggle()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: moving ? "stop.fill" : "play.fill").font(.system(size: 8))
                        Text(moving ? "Stop sim" : "Simulate")
                    }
                }
                .buttonStyle(SheetButtonStyle(filled: moving, compact: true))
                .disabled(variant?.glb == nil)
                .help("Watch the arm move through a demo routine; drag the joint sliders to pose it")
                Button(shaded ? "Line" : "Shade") { shaded.toggle() }
                    .buttonStyle(SheetButtonStyle(compact: true))
                    .help("Toggle technical line drawing / shaded")
                Button("Build") { session.buildCAD(variantName) }
                    .buttonStyle(SheetButtonStyle(compact: true))
                    .disabled(variantName == nil)
            }
            ZStack {
                if let v = variant, let glb = v.glb {
                    CADWebView(projectRoot: session.root, modelURL: glb, stamp: v.glbModified, shaded: shaded, motion: moving,
                               appearance: AppearanceMode(rawValue: appearanceRaw) ?? .system,
                               replay: replayReport.flatMap { r in
                                   r.replay.map { CADWebView.Replay(url: $0, stamp: r.replayModified, title: r.id) }
                               })
                } else if variant != nil {
                    EmptySheet(symbol: "cube.transparent",
                               label: replayReport != nil ? "Replay needs the model: build CAD" : "No model yet",
                               actionTitle: "Build CAD") {
                        session.buildCAD(variantName)
                    }
                } else {
                    EmptySheet(symbol: "cube.transparent", label: "No design variants")
                }
            }
        }
        .onChange(of: variantName) { _, new in
            if let new { session.focusedVariant = new }
        }
    }

    private var variantPicker: some View {
        HStack(spacing: Theme.Space.xs) {
            ForEach(session.variants) { v in
                let selected = v.name == variantName
                let chosen = v.name == session.chosenVariant
                Button {
                    session.setParam(panel.id, v.name)
                    session.focusedVariant = v.name
                    // A replay belongs to the variant it was simulated on.
                    if let r = replayReport, r.variant != nil, r.variant != v.name {
                        session.setReplay(panel.id, nil)
                    }
                } label: {
                    Text(Theme.tag(v.name))
                        .font(Theme.Typo.mono(11, selected ? .semibold : .regular))
                        .foregroundStyle(selected ? Theme.accent : Theme.ink)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .overlay(
                            Rectangle().stroke(selected ? Theme.accent : (chosen ? Theme.ink : Theme.muted),
                                               style: chosen || selected ? StrokeStyle(lineWidth: 1) : Theme.Stroke.dashed)
                        )
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .help(chosen ? "\(v.name) (chosen)" : v.name)
            }
        }
    }
}

extension CADPanel {
    /// Live tag for the replay playing in the viewer, with a close box.
    fileprivate func replayTag(_ r: SimReport) -> some View {
        HStack(spacing: 0) {
            HStack(spacing: 4) {
                Rectangle().fill(Theme.accent).frame(width: 6, height: 6)
                Text("Replay \(r.id)").monoLabel(Theme.accent, size: 9).lineLimit(1)
            }
            .padding(.horizontal, 6)
            .padding(.vertical, 3)
            Rectangle().fill(Theme.accent).frame(width: Theme.Stroke.frame)
            Button { session.setReplay(panel.id, nil) } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 8, weight: .semibold))
                    .foregroundStyle(Theme.accent)
                    .frame(width: 18, height: 18)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .help("Close the replay")
        }
        .overlay(Rectangle().stroke(Theme.accent, lineWidth: Theme.Stroke.frame))
        .fixedSize()
        .help("Sim replay of \(r.id): space plays/pauses, [ and ] change throw")
    }
}

/// Copies the bundled viewer page into <project>/.mechy/viewer/ so one
/// `loadFileURL(_:allowingReadAccessTo: projectRoot)` grants access to both the page
/// and the model files.
enum ViewerPage {
    static var bundled: URL? {
        Bundle.module.url(forResource: "index", withExtension: "html", subdirectory: "viewer")
    }

    /// The bundled viewer folder (index.html + vendored three.js).
    static var bundledFolder: URL? { bundled?.deletingLastPathComponent() }

    /// Copy the whole bundled viewer folder (index.html plus vendor/) into
    /// .mechy/viewer/, rewriting only files whose bytes differ.
    static func install(into projectRoot: URL) -> URL? {
        guard let src = bundledFolder else { return nil }
        let dir = projectRoot.appendingPathComponent(".mechy/viewer", isDirectory: true)
        let dest = dir.appendingPathComponent("index.html")
        do {
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            let fm = FileManager.default
            guard let files = fm.enumerator(at: src, includingPropertiesForKeys: nil) else { return nil }
            for case let f as URL in files {
                guard !f.hasDirectoryPath else { continue }
                let rel = f.path.dropFirst(src.path.count + 1)
                let to = dir.appendingPathComponent(String(rel))
                let data = try Data(contentsOf: f)
                if (try? Data(contentsOf: to)) != data {
                    try fm.createDirectory(at: to.deletingLastPathComponent(), withIntermediateDirectories: true)
                    try data.write(to: to, options: .atomic)
                }
            }
            return dest
        } catch {
            return nil
        }
    }
}

struct CADWebView: NSViewRepresentable {
    /// A sim/<task>/replay.json to play over the model (contracts §11).
    struct Replay: Equatable {
        let url: URL
        let stamp: Date?
        let title: String
    }

    let projectRoot: URL
    let modelURL: URL
    let stamp: Date?
    let shaded: Bool
    var motion = false
    var appearance: AppearanceMode = .system
    var replay: Replay? = nil

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.userContentController.add(context.coordinator, name: "mechy")
        // file:// pages cannot load ES modules (the vendored three.js) without this.
        config.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")
        // Theme before first paint: the page reads window.__mechyTheme at start-up.
        let themeScript = WKUserScript(source: "window.__mechyTheme = \(Coordinator.jsString(appearance.webTheme));",
                                       injectionTime: .atDocumentStart, forMainFrameOnly: true)
        config.userContentController.addUserScript(themeScript)
        let web = WKWebView(frame: .zero, configuration: config)
        web.allowsMagnification = false
        web.appearance = appearance.nsAppearance   // prefers-color-scheme inside the page
        context.coordinator.web = web
        context.coordinator.desired = Coordinator.Desired(url: modelURL, stamp: stamp, shaded: shaded, motion: motion,
                                                          theme: appearance.webTheme, replay: replay)
        if let page = ViewerPage.install(into: projectRoot) {
            web.loadFileURL(page, allowingReadAccessTo: projectRoot)
        } else if let page = ViewerPage.bundled {
            // Fallback: page from the app bundle; the model then arrives as base64.
            web.loadFileURL(page, allowingReadAccessTo: page.deletingLastPathComponent())
        }
        return web
    }

    func updateNSView(_ web: WKWebView, context: Context) {
        if web.appearance?.name != appearance.nsAppearance?.name { web.appearance = appearance.nsAppearance }
        context.coordinator.show(Coordinator.Desired(url: modelURL, stamp: stamp, shaded: shaded, motion: motion,
                                                     theme: appearance.webTheme, replay: replay))
    }

    static func dismantleNSView(_ web: WKWebView, coordinator: Coordinator) {
        web.configuration.userContentController.removeScriptMessageHandler(forName: "mechy")
    }

    final class Coordinator: NSObject, WKScriptMessageHandler {
        struct Desired: Equatable {
            let url: URL
            let stamp: Date?
            let shaded: Bool
            var motion = false
            let theme: String
            var replay: Replay? = nil
        }

        weak var web: WKWebView?
        var desired: Desired?
        private var shown: Desired?
        private var ready = false
        /// Replay already re-sent as base64 after the page could not read the file URL.
        private var replayFallbackSent: Replay?

        func show(_ d: Desired) {
            desired = d
            push()
        }

        private func push() {
            guard ready, let d = desired, let web else { return }
            if shown?.url != d.url || shown?.stamp != d.stamp {
                let stamp = Int(d.stamp?.timeIntervalSince1970 ?? 0)
                let js = "window.mechy && window.mechy.load(\(Self.jsString(d.url.absoluteString)), \(stamp))"
                web.evaluateJavaScript(js, completionHandler: nil)
            }
            if shown?.theme != d.theme {
                web.evaluateJavaScript("window.mechy && window.mechy.setTheme && window.mechy.setTheme(\(Self.jsString(d.theme)))",
                                       completionHandler: nil)
            }
            if shown?.shaded != d.shaded {
                web.evaluateJavaScript("window.mechy && window.mechy.setShaded(\(d.shaded ? "true" : "false"))",
                                       completionHandler: nil)
            }
            if shown?.motion != d.motion {
                web.evaluateJavaScript("window.mechy && window.mechy.setMotion && window.mechy.setMotion(\(d.motion ? "true" : "false"))",
                                       completionHandler: nil)
            }
            if shown == nil || shown?.replay != d.replay {
                if let r = d.replay {
                    replayFallbackSent = nil
                    let stamp = Int(r.stamp?.timeIntervalSince1970 ?? 0)
                    let js = "window.mechy && window.mechy.loadReplay && window.mechy.loadReplay("
                        + "\(Self.jsString(r.url.absoluteString)), \(stamp), \(Self.jsString(r.title)))"
                    web.evaluateJavaScript(js, completionHandler: nil)
                } else if shown?.replay != nil {
                    web.evaluateJavaScript("window.mechy && window.mechy.closeReplay && window.mechy.closeReplay()",
                                           completionHandler: nil)
                }
            }
            shown = d
        }

        /// Fallback when the page cannot read replay.json from its file URL: send it as base64.
        private func sendReplayBase64() {
            guard let r = desired?.replay, replayFallbackSent != r else { return }
            replayFallbackSent = r
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                guard let data = try? Data(contentsOf: r.url) else { return }
                let b64 = data.base64EncodedString()
                DispatchQueue.main.async {
                    guard let self, self.desired?.replay == r else { return }
                    self.web?.evaluateJavaScript(
                        "window.mechy && window.mechy.loadReplayBase64('\(b64)', \(Self.jsString(r.title)))",
                        completionHandler: nil)
                }
            }
        }

        /// Fallback when the page cannot fetch the file URL: send the bytes as base64.
        private func sendBase64() {
            guard let d = desired else { return }
            let url = d.url
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                guard let data = try? Data(contentsOf: url) else { return }
                let b64 = data.base64EncodedString()
                DispatchQueue.main.async {
                    self?.web?.evaluateJavaScript("window.mechy && window.mechy.loadBase64('\(b64)')",
                                                  completionHandler: nil)
                }
            }
        }

        func userContentController(_ userContentController: WKUserContentController,
                                   didReceive message: WKScriptMessage) {
            guard let body = message.body as? [String: Any], let type = body["type"] as? String else { return }
            switch type {
            case "ready":
                ready = true
                shown = nil
                push()
            case "loadFailed":
                sendBase64()
            case "replayFailed":
                // A parse error will not get better as base64; only retry unreadable URLs.
                if (body["parse"] as? Bool) != true { sendReplayBase64() }
            default:
                break
            }
        }

        static func jsString(_ s: String) -> String {
            YAMLScalar.quote(s)   // JSON-compatible double-quoted string
        }
    }
}
