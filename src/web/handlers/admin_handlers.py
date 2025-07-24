import logging
import secrets
import string
from aiohttp import web
from typing import Callable
from src.config.app_config import add_bot, update_bot_webhook_secret, delete_bot, update_synapse_admin_token
from src.matrix.synapse_client import SynapseAdminClient

logger = logging.getLogger(__name__)

# Handles administrative API endpoints.
class AdminHandlers:
    def __init__(self, synapse_client: SynapseAdminClient, token_cache_update_callback: Callable, bots_state: dict = None, synapse_client_update_callback: Callable = None):
        self.synapse_client = synapse_client
        self.update_token_cache = token_cache_update_callback
        self.update_synapse_client = synapse_client_update_callback
        self.bots_state = bots_state or {'instances': {}, 'tasks': {}}

    def _generate_secure_string(self, length=24):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    # Handles creating a new user in Synapse.
    async def handle_create_user(self, request: web.Request):
        if not self.synapse_client:
            return web.json_response({"error": "Synapse Admin Client not configured"}, status=501)
            
        try:
            data = await request.json()
            username, password = data.get('username'), data.get('password')
            if not all([username, password]):
                return web.json_response({"error": "username and password are required"}, status=400)
            
            user = await self.synapse_client.create_user(
                username, password, data.get('display_name'), data.get('recovery_email')
            )
            return web.json_response({"status": "success"}, status=201)
        except Exception as e:
            logger.error(f"User creation error: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=400)
        
    # Handels deleting a user in Synapse.
    async def handle_delete_user(self, request: web.Request):
        if not self.synapse_client:
            return web.json_response({"error": "Synapse Admin Client not configured"}, status=501)
            
        try:
            data = await request.json()
            username = data.get('username')
            if not username:
                return web.json_response({"error": "username is required"}, status=400)
            
            await self.synapse_client.delete_user(username)
            return web.json_response({"status": "success"}, status=200)
        except Exception as e:
            logger.error(f"User deletion error: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=400)

    # Handles creating a bot user and saving it to the database.
    async def handle_create_bot(self, request: web.Request):
        if not self.synapse_client:
            return web.json_response({"error": "Synapse Admin Client not configured"}, status=501)

        try:
            data = await request.json()
            username = data.get('username')
            webhook_secret = data.get('token')
            if not username or not webhook_secret:
                return web.json_response({"error": "username and token are required"}, status=400)
        except Exception:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        password = self._generate_secure_string(32)

        try:
            user = await self.synapse_client.create_user(username, password, displayname=username)
            user_id = user.get('name')
            logger.info(f"Successfully created bot user '{user_id}' in Synapse.")

            store_path = f"./crypto_store/{username}/"
            await add_bot(user_id, password, store_path, webhook_secret)
            
            # Update the auth middleware's token cache
            self.update_token_cache(webhook_secret, user_id)

            logger.info(f"Successfully created bot '{user_id}'.")
            return web.json_response({"status": "success"}, status=201)
        except Exception as e:
            logger.error(f"Bot creation error: {e}", exc_info=True)
            return web.json_response({"error": f"An unexpected error occurred: {e}"}, status=500)
    
    # Handles deleating a bot user and removing it from the database.
    async def handle_delete_bot(self, request: web.Request):
        if not self.synapse_client:
            return web.json_response({"error": "Synapse Admin Client not configured"}, status=501)

        try:
            data = await request.json()
            username = data.get('username')
            if not username:
                return web.json_response({"error": "username is required"}, status=400)
        except Exception:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)
        
        # If the bot is active, deactivate it first
        if username in self.bots_state['instances']:
            try:
                task = self.bots_state['tasks'].pop(username, None)
                if task and not task.done():
                    task.cancel()
                del self.bots_state['instances'][username]
                logger.info(f"Deactivated bot '{username}' before deletion.")
            except Exception as e:
                logger.error(f"Failed to deactivate bot '{username}': {e}")
                return web.json_response({"error": f"Failed to deactivate bot: {e}"}, status=500)

        try:
            # Remove the bot from synapse
            await self.synapse_client.delete_user(username)
            # Remove the bot from the database
            await delete_bot(username)
            logger.info(f"Successfully deleted bot '{username}'.")
            return web.json_response({"status": "success"}, status=200)
        except Exception as e:
            logger.error(f"Bot deletion error: {e}", exc_info=True)
            return web.json_response({"error": f"An unexpected error occurred: {e}"}, status=500)
        
    # Handles updating the bot's webhook secret.
    async def handle_update_bot_ws(self, request: web.Request):
        if not self.synapse_client:
            return web.json_response({"error": "Synapse Admin Client not configured"}, status=501)
        
        try:
            data = await request.json()
            username = data.get('username')
            webhook_secret = data.get('token')
            if not username or not webhook_secret:
                return web.json_response({"error": "username and token are required"}, status=400)
        except Exception:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)
        
        try:
            # Update the bot's webhook secret in the database
            await update_bot_webhook_secret(username, webhook_secret)
            
            # Update the auth middleware's token cache
            self.update_token_cache(webhook_secret, username)

            logger.info(f"Successfully updated token for bot '{username}'.")
            return web.json_response({"status": "success"}, status=200)

        except Exception as e:
            logger.error(f"Error updating bot token: {e}", exc_info=True)
            return web.json_response({"error": f"An unexpected error occurred: {e}"}, status=500)

    # Handles setting the Synapse admin token
    async def handle_set_synapse_admin_token(self, request: web.Request):
        if not self.synapse_client:
            return web.json_response({"error": "Synapse Admin Client not configured"}, status=501)
        
        try:
            data = await request.json()
            token = data.get('token')
            if not token:
                return web.json_response({"error": "token is required"}, status=400)
        except Exception:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)
        
        try:
            # Update the token in .env file
            update_synapse_admin_token(token)
            
            # Create new Synapse client
            if self.update_synapse_client:
                await self.update_synapse_client(token)
                logger.info("Successfully updated Synapse admin token")
                return web.json_response({"status": "success"}, status=200)
            else:
                return web.json_response({"error": "Synapse client update callback not configured"}, status=500)
        
        except Exception as e:
            logger.error(f"Error setting Synapse admin token: {e}", exc_info=True)
            return web.json_response({"error": f"An unexpected error occurred: {e}"}, status=500)