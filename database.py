import aiosqlite
from config import DB_PATH

class Database:
    def __init__(self):
        self.db_path = DB_PATH

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS voice_channels (
                    channel_id INTEGER PRIMARY KEY,
                    owner_id INTEGER NOT NULL
                )
                """
            )
            await db.commit()

    async def add_channel(self, channel_id: int, owner_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO voice_channels (channel_id, owner_id) VALUES (?, ?)",
                (channel_id, owner_id)
            )
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

db = Database()