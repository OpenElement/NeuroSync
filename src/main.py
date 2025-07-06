# main.py
import asyncio
import logging
import sys
from src.config import Config, ConfigError
from src.matrix_bot import MatrixBot
from src.web_server import WebServer
from src.synapse_client import SynapseAdminClient

# --- Configure Logging ---
# (Logging configuration remains the same)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# Initializes and runs the bot and web server for NeuroSync.
async def main():
    try:
        config = Config()
        message_queue = asyncio.Queue()
        
        synapse_client = None
        if config.synapse_admin_token:
            synapse_client = SynapseAdminClient(
                config.matrix_homeserver, 
                config.synapse_admin_token
                )
                
            logger.info("Synapse Admin Client initialized.")
        else:
            logger.warning("SYNAPSE_ADMIN_ACCESS_TOKEN not set. User creation endpoint will be disabled.")

        bots = {}
        for bot_config in config.bots:
            user_id = bot_config['user_id']
            bot = MatrixBot(
                homeserver=config.matrix_homeserver,
                user_id=user_id,
                password=bot_config['password'],
                store_path=bot_config['store_path'],
                message_queue=message_queue
            )
            bots[user_id] = bot
        
        if not bots:
            logger.warning("No bots configured to run. Check your .env file for NUM_BOTS and bot credentials.")

        # Pass the dictionary of bot instances to the web server
        web_server = WebServer(config, bots, synapse_client, message_queue)

        # Create tasks for each component
        bot_tasks = [asyncio.create_task(bot.run()) for bot in bots.values()]
        web_task = asyncio.create_task(web_server.run())

        logger.info(f"NeuroSync is starting with {len(bots)} bot(s)...")
        await asyncio.gather(*bot_tasks, web_task)

    except ConfigError as e:
        logger.critical(f"Configuration Error: {e}")
    except Exception as e:
        logger.critical(f"A critical error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("NeuroSync is shutting down...")