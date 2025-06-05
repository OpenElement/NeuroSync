#Provides a /send HTTP POST webhook that echoes JSON payloads.

import json
from aiohttp import web

class SendWebhook:


    def __init__(self, secret: str):
        #Initializes with a shared secret for Bearer token auth.
        self.secret = secret

    async def auth_request(self, request: web.Request) -> web.Response | None:
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != f"Bearer {self.secret}":
            return web.Response(text="Unauthorized", status=401)
        return None # Authentication successful

    async def create_bot_handler(self, request: web.Request) -> web.Response:
        if auth_response := await self.auth_request(request): return auth_response
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.Response(text="Invalid JSON payload", status=400)
            
        uuid = data.get("uuid", None)    
        username = data.get("username", None)
        display_name = data.get("display_name", None)

        if not username or not display_name or not uuid:
            return web.Response(text="username, display_name or uuid not in payload", status=400)

        # For now, just echo the username back.
        return web.json_response({"created_bot_username": username})

    async def create_user_handler(self, request: web.Request) -> web.Response:
        if auth_response := await self.auth_request(request): return auth_response
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.Response(text="Invalid JSON payload", status=400)

        username = data.get("username", None)
        display_name = data.get("display_name", None)
        uuid = data.get("uuid", None)
        password = data.get("password", None)
        auto_invite = data.get("auto_invite", False)
        recovery_email = data.get("recovery_email", None)

        if not username or not display_name or not uuid:
                    return web.Response(text="username, display_name or uuid not in payload", status=400)

        # For now, just echo the username back.
        return web.json_response({"created_user_username": username})

def register_routes(app: web.Application, secret: str):
    webhook_server = SendWebhook(secret=secret)
    app.add_routes([web.post("/create/bot", webhook_server.create_bot_handler)])
    app.add_routes([web.post("/create/user", webhook_server.create_user_handler)])