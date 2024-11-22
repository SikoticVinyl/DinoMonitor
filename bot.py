import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
SIK_ID = int(os.getenv('SIK_ID'))

def is_owner():
    async def predicate(interaction: discord.Interaction):
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(predicate)

class DinoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        print("Setting up bot...")
        # Clear any existing commands first
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        print("Cleared all global commands")
        
        # Load cogs
        cogs_folder = './cogs'
        if os.path.exists(cogs_folder) and os.path.isdir(cogs_folder):
            for filename in os.listdir(cogs_folder):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f'Loaded extension: {filename[:-3]}')
                    except Exception as e:
                        print(f'Failed to load extension {filename[:-3]}: {e}')
        else:
            print('No cogs found. Skipping cog loading.')
        
        # Sync commands globally
        await self.tree.sync()
        print("Synced commands globally")

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord!')
        print("Registered commands:")
        for command in self.tree.get_commands():
            print(f"- {command.name}")

bot = DinoBot()
bot.owner_id = SIK_ID

@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! Latency: {latency}ms")

@bot.tree.command(name="sync", description="Manually sync commands")
@is_owner()
async def sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            await interaction.followup.send(f"Synced {len(synced)} commands to guild: {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            await interaction.followup.send(f"Synced {len(synced)} commands globally")
    except Exception as e:
        await interaction.followup.send(f"An error occurred while syncing commands: {str(e)}")

@bot.tree.command(name="clear_commands", description="Clear all commands and re-sync")
@is_owner()
async def clear_commands(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
        else:
            bot.tree.clear_commands()
            await bot.tree.sync()
        
        # Re-add all commands
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
        else:
            synced = await bot.tree.sync()
        
        await interaction.followup.send(f"Cleared all commands and re-synced {len(synced)} commands.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred while clearing and re-syncing commands: {str(e)}")

if __name__ == "__main__":
    bot.run(TOKEN)