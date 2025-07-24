import asyncio
import logging
import sys
from src.config.app_config import Config, init_db, get_all_bots, ConfigError
from src.matrix.synapse_client import SynapseAdminClient
from src.web.server import WebServer
from src.web.message_dispatcher import MessageDispatcher

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Initializes and runs all components.
async def main():
    try:
        config = Config()
        await init_db(config.db_url)
        
        # Initialize the message dispatcher for fan-out queuing
        message_dispatcher = MessageDispatcher()

        # Initialize the Synapse Admin client if a token is provided
        synapse_client = None
        if config.synapse_admin_token:
            synapse_client = SynapseAdminClient(
                config.matrix_homeserver,
                config.synapse_admin_token
            )
            logger.info("Synapse Admin Client initialized.")
        else:
            logger.warning("SYNAPSE_ADMIN_TOKEN not set.")

        # Load initial bot tokens for auth middleware
        bot_configs = await get_all_bots()
        bot_tokens = {bot['webhook_secret']: bot['user_id'] for bot in bot_configs}

        # The WebServer now manages state like active bots and tasks
        web_server = WebServer(
            config=config,
            message_dispatcher=message_dispatcher,
            synapse_client=synapse_client,
            initial_bot_tokens=bot_tokens
        )

        logger.info("NeuroSync is starting...")

        # Create and run concurrent tasks
        server_task = asyncio.create_task(web_server.run())
        dispatcher_task = asyncio.create_task(message_dispatcher.run())

        await asyncio.gather(server_task, dispatcher_task)

    except ConfigError as e:
        logger.critical(f"Configuration Error: {e}")
    except Exception as e:
        logger.critical(f"A critical error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("NeuroSync is shutting down...")