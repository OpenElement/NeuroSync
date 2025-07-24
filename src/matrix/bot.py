import asyncio
import logging
import time
from typing import TypedDict
import simplematrixbotlib as botlib

logger = logging.getLogger(__name__)

# A structured dictionary for messages passed to the queue.
class MatrixMessage(TypedDict):
    collector_bot: str
    room_id: str
    sender: str
    message: str
    timestamp: int

# Manages a simplematrixbotlib bot instance and its events.
class MatrixBot:
    def __init__(self, homeserver: str, user_id: str, password: str, store_path: str, message_queue: asyncio.Queue):
        self.user_id = user_id
        self.message_queue = message_queue
        self.start_time = time.time()
        
        creds = botlib.Creds(homeserver, user_id, password)
        config = botlib.Config()
        config.encryption_enabled = True
        config.store_path = store_path
        config.join_on_invite = True
        
        self.bot = botlib.Bot(creds, config)
        self._register_callbacks()

    # Registers event listeners for the bot.
    def _register_callbacks(self):
        self.bot.listener.on_startup(self.on_startup)
        self.bot.listener.on_message_event(self.on_message)

    async def on_startup(self, room_id: str):
        logger.info(f"Bot '{self.user_id}' started successfully in room: {room_id}")

    # Puts incoming messages into the shared queue.
    async def on_message(self, room, event):
        if event.sender == self.user_id:
            return
        
        message: MatrixMessage = {
            "collector_bot": self.user_id,
            "room_id": room.room_id,
            "sender": event.sender,
            "message": event.body,
            "timestamp": event.server_timestamp
        }
        await self.message_queue.put(message)
        logger.info(f"Queued message from {event.sender} in room {room.room_id}")

    # Sends a message to a specified room.
    async def send_message(self, room_id: str, message: str):
        await self.bot.api.send_text_message(room_id, message)
    
    # Gets the uptime of the bot in seconds.
    def get_uptime(self) -> float:
        return time.time() - self.start_time

    # Starts the bot's main loop.    
    async def run(self):
        await self.bot.main()