import os
import logging
from dotenv import load_dotenv, set_key
from sqlalchemy import Column, String, create_engine, select
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

# Custom exception for configuration errors.
class ConfigError(Exception):
    pass

# Handles application configuration from environment variables.
class Config:
    def __init__(self):
        load_dotenv()
        self.matrix_homeserver = os.getenv("MATRIX_HOMESERVER")
        self.admin_token = os.getenv("NS_ADMIN_TOKEN")
        self.synapse_admin_token = os.getenv("SYNAPSE_ADMIN_TOKEN")
        self.db_url = "sqlite+aiosqlite:///data/bots.db"

        if not self.matrix_homeserver or not self.admin_token:
            raise ConfigError("Missing required env vars: MATRIX_HOMESERVER, NS_ADMIN_TOKEN")

    # Update the synapse admin token both in memory and in the .env file
    def update_synapse_admin_token(self, token: str):
        self.synapse_admin_token = token
        update_synapse_admin_token(token)


Base = declarative_base()
async_session_factory = None

# SQLAlchemy model for a bot
class Bot(Base):
    __tablename__ = "bots"
    user_id = Column(String, primary_key=True)
    password = Column(String, nullable=False)
    store_path = Column(String, nullable=False)
    webhook_secret = Column(String, nullable=False)

# Initializes the database and creates tables if they don't exist.
async def init_db(db_url: str):
    global async_session_factory
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("Database initialized successfully.")

# Retrieves all bot configurations from the database
async def get_all_bots():
    async with async_session_factory() as session:
        result = await session.execute(select(Bot))
        bots = result.scalars().all()
        return [
            {"user_id": b.user_id, "password": b.password, "store_path": b.store_path, "webhook_secret": b.webhook_secret}
            for b in bots
        ]
    
# Gets a specific bot configuration by user_id.
async def get_bot_by_user_id(user_id: str):
    async with async_session_factory() as session:
        result = await session.execute(select(Bot).where(Bot.user_id == user_id))
        bot = result.scalar_one_or_none()
        if bot:
            return {"user_id": bot.user_id, "password": bot.password, "store_path": bot.store_path, "webhook_secret": bot.webhook_secret}
        return None

# Adds a new bot to the database.
async def add_bot(user_id: str, password: str, store_path: str, webhook_secret: str):
    async with async_session_factory() as session:
        try:
            new_bot = Bot(user_id=user_id, password=password, store_path=store_path, webhook_secret=webhook_secret)
            session.add(new_bot)
            await session.commit()
            logger.info(f"Added new bot {user_id} to the database.")
        except IntegrityError:
            await session.rollback()
            logger.error(f"Bot with user_id {user_id} already exists.")
            raise ValueError(f"Bot {user_id} already exists.")
        
# Deletes a bot from the database.
async def delete_bot(user_id: str):
    async with async_session_factory() as session:
        try:
            await session.execute(select(Bot).where(Bot.user_id == user_id))
            await session.commit()
            logger.info(f"Deleted bot {user_id} from the database.")
        except Exception as e:
            logger.error(f"Failed to delete bot {user_id}: {e}")
            raise ValueError(f"Failed to delete bot {user_id}: {e}")
        
# Updates the webhook secret for a bot.
async def update_bot_webhook_secret(user_id: str, new_secret: str):
    async with async_session_factory() as session:
        try:
            bot = await session.execute(select(Bot).where(Bot.user_id == user_id))
            bot = bot.scalar_one_or_none()
            if not bot:
                raise ValueError(f"Bot {user_id} does not exist.")
            bot.webhook_secret = new_secret
            await session.commit()
            logger.info(f"Updated webhook secret for bot {user_id}.")
        except Exception as e:
            logger.error(f"Failed to update webhook secret for bot {user_id}: {e}")
            raise ValueError(f"Failed to update webhook secret for bot {user_id}: {e}")

# Updates the SYNAPSE_ADMIN_TOKEN in the .env file
def update_synapse_admin_token(token: str):

    env_file_path = ".env"
    
    # Create .env file if it doesn't exist
    if not os.path.exists(env_file_path):
        with open(env_file_path, 'w') as f:
            f.write("# NeuroSync Environment Variables\n")
            f.write("MATRIX_HOMESERVER=\n")
            f.write("NS_ADMIN_TOKEN=\n")
            f.write("SYNAPSE_ADMIN_TOKEN=\n")
    
    # Update the SYNAPSE_ADMIN_TOKEN value
    set_key(env_file_path, "SYNAPSE_ADMIN_TOKEN", token)
    logger.info("Updated SYNAPSE_ADMIN_TOKEN in .env file")