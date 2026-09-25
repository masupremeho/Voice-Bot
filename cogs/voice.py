import asyncio
import unicodedata
import discord
import aiosqlite
from discord.ext import commands, tasks
from database import db

class VoiceControlView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def _is_owner(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in your voice channel.", ephemeral=True)
            return False
        owner_id = await db.get_owner(interaction.user.voice.channel.id)
        if owner_id != interaction.user.id:
            await interaction.response.send_message("❌ You are not the channel owner.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.red, custom_id="vc_lock", emoji="🔒")
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction): return
        channel = interaction.user.voice.channel
        overwrites = channel.overwrites_for(interaction.guild.default_role)
        overwrites.connect = False
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
        await interaction.response.send_message("🔒 Channel locked. Use `.vc permit @user` to let friends in.", ephemeral=True)

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.green, custom_id="vc_unlock", emoji="🔓")
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_owner(interaction): return
        channel = interaction.user.voice.channel
        overwrites = channel.overwrites_for(interaction.guild.default_role)
        overwrites.connect = True
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
        await interaction.response.send_message("🔓 Channel unlocked.", ephemeral=True)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.blurple, custom_id="vc_claim", emoji="👑")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("❌ You must be in a voice channel.", ephemeral=True)
        channel = interaction.user.voice.channel
        owner_id = await db.get_owner(channel.id)
        
        if not owner_id:
            return await interaction.response.send_message("❌ Channel not managed by bot.", ephemeral=True)
        if any(m.id == owner_id for m in channel.members):
            return await interaction.response.send_message("❌ Current owner is still present.", ephemeral=True)

        await db.update_owner(channel.id, interaction.user.id)
        await channel.set_permissions(interaction.user, manage_channels=True, move_members=True, connect=True)
        await interaction.response.send_message(f"👑 {interaction.user.mention} claimed ownership!")

class VoiceEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_creations = set()
        self.locks = {}
        self.ghost_sweeper.start()

    def cog_unload(self):
        self.ghost_sweeper.cancel()

    def get_lock(self, guild_id: int) -> asyncio.Lock:
        if guild_id not in self.locks:
            self.locks[guild_id] = asyncio.Lock()
        return self.locks[guild_id]

    def parse_template(self, channel_name: str):
        normalized = unicodedata.normalize('NFKD', channel_name).lower()
        if "duo" in normalized: return "Duo", 2
        elif "trio" in normalized: return "Trio", 3
        elif "squad" in normalized or "quad" in normalized: return "Squad", 4
        elif "team" in normalized: return "Team", 10
        elif any(symbol in channel_name for symbol in ["➕", "✚", "[+]", "♡"]): return "General", 0
        return None, 0

    @tasks.loop(minutes=10)
    async def ghost_sweeper(self):
        try:
            # Replaced raw aiosqlite connection with our new helper method
            rows = await db.get_all_channels()
                    
            for row in rows:
                channel_id = row[0]
                channel = self.bot.get_channel(channel_id)
                if channel is None:
                    try:
                        channel = await self.bot.fetch_channel(channel_id)
                    except discord.NotFound:
                        await db.remove_channel(channel_id)
                        continue
                    except: continue

                if len(channel.members) == 0:
                    try:
                        await channel.delete(reason="Ghost sweeper cleanup")
                    except: pass
                    finally:
                        await db.remove_channel(channel_id)
        except Exception as e:
            print(f"Sweeper error: {e}")

    @ghost_sweeper.before_loop
    async def before_sweeper(self):
        await self.bot.wait_until_ready()

    async def handle_auto_transfer(self, channel_id: int, old_owner_id: int):
        await asyncio.sleep(300) 
        
        # Re-fetch the channel safely after the wait
        channel = self.bot.get_channel(channel_id)
        if not channel: return

        current_owner = await db.get_owner(channel.id)
        if not current_owner or current_owner != old_owner_id:
            return 
            
        if any(m.id == old_owner_id for m in channel.members):
            return
            
        # Only transfer to actual users, not bots
        eligible_members = [m for m in channel.members if not m.bot]
        if not eligible_members:
            return 
            
        new_owner = eligible_members[0]
        await db.update_owner(channel.id, new_owner.id)
        await channel.set_permissions(new_owner, manage_channels=True, move_members=True, connect=True)
        
        try:
            await channel.send(f"👑 {new_owner.mention}, the previous owner left 5 minutes ago. You are the new channel owner!")
        except: pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Ignore simple mute/deafen updates
        if before.channel == after.channel:
            return

        if after.channel:
            # THE FIX: Check if they are joining an ALREADY generated temporary channel
            is_generated_vc = await db.get_owner(after.channel.id)
            
            # If it's NOT a generated VC, then we check if we need to create one
            if not is_generated_vc:
                type_name, limit = self.parse_template(after.channel.name)
                if type_name and member.id not in self.active_creations:
                    self.active_creations.add(member.id)
                    try:
                        async with self.get_lock(member.guild.id):
                            if member.voice and member.voice.channel == after.channel:
                                overwrites = {
                                    member.guild.default_role: discord.PermissionOverwrite(connect=True),
                                    member: discord.PermissionOverwrite(manage_channels=True, move_members=True, connect=True)
                                }
                                new_channel = await member.guild.create_voice_channel(
                                    name=f"{type_name} | {member.display_name}",
                                    category=after.channel.category,
                                    user_limit=limit,
                                    overwrites=overwrites
                            )
                            try:
                                await member.move_to(new_channel)
                                await db.add_channel(new_channel.id, member.id)

                                embed = discord.Embed(
                                    title="🎙️ Voice Control Panel",
                                    description="Manage your channel using the buttons below or commands (`.vc permit`, `.vc kick`, `.vc ban`, `.vc rename`).",
                                    color=discord.Color.blurple()
                                )
                                await new_channel.send(embed=embed, view=VoiceControlView(self.bot))
                            except discord.HTTPException:
                                # The user disconnected before we could move them. Nuke the channel instantly.
                                await new_channel.delete(reason="User left during channel creation phase.")
                    except Exception as e:
                        print(f"Error creating channel: {e}")
                    finally:
                        self.active_creations.discard(member.id)

        if before.channel:
            owner_id = await db.get_owner(before.channel.id)
            if owner_id:
                if len(before.channel.members) == 0:
                    async with self.get_lock(member.guild.id):
                        if len(before.channel.members) == 0:
                            try:
                                await before.channel.delete()
                            except (discord.NotFound, discord.Forbidden):
                                pass
                            await db.remove_channel(before.channel.id)
                
                elif owner_id == member.id:
                    self.bot.loop.create_task(self.handle_auto_transfer(before.channel.id, owner_id))

async def setup(bot):
    await bot.add_cog(VoiceEvents(bot))