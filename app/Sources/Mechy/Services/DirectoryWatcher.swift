import Foundation
import CoreServices

/// Recursive folder watcher built on FSEvents. Calls `onChange` on the main queue
/// with the changed paths, coalesced by `latency` seconds.
final class DirectoryWatcher {
    private let url: URL
    private let latency: CFTimeInterval
    private let onChange: ([String]) -> Void
    private var stream: FSEventStreamRef?

    init(url: URL, latency: CFTimeInterval = 0.3, onChange: @escaping ([String]) -> Void) {
        self.url = url
        self.latency = latency
        self.onChange = onChange
    }

    deinit { stop() }

    func start() {
        guard stream == nil else { return }
        var context = FSEventStreamContext(
            version: 0,
            info: Unmanaged.passUnretained(self).toOpaque(),
            retain: nil,
            release: nil,
            copyDescription: nil
        )
        let callback: FSEventStreamCallback = { _, info, count, eventPaths, _, _ in
            guard let info else { return }
            let watcher = Unmanaged<DirectoryWatcher>.fromOpaque(info).takeUnretainedValue()
            // With kFSEventStreamCreateFlagUseCFTypes, eventPaths is a CFArray of CFString.
            let array = Unmanaged<CFArray>.fromOpaque(eventPaths).takeUnretainedValue()
            let paths = (array as NSArray).compactMap { $0 as? String }
            if paths.isEmpty && count > 0 { return }
            watcher.onChange(paths)
        }
        let flags = FSEventStreamCreateFlags(
            kFSEventStreamCreateFlagUseCFTypes | kFSEventStreamCreateFlagFileEvents | kFSEventStreamCreateFlagNoDefer
        )
        // Bound to an optional so this compiles whether the SDK imports the result as optional or not.
        let created: FSEventStreamRef? = FSEventStreamCreate(
            kCFAllocatorDefault,
            callback,
            &context,
            [url.path] as CFArray,
            FSEventStreamEventId(kFSEventStreamEventIdSinceNow),
            latency,
            flags
        )
        guard let s = created else { return }
        FSEventStreamSetDispatchQueue(s, DispatchQueue.main)
        FSEventStreamStart(s)
        stream = s
    }

    func stop() {
        guard let s = stream else { return }
        FSEventStreamStop(s)
        FSEventStreamInvalidate(s)
        FSEventStreamRelease(s)
        stream = nil
    }
}

/// Incrementally reads `.mechy/events.jsonl` (contracts §6).
final class EventTail {
    let url: URL
    private var offset: UInt64 = 0
    private var partial = Data()

    init(url: URL) { self.url = url }

    private var fileSize: UInt64 {
        ((try? FileManager.default.attributesOfItem(atPath: url.path))?[.size] as? NSNumber)?.uint64Value ?? 0
    }

    /// The last events in the file (reads at most the final 64 KB), and moves to the end.
    func readRecent(maxBytes: UInt64 = 65_536) -> [EngineEvent] {
        let size = fileSize
        let start = size > maxBytes ? size - maxBytes : 0
        guard let data = read(from: start) else { offset = size; return [] }
        offset = start + UInt64(data.count)
        var lines = String(decoding: data, as: UTF8.self).components(separatedBy: "\n")
        if start > 0, !lines.isEmpty { lines.removeFirst() }   // first line may be cut
        partial = Data()
        return lines.compactMap(EventTail.parse)
    }

    /// Events appended since the last read.
    func readNew() -> [EngineEvent] {
        let size = fileSize
        if size < offset { offset = 0; partial = Data() }   // truncated or replaced
        guard size > offset, let data = read(from: offset) else { return [] }
        offset += UInt64(data.count)
        var buf = partial
        buf.append(data)
        var events: [EngineEvent] = []
        while let nl = buf.firstIndex(of: 0x0A) {
            let line = String(decoding: buf[buf.startIndex..<nl], as: UTF8.self)
            if let ev = EventTail.parse(line) { events.append(ev) }
            buf.removeSubrange(buf.startIndex...nl)
        }
        partial = Data(buf)
        return events
    }

    private func read(from start: UInt64) -> Data? {
        guard let h = try? FileHandle(forReadingFrom: url) else { return nil }
        defer { try? h.close() }
        do {
            try h.seek(toOffset: start)
            return try h.readToEnd() ?? Data()
        } catch {
            return nil
        }
    }

    private static func parse(_ line: String) -> EngineEvent? {
        let t = line.trimmingCharacters(in: .whitespaces)
        guard t.hasPrefix("{"), let d = FileIO.parseJSONLine(t) else { return nil }
        return EngineEvent(d)
    }
}
