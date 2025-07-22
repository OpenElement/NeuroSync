import logging
from sqlalchemy import Column, String, Boolean, create_engine, select, update
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

DB_URL = "sqlite+aiosqlite:///data/bots.db"

Base = declarative_base()

class Bot(Base):
    __tablename__ = "bots"
    
    user_id = Column(String, primary_key=True)
    password = Column(String, nullable=False)
    store_path = Column(String, nullable=False)
    webhook_secret = Column(String, nullable=False)
    active = Column(Boolean, default=False, nullable=False)

engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Initializes the database and creates the bots table if it doesn't exist
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully.")

# Retrieves all bot configurations from the database
async def get_all_bots():
    async with async_session() as session:
        result = await session.execute(select(Bot))
        bots = result.scalars().all()
        return [{"user_id": bot.user_id, "password": bot.password, "store_path": bot.store_path, "webhook_secret": bot.webhook_secret, "active": bot.active} for bot in bots]

# Retrieves only active bot configurations from the database
async def get_active_bots():
    async with async_session() as session:
        result = await session.execute(select(Bot).where(Bot.active == True))
        bots = result.scalars().all()
        return [{"user_id": bot.user_id, "password": bot.password, "store_path": bot.store_path, "webhook_secret": bot.webhook_secret, "active": bot.active} for bot in bots]

# Gets a specific bot by user_id
async def get_bot_by_user_id(user_id: str):
    async with async_session() as session:
        result = await session.execute(select(Bot).where(Bot.user_id == user_id))
        bot = result.scalar_one_or_none()
        if bot:
            return {"user_id": bot.user_id, "password": bot.password, "store_path": bot.store_path, "webhook_secret": bot.webhook_secret, "active": bot.active}
        return None

# Updates the active status of a bot
async def set_bot_active_status(user_id: str, active: bool):
    async with async_session() as session:
        await session.execute(
            update(Bot).where(Bot.user_id == user_id).values(active=active)
        )
        await session.commit()
        logger.info(f"Bot {user_id} active status set to {active}")

# Adds a new bot to the database.
async def add_bot(user_id: str, password: str, store_path: str, webhook_secret: str):
    async with async_session() as session:
        try:
            new_bot = Bot(user_id=user_id, password=password, store_path=store_path, webhook_secret=webhook_secret, active=False)
            session.add(new_bot)
            await session.commit()
            logger.info(f"Added new bot {user_id} to the database.")
            return webhook_secret
        except IntegrityError:
            await session.rollback()
            logger.error(f"Bot with user_id {user_id} already exists in the database.")
            raise Exception(f"Bot {user_id} already exists.")