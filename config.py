import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("DB_PATH", "voice_system.db")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is missing from environment variables!")