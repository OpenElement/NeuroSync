import os
import logging
from dotenv import load_dotenv
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
        self.db_url = os.getenv("sqlite+aiosqlite:///data/bots.db")

        if not self.matrix_homeserver or not self.admin_token:
            raise ConfigError("Missing required env vars: MATRIX_HOMESERVER, NS_ADMIN_TOKEN")


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