import pathlib, socket, struct, sys, threading, unittest, zlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'host'))
import transport as t

class TransportTests(unittest.TestCase):
    def decode(self, packet, expected=0):
        left, right = socket.socketpair()
        with left, right:
            left.sendall(packet); left.shutdown(socket.SHUT_WR)
            return t.receive(right, expected)
    def test_crc_known_vector(self):
        self.assertEqual(zlib.crc32(b'123456789'), 0xcbf43926)
    def test_float_bits(self):
        data = t.fixture(400)
        self.assertEqual(self.decode(t.frame(0, data)), data)
        self.assertEqual(struct.unpack('<II', data[:8]), (0, 0x80000000))
    def test_corruption(self):
        packet = bytearray(t.frame(0, t.fixture(40))); packet[-1] ^= 1
        with self.assertRaises(ValueError): self.decode(packet)
    def test_headers(self):
        for magic, seq, size in [(b'BAD!',0,4),(b'RSC1',2,4),(b'RSC1',0,0),(b'RSC1',0,5),(b'RSC1',0,t.MAX+4)]:
            with self.subTest(size=size, seq=seq, magic=magic):
                with self.assertRaises(ValueError): self.decode(t.HEADER.pack(magic,seq,size,0))
    def test_truncation(self):
        for packet in [b'RSC', t.frame(0,t.fixture(40))[:-1]]:
            with self.assertRaises(EOFError): self.decode(packet)
    def test_fragmented_and_coalesced(self):
        left, right = socket.socketpair()
        packets = t.frame(0,t.fixture(40)) + t.frame(1,t.fixture(80))
        def send():
            with left:
                for byte in packets: left.sendall(bytes([byte]))
        thread = threading.Thread(target=send); thread.start()
        with right:
            self.assertEqual(t.receive(right,0),t.fixture(40))
            self.assertEqual(t.receive(right,1),t.fixture(80))
        thread.join()
    def test_loopback_diagnostics(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1',0)); server.listen()
            def run():
                conn,_ = server.accept()
                with conn:
                    try: t.serve_connection(conn)
                    except EOFError: pass
            worker = threading.Thread(target=run); worker.start()
            result = t.probe(server.getsockname()[1],262144,100)
            worker.join()
            self.assertEqual(result['frames'],100)
            print('\nLOOPBACK_ONLY', result)

if __name__ == '__main__': unittest.main(verbosity=2)
