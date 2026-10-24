import SwiftUI
import AppKit

/// A panel on the sheet: a 1 pt ink frame, a thin drag strip along the top edge, and a
/// drawing title block at the bottom-right (kind, parameter, scale/date, close).
/// Drag the top strip or the title block to move; drag the corner node to resize.
struct PanelFrame: View {
    let panel: PanelState
    let zoom: CGFloat
    let pan: CGPoint
    /// Observed so the "agent working" strip follows engine runs as they progress.
    @ObservedObject var engine: EngineClient

    @EnvironmentObject var session: ProjectSession
    @State private var move: CGSize = .zero
    @State private var grow: CGSize = .zero
    @State private var hoverClose = false

    var body: some View {
        let cw = max(Theme.Canvas.panelMinWidth, CGFloat(panel.w) + grow.width / zoom)
        let ch = max(Theme.Canvas.panelMinHeight, CGFloat(panel.h) + grow.height / zoom)
        let sw = cw * zoom, sh = ch * zoom
        let sx = CGFloat(panel.x) * zoom + pan.x + move.width
        let sy = CGFloat(panel.y) * zoom + pan.y + move.height

        let activity = session.activity(for: panel.kind)

        VStack(spacing: 0) {
            // Drag strip: invisible chrome with a hairline grip; while an agent works on this
            // panel it grows into an accent status line.
            Group {
                if let activity {
                    ActivityStrip(activity: activity)
                } else {
                    Rectangle()
                        .fill(Theme.surface)
                        .frame(height: Theme.Canvas.dragStripHeight)
                        .overlay(alignment: .center) {
                            Rectangle().fill(Theme.hairline).frame(width: 28, height: 2)
                        }
                }
            }
            .contentShape(Rectangle())
            .gesture(moveGesture)
            if let note = session.pinnedNote(for: panel.kind) {
                PinnedNote(note: note)
            }
            PanelContent(panel: panel)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            titleBlock
        }
        .frame(width: sw, height: sh)
        .background(Theme.surface)
        .overlay(Rectangle().stroke(activity != nil ? Theme.accent : Theme.frame,
                                    lineWidth: activity != nil ? 1.5 : Theme.Stroke.frame))
        .overlay(alignment: .bottomTrailing) { resizeNode }
        .position(x: sx + sw / 2, y: sy + sh / 2)
        .simultaneousGesture(TapGesture().onEnded { session.bringToFront(panel.id) })
    }

    // MARK: Title block (bottom-right, like a drawing)

    private var titleBlock: some View {
        VStack(spacing: 0) {
            Rectangle().fill(Theme.frame).frame(height: Theme.Stroke.frame)
            HStack(spacing: 0) {
                Spacer(minLength: 0)
                HStack(spacing: 0) {
                    cell { Image(systemName: panel.kind.symbol).font(.system(size: 9)).foregroundStyle(Theme.ink) }
                    cell { Text(panel.kind.title).monoLabel(Theme.ink) }
                    if let p = paramLabel { cell { Text(p).monoLabel() } }
                    cell { Text(Self.dateString).monoLabel() }
                    Button { session.closePanel(panel.id) } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 8, weight: .semibold))
                            .foregroundStyle(hoverClose ? Theme.danger : Theme.ink)
                            .frame(width: Theme.Canvas.titleBlockHeight, height: Theme.Canvas.titleBlockHeight)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .onHover { hoverClose = $0 }
                    .help("Close panel")
                    Spacer().frame(width: 12)   // room for the resize node
                }
                .overlay(alignment: .leading) {
                    Rectangle().fill(Theme.frame).frame(width: Theme.Stroke.frame)
                }
                .contentShape(Rectangle())
                .gesture(moveGesture)
            }
            .frame(height: Theme.Canvas.titleBlockHeight)
        }
    }

    private func cell<C: View>(@ViewBuilder _ c: () -> C) -> some View {
        c()
            .padding(.horizontal, 6)
            .frame(height: Theme.Canvas.titleBlockHeight)
            .overlay(alignment: .trailing) { Rectangle().fill(Theme.frame).frame(width: Theme.Stroke.hair) }
    }

    private var paramLabel: String? {
        switch panel.kind {
        case .cad:
            let v = (panel.param ?? session.activeVariant).map(Theme.tag)
            if let r = panel.replay { return [v, "▸ \(r)"].compactMap { $0 }.joined(separator: " ") }
            return v
        case .parts, .loads, .manufacturing: return (panel.param ?? session.activeVariant).map(Theme.tag)
        case .docs: return panel.param.map { ($0 as NSString).lastPathComponent }
        case .sim: return panel.param ?? session.simReports.first?.id
        default: return nil
        }
    }

    private static var dateString: String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy.MM.dd"
        return f.string(from: Date())
    }

    // MARK: Gestures

    private var moveGesture: some Gesture {
        DragGesture(minimumDistance: 1, coordinateSpace: .global)
            .onChanged { move = $0.translation }
            .onEnded { v in
                session.movePanel(panel.id, dx: Double(v.translation.width / zoom), dy: Double(v.translation.height / zoom))
                move = .zero
                session.bringToFront(panel.id)
            }
    }

    private var resizeNode: some View {
        Rectangle()
            .stroke(Theme.ink, lineWidth: Theme.Stroke.frame)
            .background(Rectangle().fill(Theme.surface))
            .frame(width: 8, height: 8)
            .padding(2)
            .contentShape(Rectangle().inset(by: -4))
            .gesture(
                DragGesture(minimumDistance: 1, coordinateSpace: .global)
                    .onChanged { grow = $0.translation }
                    .onEnded { v in
                        session.resizePanel(panel.id,
                                            w: panel.w + Double(v.translation.width / zoom),
                                            h: panel.h + Double(v.translation.height / zoom))
                        grow = .zero
                    }
            )
            .onHover { inside in
                if inside { NSCursor.crosshair.push() } else { NSCursor.pop() }
            }
            .help("Resize")
    }
}

