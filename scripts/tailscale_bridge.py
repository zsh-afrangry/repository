#!/usr/bin/env python3
"""Local TCP bridge to forward traffic from Tailscale Serve endpoint (e.g. 8020) to dev frontend (e.g. 3000).

Used by dev-start.sh when Tailscale Serve forwards to 8020 but dev frontend runs on 3000.
"""

import signal
import socket
import sys
import threading


def pipe(src: socket.socket, dst: socket.socket):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            src.close()
        except Exception:
            pass
        try:
            dst.close()
        except Exception:
            pass


def main():
    listen_port = int(sys.argv[1]) if len(sys.argv) > 1 else 8020
    target_port = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    try:
        server.bind(("127.0.0.1", listen_port))
    except OSError as err:
        sys.stderr.write(f"Tailscale bridge unable to bind port {listen_port}: {err}\n")
        sys.exit(1)

    server.listen(128)
    stop_event = threading.Event()

    def handle_sig(sig, frame):
        stop_event.set()
        try:
            server.close()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    while not stop_event.is_set():
        try:
            client_sock, _ = server.accept()
        except OSError:
            break
        try:
            target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_sock.connect(("127.0.0.1", target_port))
        except Exception as err:
            client_sock.close()
            continue

        threading.Thread(target=pipe, args=(client_sock, target_sock), daemon=True).start()
        threading.Thread(target=pipe, args=(target_sock, client_sock), daemon=True).start()


if __name__ == "__main__":
    main()
