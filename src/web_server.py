# src/web_server.py
import asyncio
import json
import logging
from aiohttp import web
from .config import Config
from .matrix_bot import MatrixBot
from .synapse_client import SynapseAdminClient

logger = logging.getLogger(__name__)

# Manages the aiohttp web application and its endpoints.
class WebServer:
    def __init__(self, config: Config, bots: dict[str, MatrixBot], synapse_client: SynapseAdminClient, message_queue: asyncio.Queue):
        self.config = config
        self.bots = bots
        self.synapse_client = synapse_client
        self.message_queue = message_queue
        self.app = web.Application(middlewares=[self.auth_middleware])
        self._setup_routes()

    def _setup_routes(self):
        self.app.add_routes([
            web.post('/msg/send', self.handle_send),
            web.get('/msg/receive', self.handle_receive),
            web.post('/msg/receive', self.handle_receive),
            web.post('/create/user', self.handle_create_user),
        ])

    @web.middleware
    # (auth_middleware remains the same)
    async def auth_middleware(self, request, handler):
        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {self.config.webhook_secret}":
            return web.json_response({"error": "Unauthorized"}, status=401)
        return await handler(request)

    # (handle_send remains the same)
    async def handle_send(self, request):
        try:
            data = await request.json()
            user_id = data.get('user_id')
            room_id = data.get('room_id')
            message = data.get('message')

            if not all([user_id, room_id, message]):
                return web.json_response({"error": "user_id, room_id, and message are required"}, status=400)
            
            bot = self.bots.get(user_id)
            if not bot:
                return web.json_response({"error": f"Bot with user_id '{user_id}' not found or not initialized."}, status=404)
            
            await bot.send_message(room_id, message)
            return web.json_response({"status": "success", "sender": user_id})
        except Exception as e:
            logger.error(f"Send error: {e}")
            return web.json_response({"error": "Failed to send message"}, status=500)

    async def handle_receive(self, request):
        params = request.query if request.method == 'GET' else await request.json()
        room_id = params.get('room_id')
        timeout = float(params.get('timeout', 10.0))
        
        if not room_id:
            return web.json_response({"error": "room_id required"}, status=400)

        try:
            # If room_id is "ALL", drain the entire queue and return all messages.
            if room_id == "ALL":
                messages = []
                while not self.message_queue.empty():
                    messages.append(self.message_queue.get_nowait())
                return web.json_response(messages)

            # Otherwise, perform long-polling for a message from a specific room.
            async with asyncio.timeout(timeout):
                while True:
                    message = await self.message_queue.get()
                    if message.get("room_id") == room_id:
                        return web.json_response(message)
                    else:
                        # If the message is not for the requested room, put it back.
                        await self.message_queue.put(message)
                        await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            # Timeout only occurs when polling for a specific room.
            return web.json_response({"status": "timeout"}, status=204)
        except Exception as e:
            logger.error(f"Receive error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)

    # (handle_create_user remains the same)
    async def handle_create_user(self, request):
        try:
            data = await request.json()
            username, password = data.get('username'), data.get('password')
            if not all([username, password]):
                return web.json_response({"error": "username and password are required"}, status=400)
            
            user = await self.synapse_client.create_user(
                username, password, data.get('display_name'), data.get('recovery_email')
            )
            return web.json_response({"status": "success", "user_id": user.get('name')}, status=201)
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)
        except Exception as e:
            logger.error(f"User creation error: {e}")
            return web.json_response({"error": str(e)}, status=400)
            
    # (run method remains the same)
    async def run(self, host='0.0.0.0', port=8080):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"WebServer started on http://{host}:{port}")
        await asyncio.Event().wait()