# src/web_server.py
import asyncio
import json
import logging
import secrets  # New import for password generation
import string   # New import for password generation
import os       # New import for file path handling
from aiohttp import web
from .config import Config
from .matrix_bot import MatrixBot
from .synapse_client import SynapseAdminClient

logger = logging.getLogger(__name__)

class WebServer:
    def __init__(self, config: Config, bots: dict[str, MatrixBot], synapse_client: SynapseAdminClient, message_queue: asyncio.Queue):
        self.config = config
        self.bots = bots
        self.synapse_client = synapse_client
        self.message_queue = message_queue
        self.app = web.Application(middlewares=[self.auth_middleware])
        # Add a lock to safely handle file writing
        self.env_lock = asyncio.Lock()
        self.env_path = '.env'  # Define path to your .env file
        self._setup_routes()

    def _setup_routes(self):
        self.app.add_routes([
            web.post('/msg/send', self.handle_send),
            web.get('/msg/receive', self.handle_receive),
            web.post('/msg/receive', self.handle_receive),
            web.post('/create/user', self.handle_create_user),
            web.post('/create/bot', self.handle_create_bot),  # New route
        ])

    def _generate_secure_password(self, length=24):
        """Generates a secure password suitable for .env files."""
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        return password

    @web.middleware
    # (auth_middleware remains the same)
    async def auth_middleware(self, request, handler):
        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {self.config.webhook_secret}":
            return web.json_response({"error": "Unauthorized"}, status=401)
        return await handler(request)

    # (handle_send, handle_receive, handle_create_user remain the same)
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
        """Creates a bot user, generates a password, and updates the .env file."""
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
            # Step 1: Create the user in Synapse
            user = await self.synapse_client.create_user(username, password, displayname=username)
            user_id = user.get('name')
            logger.info(f"Successfully created bot user '{user_id}' in Synapse.")

            # Step 2: Safely update the .env file using a lock
            async with self.env_lock:
                if os.path.exists(self.env_path):
                    with open(self.env_path, 'r') as f:
                        lines = f.readlines()
                else:
                    lines = []

                num_bots = 0
                output_lines = []
                num_bots_line_found = False

                # Find and update NUM_BOTS
                for line in lines:
                    if line.strip().startswith('NUM_BOTS'):
                        num_bots_line_found = True
                        try:
                            num_bots = int(line.strip().split('=')[1])
                            output_lines.append(f"NUM_BOTS={num_bots + 1}\n")
                        except (ValueError, IndexError):
                            output_lines.append(line) # Keep malformed line
                    else:
                        output_lines.append(line)
                
                # If NUM_BOTS was not in the file, add it
                if not num_bots_line_found:
                    output_lines.insert(0, f"NUM_BOTS=1\n")
                    new_bot_num = 1
                else:
                    new_bot_num = num_bots + 1
                
                # Append the new bot's credentials
                output_lines.append(f"\n# --- Bot {new_bot_num} Credentials ---\n")
                output_lines.append(f"MATRIX_USER_ID_{new_bot_num}={user_id}\n")
                output_lines.append(f"MATRIX_PASSWORD_{new_bot_num}={password}\n")
                output_lines.append(f"CRYPTO_STORE_PATH_{new_bot_num}=./crypto_store/bot_{new_bot_num}/\n")

                # Write the updated content back to the .env file
                with open(self.env_path, 'w') as f:
                    f.writelines(output_lines)

            logger.info(f"Successfully updated .env file for new bot '{user_id}'.")
            
            return web.json_response({
                "status": "success",
                "user_id": user_id,
                "password": password, # Return the generated password
                "message": "Bot created and .env file updated. You MUST restart the application for the new bot to become active."
            }, status=201)

        except Exception as e:
            logger.error(f"Bot creation error: {e}", exc_info=True)
            return web.json_response({"error": f"An unexpected error occurred: {e}"}, status=500)

    # (run method remains the same)
    async def run(self, host='0.0.0.0', port=8080):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"WebServer started on http://{host}:{port}")
        await asyncio.Event().wait()