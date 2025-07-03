from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from urllib.parse import parse_qs, urlparse

# Configuración
host = "0.0.0.0"
port = 8000

# Manejador HTTP básico
class SimpleAPIHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type, Accept')
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers()
        
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            # Ruta principal
            response = {
                'message': 'Bienvenido a la API de BioGenetic',
                'version': '0.1.0'
            }
            self._set_headers()
            self.wfile.write(json.dumps(response).encode())
            
        elif path == '/api/status':
            # Ruta de estado
            response = {
                'status': 'online'
            }
            self._set_headers()
            self.wfile.write(json.dumps(response).encode())
            
        else:
            # Ruta no encontrada
            response = {
                'error': 'Ruta no encontrada'
            }
            self._set_headers(404)
            self.wfile.write(json.dumps(response).encode())

def run_server(server_class=HTTPServer, handler_class=SimpleAPIHandler):
    server_address = (host, port)
    httpd = server_class(server_address, handler_class)
    print(f"Servidor ejecutándose en http://{host}:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server() 