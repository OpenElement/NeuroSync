import asyncio
import logging
from aiohttp import web, ClientSession
from src.config.app_config import Config, get_bot_by_user_id
from src.matrix.bot import MatrixBot
from src.web.message_dispatcher import MessageDispatcher

logger = logging.getLogger(__name__)

# Handles message-related and bot-specific API endpoints.
class MessageHandlers:
    def __init__(self, config: Config, message_dispatcher: MessageDispatcher, bots_state: dict, http_session: ClientSession):
        self.config = config
        self.message_dispatcher = message_dispatcher
        self.bots = bots_state['instances']
        self.bot_tasks = bots_state['tasks']
        self.http_session = http_session
        self.webhook_registrations = {} 
    
    # Sends a message via a bot.
    async def handle_send(self, request: web.Request):
        data = await request.json()
        user_id, room_id, message = data.get('username'), data.get('room_id'), data.get('message')

        if not all([user_id, room_id, message]):
            return web.json_response({"error": "username, room_id, and message are required"}, status=400)
        
        bot = self.bots.get(user_id)
        if not bot:
            return web.json_response({"error": f"Bot '{user_id}' not found or not active."}, status=404)
        
        await bot.send_message(room_id, message)
        return web.json_response({"status": "success", "sender": user_id})

    # Receives messages for a room with long-polling.
    async def handle_receive(self, request: web.Request):
        params = request.query
        room_id = params.get('room_id')
        timeout = float(params.get('timeout', 10.0))
        
        if not room_id:
            return web.json_response({"error": "room_id is required"}, status=400)

        subscriber_queue = self.message_dispatcher.subscribe()
        try:
            async with asyncio.timeout(timeout):
                while True:
                    message = await subscriber_queue.get()
                    if room_id == "ALL" or message.get("room_id") == room_id:
                        return web.json_response(message)
        except asyncio.TimeoutError:
            return web.json_response({"status": "timeout"}, status=204)
        finally:
            self.message_dispatcher.unsubscribe(subscriber_queue)

    # Bot Activation/Deactivation
    async def handle_activate_bot(self, request: web.Request):
        user_id = request.get('authenticated_user_id')
        if user_id in self.bots:
            return web.json_response({"error": f"Bot '{user_id}' is already running."}, status=409)

        bot_config = await get_bot_by_user_id(user_id)
        if not bot_config:
            return web.json_response({"error": "Bot config not found in database."}, status=404)

        new_bot = MatrixBot(
            homeserver=self.config.matrix_homeserver,
            user_id=user_id,
            password=bot_config['password'],
            store_path=bot_config['store_path'],
            message_queue=self.message_dispatcher.source_queue
        )
        
        task = asyncio.create_task(new_bot.run())
        self.bots[user_id] = new_bot
        self.bot_tasks[user_id] = task
        
        logger.info(f"Successfully activated bot {user_id}")
        return web.json_response({"status": "success", "user_id": user_id}, status=200)

    async def handle_deactivate_bot(self, request: web.Request):
        user_id = request.get('authenticated_user_id')
        if user_id not in self.bots:
            return web.json_response({"error": f"Bot '{user_id}' was not running."}, status=404)
        
        task = self.bot_tasks.pop(user_id, None)
        if task and not task.done():
            task.cancel()
        del self.bots[user_id]
        
        logger.info(f"Successfully deactivated bot {user_id}")
        return web.json_response({"status": "success", "user_id": user_id}, status=200)

    # Webhook Endpoints
    async def handle_register_webhook(self, request: web.Request):
        user_id = request.get('authenticated_user_id')
        data = await request.json()
        webhook_url = data.get('webhook_url')

        if not webhook_url or not (webhook_url.startswith('http://') or webhook_url.startswith('https://')):
            return web.json_response({"error": "A valid webhook_url is required"}, status=400)

        self.webhook_registrations[user_id] = webhook_url
        logger.info(f"Registered webhook for bot '{user_id}': {webhook_url}")
        return web.json_response({"status": "success"}, status=200)

    async def handle_unregister_webhook(self, request: web.Request):
        user_id = request.get('authenticated_user_id')
        if user_id in self.webhook_registrations:
            del self.webhook_registrations[user_id]
            logger.info(f"Unregistered webhook for bot '{user_id}'")
            return web.json_response({"status": "success"}, status=200)
        return web.json_response({"error": "No webhook was registered for this bot"}, status=404)
    
    # Status Endpoint
    async def handle_bot_status(self, request: web.Request):
        user_id = request.get('authenticated_user_id')
        is_active = user_id in self.bots
        bot_instance = self.bots.get(user_id)
        
        return web.json_response({
            "user_id": user_id,
            "is_active": is_active,
            "uptime_seconds": bot_instance.get_uptime() if bot_instance else 0,
            "webhook_url": self.webhook_registrations.get(user_id),
            "source_queue_size": self.message_dispatcher.source_queue.qsize()
        }, status=200)

    # A worker task that sends notifications for registered webhooks.
    async def webhook_notification_worker(self):
        logger.info("Webhook notification worker started.")
        subscriber_queue = self.message_dispatcher.subscribe()
        try:
            while True:
                message = await subscriber_queue.get()
                collector_bot = message.get("collector_bot")
                
                if collector_bot in self.webhook_registrations:
                    webhook_url = self.webhook_registrations[collector_bot]
                    asyncio.create_task(self._send_notification(webhook_url, message))
        finally:
            self.message_dispatcher.unsubscribe(subscriber_queue)
            logger.info("Webhook notification worker stopped.")
            
    # Sends a single webhook POST request.
    async def _send_notification(self, url: str, message_data: dict):
        payload = {"event": "message_received", "data": message_data}
        try:
            async with self.http_session.post(url, json=payload, timeout=10) as response:
                if response.status >= 300:
                    logger.warning(f"Webhook to {url} failed with status {response.status}")
        except Exception as e:
            logger.error(f"Error sending webhook to {url}: {e}")