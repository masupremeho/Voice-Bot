import aiosqlite
from config import DB_PATH

class Database:
    def __init__(self):
        self.db_path = DB_PATH

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Table for Voice Channels
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS voice_channels (
                    channel_id INTEGER PRIMARY KEY,
                    owner_id INTEGER NOT NULL
                )
                """
            )
            # Table for Sub-Admins
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sub_admins (
                    user_id INTEGER PRIMARY KEY
                )
                """
            )
            await db.commit()

    # --- Voice Channel Methods ---
    async def add_channel(self, channel_id: int, owner_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO voice_channels (channel_id, owner_id) VALUES (?, ?)", (channel_id, owner_id))
            await db.commit()

    async def remove_channel(self, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM voice_channels WHERE channel_id = ?", (channel_id,))
            await db.commit()

    async def get_owner(self, channel_id: int) -> int | None:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT owner_id FROM voice_channels WHERE channel_id = ?", (channel_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def update_owner(self, channel_id: int, new_owner_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE voice_channels SET owner_id = ? WHERE channel_id = ?", (new_owner_id, channel_id))
            await db.commit()

    # --- Sub-Admin Methods ---
    async def add_admin(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO sub_admins (user_id) VALUES (?)", (user_id,))
            await db.commit()

    async def remove_admin(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sub_admins WHERE user_id = ?", (user_id,))
            await db.commit()

    async def is_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id FROM sub_admins WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row is not None

db = Database()