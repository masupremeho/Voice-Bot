import aiosqlite
from config import DB_PATH

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.conn = None # Persistent connection

    async def init(self):
        # Open the connection once when the bot boots
        self.conn = await aiosqlite.connect(self.db_path)
        
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS voice_channels (
                channel_id INTEGER PRIMARY KEY,
                owner_id INTEGER NOT NULL
            )
            """
        )
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sub_admins (
                user_id INTEGER PRIMARY KEY
            )
            """
        )
        await self.conn.commit()

    # --- Voice Channel Methods ---
    async def add_channel(self, channel_id: int, owner_id: int):
        await self.conn.execute("INSERT OR REPLACE INTO voice_channels (channel_id, owner_id) VALUES (?, ?)", (channel_id, owner_id))
        await self.conn.commit()

    async def remove_channel(self, channel_id: int):
        await self.conn.execute("DELETE FROM voice_channels WHERE channel_id = ?", (channel_id,))
        await self.conn.commit()

    async def get_owner(self, channel_id: int) -> int | None:
        async with self.conn.execute("SELECT owner_id FROM voice_channels WHERE channel_id = ?", (channel_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    async def update_owner(self, channel_id: int, new_owner_id: int):
        await self.conn.execute("UPDATE voice_channels SET owner_id = ? WHERE channel_id = ?", (new_owner_id, channel_id))
        await self.conn.commit()

    async def get_all_channels(self):
        async with self.conn.execute("SELECT channel_id FROM voice_channels") as cursor:
            return await cursor.fetchall()

    # --- Sub-Admin Methods ---
    async def add_admin(self, user_id: int):
        await self.conn.execute("INSERT OR IGNORE INTO sub_admins (user_id) VALUES (?)", (user_id,))
        await self.conn.commit()

    async def remove_admin(self, user_id: int):
        await self.conn.execute("DELETE FROM sub_admins WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    async def is_admin(self, user_id: int) -> bool:
        async with self.conn.execute("SELECT user_id FROM sub_admins WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None

db = Database()