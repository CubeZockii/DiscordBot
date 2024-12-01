import discord
from discord.ext import commands
import json
import os
import sys
from datetime import datetime
from discord import app_commands

# Bot Setup
with open("config.json") as config_file:
    config = json.load(config_file)

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=config["prefix"], intents=intents)

# Syncing Slash commands
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync the slash commands with Discord
    print(f'{bot.user} has connected to Discord!')

# Datenbanken für Leveling und Warnsystem
user_data = {}
warns = {}
user_last_message = {}  # Für XP-Cooldown

# Leveling System
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    now = datetime.now()
    user = message.author

    # Cooldown von 60 Sekunden für XP-Vergabe
    if user.id in user_last_message and (now - user_last_message[user.id]).total_seconds() < 60:
        await bot.process_commands(message)
        return

    user_last_message[user.id] = now

    if user.id not in user_data:
        user_data[user.id] = {"xp": 0, "level": 1}

    user_data[user.id]["xp"] += 10
    xp = user_data[user.id]["xp"]
    level = user_data[user.id]["level"]

    # Level-Up
    if xp >= level * 100:
        user_data[user.id]["level"] += 1
        await message.channel.send(f"🎉 {user.mention}, Glückwunsch! Du hast Level {user_data[user.id]['level']} erreicht!")

    await bot.process_commands(message)

# Check if the user is either the bot owner or the server owner
def has_mod_permissions(user, guild):
    return user.id == config["owner_id"] or user.id == guild.owner_id or user.guild_permissions.administrator

# Warnsystem: Funktionen zum Überprüfen der Berechtigungen
def can_warn(interaction, member):
    return interaction.user.guild_permissions.manage_messages or interaction.user.id == interaction.guild.owner_id

def is_not_mod_or_owner(member, interaction):
    return member.id != interaction.guild.owner_id and not member.guild_permissions.manage_messages

