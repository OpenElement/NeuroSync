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
from .database import add_bot, get_all_bots, get_bot_by_user_id, set_bot_active_status

logger = logging.getLogger(__name__)

class WebServer:
    def __init__(self, config: Config, bots: dict[str, MatrixBot], bot_tasks: list, synapse_client: SynapseAdminClient, message_queue: asyncio.Queue):
        self.config = config
        self.bots = bots
        self.bot_tasks = bot_tasks
        self.bot_task_map = {}  # Maps user_id to task for better tracking
        self.synapse_client = synapse_client
        self.message_queue = message_queue
        self.app = web.Application(middlewares=[self.auth_middleware])
        self._setup_routes()

    def _setup_routes(self):
        self.app.add_routes([
            web.post('/msg/send', self.handle_send),
            web.get('/msg/receive', self.handle_receive),
            web.post('/msg/receive', self.handle_receive),
            web.post('/user/create', self.handle_create_user),
            web.post('/bot/create', self.handle_create_bot),
            web.post('/bot/activate', self.handle_activate_bot),
            web.post('/bot/deactivate', self.handle_deactivate_bot),
        ])

    # Generates a secure random string suitable for passwords and webhook secrets.
    def _generate_secure_string(self, length=32):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for i in range(length))

    @web.middleware
    async def auth_middleware(self, request, handler):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return web.json_response({"error": "Unauthorized"}, status=401)
        
        token = auth_header.replace("Bearer ", "")
        path = request.path
        
        # Admin endpoints - check admin token
        admin_endpoints = ['/create/user', '/create/bot']
        if path in admin_endpoints:
            if self.config.webhook_secret and token == self.config.webhook_secret:
                return await handler(request)
            return web.json_response({"error": "Unauthorized"}, status=401)
        
        # Bot endpoints - check bot token
        bot_configs = await get_all_bots()
        for bot_config in bot_configs:
            if bot_config['webhook_secret'] == token:
                request['authenticated_user_id'] = bot_config['user_id']
                return await handler(request)
        
        return web.json_response({"error": "Unauthorized"}, status=401)

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
        """Creates a bot user, saves to DB (inactive by default)."""
        if not self.synapse_client:
            return web.json_response({"error": "Synapse Admin Client not configured"}, status=501)

        try:
            data = await request.json()
            username = data.get('username')
            if not username:
                return web.json_response({"error": "username is required"}, status=400)
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        password = self._generate_secure_string(24)
        
        try:
            # Create the user in Synapse
            user = await self.synapse_client.create_user(username, password, displayname=username)
            user_id = user.get('name')
            logger.info(f"Successfully created bot user '{user_id}' in Synapse.")

            # Add the new bot to the database (inactive by default)
            store_path = f"./crypto_store/{username}/"
            webhook_secret = self._generate_secure_string(32)
            await add_bot(user_id, password, store_path, webhook_secret)

            logger.info(f"Successfully created bot '{user_id}' (inactive by default).")
            
            return web.json_response({
                "status": "success",
                "user_id": user_id,
                "password": password,
                "webhook_secret": webhook_secret,
                "message": "Bot created but not active. Use /activate/bot to start it."
            }, status=201)

        except Exception as e:
            logger.error(f"Bot creation error: {e}", exc_info=True)
            return web.json_response({"error": f"An unexpected error occurred: {e}"}, status=500)
    # Activates a bot by username
    async def handle_activate_bot(self, request):
        try:
            data = await request.json()
            username = data.get('username') 
            
            if not username:
                return web.json_response({"error": "username is required"}, status=400)
                
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        try:
            user_id = username
            
            # Get the authenticated user_id from auth_middleware
            authenticated_user_id = request.get('authenticated_user_id')
            
            # Verify the authenticated user matches the requested bot to activate
            if authenticated_user_id != user_id:
                return web.json_response({"error": "Bearer token does not match the requested bot"}, status=401)
            
            # Get bot config from database
            bot_config = await get_bot_by_user_id(user_id)
            if not bot_config:
                return web.json_response({"error": f"Bot with user_id '{username}' not found"}, status=404)
            
            # Check if already active
            if bot_config['active']:
                return web.json_response({"error": f"Bot '{username}' is already active"}, status=409)
            
            # Check if bot instance already exists
            if user_id in self.bots:
                return web.json_response({"error": f"Bot '{username}' is already running"}, status=409)
            
            # Create and start the bot
            new_bot = MatrixBot(
                homeserver=self.config.matrix_homeserver,
                user_id=user_id,
                password=bot_config['password'],
                store_path=bot_config['store_path'],
                message_queue=self.message_queue
            )
            
            self.bots[user_id] = new_bot
            new_task = asyncio.create_task(new_bot.run())
            self.bot_tasks.append(new_task)
            self.bot_task_map[user_id] = new_task 
            
            # Update database
            await set_bot_active_status(user_id, True)
            
            logger.info(f"Successfully activated bot {user_id}")
            
            return web.json_response({
                "status": "success",
                "user_id": user_id,
                "message": f"Bot {user_id} is now active."
            }, status=200)
            
        except Exception as e:
            logger.error(f"Bot activation error: {e}", exc_info=True)
            return web.json_response({"error": f"Failed to activate bot: {e}"}, status=500)
        
    # Deactivates a bot by username
    async def handle_deactivate_bot(self, request):
        try:
            data = await request.json()
            username = data.get('username')
            
            if not username:
                return web.json_response({"error": "username is required"}, status=400)
                
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        try:
            user_id = username
            
            # Get the authenticated user_id from auth_middleware
            authenticated_user_id = request.get('authenticated_user_id')
            
            # Verify the authenticated user matches the requested bot to deactivate
            if authenticated_user_id != user_id:
                return web.json_response({"error": "Bearer token does not match the requested bot"}, status=401)
            
            # Get bot config from database
            bot_config = await get_bot_by_user_id(user_id)
            if not bot_config:
                return web.json_response({"error": f"Bot with user_id '{username}' not found"}, status=404)
            
            # Check if already inactive
            if not bot_config['active']:
                return web.json_response({"error": f"Bot '{username}' is already inactive"}, status=409)
            
            # Check if bot instance exists
            if user_id not in self.bots:
                # Bot is marked as active in DB but not running - fix the inconsistency
                await set_bot_active_status(user_id, False)
                return web.json_response({"error": f"Bot '{username}' was not running (status corrected)"}, status=404)
            
            # Cancel the specific bot task
            if user_id in self.bot_task_map:
                task = self.bot_task_map[user_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # Remove from task tracking
                del self.bot_task_map[user_id]
                
                # Remove from task list
                if task in self.bot_tasks:
                    self.bot_tasks.remove(task)
            
            # Remove the bot from active bots
            del self.bots[user_id]
            
            # Update database
            await set_bot_active_status(user_id, False)
            
            logger.info(f"Successfully deactivated bot{user_id}")
            
            return web.json_response({
                "status": "success",
                "user_id": user_id,
                "message": f"Bot '{user_id}' is now inactive."
            }, status=200)
            
        except Exception as e:
            logger.error(f"Bot deactivation error: {e}", exc_info=True)
            return web.json_response({"error": f"Failed to deactivate bot: {e}"}, status=500)

    async def run(self, host='0.0.0.0', port=8080):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"WebServer started on http://{host}:{port}")
        
        await asyncio.Event().wait()