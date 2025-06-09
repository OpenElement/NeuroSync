import asyncio
import signal
from app.webserver import NeuroSync

async def main():
    bot = NeuroSync()
    
    loop = asyncio.get_event_loop()

    # Add signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop, bot)))

    try:
        await bot.start()
    except Exception as e:
        print(f"Error during bot startup or main execution: {e}")

async def shutdown(sig, loop, bot_instance):
    print("Starting shutdown...")

    if bot_instance:
        await bot_instance.stop()

    tasks = [t for t in asyncio.all_tasks(loop=loop) if t is not asyncio.current_task(loop=loop)]
    if tasks:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    else:
        pass
    
    loop.stop() # Stop the event loop
    print("Shutdown complete.")


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    main_task = None
    try:
        main_task = asyncio.ensure_future(main())
        loop.run_forever()
    except KeyboardInterrupt:
        if main_task and not main_task.done():
            loop.run_until_complete(shutdown(signal.SIGINT, loop, None))
    finally:
        if loop.is_running():
            loop.stop()
        if not loop.is_closed():
            loop.close()

