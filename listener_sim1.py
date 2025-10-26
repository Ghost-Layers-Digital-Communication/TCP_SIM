#!/usr/bin/env python3
# listener_pi_interactive.py
# Fully interactive Pi listener for TCP_SIM ASCII sequences.

import socket, threading, os, time

HOST = "192.168.254.140"
PORT = 5150
EXPECTED_PASSWORD = "SECRET"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ASCII_DIR = os.path.join(SCRIPT_DIR, "ASCII")
os.makedirs(ASCII_DIR, exist_ok=True)
SLEEP_LINE = 0.12 # delay between streamed ASCII lines

def safe_send(conn, text):
    try:
        conn.sendall((text + "\n").encode())
    except:
        pass

def recv_line(conn, timeout=None):
    conn.settimeout(timeout)
    buf = b""
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                return None
            buf += chunk
            if b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                return line.decode(errors="replace").strip()
    except socket.timeout:
        return None
    finally:
        conn.settimeout(None)

def stream_file(conn, filename):
    fpath = os.path.join(ASCII_DIR, filename)
    if not os.path.isfile(fpath):
        safe_send(conn, f"run: {filename}: No such file")
        return
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        safe_send(conn, f"EXECUTING {filename} ...")
        total = len(lines)
        for i, line in enumerate(lines, start=1):
            safe_send(conn, line)
            time.sleep(SLEEP_LINE)
            if i % 6 == 0 and total > 6:
                safe_send(conn, f"[{i}/{total}] running...")
                time.sleep(0.03)
        if any("FLAG{" in l or "CTF{" in l or "PAYLOAD_MARKER" in l for l in lines):
            safe_send(conn, "PAYLOAD: FLAG CAPTURED")
        safe_send(conn, "PAYLOAD EXIT CODE: 0")
    except Exception as e:
        safe_send(conn, f"run: error reading file: {e}")

def stream_ascii(conn, filename):
    path = os.path.join(ASCII_DIR, filename)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    safe_send(conn, line.rstrip("\n"))
                    time.sleep(SLEEP_LINE)
        except Exception as e:
            safe_send(conn, f"(error streaming {filename}: {e})")

def handle_client(conn, addr):
    print(f"[+] connection from {addr}")
    try:
        # Authentication
        safe_send(conn, "PASSWORD:")
        pw = recv_line(conn, timeout=10)
        if pw != EXPECTED_PASSWORD:
            safe_send(conn, "AUTH_FAIL")
            print(f"[!] authentication failed: {pw!r}")
            conn.close()
            return
        safe_send(conn, "AUTH_OK")
        print(f"[+] authentication successful")
        stream_ascii(conn, "auth.txt")

        # Wait for CONNECT command
        while True:
            line = recv_line(conn)
            if line is None:
                break
            cmd = line.strip().upper()
            print(f"[controller ->] {cmd}")
            if cmd == "CONNECT":
                stream_ascii(conn, "connect.txt")
                break
            else:
                safe_send(conn, "Please type CONNECT to proceed.")

        # Main command loop
        while True:
            line = recv_line(conn)
            if line is None:
                print("[*] controller disconnected")
                break
            cmd = line.strip().upper()
            print(f"[controller ->] {cmd}")

            if cmd == "SPAWN":
                stream_ascii(conn, "spawned.txt")
                safe_send(conn, "SHELL SPAWNED")
                continue
            if cmd == "ESCALATE":
                stream_ascii(conn, "escalated.txt")
                safe_send(conn, "PRIVILEGE ESCALATED")
                safe_send(conn, "PROMPT: root@fake:/#")
                continue
            if cmd == "TD":
                stream_file(conn, "td_script.txt")
                continue
            if cmd in ("DISCONNECT", "QUIT", "EXIT"):
                stream_ascii(conn, "disconnect.txt")
                safe_send(conn, "Goodbye.")
                break
            safe_send(conn, f"UNKNOWN COMMAND: {cmd}")

    finally:
        try:
            conn.close()
        except:
            pass
        print(f"[-] closed {addr}")

def main():
    print(f"Listener starting on {HOST}:{PORT}")
    print(f"ASCII folder: {ASCII_DIR}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(4)
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()

if __name__ == "__main__":
    main()