/// Accent status line across the top of a panel an agent is working on.
private struct ActivityStrip: View {
    let activity: PanelActivity

    var body: some View {
        HStack(spacing: 6) {
            LivePulse()
            Text(activity.who).monoLabel(Theme.accent, size: 9)
            Text(activity.detail)
                .font(Theme.Typo.mono(9))
                .foregroundStyle(Theme.ink)
                .lineLimit(1)
                .truncationMode(.tail)
            Spacer(minLength: 0)
            if let f = activity.fraction {
                Text(Theme.percent(f)).font(Theme.Typo.mono(9, .medium)).foregroundStyle(Theme.accent)
            } else {
                ProgressView().controlSize(.mini).scaleEffect(0.7)
            }
        }
        .padding(.horizontal, 8)
        .frame(height: 20)
        .background(Theme.accentWash)
        .overlay(alignment: .bottom) { Rectangle().fill(Theme.accent).frame(height: Theme.Stroke.hair) }
        .help("\(activity.who): \(activity.detail)")
    }
}

/// Mechy's comment pinned at the top of a panel: what it just did here, or what it needs.
private struct PinnedNote: View {
    let note: WorkspaceNote
    @EnvironmentObject var session: ProjectSession

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            Text(note.kind == .question ? "Mechy asks" : "Mechy").monoLabel(Theme.ink, size: 9)
            Text(note.text)
                .font(Theme.Typo.small)
                .foregroundStyle(Theme.ink)
                .lineLimit(3)
                .frame(maxWidth: .infinity, alignment: .leading)
                .textSelection(.enabled)
            Button { session.dismiss(note) } label: {
                Image(systemName: "xmark").font(.system(size: 8, weight: .semibold)).foregroundStyle(Theme.muted)
            }
            .buttonStyle(.plain)
            .help("Close comment (it stays in the chat)")
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(Theme.wash)
        .overlay(alignment: .leading) { Rectangle().fill(Theme.ink).frame(width: 2) }
        .overlay(alignment: .bottom) { Rectangle().fill(Theme.hairline).frame(height: Theme.Stroke.hair) }
    }
}

/// Picks the content view for a panel kind.
struct PanelContent: View {
    let panel: PanelState
    var body: some View {
        switch panel.kind {
        case .inspiration: InspirationPanel()
        case .cad: CADPanel(panel: panel)
        case .options: OptionsPanel()
        case .questions: QuestionsPanel()
        case .sim: SimPanel(panel: panel)
        case .tasks: TasksPanel()
        case .docs: DocsPanel(panel: panel)
        case .parts: PartsPanel(panel: panel)
        case .electronics: ElectronicsPanel()
        case .loads: LoadsPanel(panel: panel)
        case .manufacturing: ManufacturingPanel(panel: panel)
        case .history: HistoryPanel()
        }
    }
}
