import asyncio
import signal

from app.config import AppConfig
from app.matrix_manager import MatrixManager
from app.webserver import WebServer

from hooks.messaging import MessageWebhooks
from hooks.accounts import AccountWebhooks

async def shutdown_handler(sig, loop, matrix_manager, web_server):
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)

    if matrix_manager:
        await matrix_manager.close()
    if web_server:
        await web_server.stop()

    loop.stop()
    print("Shutdown complete.")

async def run_application():
    matrix_mgr = MatrixManager(
        homeserver=AppConfig.MATRIX_HOMESERVER,
        user_id=AppConfig.MATRIX_USER_ID,
        access_token=AppConfig.MATRIX_ACCESS_TOKEN,
        default_room_id=AppConfig.DEFAULT_ROOM_ID
    )

    web_svr = WebServer(webhook_secret=AppConfig.WEBHOOK_SECRET)

    message_handlers = MessageWebhooks(
        matrix_client=matrix_mgr.client,
        default_room_id=AppConfig.DEFAULT_ROOM_ID,
        message_queue=matrix_mgr.message_queue
    )
    account_handlers = AccountWebhooks(
        matrix_client=matrix_mgr.client
    )

    web_svr.add_webhook_routes(message_handlers)
    web_svr.add_webhook_routes(account_handlers)
    
    loop = asyncio.get_event_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown_handler(s, loop, matrix_mgr, web_svr))
        )

    matrix_sync_task = loop.create_task(matrix_mgr.start_sync())
    web_server_task = loop.create_task(web_svr.start(AppConfig.HTTP_HOST, AppConfig.HTTP_PORT))

    print("Application started. Press Ctrl+C to exit.")
    
    try:
        await asyncio.gather(matrix_sync_task, web_server_task)
    except asyncio.CancelledError:
        print("Main tasks cancelled during shutdown.")
    finally:
        # Ensure cleanup if tasks end for other reasons
        if not matrix_mgr.client.closed: # Check if already closed by shutdown_handler or start_sync finally
            await matrix_mgr.close()
        if web_svr.site and web_svr.site._server: # Check if server is running
             await web_svr.stop()


if __name__ == "__main__":
    try:
        asyncio.run(run_application())
    except KeyboardInterrupt:
        print("KeyboardInterrupt caught, application will exit.")
    except ValueError as ve:
        print(f"Startup Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Application has exited.")