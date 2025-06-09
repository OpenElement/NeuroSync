# Proof of Concept for Matrix Webhook Bot
# This script connects to a Matrix bot and provides a webhook interface to send and receive messages.
# It requires a shared secret for authentication and uses aiohttp for the web server.

# Import necessary libraries
import os
import asyncio, json # Added json for specific exception handling
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
        # self.room_id is no longer loaded from .env; it will be passed in requests.
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
            web.post('/msg/send', self.handle_send),
            web.get('/msg/receive', self.handle_receive),
            web.post('/msg/receive', self.handle_receive)
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
            try:
                data = await request.json()
            except json.JSONDecodeError:
                return web.json_response({"error": "Invalid JSON payload"}, status=400)

            room_id = data.get('room_id')
            message_body = data.get('message')

            if not room_id:
                return web.json_response({"error": "room_id is required in payload"}, status=400)
            if message_body is None: # Allow empty string, but not missing key
                return web.json_response({"error": "message is required in payload"}, status=400)

            await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": message_body}
            )
            return web.json_response({"status": "success"})
        except Exception as e:
            # General errors (e.g., Matrix communication failure) should be 500
            print(f"Error in handle_send: {e}")
            return web.json_response({"error": "Failed to send message"}, status=500)

    # Handle receiving messages from the queue 
    async def handle_receive(self, request):
        desired_room_id = None
        timeout_val = 1.0  # Default timeout

        try:
            if request.method == 'POST':
                try:
                    data = await request.json()
                    desired_room_id = data.get('room_id')
                    timeout_val = float(data.get('timeout', timeout_val))
                except json.JSONDecodeError:
                    return web.json_response({"error": "Invalid JSON payload"}, status=400)
                except ValueError:
                    return web.json_response({"error": "Invalid timeout value in payload"}, status=400)
            elif request.method == 'GET':
                desired_room_id = request.query.get('room_id')
                try:
                    timeout_val = float(request.query.get('timeout', str(timeout_val)))
                except ValueError:
                    return web.json_response({"error": "Invalid timeout value in query"}, status=400)

            if not desired_room_id:
                return web.json_response({"error": "room_id is required"}, status=400)

            start_time = asyncio.get_event_loop().time()
            local_deferred_messages = []

            try:
                while True:
                    current_loop_time = asyncio.get_event_loop().time()
                    elapsed_time = current_loop_time - start_time
                    if elapsed_time >= timeout_val:
                        break 

                    remaining_time_for_get = max(0.01, timeout_val - elapsed_time) # Ensure small positive timeout

                    try:
                        message = await asyncio.wait_for(
                            self.message_queue.get(),
                            timeout=remaining_time_for_get
                        )
                        if message.get("room_id") == desired_room_id:
                            for m_deferred in local_deferred_messages:
                                await self.message_queue.put(m_deferred)
                            return web.json_response(message)
                        else:
                            local_deferred_messages.append(message)
                    except asyncio.TimeoutError:
                        break 
                
                for m_deferred in local_deferred_messages:
                    await self.message_queue.put(m_deferred)
                return web.json_response({"status": "no_messages_for_room_or_timeout", "room_id": desired_room_id}, status=204)
            
            except Exception as e_inner: # Catch errors during the get/filter loop
                for m_deferred in local_deferred_messages: # Ensure cleanup
                    await self.message_queue.put(m_deferred)
                raise e_inner # Re-raise to be caught by outer handler

        except Exception as e:
            print(f"Error in handle_receive: {e}")
            return web.json_response({"error": str(e)}, status=500)

if __name__ == "__main__":
    bot = MatrixWebhookBot()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(bot.start())
        loop.run_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if 'bot' in locals() and hasattr(bot, 'client') and bot.client:
            # Gracefully close the Matrix client connection
            print("Closing Matrix client connection...")
            loop.run_until_complete(bot.client.close())
        
        # Standard asyncio cleanup from Python 3.7+ examples
        tasks = [t for t in asyncio.all_tasks(loop=loop) if t is not asyncio.current_task(loop=loop)]
        if tasks:
            print(f"Cancelling {len(tasks)} outstanding tasks...")
            for task in tasks:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        
        print("Closing event loop...")
        loop.close()
        print("Shutdown complete.")