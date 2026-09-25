import discord
from discord.ext import commands
from database import db

class VoiceCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_owner(self, ctx) -> bool:
        if not ctx.author.voice or not ctx.author.voice.channel:
            return False
        owner_id = await db.get_owner(ctx.author.voice.channel.id)
        return owner_id == ctx.author.id

    @commands.group(name="vc", invoke_without_command=True)
    async def vc(self, ctx):
        await ctx.send("⚙️ **Usage:** `.vc permit @user`, `.vc kick @user`, `.vc ban @user`, `.vc unban @user`, `.vc rename <name>`")

    @vc.command(name="permit")
    async def permit(self, ctx, target: discord.Member):
        if not await self.is_owner(ctx):
            return await ctx.send("❌ You do not own this voice channel.")
        channel = ctx.author.voice.channel
        await channel.set_permissions(target, connect=True)
        await ctx.send(f"🎟️ **VIP Pass:** {target.mention} has been permitted to join this locked channel.")

    @vc.command(name="kick")
    async def kick(self, ctx, target: discord.Member):
        if not await self.is_owner(ctx):
            return await ctx.send("❌ You do not own this voice channel.")
        if target.voice and target.voice.channel == ctx.author.voice.channel:
            await target.move_to(None)
            await ctx.send(f"👢 Kicked {target.mention} from the channel.")

    @vc.command(name="ban")
    async def ban(self, ctx, target: discord.Member):
        if not await self.is_owner(ctx):
            return await ctx.send("❌ You do not own this voice channel.")
        ch = ctx.author.voice.channel
        await ch.set_permissions(target, connect=False, view_channel=False)
        if target.voice and target.voice.channel == ch:
            await target.move_to(None)
        await ctx.send(f"🚫 Banned {target.mention} from the channel.")

    @vc.command(name="unban")
    async def unban(self, ctx, target: discord.Member):
        if not await self.is_owner(ctx):
            return await ctx.send("❌ You do not own this voice channel.")
        await ctx.author.voice.channel.set_permissions(target, overwrite=None)
        await ctx.send(f"🔓 Unbanned {target.mention}.")

    @vc.command(name="rename")
    async def rename(self, ctx, *, name: str):
        if not await self.is_owner(ctx):
            return await ctx.send("❌ You do not own this voice channel.")
        await ctx.author.voice.channel.edit(name=name[:32])
        await ctx.send(f"✏️ Renamed channel to **{name[:32]}**.")

    @commands.command(name="reload", hidden=True)
    @commands.is_owner()
    async def reload_cogs(self, ctx):
        await self.bot.reload_extension("cogs.voice")
        await self.bot.reload_extension("cogs.commands")
        await ctx.send("✅ Cogs successfully hot-reloaded! New code is active.")

async def setup(bot):
    await bot.add_cog(VoiceCommands(bot))