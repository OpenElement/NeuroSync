#Provides a /send HTTP POST webhook that echoes JSON payloads.

import json
from aiohttp import web

class SendWebhook:


    def __init__(self, secret: str):
        #Initializes with a shared secret for Bearer token auth.
        self.secret = secret

    async def send_handler(self, request: web.Request) -> web.Response:
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != f"Bearer {self.secret}":
            return web.Response(text="Unauthorized", status=401)

        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.Response(text="Invalid JSON payload", status=400)
        
        return web.json_response(data) # Echo payload

def register_routes(app: web.Application, secret: str):
    webhook_server = SendWebhook(secret=secret)
    app.add_routes([web.post("/send", webhook_server.send_handler)])