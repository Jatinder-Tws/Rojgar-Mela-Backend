import socket
import threading

LISTEN_HOST = "0.0.0.0"  # allow external connections
LISTEN_PORT = 9006        # mirror port
TARGET_HOST = "127.0.0.1" # original service
TARGET_PORT = 8000       # original service port

def forward(source, destination):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            destination.sendall(data)
    except (ConnectionResetError, ConnectionAbortedError, OSError):
        # Normal disconnect on Windows
        pass
    finally:
        try:
            source.close()
        except:
            pass
        try:
            destination.close()
        except:
            pass

def handle_client(client_socket):
    target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    target_socket.connect((TARGET_HOST, TARGET_PORT))
    threading.Thread(target=forward, args=(client_socket, target_socket), daemon=True).start()
    threading.Thread(target=forward, args=(target_socket, client_socket), daemon=True).start()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen(100)
    print(f"Forwarding {LISTEN_PORT} -> {TARGET_PORT} (mirror of 9000)")

    while True:
        client_socket, _ = server.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == "__main__":
    main()
