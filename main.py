import discord
from discord.ext import commands
from config import TOKEN
from database import db
from cogs.voice import VoiceControlView

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.voice_states = True
        intents.guilds = True
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents, help_command=None)

    async def setup_hook(self):
        await db.init()
        self.add_view(VoiceControlView(self))
        await self.load_extension("cogs.voice")
        await self.load_extension("cogs.commands")
        print("Cogs loaded and database initialized.")

bot = Bot()

if __name__ == "__main__":
    bot.run(TOKEN)