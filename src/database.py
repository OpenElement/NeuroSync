import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_PATH = "data/bots.db"

# Initializes the database and creates the bots table if it doesn't exist
async def init_db():

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                user_id TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                store_path TEXT NOT NULL
            )
        """)
        await db.commit()
    logger.info("Database initialized successfully.")

# Retrieves all bot configurations from the database
async def get_all_bots():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bots") as cursor:
            return await cursor.fetchall()

# Adds a new bot to the database.
async def add_bot(user_id: str, password: str, store_path: str):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO bots (user_id, password, store_path) VALUES (?, ?, ?)",
                (user_id, password, store_path)
            )
            await db.commit()
            logger.info(f"Added new bot {user_id} to the database.")
        except aiosqlite.IntegrityError:
            logger.error(f"Bot with user_id {user_id} already exists in the database.")
            raise Exception(f"Bot {user_id} already exists.")