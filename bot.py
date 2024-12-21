import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN') 
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
        try:
            # Load cogs first
            cogs_folder = './cogs'
            if os.path.exists(cogs_folder) and os.path.isdir(cogs_folder):
                for filename in os.listdir(cogs_folder):
                    if filename.endswith('.py'):
                        try:
                            await self.load_extension(f'cogs.{filename[:-3]}')
                            print(f'✓ Loaded extension: {filename[:-3]}')
                        except Exception as e:
                            print(f'✗ Failed to load extension {filename[:-3]}: {e}')
            else:
                print('No cogs folder found. Skipping cog loading.')
            
            # Sync commands globally
            print("Syncing commands globally...")
            synced = await self.tree.sync()
            print(f"Successfully synced {len(synced)} commands globally")
            
        except Exception as e:
            print(f"Error during setup: {str(e)}")

    async def on_ready(self):
        print(f'\n{self.user.name} is now online!')
        print(f'Bot ID: {self.user.id}')
        print("\nRegistered commands:")
        for command in self.tree.get_commands():
            print(f"- {command.name}")
        
        # Set custom status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="dinosaurs 🦖"
            )
        )

bot = DinoBot()
bot.owner_id = SIK_ID

@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(
        f"🏓 Pong! Latency: {latency}ms",
        ephemeral=True
    )

@bot.tree.command(name="sync", description="Manually sync commands (Owner only)")
@is_owner()
async def sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        print("Manually syncing commands...")
        synced = await bot.tree.sync()
        await interaction.followup.send(
            f"Successfully synced {len(synced)} commands globally ✓",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while syncing commands: {str(e)}",
            ephemeral=True
        )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound):
        return  # Ignore command not found errors
    print(f"Error: {str(error)}")

if __name__ == "__main__":
    try:
        print("Starting DinoBot...")
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Invalid bot token")
    except Exception as e:
        print(f"Error starting bot: {str(e)}")