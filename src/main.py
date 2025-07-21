import asyncio
import logging
import sys
from src.config import Config, ConfigError
from src.matrix_bot import MatrixBot
from src.web_server import WebServer
from src.synapse_client import SynapseAdminClient
from src.database import init_db

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# Initializes and runs the bot and web server for NeuroSync.
async def main():
    try:
        # Initialize database and config
        await init_db()
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
        
        # Create tasks for each component - no bot tasks initially
        bot_tasks = []
        
        web_server = WebServer(config, bots, bot_tasks, synapse_client, message_queue)

        logger.info(f"NeuroSync is starting with {len(bots)} bot(s)...")
        web_task = asyncio.create_task(web_server.run())
        await web_task

    except ConfigError as e:
        logger.critical(f"Configuration Error: {e}")
    except Exception as e:
        logger.critical(f"A critical error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("NeuroSync is shutting down...")