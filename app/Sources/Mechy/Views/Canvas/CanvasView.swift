import SwiftUI

/// The drafting sheet: pan (drag empty paper), zoom (pinch, ⌘= / ⌘-, or the zoom
/// controls in the agent bar), and freely positioned panels. Nothing floats over the
/// sheet, so panels are never hidden under controls.
///
/// Zoom scales panel positions and frame sizes; panel contents re-layout at the new
/// size rather than being bitmap-scaled (keeps WKWebView / QuickLook hit-testing right).
struct CanvasView: View {
    @EnvironmentObject var session: ProjectSession
    @State private var dragPan: CGSize = .zero
    @State private var pinch: CGFloat = 1

    var body: some View {
        GeometryReader { geo in
            let zoom = CGFloat(session.layout.zoom) * pinch
            let pan = CGPoint(x: CGFloat(session.layout.panX) + dragPan.width,
                              y: CGFloat(session.layout.panY) + dragPan.height)
            ZStack(alignment: .topLeading) {
                SheetGrid(zoom: zoom, pan: pan)
                    .contentShape(Rectangle())
                    .gesture(panGesture.simultaneously(with: zoomGesture))
                    .onTapGesture(count: 2) { session.zoomToFit() }

                ForEach(session.layout.panels.sorted { $0.z < $1.z }) { panel in
                    PanelFrame(panel: panel, zoom: zoom, pan: pan, engine: session.engine)
                }

                if session.layout.panels.isEmpty {
                    EmptySheet(symbol: "plus.square.dashed", label: "Empty sheet — add a panel")
                        .frame(width: 260, height: 140)
                        .position(x: geo.size.width / 2, y: geo.size.height / 2)
                        .allowsHitTesting(false)
                }
            }
            .frame(width: geo.size.width, height: geo.size.height)
            .clipped()
            .onAppear {
                session.viewportSize = geo.size
                scheduleLaunchFit()
            }
            .onChange(of: geo.size) { _, newSize in
                session.viewportSize = newSize
                if !session.didLaunchFit { scheduleLaunchFit() }
            }
        }
        .background(Theme.paper)
    }

    /// Fit the sheet to the real canvas size once the window has settled (the first
    /// GeometryReader pass can report a provisional size while the window restores).
    private func scheduleLaunchFit() {
        let s = session
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) {
            s.fitToViewportAtLaunch(s.viewportSize)
        }
    }

    private var panGesture: some Gesture {
        DragGesture(minimumDistance: 2, coordinateSpace: .global)
            .onChanged { dragPan = $0.translation }
            .onEnded { v in
                session.layout.panX += Double(v.translation.width)
                session.layout.panY += Double(v.translation.height)
                dragPan = .zero
                session.saveLayout()
            }
    }

    private var zoomGesture: some Gesture {
        MagnifyGesture()
            .onChanged { pinch = $0.magnification }
            .onEnded { v in
                pinch = 1
                session.setZoom(session.layout.zoom * Double(v.magnification))
            }
    }
}

/// Fine dot grid plus a coarser grid of small hollow square nodes (every 8 units).
struct SheetGrid: View {
    let zoom: CGFloat
    let pan: CGPoint

    var body: some View {
        Canvas { ctx, size in
            var unit = Theme.Canvas.gridUnit * zoom
            var every = Theme.Canvas.nodeEvery
            if unit < 12 { unit *= 2; every = max(1, every / 2) }   // keep dots readable when zoomed out
            func firstLine(_ offset: CGFloat, _ step: CGFloat) -> CGFloat {
                let r = offset.truncatingRemainder(dividingBy: step)
                return r < 0 ? r + step : r
            }
            // Dots
            let r = Theme.Canvas.dotRadius
            var dots = Path()
            var x = firstLine(pan.x, unit)
            while x <= size.width {
                var y = firstLine(pan.y, unit)
                while y <= size.height {
                    dots.addEllipse(in: CGRect(x: x - r, y: y - r, width: 2 * r, height: 2 * r))
                    y += unit
                }
                x += unit
            }
            ctx.fill(dots, with: .color(Theme.gridDot))

            // Nodes
            let step = unit * CGFloat(every)
            let s = Theme.Canvas.nodeSize
            var nodes = Path()
            x = firstLine(pan.x, step)
            while x <= size.width {
                var y = firstLine(pan.y, step)
                while y <= size.height {
                    nodes.addRect(CGRect(x: x - s / 2, y: y - s / 2, width: s, height: s))
                    y += step
                }
                x += step
            }
            ctx.stroke(nodes, with: .color(Theme.hairline), lineWidth: Theme.Stroke.hair)
        }
    }
}

/// Zoom out / percentage (click resets to 100%) / zoom in / fit all.
/// Lives in the agent bar so it never covers a panel.
struct ZoomControls: View {
    @EnvironmentObject var session: ProjectSession
    var body: some View {
        HStack(spacing: 0) {
            button("minus") { session.zoomOut() }.help("Zoom out (⌘-)")
            divider
            Button { session.setZoom(1) } label: {
                Text(Theme.percent(session.layout.zoom))
                    .font(Theme.Typo.mono(10, .medium))
                    .foregroundStyle(Theme.ink)
                    .frame(width: 44, height: 24)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .help("Reset zoom to 100%")
            divider
            button("plus") { session.zoomIn() }.help("Zoom in (⌘=)")
            divider
            button("arrow.up.left.and.arrow.down.right") { session.zoomToFit() }.help("Fit all panels (⌘0)")
        }
        .background(Theme.surface)
        .overlay(Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.frame))
    }

    private var divider: some View { Rectangle().fill(Theme.ink).frame(width: Theme.Stroke.frame, height: 24) }

    private func button(_ symbol: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: symbol)
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(Theme.ink)
                .frame(width: 26, height: 24)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}