# Kick Command
@bot.tree.command(name="kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not has_mod_permissions(interaction.user, interaction.guild):
        embed = discord.Embed(
            title="⚠️ Permission Denied",
            description="You do not have permission to use this command.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return

    try:
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 User Kicked",
            description=f"{member.mention} has been kicked. Reason: {reason}",
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I do not have permission to kick this user.")

# Ban Command
@bot.tree.command(name="ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not has_mod_permissions(interaction.user, interaction.guild):
        embed = discord.Embed(
            title="⚠️ Permission Denied",
            description="You do not have permission to use this command.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return

    try:
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="⛔ User Banned",
            description=f"{member.mention} has been banned. Reason: {reason}",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I do not have permission to ban this user.")

# Mute Command
@bot.tree.command(name="mute")
async def mute(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not has_mod_permissions(interaction.user, interaction.guild):
        embed = discord.Embed(
            title="⚠️ Permission Denied",
            description="You do not have permission to use this command.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return

    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await interaction.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False, speak=False))
        for channel in interaction.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)

    try:
        await member.add_roles(mute_role, reason=reason)
        embed = discord.Embed(
            title="🔇 User Muted",
            description=f"{member.mention} has been muted. Reason: {reason}",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I do not have permission to mute this user.")

# Unmute Command
@bot.tree.command(name="unmute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if not has_mod_permissions(interaction.user, interaction.guild):
        embed = discord.Embed(
            title="⚠️ Permission Denied",
            description="You do not have permission to use this command.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return

    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        embed = discord.Embed(
            title="🔊 User Unmuted",
            description=f"{member.mention} has been unmuted.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ User is not muted.")

# Add Role Command
@bot.tree.command(name="addrole")
async def addrole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not has_mod_permissions(interaction.user, interaction.guild):
        embed = discord.Embed(
            title="⚠️ Permission Denied",
            description="You do not have permission to use this command.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return

    try:
        await member.add_roles(role)
        embed = discord.Embed(
            title="✅ Role Added",
            description=f"{role.name} has been added to {member.mention}.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I do not have permission to assign this role.")

# Remove Role Command
@bot.tree.command(name="removerole")
async def removerole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not has_mod_permissions(interaction.user, interaction.guild):
        embed = discord.Embed(
            title="⚠️ Permission Denied",
            description="You do not have permission to use this command.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return

    try:
        await member.remove_roles(role)
        embed = discord.Embed(
            title="❌ Role Removed",
            description=f"{role.name} has been removed from {member.mention}.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I do not have permission to remove this role.")

# Warn Befehl
@bot.tree.command(name="warn")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not can_warn(interaction, member):
        embed = discord.Embed(
            title="⚠️ Permission Denied",
            description="You cannot warn admins, moderators, or the owner.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return

    if is_not_mod_or_owner(member, interaction):
        if member.id not in warns:
            warns[member.id] = []
        warns[member.id].append(reason)

        embed = discord.Embed(
            title="⚠️ User Warned",
            description=f"{member.mention} has been warned. Reason: {reason}",
            color=discord.Color.yellow(),
        )
        await interaction.response.send_message(embed=embed)

# Unwarn Command with Specific Warning Selection and User Confirmation
@bot.tree.command(name="unwarn")
async def unwarn(interaction: discord.Interaction, member: discord.Member, warning_index: int = None):
    if not can_warn(interaction, member):
        embed = discord.Embed(
            title="⚠️ Permission Denied",
            description="You cannot unwarn admins, moderators, or the owner.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return

    if member.id not in warns or not warns[member.id]:
        embed = discord.Embed(
            title="⚠️ No Warnings",
            description=f"{member.mention} has no warnings.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return

    if warning_index is None:
        # Show the warnings for the member
        warning_list = "\n".join([f"{idx + 1}: {warn}" for idx, warn in enumerate(warns[member.id])])
        embed = discord.Embed(
            title=f"⚠️ Warnings for {member.mention}",
            description=warning_list,
            color=discord.Color.orange(),
        )
        embed.add_field(name="Usage", value="To unwarn, provide the warning number. Example: `/unwarn @member 1`.")
        await interaction.response.send_message(embed=embed)
    else:
        # Attempt to remove the specific warning by index
        try:
            warning_index = int(warning_index) - 1  # Convert to zero-index
            if warning_index < 0 or warning_index >= len(warns[member.id]):
                raise ValueError("Invalid warning number.")
            removed_warning = warns[member.id].pop(warning_index)  # Remove the selected warning
            embed = discord.Embed(
                title="✅ Warning Removed",
                description=f"The warning for {member.mention} has been removed. Reason: {removed_warning}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
        except (ValueError, IndexError):
            embed = discord.Embed(
                title="⚠️ Invalid Selection",
                description="The warning number provided is invalid. Please try again.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed)

# Show Warnings Command
@bot.tree.command(name="warnings")
async def show_warnings(interaction: discord.Interaction, member: discord.Member):
    if member.id not in warns or not warns[member.id]:
        embed = discord.Embed(
            title="⚠️ No Warnings",
            description=f"{member.mention} has no warnings.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="⚠️ User Warnings",
            description=f"Warnings for {member.mention}: " + "\n".join(warns[member.id]),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed)

# Serverinfo Command
@bot.tree.command(name="serverinfo")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(
        title=f"Information for {guild.name}",
        description=f"Server Information",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Server Name", value=guild.name, inline=True)
    embed.add_field(name="Server Owner", value=guild.owner, inline=True)
    embed.add_field(name="Member Count", value=guild.member_count, inline=True)
    embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Preferred Locale", value=guild.preferred_locale, inline=True)
    await interaction.response.send_message(embed=embed)


# User Info Command
@bot.tree.command(name="userinfo")
async def userinfo(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(
        title=f"Information for {member.name}",
        description=f"User Information",
        color=discord.Color.green(),
    )
    embed.add_field(name="User Name", value=member.name, inline=True)
    embed.add_field(name="User ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server At", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Created At", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    await interaction.response.send_message(embed=embed)

# Restart Command (only for bot owner and server owner)
@bot.tree.command(name="restart")
async def restart(interaction: discord.Interaction):
    if not has_mod_permissions(interaction.user, interaction.guild):
        embed = discord.Embed(
            title="⚠️ Permission Denied",
            description="You do not have permission to use this command.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(
        title="🔄 Restarting Bot",
        description="The bot is restarting now. Please wait...",
        color=discord.Color.blue(),
    )
    await interaction.response.send_message(embed=embed)

    # Restarting the bot
    os.execv(sys.executable, ['python'] + sys.argv)

# Ping Command
@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! Latency is {round(bot.latency * 1000)}ms")

# Bot starten
bot.run(config["token"])
