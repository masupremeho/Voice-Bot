import discord
from discord.ext import commands
from database import db

# Custom check for sub-admins or the true bot owner
async def is_admin_or_owner(ctx):
    if await ctx.bot.is_owner(ctx.author):
        return True
    if await db.is_admin(ctx.author.id):
        return True
    raise commands.CheckFailure("❌ You do not have bot admin permissions.")

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
            try:
                await target.move_to(None)
                await ctx.send(f"👢 Kicked {target.mention} from the channel.")
            except discord.HTTPException:
                await ctx.send(f"⚠️ {target.mention} already left the channel.")

    @vc.command(name="ban")
    async def ban(self, ctx, target: discord.Member):
        if not await self.is_owner(ctx):
            return await ctx.send("❌ You do not own this voice channel.")
        ch = ctx.author.voice.channel
        await ch.set_permissions(target, connect=False, view_channel=False)
        if target.voice and target.voice.channel == ch:
            try:
                await target.move_to(None)
            except discord.HTTPException:
                pass # User already left
        await ctx.send(f"🚫 Banned {target.mention} from the channel.")

    @vc.command(name="unban")
    async def unban(self, ctx, target: discord.Member):
        if not await self.is_owner(ctx):
            return await ctx.send("❌ You do not own this voice channel.")
        await ctx.author.voice.channel.set_permissions(target, overwrite=None)
        await ctx.send(f"🔓 Unbanned {target.mention}.")

    @vc.command(name="rename")
    @commands.cooldown(2, 600, commands.BucketType.channel) # 2 uses per 600 seconds (10 mins)
    async def rename(self, ctx, *, name: str):
        if not await self.is_owner(ctx):
            return await ctx.send("❌ You do not own this voice channel.")
        try:
            await ctx.author.voice.channel.edit(name=name[:32])
            await ctx.send(f"✏️ Renamed channel to **{name[:32]}**.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to rename channel. Discord API Error: {e}")

    @rename.error
    async def rename_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            await ctx.send(f"⏳ Discord limits channel renaming. Try again in {int(minutes)}m {int(seconds)}s.")

    @commands.command(name="help")
    async def help_cmd(self, ctx):
        embed = discord.Embed(
            title="🎙️ Voice Bot Help Menu",
            description="Here are the commands you can use with this bot.",
            color=discord.Color.blurple()
        )
        
        # Standard User Commands
        vc_cmds = (
            "`.vc permit @user` — Allow a user into a locked channel\n"
            "`.vc kick @user` — Disconnect a user from your channel\n"
            "`.vc ban @user` — Ban a user from rejoining your channel\n"
            "`.vc unban @user` — Unban a user\n"
            "`.vc rename <name>` — Rename your channel (max 32 chars)"
        )
        embed.add_field(name="👥 Channel Owner Commands", value=vc_cmds, inline=False)
        
        # Admin / Sub-Admin Dynamic Checks
        is_admin = False
        is_true_owner = await self.bot.is_owner(ctx.author)
        
        if is_true_owner:
            is_admin = True
        else:
            is_admin = await db.is_admin(ctx.author.id)
            
        if is_admin:
            admin_cmds = "`.reload` — Hot-reload the bot's code without restarting\n"
            if is_true_owner:
                admin_cmds += "`.admin add @user` — Grant a user sub-admin privileges\n"
                admin_cmds += "`.admin remove @user` — Revoke sub-admin privileges\n"
            
            embed.add_field(name="🛡️ Admin Commands", value=admin_cmds, inline=False)
            
        await ctx.send(embed=embed)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="admin", invoke_without_command=True)
    @commands.check(is_admin_or_owner)
    async def admin_group(self, ctx):
        await ctx.send("⚙️ Type `.admin help` for a list of admin commands.")

    @admin_group.command(name="help")
    @commands.check(is_admin_or_owner)
    async def admin_help(self, ctx):
        embed = discord.Embed(
            title="🛡️ Bot Admin Panel",
            description="Commands for managing the bot and its sub-admins.",
            color=discord.Color.red()
        )
        embed.add_field(name=".reload", value="Hot-reloads the bot code without restarting it. (Usable by Owner & Sub-Admins)", inline=False)
        embed.add_field(name=".admin add @user", value="Grants sub-admin privileges to a user. (Owner Only)", inline=False)
        embed.add_field(name=".admin remove @user", value="Revokes sub-admin privileges from a user. (Owner Only)", inline=False)
        await ctx.send(embed=embed)

    @admin_group.command(name="add")
    @commands.is_owner() # ONLY the true Discord Application owner can use this
    async def admin_add(self, ctx, target: discord.Member):
        await db.add_admin(target.id)
        await ctx.send(f"✅ {target.mention} has been added as a Sub-Admin.")

    @admin_group.command(name="remove")
    @commands.is_owner() # ONLY the true Discord Application owner can use this
    async def admin_remove(self, ctx, target: discord.Member):
        await db.remove_admin(target.id)
        await ctx.send(f"❌ {target.mention} has been removed from Sub-Admins.")

    @commands.command(name="reload", hidden=True)
    @commands.check(is_admin_or_owner) # Sub-admins and Owner can reload
    async def reload_cogs(self, ctx):
        await self.bot.reload_extension("cogs.voice")
        await self.bot.reload_extension("cogs.commands")
        await ctx.send("✅ Cogs successfully hot-reloaded! New code is active.")

    @reload_cogs.error
    @admin_group.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send(str(error))


async def setup(bot):
    await bot.add_cog(VoiceCommands(bot))
    await bot.add_cog(AdminCommands(bot))