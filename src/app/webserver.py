import asyncio
from aiohttp import web
from nio import AsyncClient

from app import config
from hooks import messaging, accounts

class NeuroSync:
    def __init__(self):
        self.config = config # Store config for easy access
        self.client = AsyncClient(
            self.config.MATRIX_HOMESERVER,
            self.config.MATRIX_USER_ID
        )
        self.client.access_token = self.config.MATRIX_ACCESS_TOKEN
        self.message_queue = asyncio.Queue()
        self.webhook_secret = self.config.WEBHOOK_SECRET
        self.web_app = None # Will be initialized in start()
        self.sync_task = None

    @web.middleware
    # Require Authorization header for ALL endpoints.
    async def auth_middleware(self, request, handler):
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != f"Bearer {self.webhook_secret}":
            return web.json_response(
                {"error": "Unauthorized"},
                status=401
            )
        return await handler(request)

    def setup_web_app(self):
        # Sets up the aiohttp web application, applies middleware, and registers all hooks.
        app = web.Application(middlewares=[self.auth_middleware])
        
        # Register hooks from modules
        messaging.register_messaging_hooks(self, app)
        accounts.register_account_hooks(self, app)
        
        return app

    async def start(self):
        # Starts the Matrix client sync and the HTTP web server.
        print("Starting NeuroSync...")
        
        # Setup web application
        self.web_app = self.setup_web_app()

        # Start HTTP server
        runner = web.AppRunner(self.web_app)
        await runner.setup()
        site = web.TCPSite(runner, self.config.HOST, self.config.PORT)
        await site.start()
        print(f"HTTP server running at http://{self.config.HOST}:{self.config.PORT}")
        self.sync_task = asyncio.create_task(self.client.sync_forever(timeout=30000, full_state=True))
    
    # Gracefully stops the bot and cleans up resources.
    async def stop(self):

        if self.sync_task:
            if not self.sync_task.done():
                self.sync_task.cancel()
            else:
                # If task is already done, check for exceptions
                if self.sync_task.exception():
                    print(f"Sync task finished with exception: {self.sync_task.exception()}")
        
        if self.client:
            await self.client.close()
