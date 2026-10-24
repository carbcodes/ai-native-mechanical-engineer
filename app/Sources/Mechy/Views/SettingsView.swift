import SwiftUI
import AppKit

/// Settings: appearance, agent provider, and paths to the mechy / claude / codex executables.
struct SettingsView: View {
    @EnvironmentObject var app: AppState
    @AppStorage(SettingsKey.provider) private var provider = AgentProvider.auto.rawValue
    @AppStorage(SettingsKey.mechyPath) private var mechyPath = ""
    @AppStorage(SettingsKey.claudePath) private var claudePath = ""
    @AppStorage(SettingsKey.codexPath) private var codexPath = ""
    @State private var detected: [String: String] = [:]
    @State private var doctorLog: String = ""
    @State private var doctorRunning = false

    var body: some View {
        Form {
            Section {
                Picker("Sheet", selection: $app.appearance) {
                    ForEach(AppearanceMode.allCases) { mode in Text(mode.title).tag(mode) }
                }
                .pickerStyle(.segmented)
                Text("Paper is the light drawing sheet, Graphite the dark one. Also in View ▸ Appearance.")
                    .font(Theme.Typo.small).foregroundStyle(Theme.muted)
            } header: { Text("Appearance").monoLabel() }

            Section {
                ForEach(["claude", "codex"], id: \.self) { p in
                    HStack {
                        AccountChip(accounts: app.accounts, provider: p)
                        Spacer()
                        if let s = app.accounts.accounts[p], !s.installed {
                            Text("Not installed — \(s.installHint(p))")
                                .font(Theme.Typo.mono(10)).foregroundStyle(Theme.muted)
                        } else {
                            Button(app.accounts.accounts[p]?.loggedIn == true ? "Reconnect" : "Connect") {
                                app.accounts.connect(p)
                            }
                            .buttonStyle(SheetButtonStyle())
                            .disabled(app.accounts.accounts[p]?.installed != true)
                        }
                    }
                }
                HStack {
                    Button("Refresh") { app.accounts.refresh() }.buttonStyle(SheetButtonStyle())
                    if app.accounts.loading { ProgressView().controlSize(.mini) }
                }
            } header: { Text("Accounts").monoLabel() }

            Section {
                Picker("Provider", selection: $provider) {
                    ForEach(AgentProvider.allCases) { p in Text(p.title).tag(p.rawValue) }
                }
                .pickerStyle(.segmented)
                Text("Which agent CLI the engine drives. Passed to mechy as MECHY_PROVIDER.")
                    .font(Theme.Typo.small).foregroundStyle(Theme.muted)
            } header: { Text("Agents").monoLabel() }

            Section {
                pathRow("mechy", text: $mechyPath, name: "mechy")
                pathRow("claude", text: $claudePath, name: "claude")
                pathRow("codex", text: $codexPath, name: "codex")
            } header: { Text("Executables").monoLabel() } footer: {
                Text("Leave empty to search PATH, your login shell's PATH, ~/.local/bin, /opt/homebrew/bin and /usr/local/bin.")
                    .font(Theme.Typo.small).foregroundStyle(Theme.muted)
            }

            Section {
                HStack {
                    Button(doctorRunning ? "Running…" : "Run mechy doctor") { runDoctor() }
                        .disabled(doctorRunning)
                    Spacer()
                }
                if !doctorLog.isEmpty {
                    ScrollView {
                        Text(doctorLog)
                            .font(Theme.Typo.monoBody)
                            .textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(height: 140)
                }
            } header: { Text("Check").monoLabel() }
        }
        .formStyle(.grouped)
        .frame(width: 560)
        .padding(.vertical, Theme.Space.s)
        .onAppear { detect(); app.accounts.refresh() }
        .onChange(of: mechyPath) { _, _ in detect() }
        .onChange(of: claudePath) { _, _ in detect() }
        .onChange(of: codexPath) { _, _ in detect() }
    }

    private func pathRow(_ label: String, text: Binding<String>, name: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(label).font(Theme.Typo.mono(12, .medium)).frame(width: 60, alignment: .leading)
                TextField("auto", text: text).font(Theme.Typo.monoBody)
                Button("Choose…") { choose(into: text) }
            }
            Text(detected[name].map { "→ " + $0 } ?? (text.wrappedValue.isEmpty ? "not found" : "not executable"))
                .font(Theme.Typo.mono(10))
                .foregroundStyle(detected[name] == nil ? Theme.danger : Theme.muted)
                .padding(.leading, 68)
        }
    }

    private func choose(into binding: Binding<String>) {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.showsHiddenFiles = true
        if panel.runModal() == .OK, let url = panel.url { binding.wrappedValue = url.path }
    }

    private func detect() {
        let m = mechyPath, cl = claudePath, cx = codexPath
        DispatchQueue.global(qos: .userInitiated).async {
            var found: [String: String] = [:]
            found["mechy"] = EngineLocator.find("mechy", override: m.isEmpty ? nil : (m as NSString).expandingTildeInPath)?.path
            found["claude"] = EngineLocator.find("claude", override: cl.isEmpty ? nil : (cl as NSString).expandingTildeInPath)?.path
            found["codex"] = EngineLocator.find("codex", override: cx.isEmpty ? nil : (cx as NSString).expandingTildeInPath)?.path
            DispatchQueue.main.async { detected = found }
        }
    }

    private func runDoctor() {
        doctorRunning = true
        doctorLog = ""
        app.engine.doctor { run in
            doctorRunning = false
            var lines = run.log
            if case .failed(let why) = run.state, !lines.contains(why) { lines.append(why) }
            doctorLog = lines.joined(separator: "\n")
        }
    }
}
