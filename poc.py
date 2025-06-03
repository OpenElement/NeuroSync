# Proof of Concept for Matrix Webhook Bot
# This script connects to a Matrix bot and provides a webhook interface to send and receive messages.
# It requires a shared secret for authentication and uses aiohttp for the web server.

# Import necessary libraries
import os
import asyncio
from aiohttp import web
from nio import AsyncClient, RoomMessageText, InviteMemberEvent
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define the Matrix Webhook Bot class
class MatrixWebhookBot:
    def __init__(self):

        # Initialize the Matrix client with environment variables
        self.client = AsyncClient(
            os.getenv("MATRIX_HOMESERVER"),
            os.getenv("MATRIX_USER_ID")
        )
        self.client.access_token = os.getenv("MATRIX_ACCESS_TOKEN")
        self.room_id = os.getenv("ROOM_ID")
        self.message_queue = asyncio.Queue()
        self.webhook_secret = os.getenv("WEBHOOK_SECRET")  
        self.web_app = self.setup_web_app()

    # Authentication middleware for aiohttp
    @web.middleware
    async def auth_middleware(self, request, handler):
        """Require Authorization header for ALL endpoints"""
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != f"Bearer {self.webhook_secret}":
            # If the Authorization header is missing or incorrect, return 401 Unauthorized
            return web.json_response(
                {"error": "Unauthorized"},
                status=401
            )
        return await handler(request)

    async def start(self):

        # Register Matrix event callbacks
        self.client.add_event_callback(self.message_callback, RoomMessageText)
        self.client.add_event_callback(self.invite_callback, InviteMemberEvent)
        
        # Start HTTP server
        runner = web.AppRunner(self.web_app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        print("HTTP server running at http://localhost:8080")

        # Start Matrix sync in background
        asyncio.create_task(self.client.sync_forever(timeout=30000))

    # Setup the aiohttp web application with routes and middleware
    def setup_web_app(self):
        """Apply auth middleware to ALL routes"""
        app = web.Application(middlewares=[self.auth_middleware])
        app.add_routes([
            web.post('/send', self.handle_send),
            web.get('/receive', self.handle_receive),
            web.post('/receive', self.handle_receive)
        ])
        return app

    # --- Matrix Event Handlers ---
    async def message_callback(self, room, event):
        if event.sender != self.client.user_id:
            await self.message_queue.put({
                "room_id": room.room_id,
                "sender": event.sender,
                "message": event.body,
                "timestamp": event.server_timestamp
            })

    async def invite_callback(self, room, event):
        if event.state_key == self.client.user_id:
            await self.client.join(room.room_id)
            print(f"Joined new room: {room.room_id}")

    # --- HTTP Endpoints ---
    # Handle sending messages to a room
    async def handle_send(self, request):
        try:
            data = await request.json()
            await self.client.room_send(
                room_id=data.get('room_id', self.room_id),
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": data['message']}
            )
            return web.json_response({"status": "success"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    # Handle receiving messages from the queue 
    async def handle_receive(self, request):
        try:
            timeout = float(request.query.get('timeout', 1.0))
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=timeout
                )
                return web.json_response(message)
            except asyncio.TimeoutError:
                return web.json_response({"status": "no_messages"}, status=204)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

if __name__ == "__main__":
    bot = MatrixWebhookBot()
    asyncio.get_event_loop().run_until_complete(bot.start())
    asyncio.get_event_loop().run_forever()