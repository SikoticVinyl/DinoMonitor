import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

class DinoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Cog loading logic
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
        
        await self.tree.sync()

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord!')
        print(f'Synced {len(self.tree.get_commands())} command(s)')

bot = DinoBot()

@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! Latency: {latency}ms")

if __name__ == "__main__":
    bot.run(TOKEN)