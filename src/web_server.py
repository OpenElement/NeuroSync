import asyncio
import json
import logging
import secrets
import string
import os
from aiohttp import web
from .config import Config
from .matrix_bot import MatrixBot
from .synapse_client import SynapseAdminClient
from .database import add_bot

logger = logging.getLogger(__name__)

class WebServer:
    def __init__(self, config: Config, bots: dict[str, MatrixBot], bot_tasks: list, synapse_client: SynapseAdminClient, message_queue: asyncio.Queue):
        self.config = config
        self.bots = bots
        self.bot_tasks = bot_tasks
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
            web.post('/create/bot', self.handle_create_bot),
        ])

    # Generates a secure password suitable for .env files.
    def _generate_secure_password(self, length=24):
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        return password

    @web.middleware
    async def auth_middleware(self, request, handler):
        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {self.config.webhook_secret}":
            return web.json_response({"error": "Unauthorized"}, status=401)
        return await handler(request)

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
            if room_id == "ALL":
                messages = []
                while not self.message_queue.empty():
                    messages.append(self.message_queue.get_nowait())
                return web.json_response(messages)

            async with asyncio.timeout(timeout):
                while True:
                    message = await self.message_queue.get()
                    if message.get("room_id") == room_id:
                        return web.json_response(message)
                    else:
                        await self.message_queue.put(message)
                        await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            return web.json_response({"status": "timeout"}, status=204)
        except Exception as e:
            logger.error(f"Receive error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)

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
            
    async def handle_create_bot(self, request):
        """Creates a bot user, saves to DB, and starts it dynamically."""
        if not self.synapse_client:
            return web.json_response({"error": "Synapse Admin Client not configured"}, status=501)

        try:
            data = await request.json()
            username = data.get('username')
            if not username:
                return web.json_response({"error": "username is required"}, status=400)
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        password = self._generate_secure_password()
        
        try:
            # Create the user in Synapse
            user = await self.synapse_client.create_user(username, password, displayname=username)
            user_id = user.get('name')
            logger.info(f"Successfully created bot user '{user_id}' in Synapse.")

            # Add the new bot to the database
            store_path = f"./crypto_store/{username}/"
            await add_bot(user_id, password, store_path)

            # Create and start the new bot instance dynamically
            new_bot = MatrixBot(
                homeserver=self.config.matrix_homeserver,
                user_id=user_id,
                password=password,
                store_path=store_path,
                message_queue=self.message_queue
            )
            self.bots[user_id] = new_bot
            new_task = asyncio.create_task(new_bot.run())
            self.bot_tasks.append(new_task)

            logger.info(f"Successfully started new bot '{user_id}'.")
            
            return web.json_response({
                "status": "success",
                "user_id": user_id,
                "password": password,
                "message": "Bot created and is now active."
            }, status=201)

        except Exception as e:
            logger.error(f"Bot creation error: {e}", exc_info=True)
            return web.json_response({"error": f"An unexpected error occurred: {e}"}, status=500)

    async def run(self, host='0.0.0.0', port=8080):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"WebServer started on http://{host}:{port}")
        
        await asyncio.Event().wait()