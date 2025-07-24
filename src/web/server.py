import asyncio
import logging
from aiohttp import web, ClientSession
from src.config.app_config import Config
from src.matrix.synapse_client import SynapseAdminClient
from src.web.message_dispatcher import MessageDispatcher
from src.web.handlers.admin_handlers import AdminHandlers
from src.web.handlers.message_handlers import MessageHandlers

logger = logging.getLogger(__name__)

# Manages the aiohttp web application, routes, and state.
class WebServer:
    def __init__(self, config: Config, message_dispatcher: MessageDispatcher, synapse_client: SynapseAdminClient, initial_bot_tokens: dict):
        self.config = config
        self.bot_tokens = initial_bot_tokens
        self.bots_state = {'instances': {}, 'tasks': {}}
        
        self.app = web.Application(middlewares=[self.auth_middleware])
        self.http_session = None
        
        # Instantiate handlers
        admin_handlers = AdminHandlers(synapse_client, self.add_bot_token, self.bots_state)
        self.message_handlers = MessageHandlers(config, message_dispatcher, self.bots_state, None)
        
        self._setup_routes(admin_handlers, self.message_handlers)

    # Callback to update the in-memory token cache when a bot is created.
    def add_bot_token(self, token: str, user_id: str):
        self.bot_tokens[token] = user_id
        logger.info(f"Updated auth token cache for user {user_id}")

    # Efficiently authenticates requests using an in-memory token cache.
    @web.middleware
    async def auth_middleware(self, request: web.Request, handler):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return web.json_response({"error": "Authorization header missing or invalid"}, status=401)
        
        token = auth_header.split(" ")[1]
        
        # Admin endpoints check the global admin token.
        if request.path in ['/user/create', '/bot/create', '/user/delete', '/bot/auth', '/bot/delete']:
            if self.config.admin_token and token == self.config.admin_token:
                return await handler(request)
            return web.json_response({"error": "Unauthorized: Invalid admin token"}, status=401)
        
        # Bot-specific endpoints check the cached bot tokens.
        user_id = self.bot_tokens.get(token)
        if user_id:
            request['authenticated_user_id'] = user_id
            return await handler(request)
            
        return web.json_response({"error": "Unauthorized: Invalid bot token"}, status=401)

    def _setup_routes(self, admin_handlers: AdminHandlers, msg_handlers: MessageHandlers):
        self.app.add_routes([
            web.post('/user/create', admin_handlers.handle_create_user),
            web.post('/user/delete', admin_handlers.handle_delete_user),
            web.post('/bot/create', admin_handlers.handle_create_bot),
            web.post('/bot/delete', admin_handlers.handle_delete_bot),
            web.post('/bot/auth', admin_handlers.handle_update_bot_ws),
            web.post('/msg/send', msg_handlers.handle_send),
            web.get('/msg/receive', msg_handlers.handle_receive),
            web.post('/bot/activate', msg_handlers.handle_activate_bot),
            web.post('/bot/deactivate', msg_handlers.handle_deactivate_bot),
            web.post('/bot/status', msg_handlers.handle_bot_status),
            web.post('/webhook/register', msg_handlers.handle_register_webhook),
            web.post('/webhook/unregister', msg_handlers.handle_unregister_webhook),

        ])

    # Starts the web server and associated background tasks.
    async def run(self, host='0.0.0.0', port=8080):
        self.http_session = ClientSession()
        self.message_handlers.http_session = self.http_session

        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"WebServer started on http://{host}:{port}")

        # Start the background worker for sending webhook notifications.
        webhook_worker_task = asyncio.create_task(self.message_handlers.webhook_notification_worker())

        try:
            # Keep the server running indefinitely.
            await asyncio.Event().wait()
        finally:
            logger.info("Shutting down WebServer...")
            webhook_worker_task.cancel()
            await self.http_session.close()
            await runner.cleanup()