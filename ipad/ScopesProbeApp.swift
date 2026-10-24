import SwiftUI
import Network

// Integer-only checksum preserves every IEEE754 bit pattern.
func crc32(_ bytes: Data) -> UInt32 {
    var crc: UInt32 = 0xffffffff
    for byte in bytes {
        crc ^= UInt32(byte)
        for _ in 0..<8 { crc = (crc >> 1) ^ ((crc & 1) == 1 ? 0xedb88320 : 0) }
    }
    return crc ^ 0xffffffff
}
func word(_ bytes: Data, _ offset: Int) -> UInt32 {
    (0..<4).reduce(UInt32(0)) { $0 | UInt32(bytes[bytes.startIndex + offset + $1]) << (8 * $1) }
}
final class Peer {
    let connection: NWConnection
    var buffer = Data()
    var expected: UInt32 = 0
    let report: (String) -> Void
    init(_ connection: NWConnection, report: @escaping (String) -> Void) {
        self.connection = connection
        self.report = report
    }
    func read() {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [self] data, _, done, error in
            if let data = data { buffer.append(data) }
            if error != nil || done { report("Disconnected; reconnect to reset sequence"); connection.cancel(); return }
            process()
        }
    }
    func process() {
        guard buffer.count >= 16 else { read(); return }
        let size = Int(word(buffer, 8))
        guard Array(buffer.prefix(4)) == Array("RSC1".utf8),
              word(buffer, 4) == expected, size > 0, size <= 4194304, size % 4 == 0 else {
            report("Rejected header/sequence"); connection.cancel(); return
        }
        guard buffer.count >= 16 + size else { read(); return }
        let packet = Data(buffer.prefix(16 + size))
        let payload = Data(packet.dropFirst(16))
        guard crc32(payload) == word(packet, 12) else {
            report("Rejected checksum"); connection.cancel(); return
        }
        buffer = Data(buffer.dropFirst(16 + size))
        expected &+= 1
        // One outstanding echo applies backpressure and bounds memory.
        connection.send(content: packet, completion: .contentProcessed { [self] error in
            guard error == nil else { connection.cancel(); return }
            if expected % 25 == 0 || expected == 1 { report("Verified \(expected) frames; last \(size) bytes") }
            process()
        })
    }
}
final class Probe: ObservableObject {
    @Published var status = "Stopped"
    private var listener: NWListener?
    private var peer: Peer?
    private let queue = DispatchQueue(label: "ScopesProbe.transport")
    private func show(_ value: String) {
        print("[ScopesProbe] \(value)")
        DispatchQueue.main.async { self.status = value }
    }
    func start() {
        queue.async { [self] in
            guard listener == nil else { return }
            do {
                let parameters = NWParameters.tcp
                // usbmux forwards to the device IPv4 loopback. Bind it explicitly.
                parameters.requiredLocalEndpoint = .hostPort(host: .ipv4(.loopback), port: 23456)
                let tcp = parameters.defaultProtocolStack.transportProtocol as? NWProtocolTCP.Options
                tcp?.noDelay = true
                let server = try NWListener(using: parameters)
                listener = server
                server.stateUpdateHandler = { [weak self] state in self?.show("Listener 127.0.0.1:23456: \(state)") }
                server.newConnectionHandler = { [weak self] connection in
                    guard let self = self else { connection.cancel(); return }
                    self.show("Accepted peer: \(connection.endpoint)")
                    self.peer?.connection.cancel()
                    let next = Peer(connection) { [weak self] in self?.show($0) }
                    self.peer = next
                    connection.start(queue: self.queue)
                    next.read()
                }
                server.start(queue: queue)
            } catch { show("Start failed: \(error)") }
        }
    }
    func stop() {
        queue.async { [self] in
            peer?.connection.cancel(); peer = nil
            listener?.cancel(); listener = nil
            show("Stopped")
        }
    }
}
@main struct ScopesProbeApp: App {
    @StateObject private var probe = Probe()
    var body: some Scene {
        WindowGroup {
            VStack(spacing: 24) {
                Text("Resolve → iPad: USB probe").font(.title)
                Text(probe.status)
                Text("TCP 23456 • keep app in foreground")
                Button("Start listener") { probe.start() }
                Button("Stop listener") { probe.stop() }
            }.padding()
        }
    }
}
