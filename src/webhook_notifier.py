import asyncio
import json
import logging
import aiohttp
from typing import Dict

logger = logging.getLogger(__name__)


class WebhookNotifier:
    def __init__(self):
        self.session = None
        
    async def initialize(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10.0)
            )
    
    async def cleanup(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def notify_webhook(self, webhook_url: str, message_data: Dict):
        if not self.session:
            await self.initialize()
            
        try:
            # Prepare the webhook payload
            payload = {
                "event": "message_received",
                "data": {
                    "collector_bot": message_data.get("collector_bot"),
                    "room_id": message_data.get("room_id"),
                    "sender": message_data.get("sender"),
                    "message": message_data.get("message"),
                    "timestamp": message_data.get("timestamp")
                }
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            async with self.session.post(webhook_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent webhook notification to {webhook_url}")
                else:
                    response_text = await response.text()
                    logger.warning(f"Webhook notification failed to {webhook_url}: {response.status} - {response_text}")
                    
        except asyncio.TimeoutError:
            logger.warning(f"Webhook notification timeout to {webhook_url}")
        except Exception as e:
            logger.error(f"Error sending webhook notification to {webhook_url}: {e}")
    
    async def notify_registered_webhooks(self, webhook_registrations: Dict[str, str], message_data: Dict):
        collector_bot = message_data.get("collector_bot")
        
        if collector_bot and collector_bot in webhook_registrations:
            webhook_url = webhook_registrations[collector_bot]
            await self.notify_webhook(webhook_url, message_data)
