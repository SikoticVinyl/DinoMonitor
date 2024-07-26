import discord
from discord.ext import commands
import requests

# Replace 'YOUR_BOT_TOKEN' with your bot's token
TOKEN = 'YOUR_BOT_TOKEN'
STEAM_API_KEY = 'YOUR_STEAM_API_KEY'

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'DinoMonitor is ready. Logged in as {bot.user}')

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command(name='linksteam')
async def link_steam(ctx, steam_id: str):
    # Save the Steam ID to a database (for now, just print it)
    await ctx.send(f'Steam ID {steam_id} linked!')

@bot.command(name='steamstats')
async def steam_stats(ctx, steam_id: str):
    response = requests.get(f'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steam_id}')
    data = response.json()
    
    if data['response']['players']:
        player = data['response']['players'][0]
        player_name = player['personaname']
        await ctx.send(f'Steam stats for {player_name}: {player}')
    else:
        await ctx.send('No player found with that Steam ID.')

# Run the bot
bot.run(TOKEN)
