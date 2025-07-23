import asyncio
import logging
from collections import deque

logger = logging.getLogger(__name__)

# Distributes messages from a single source queue to multiple subscribers.
class MessageDispatcher:
    def __init__(self):
        self.source_queue = asyncio.Queue()
        self._subscribers = set()

    # The main loop that consumes from the source and fans out to subscribers.
    async def run(self):
        logger.info("Message dispatcher started.")
        while True:
            try:
                message = await self.source_queue.get()
                if not self._subscribers:
                    continue
                
                # Create a list of subscribers to avoid issues with modification during iteration.
                current_subscribers = list(self._subscribers)
                for queue in current_subscribers:
                    queue.put_nowait(message)
                    
            except Exception as e:
                logger.error(f"Error in message dispatcher: {e}", exc_info=True)

    # Adds a new subscriber queue and returns it.
    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._subscribers.add(queue)
        logger.info(f"New subscriber added. Total: {len(self._subscribers)}")
        return queue
    
    # Removes a subscriber queue.
    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.discard(queue)
        logger.info(f"Subscriber removed. Total: {len(self._subscribers)}")