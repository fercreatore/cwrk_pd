"""
Endpoint HTTP que recibe tokens frescos desde n8n y actualiza los config files.

n8n tiene un workflow que refresca tokens de ML cada 4-5h y los guarda en una Data Table.
Ese workflow también hace POST acá con los tokens actualizados.

USO:
    python -m multicanal.webhook_tokens

    Escucha en puerto 8506 (configurable con --port)
    Endpoint: POST /api/tokens/update

PAYLOAD esperado (desde n8n):
    {
        "calzalindo_h": "Bearer APP_USR-...",
        "calzalindo_tama": "Bearer APP_USR-...",
        "calzalindo_lu": "Bearer APP_USR-...",
        "tiendanube": "bearer ...",
        "id_tiendanube": "7018867",
        "tiendanube2": "bearer ...",
        "id_tiendanube2": "6466615"
    }

DEPLOY en Windows 112:
    iniciar_webhook_tokens.bat (auto-start con Windows via schtasks)
"""

import json
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PORT = 8506
SECRET = os.environ.get('WEBHOOK_SECRET', '')  # opcional: validar con header X-Webhook-Secret


class TokenHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != '/api/tokens/update':
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')
            return

        # Validar secret si está configurado
        if SECRET:
            req_secret = self.headers.get('X-Webhook-Secret', '')
            if req_secret != SECRET:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'Forbidden')
                return

        # Leer body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid JSON')
            return

        # Actualizar tokens
        try:
            from multicanal.refresh_token_ml import actualizar_desde_n8n
            actualizar_desde_n8n(data)

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] Tokens actualizados desde n8n")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'updated_at': timestamp,
            }).encode())

        except Exception as e:
            print(f"[ERROR] {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'service': 'token-webhook'}).encode())
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # Solo loguear requests no-health
        if '/health' not in (args[0] if args else ''):
            super().log_message(format, *args)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Webhook receiver para tokens de n8n')
    parser.add_argument('--port', type=int, default=PORT, help=f'Puerto (default: {PORT})')
    args = parser.parse_args()

    server = HTTPServer(('0.0.0.0', args.port), TokenHandler)
    print(f"Token webhook escuchando en http://0.0.0.0:{args.port}")
    print(f"  POST /api/tokens/update — recibe tokens de n8n")
    print(f"  GET  /health — health check")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWebhook detenido.")
        server.server_close()
