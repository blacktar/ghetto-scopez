"""RSC1 framed float32 probe; standard library only."""
import argparse, json, socket, struct, time, zlib
HEADER = struct.Struct('<4sIII')
MAX = 4 * 1024 * 1024

def fixture(size):
    # Preserve IEEE754 bits, including NaNs, infinities and signed zero.
    words = [0, 0x80000000, 0x3f800000, 0xbf800000, 0x7f800000,
             0xff800000, 0x7fc01234, 1, 0x3eaaaaab, 0x40800000]
    return b''.join(struct.pack('<I', words[i % len(words)]) for i in range(size // 4))

def frame(seq, payload):
    if not payload or len(payload) % 4 or len(payload) > MAX:
        raise ValueError('invalid float32 payload length')
    return HEADER.pack(b'RSC1', seq, len(payload), zlib.crc32(payload)) + payload

def exact(sock, count):
    data = bytearray()
    while len(data) < count:
        part = sock.recv(count - len(data))
        if not part:
            raise EOFError('connection closed mid-frame')
        data.extend(part)
    return bytes(data)

def receive(sock, expected):
    magic, seq, size, crc = HEADER.unpack(exact(sock, HEADER.size))
    if magic != b'RSC1' or seq != expected or not 0 < size <= MAX or size % 4:
        raise ValueError('header/sequence error')
    payload = exact(sock, size)
    if zlib.crc32(payload) != crc:
        raise ValueError('checksum error')
    return payload

def serve_connection(sock):
    seq = 0
    while True:
        payload = receive(sock, seq)
        sock.sendall(frame(seq, payload))
        seq += 1

def probe(port, size, count):
    payload = fixture(size)
    samples = []
    with socket.create_connection(('127.0.0.1', port), timeout=10) as sock:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        start = time.perf_counter()
        for seq in range(count):
            tick = time.perf_counter()
            sock.sendall(frame(seq, payload))
            if receive(sock, seq) != payload:
                raise ValueError('bitwise float32 mismatch')
            samples.append((time.perf_counter() - tick) * 1000)
        elapsed = time.perf_counter() - start
    ordered = sorted(samples)
    return dict(frames=count, payload_bytes=size, elapsed_s=elapsed,
                verified_payload_MiB_s=size * count / elapsed / 1048576,
                rtt_ms_min=min(samples), rtt_ms_median=ordered[len(ordered)//2],
                rtt_ms_p95=ordered[min(len(ordered)-1, int(len(ordered)*.95))],
                bitwise_integrity='PASS', mode='stop-and-wait echo; not one-way latency or USB line rate')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=23456)
    parser.add_argument('--bytes', type=int, default=262144)
    parser.add_argument('--frames', type=int, default=100)
    args = parser.parse_args()
    if args.frames < 1 or args.frames > 1000000 or args.bytes % 4 or not 0 < args.bytes <= MAX:
        parser.error('frames 1..1000000; bytes must be multiple of 4 up to 4 MiB')
    print(json.dumps(probe(args.port, args.bytes, args.frames), indent=2))
