# Main application entry point for NeuroSync."""

import asyncio
from aiohttp import web

from app.config import load_app_config, AppConfig
from app.app_setup import create_application
from matrix.rtc_client import MatrixRTC

async def main():
    # Initializes and runs the NeuroSync application.
    print("Initializing NeuroSync...")

    # Load configuration
    try:
        config: AppConfig = load_app_config()

    # Initialize and start MatrixRTC client
    matrix_rtc = MatrixRTC(
        homeserver=config.homeserver, user_id=config.user_id,
        access_token=config.access_token, room_id=config.room_id
    )
    await matrix_rtc.start()

    # Create aiohttp application
    app = create_application(config=config, matrix_rtc=matrix_rtc)

    # Setup and run aiohttp server
    runner = web.AppRunner(app)
    await runner.setup()
    site_host, site_port = "0.0.0.0", 8080 # Consider making configurable
    site = web.TCPSite(runner, site_host, site_port)
    await site.start()
    print(f"[Main] Server running on http://{site_host}:{site_port}. Press Ctrl+C to stop.")
    
    # Keep alive loop
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[Main] Shuting down...")
    finally:
        print("[Main] Shutdown...")
        if matrix_rtc: await matrix_rtc.stop()
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[MainBootstrap] Unhandled error during execution: {e}")