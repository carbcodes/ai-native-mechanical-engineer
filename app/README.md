# Mechy — macOS app (Phase 0 shell)

SwiftUI app for Mechy. It is a drawing sheet of panels, not a chat window. The app never does engineering itself. It starts `mechy` engine commands and shows the files they write (see `docs/architecture/contracts.md`). Visual style: `docs/architecture/ui-style.md`. All tokens are in `Sources/Mechy/Theme/Theme.swift`.

## Build and run (macOS 14+, Xcode 15+/Swift 5.9+)

```sh
cd app
swift run Mechy          # builds, fetches Yams, launches the app
swift test               # YAML write-back + model tests
```

You can also open `app/Package.swift` in Xcode and run the `Mechy` scheme.

The app needs the engine CLI `mechy` (see `engine/`). If it is not on PATH, set its path in **Mechy ▸ Settings**. The CAD viewer loads three.js 0.169.0 from cdn.jsdelivr.net, so it needs internet the first time.

## What's in it

| Area | Files |
|---|---|
| App, windows, menus | `App/MechyApp.swift`, `App/AppState.swift` (open/create project, recent projects) |
| Look | `Theme/Theme.swift` (colours, lines, type, spacing, sheet button style) |
| Contract mirrors | `Models/ProjectModels.swift`, `Models/Loose.swift` (lenient YAML/JSON reading through Yams), `Models/PanelModels.swift` |
| Engine bridge | `Services/EngineClient.swift` (Process + `--json` line events), `Services/EngineLocator.swift` (finds mechy/claude/codex) |
| Project store | `Services/ProjectSession.swift` (loads files, writes answers/choices, inspiration, inbox, canvas layout) |
| File watching | `Services/DirectoryWatcher.swift` (FSEvents + `.mechy/events.jsonl` tail) |
| Safe YAML writes | `Services/YAMLPatch.swift` (changes one top-level key and keeps comments) |
| Canvas | `Views/Canvas/CanvasView.swift` (dot + node grid, pan/zoom; zoom controls sit in the agent bar), `Views/Canvas/PanelFrame.swift` (frame, title block, move/resize/close) |
| Panels | `Views/Panels/*.swift`: Inspiration, CAD (with sim replay), Options, Questions, Sim, Tasks, Docs, Parts |
| Bars | `Views/AgentBar.swift`, `Views/FileTreeSidebar.swift`, `Views/SettingsView.swift`, `Views/WelcomeView.swift` |
| 3D viewer | `Resources/viewer/index.html` (three.js, line-drawing + shaded modes, sim replay theater) |
| Parts lists | `Models/PartsModels.swift` (CSV reader, print list / BOM rows and totals) |
| Inspiration digests, docs groups, note Markdown | `Models/IntakeModels.swift` (`source.json` reader, `MarkdownBlock`) |
| Make it | `Services/MakeItPipeline.swift` (CAD → sim → firmware → docs, stops at the first failure) |

## What the app writes

- `options/<id>.yaml`: `chosen`, `feedback`
- `design/chosen`: the option id, when an option is named after a `design/<id>/` folder
- `questions/<id>.yaml`: `answer`
- `inspiration/*`: dropped files; `inspiration/links.yaml` (`links: [{url, title?, added}]`)
- `inbox/<yyyyMMdd-HHmmss>.md`: requests from the agent bar, then it runs `mechy plan` *(proposed contract addition)*
- `.mechy/viewer/index.html`: a copy of the viewer page, so one file-URL read grant covers the page and the models *(proposed)*

Canvas layouts and settings (including the appearance: System / Paper / Graphite) are kept in UserDefaults, not in the project.

## Engine commands it runs

`mechy init <dir> --example tennis-catcher --json`, `mechy cad build <v>`, `mechy sim catch <v> --throws 200`, `mechy run --jobs 2`, `mechy plan`, `mechy agent run <task>`, `mechy intake add <src>`, `mechy intake all`, `mechy doc build <v> [--print]`, `mechy control gen <v> [--board uno_cnc|mega_ramps]`, `mechy doctor`. Every command except `init` and `doctor` gets `--project <root> --json`, placed *after* the subcommand arguments. Child environment: `MECHY_PROVIDER=auto|claude|codex`, `MECHY_CLAUDE_BIN`, `MECHY_CODEX_BIN` (proposed), and a PATH that includes the login-shell PATH.

## Not verified (written on Linux; nothing here has been compiled)

- Last compiled cleanly at commit be7a132 (macOS 26 / Swift 6.4). Everything after it is uncompiled.
- New APIs to check first (round 4): `QLPreviewPanel` data source set directly without a responder-chain controller (`Components.swift` `QuickLookPanel`), the `QLPreviewPanelDataSource` method signatures, `PDFDocument.printOperation(for:scalingMode:autoRotate:)`, `Notification.Name.PDFViewPageChanged`, `PDFPage.thumbnail(of:for:)` off the main thread, `AttributedString(markdown:options:baseURL:)`, `Menu` with `.menuStyle(.button)` + `.menuIndicator(.visible)` in the agent bar.
- Nothing before be7a132 had been compiled or run. Expect a few small compile fixes on the first `swift build`.
- APIs to check first: the FSEvents callback and flag constant imports (`DirectoryWatcher.swift`), `QLPreviewView(frame:style:)` and `previewItem = url as NSURL` (`DocsPanel.swift`), `QLThumbnailGenerator` `rep.nsImage` (`Components.swift`), `MagnifyGesture` + `DragGesture.simultaneously` on the sheet, `.onChange(of:) { old, new in }` (macOS 14 form), and `WKScriptMessageHandler` actor isolation under the Swift 6 SDK (the package uses Swift 5 language mode).
- Runtime: `fetch()` of `file://` GLB inside WKWebView, which has a base64 fallback; ES-module import maps from a `file://` page; whether `--project/--json` after the subcommand matches the engine's CLI parser; draining stdout if `mechy` leaves grandchild processes holding the pipe open.
- Sim replay: the viewer assumes each joint node's axis is fixed in its parent body, and that a node's rest rotation is the rotation about that axis (this is how `engine/mechy/cad/glb.py` writes the ready pose). Node `extras.q` or a replay `glb_q` can override the rest angle. Ball, path and catch point are drawn in the parent frame of `base` (or of `turntable`). If that frame is the glTF scene itself, a z-up wrapper is assumed instead.
- Stopping agents kills the process tree through `ps` and signals, because `Process` cannot create a process group. Task `status.json` files of killed tasks may stay `running` until the engine cleans them up.
- Inter is used if installed, otherwise the system font is used (not bundled).
- Zoom changes panel positions and sizes. It does not scale panel contents. There is no scroll-wheel panning yet; pan by dragging empty paper.
