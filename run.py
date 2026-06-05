from waitress import serve
from app import app
import socket

hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

print("Server starting...")
print(f"http://{local_ip}:5000")

serve(app, host="0.0.0.0", port=5000)