# Proof of Concept for Matrix Websocket Bridge Bot

# Imports
import os
import asyncio
import json
from aiohttp import web, WSMsgType  # aiohttp provides HTTP and WebSocket handling
from nio import AsyncClient, RoomMessageText, InviteMemberEvent  # Matrix client events
from dotenv import load_dotenv  

# Load environment variables
load_dotenv()

# Define the main bot class
class MatrixBridgeBot:
    def __init__(self):
        # Create a Matrix client using environment variables
        self.client = AsyncClient(
            os.getenv("MATRIX_HOMESERVER"),
            os.getenv("MATRIX_USER_ID")
        )
        self.client.access_token = os.getenv("MATRIX_ACCESS_TOKEN")
        self.room_id = os.getenv("ROOM_ID")
        self.secret = os.getenv("WEBHOOK_SECRET")

        # WebSocket client connection
        self.ws_client = None

        # Set up the aiohttp web server
        self.app = self.setup_app()

    # Middleware to enforce token-based authentication
    @web.middleware
    async def auth(self, request, handler):
        token = request.headers.get("Authorization")
        if not token or token != f"Bearer {self.secret}":
            return web.Response(text="Unauthorized", status=401)
        return await handler(request)

    # Configure the web server application
    def setup_app(self):
        app = web.Application(middlewares=[self.auth])
        app.add_routes([web.get("/ws", self.ws_handler)])  # Define WebSocket route
        return app

    # Start the bot and WebSocket server
    async def start(self):
        # Register Matrix message and invite event handlers
        self.client.add_event_callback(self.on_message, RoomMessageText)
        self.client.add_event_callback(self.on_invite, InviteMemberEvent)

        # Start the aiohttp web server on port 8080
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        print("WebSocket bridge server listening on ws://localhost:8080/ws")

        # Start Matrix sync loop in the background
        asyncio.create_task(self.client.sync_forever(timeout=30000))

    # Handle incoming messages from Matrix
    async def on_message(self, room, event):
        # Ignore messages sent by the bot itself and only process if a client is connected
        if event.sender != self.client.user_id and self.ws_client:
            message = {
                "type": "matrix_message",
                "room_id": room.room_id,
                "sender": event.sender,
                "message": event.body,
                "timestamp": event.server_timestamp
            }
            try:
                # Forward the message to the connected WebSocket client
                await self.ws_client.send_json(message)
            except Exception as e:
                print("Failed to forward to chatbot:", e)

    # Handle room invite events
    async def on_invite(self, room, event):
        # Auto-join any room the bot is invited to
        if event.state_key == self.client.user_id:
            await self.client.join(room.room_id)
            print(f"Joined invited room: {room.room_id}")

    # Handle WebSocket connections from the chatbot
    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)  # Upgrade HTTP request to WebSocket

        self.ws_client = ws  # Store the connected WebSocket client
        print("Chatbot connected via WebSocket.")

        # Notify client that the connection was successful
        await ws.send_json({"type": "status", "message": "Connected to Matrix bridge"})

        try:
            # Process incoming WebSocket messages from the chatbot
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if data.get("type") == "send":
                            # Relay chatbot message to Matrix room
                            await self.client.room_send(
                                room_id=data.get("room_id", self.room_id),
                                message_type="m.room.message",
                                content={"msgtype": "m.text", "body": data["message"]}
                            )
                        else:
                            # Unknown message types are responded to with an error
                            await ws.send_json({"type": "error", "message": "Unknown message type"})
                    except Exception as e:
                        # Catch and send JSON errors to the chatbot
                        await ws.send_json({"type": "error", "message": str(e)})
                elif msg.type == WSMsgType.ERROR:
                    print("WebSocket error:", ws.exception())
        finally:
            # Cleanup if the chatbot disconnects
            print("Chatbot disconnected.")
            self.ws_client = None

        return ws  # Return the WebSocket connection object

    # Gracefully close the Matrix client on shutdown
    async def stop(self):
        print("Shutting down...")
        await self.client.close()

# Run the bot when executed directly
if __name__ == "__main__":
    async def main():
        bot = MatrixBridgeBot()
        try:
            await bot.start()
            while True:
                await asyncio.sleep(3600)  # Keep running indefinitely
        except KeyboardInterrupt:
            print("Interrupted by user.")
        finally:
            await bot.stop()

    asyncio.run(main())
