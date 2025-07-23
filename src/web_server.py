import asyncio
import logging
from aiohttp import web
from .config import Config
from .matrix_bot import MatrixBot
from .synapse_client import SynapseAdminClient
from .handlers import RequestHandlers
from .database import get_all_bots
from .webhook_notifier import WebhookNotifier

logger = logging.getLogger(__name__)

class WebServer:
    def __init__(self, config: Config, bots: dict[str, MatrixBot], bot_tasks: list, synapse_client: SynapseAdminClient, message_queue: asyncio.Queue):
        self.config = config
        self.bots = bots
        self.bot_tasks = bot_tasks
        self.bot_task_map = {} 
        self.synapse_client = synapse_client
        self.message_queue = message_queue
        
        # Initialize webhook notifier
        self.webhook_notifier = WebhookNotifier()
        
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
        
        # Start the message processor task
        self._message_processor_task = None

    @web.middleware
    async def auth_middleware(self, request, handler):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return web.json_response({"error": "Unauthorized"}, status=401)
        
        token = auth_header.replace("Bearer ", "")
        path = request.path
        
        # Admin endpoints - check admin token
        admin_endpoints = ['/user/create', '/bot/create']
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
            web.post('/msg/register', self.handlers.handle_register_webhook),
            web.post('/msg/unregister', self.handlers.handle_unregister_webhook),
            web.post('/user/create', self.handlers.handle_create_user),
            web.post('/bot/create', self.handlers.handle_create_bot),
            web.post('/bot/activate', self.handlers.handle_activate_bot),
            web.post('/bot/deactivate', self.handlers.handle_deactivate_bot),
        ])

    # Process messages from the queue and trigger webhook notifications
    async def _process_messages_for_webhooks(self):
        await self.webhook_notifier.initialize()
        processed_messages = set()  # Track processed messages to avoid duplicates
        
        while True:
            try:
                # Check if there are any webhook registrations
                if not self.handlers.webhook_registrations:
                    await asyncio.sleep(1)
                    continue
                
                # Process messages from the queue
                current_queue_size = self.message_queue.qsize()
                messages_processed = 0
                
                # Process a limited number of messages to avoid blocking
                while messages_processed < current_queue_size and messages_processed < 10:
                    try:
                        message = await asyncio.wait_for(self.message_queue.get(), timeout=0.1)
                        
                        # Create a unique identifier for this message
                        message_id = f"{message.get('sender', '')}-{message.get('room_id', '')}-{message.get('timestamp', '')}-{message.get('message', '')[:50]}"
                        
                        # Only process if we haven't seen this message before
                        if message_id not in processed_messages:
                            await self.webhook_notifier.notify_registered_webhooks(
                                self.handlers.webhook_registrations, 
                                message
                            )
                            processed_messages.add(message_id)
                            
                            # Limit the size of processed_messages set to prevent memory issues
                            if len(processed_messages) > 1000:
                                # Remove oldest entries (this is approximate)
                                processed_messages = set(list(processed_messages)[500:])
                        
                        # Put the message back in the queue for other consumers
                        await self.message_queue.put(message)
                        messages_processed += 1
                        
                    except asyncio.TimeoutError:
                        break
                    except asyncio.QueueEmpty:
                        break
                
                # Wait before processing again
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in webhook message processor: {e}")
                await asyncio.sleep(1)

    async def run(self, host='0.0.0.0', port=8080):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"WebServer started on http://{host}:{port}")
        
        # Start the message processor for webhooks
        self._message_processor_task = asyncio.create_task(self._process_messages_for_webhooks())
        
        try:
            await asyncio.Event().wait()
        finally:
            # Clean up
            if self._message_processor_task:
                self._message_processor_task.cancel()
            await self.webhook_notifier.cleanup()