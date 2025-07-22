import asyncio
import logging
from aiohttp import web
from .config import Config
from .matrix_bot import MatrixBot
from .synapse_client import SynapseAdminClient
from .handlers import RequestHandlers
from .database import get_all_bots

logger = logging.getLogger(__name__)

class WebServer:
    def __init__(self, config: Config, bots: dict[str, MatrixBot], bot_tasks: list, synapse_client: SynapseAdminClient, message_queue: asyncio.Queue):
        self.config = config
        self.bots = bots
        self.bot_tasks = bot_tasks
        self.bot_task_map = {} 
        self.synapse_client = synapse_client
        self.message_queue = message_queue
        
        # Create handlers instance
        self.handlers = RequestHandlers(
            config=config,
            bots=bots,
            bot_tasks=bot_tasks,
            bot_task_map=self.bot_task_map,
            synapse_client=synapse_client,
            message_queue=message_queue
        )
        
        self.app = web.Application(middlewares=[self.auth_middleware])
        self._setup_routes()

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

    def _setup_routes(self):
        self.app.add_routes([
            web.post('/msg/send', self.handlers.handle_send),
            web.get('/msg/receive', self.handlers.handle_receive),
            web.post('/msg/receive', self.handlers.handle_receive),
            web.post('/user/create', self.handlers.handle_create_user),
            web.post('/bot/create', self.handlers.handle_create_bot),
            web.post('/bot/activate', self.handlers.handle_activate_bot),
            web.post('/bot/deactivate', self.handlers.handle_deactivate_bot),
        ])

    async def run(self, host='0.0.0.0', port=8080):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"WebServer started on http://{host}:{port}")
        
        await asyncio.Event().wait()