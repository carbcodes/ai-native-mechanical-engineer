import SwiftUI
import AppKit

/// Freehand sketch sheet (pen, eraser, clear, undo stroke); hands back a PNG.
struct SketchPad: View {
    struct Stroke: Identifiable {
        let id = UUID()
        var points: [CGPoint]
        var eraser: Bool
    }

    let onSave: (Data) -> Void
    let onCancel: () -> Void

    @State private var strokes: [Stroke] = []
    @State private var current: Stroke?
    @State private var erasing = false

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: Theme.Space.m) {
                Text("Sketch").monoLabel()
                Spacer()
                Button { erasing = false } label: {
                    Label("Pen", systemImage: "pencil")
                }
                .buttonStyle(SheetButtonStyle(filled: !erasing))
                Button { erasing = true } label: {
                    Label("Eraser", systemImage: "eraser")
                }
                .buttonStyle(SheetButtonStyle(filled: erasing))
                Button("Undo") { _ = strokes.popLast() }.buttonStyle(SheetButtonStyle())
                    .disabled(strokes.isEmpty)
                Button("Clear") { strokes = [] }.buttonStyle(SheetButtonStyle())
                    .disabled(strokes.isEmpty)
                Button("Cancel") { onCancel() }.buttonStyle(SheetButtonStyle())
                Button("Save") { save() }.buttonStyle(SheetButtonStyle(filled: true))
                    .disabled(strokes.isEmpty)
            }
            .padding(Theme.Space.m)
            Divider().overlay(Theme.ink)
            Canvas { ctx, _ in
                for stroke in strokes + (current.map { [$0] } ?? []) {
                    var path = Path()
                    if let first = stroke.points.first {
                        path.move(to: first)
                        for p in stroke.points.dropFirst() { path.addLine(to: p) }
                    }
                    let col = stroke.eraser ? Color(Theme.paper) : Color(Theme.ink)
                    ctx.stroke(path, with: .color(col),
                               lineWidth: stroke.eraser ? 16 : 2)
                }
            }
            .background(Color(Theme.paper))
            .overlay(Rectangle().stroke(Theme.ink, lineWidth: Theme.Stroke.hair))
            .gesture(DragGesture(minimumDistance: 0)
                .onChanged { v in
                    let p = v.location
                    if erasing {
                        erase(near: p)
                    } else if current == nil {
                        current = Stroke(points: [p], eraser: false)
                    } else {
                        current?.points.append(p)
                    }
                }
                .onEnded { _ in
                    if let c = current, c.points.count > 1 { strokes.append(c) }
                    current = nil
                })
            .padding(Theme.Space.m)
        }
        .frame(minWidth: 560, minHeight: 420)
        .background(Color(Theme.surface))
    }

    /// Eraser removes strokes passing within 12 pt of the pointer.
    private func erase(near p: CGPoint) {
        let r: CGFloat = 12
        strokes.removeAll { s in
            s.points.contains { hypot($0.x - p.x, $0.y - p.y) < r }
        }
    }

    private func save() {
        let size = CGSize(width: 800, height: 600)
        guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(size.width),
                                         pixelsHigh: Int(size.height), bitsPerSample: 8,
                                         samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                                         colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)
        else { return }
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
        NSColor.white.setFill()
        NSRect(origin: .zero, size: size).fill()
        let scaleX = size.width / 560, scaleY = size.height / 420
        NSColor.black.setStroke()
        for s in strokes where !s.eraser && s.points.count > 1 {
            let path = NSBezierPath()
            path.lineWidth = 2.5
            path.move(to: NSPoint(x: s.points[0].x * scaleX, y: size.height - s.points[0].y * scaleY))
            for p in s.points.dropFirst() {
                path.line(to: NSPoint(x: p.x * scaleX, y: size.height - p.y * scaleY))
            }
            path.stroke()
        }
        NSGraphicsContext.restoreGraphicsState()
        if let png = rep.representation(using: .png, properties: [:]) { onSave(png) }
    }
}
