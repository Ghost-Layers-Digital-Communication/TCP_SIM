#!/usr/bin/env python3
# controller_laptop_interactive.py
# Fully interactive controller: prompts user for each command manually.

import socket, threading, time, os, sys

PI_IP = "xxxxxxxxxxx" # set your Pi IP
PORT = 5150
PASSWORD = "SECRET"
RECV_TIMEOUT = 0.2

def print_line(prefix, bline):
    try:
        s = bline.decode(errors="replace").rstrip()
    except:
        s = repr(bline)
    print(f"<{prefix}> {s}")

def stream_reader(sock, stop_event):
    buf = b""
    try:
        while not stop_event.is_set():
            try:
                data = sock.recv(4096)
            except socket.timeout:
                continue
            if not data:
                stop_event.set()
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if line:
                    print_line("pi", line)
    except:
        stop_event.set()

def send(sock, text):
    try:
        sock.sendall((text + "\n").encode())
    except:
        pass

def main():
    if PI_IP == "xxx.xxx.xxx.xxx":
        print("Edit PI_IP in the script before running.")
        sys.exit(1)

    print(f"Connecting to {PI_IP}:{PORT}")
    try:
        s = socket.create_connection((PI_IP, PORT), timeout=8)
    except Exception as e:
        print("Connect failed:", e)
        return

    stop_event = threading.Event()
    s.settimeout(RECV_TIMEOUT)
    threading.Thread(target=stream_reader, args=(s, stop_event), daemon=True).start()

    # Password authentication
    input("[>] Press Enter when you see PASSWORD prompt on Pi")
    send(s, PASSWORD)
    input("[>] Press Enter after AUTH_OK is displayed and auth.txt has streamed")

    # Command loop
    while True:
        cmd = input("[>] Enter command: ").strip()
        if not cmd:
            continue
        send(s, cmd)
        if cmd.upper() in ("DISCONNECT", "QUIT", "EXIT"):
            time.sleep(0.5)
            break
        # small pause to allow ASCII to stream
        time.sleep(0.2)

    stop_event.set()
    try:
        s.close()
    except:
        pass
    print("[*] session ended")

if __name__ == "__main__":
    main()

