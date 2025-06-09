from aiohttp import web

class WebServer:
    def __init__(self, webhook_secret):
        self.webhook_secret = webhook_secret
        self.app = web.Application(middlewares=[self._auth_middleware])
        self.runner = None
        self.site = None

    @web.middleware
    async def _auth_middleware(self, request, handler):
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != f"Bearer {self.webhook_secret}":
            return web.json_response({"error": "Unauthorized"}, status=401)
        return await handler(request)

    def add_webhook_routes(self, handler_instance):
        if hasattr(handler_instance, 'add_routes') and callable(getattr(handler_instance, 'add_routes')):
            handler_instance.add_routes(self.app)
        else:
            print(f"Error: {handler_instance.__class__.__name__} does not have a callable 'add_routes' method.")

    async def start(self, host, port):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()
        print(f"HTTP server running at http://{host}:{port}")

    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()