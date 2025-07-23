import logging
import secrets
import string
from aiohttp import web
from typing import Callable
from src.config.app_config import add_bot
from src.matrix.synapse_client import SynapseAdminClient

logger = logging.getLogger(__name__)

# Handles administrative API endpoints.
class AdminHandlers:
    def __init__(self, synapse_client: SynapseAdminClient, token_cache_update_callback: Callable):
        self.synapse_client = synapse_client
        self.update_token_cache = token_cache_update_callback

    def _generate_secure_string(self, length=24):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    # Handles creating a new user in Synapse.
    async def handle_create_user(self, request: web.Request):
        try:
            data = await request.json()
            username, password = data.get('username'), data.get('password')
            if not all([username, password]):
                return web.json_response({"error": "username and password are required"}, status=400)
            
            user = await self.synapse_client.create_user(
                username, password, data.get('display_name'), data.get('recovery_email')
            )
            return web.json_response({"status": "success", "user_id": user.get('name')}, status=201)
        except Exception as e:
            logger.error(f"User creation error: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=400)
        
    # Handles creating a bot user and saving it to the database.
    async def handle_create_bot(self, request: web.Request):
        if not self.synapse_client:
            return web.json_response({"error": "Synapse Admin Client not configured"}, status=501)

        try:
            data = await request.json()
            username = data.get('username')
            if not username:
                return web.json_response({"error": "username is required"}, status=400)
        except Exception:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        password = self._generate_secure_string(32)
        webhook_secret = self._generate_secure_string(48)
        
        try:
            user = await self.synapse_client.create_user(username, password, displayname=username)
            user_id = user.get('name')
            logger.info(f"Successfully created bot user '{user_id}' in Synapse.")

            store_path = f"./crypto_store/{username}/"
            await add_bot(user_id, password, store_path, webhook_secret)
            
            # Update the auth middleware's token cache
            self.update_token_cache(webhook_secret, user_id)

            logger.info(f"Successfully created bot '{user_id}'.")
            return web.json_response({
                "status": "success", "user_id": user_id, "webhook_secret": webhook_secret
            }, status=201)
        except Exception as e:
            logger.error(f"Bot creation error: {e}", exc_info=True)
            return web.json_response({"error": f"An unexpected error occurred: {e}"}, status=500)