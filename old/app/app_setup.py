# Configures and creates the main aiohttp web application.

from aiohttp import web
from .config import AppConfig
from matrix.rtc_client import MatrixRTC
from webhooks import send_hook
from websockets import matrix_bridge_ws

#Core Bearer token authentication logic.
async def _auth_handler_logic(request: web.Request, handler, secret: str) -> web.Response:
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header != f"Bearer {secret}":
        return web.Response(text="Unauthorized", status=401)

    # Proceed if authorized
    return await handler(request) 

# Creates and registers authentication middleware
def _setup_authentication_middleware(app: web.Application):
    @web.middleware
    async def auth_middleware_instance(request: web.Request, handler):
        secret = app['config'].webhook_secret # Get secret from app config
        return await _auth_handler_logic(request, handler, secret)
    app.middlewares.append(auth_middleware_instance)

# Creates, configures, and returns the main aiohttp application
def create_application(config: AppConfig, matrix_rtc: MatrixRTC) -> web.Application:
    app = web.Application()
    app['config'] = config

    _setup_authentication_middleware(app)

    # Register routes from component modules
    send_hook.register_routes(app, config.webhook_secret)
    matrix_bridge_ws.register_routes(app, matrix_rtc)

    return app