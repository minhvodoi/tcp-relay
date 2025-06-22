import socket
import threading

HOST = '0.0.0.0'
PORT = 4000

clients = []

def handle_client(client_socket, addr):
    print(f"[+] Client connected from {addr}")
    clients.append(client_socket)
    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            for c in clients:
                if c != client_socket:
                    c.sendall(data)
        except Exception as e:
            print(f"[!] Error: {e}")
            break
    client_socket.close()
    clients.remove(client_socket)
    print(f"[-] Client disconnected {addr}")

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(2)
    print(f"[+] Relay server listening on {HOST}:{PORT}")
    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()

if __name__ == "__main__":
    main()
