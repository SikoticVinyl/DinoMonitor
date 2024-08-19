import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import asyncio

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('dino_tracker.db')
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            discord_id INTEGER PRIMARY KEY,
            alt_accounts_enabled BOOLEAN DEFAULT 0,
            num_alt_accounts INTEGER DEFAULT 0
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alt_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id INTEGER,
            account_name TEXT,
            FOREIGN KEY (discord_id) REFERENCES user_settings (discord_id)
        )
        ''')
        self.conn.commit()

    @app_commands.command(name="toggle_alt_accounts", description="Toggle alt accounts feature")
    async def toggle_alt_accounts(self, interaction: discord.Interaction, enable: bool):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO user_settings (discord_id, alt_accounts_enabled)
        VALUES (?, ?)
        """, (interaction.user.id, enable))
        self.conn.commit()
        
        if enable:
            await interaction.response.send_message("Alt accounts feature has been enabled. How many alt accounts do you want to set up? (Max 10)", ephemeral=True)
            
            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

            try:
                num_alts_msg = await self.bot.wait_for('message', check=check, timeout=30.0)
                num_alts = int(num_alts_msg.content)
                
                if num_alts < 1 or num_alts > 10:
                    await interaction.followup.send("Please enter a number between 1 and 10. You can adjust this later using the /set_num_alts command.", ephemeral=True)
                    return

                cursor.execute("""
                UPDATE user_settings SET num_alt_accounts = ? WHERE discord_id = ?
                """, (num_alts, interaction.user.id))
                self.conn.commit()

                await interaction.followup.send(f"Great! You've set up {num_alts} alt accounts. Let's name them now.", ephemeral=True)

                for i in range(1, num_alts + 1):
                    await interaction.followup.send(f"Please enter a name for alt account #{i}:", ephemeral=True)
                    name_msg = await self.bot.wait_for('message', check=check, timeout=30.0)
                    name = name_msg.content

                    cursor.execute("""
                    INSERT INTO alt_accounts (discord_id, account_name)
                    VALUES (?, ?)
                    """, (interaction.user.id, name))
                    self.conn.commit()

                await interaction.followup.send("All alt accounts have been set up successfully!", ephemeral=True)

            except asyncio.TimeoutError:
                await interaction.followup.send("You didn't respond in time. You can set up your alt accounts later using the /set_num_alts and /name_alt commands.", ephemeral=True)
            except ValueError:
                await interaction.followup.send("Invalid input. Please use the /set_num_alts command to try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Alt accounts feature has been disabled.", ephemeral=True)

    @app_commands.command(name="set_num_alts", description="Set the number of alt accounts")
    async def set_num_alts(self, interaction: discord.Interaction, num_alts: int):
        if num_alts < 0 or num_alts > 10:
            await interaction.response.send_message("Please enter a number between 0 and 10.", ephemeral=True)
            return

        cursor = self.conn.cursor()
        cursor.execute("""
        UPDATE user_settings SET num_alt_accounts = ? WHERE discord_id = ?
        """, (num_alts, interaction.user.id))
        self.conn.commit()

        # Clear existing alt accounts
        cursor.execute("DELETE FROM alt_accounts WHERE discord_id = ?", (interaction.user.id,))
        self.conn.commit()

        await interaction.response.send_message(f"Number of alt accounts set to {num_alts}. Use the /name_alt command to name your accounts.", ephemeral=True)

    @app_commands.command(name="name_alt", description="Name an alt account")
    async def name_alt(self, interaction: discord.Interaction, alt_number: int, name: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT num_alt_accounts FROM user_settings WHERE discord_id = ?", (interaction.user.id,))
        result = cursor.fetchone()

        if not result or alt_number > result[0]:
            await interaction.response.send_message("Invalid alt account number.", ephemeral=True)
            return

        cursor.execute("""
        INSERT OR REPLACE INTO alt_accounts (discord_id, account_name)
        VALUES (?, ?)
        """, (interaction.user.id, name))
        self.conn.commit()

        await interaction.response.send_message(f"Alt account {alt_number} named as '{name}'.", ephemeral=True)

    @app_commands.command(name="list_alts", description="List all your alt accounts")
    async def list_alts(self, interaction: discord.Interaction):
        cursor = self.conn.cursor()
        cursor.execute("SELECT account_name FROM alt_accounts WHERE discord_id = ?", (interaction.user.id,))
        results = cursor.fetchall()

        if not results:
            await interaction.response.send_message("You haven't set up any alt accounts yet.", ephemeral=True)
            return

        alt_list = "\n".join([f"{i+1}. {name[0]}" for i, name in enumerate(results)])
        await interaction.response.send_message(f"Your alt accounts:\n{alt_list}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Settings(bot))