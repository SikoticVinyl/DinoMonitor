import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime
from typing import List, Optional

EVRIMA_SERVERS = {
    "Americas": ["NA 2 - West No AI", "NA 3 - West", "NA 4 - East", "NA 5- East", "CA 1 - Central", "SA 1 - East", "SA 2 - East"],
    "Europe": ["EU 1 - West", "EU 2 - West", "EU 3 - West", "EU 4 - Central No AI", "EU 5 - North", "EU 6 - South"],
    "Asia": ["AS 1 - South East", "AS 2 - South", "AS 3 - East"],
    "Australia": ["AU 1 - East"]
}
DINOSAURS = {
    "Carnivores": ["Carnotaurus", "Ceratosaurus", "Deinosuchus", "Dilophosaurus", "Herrerasaurus", "Omniraptor", "Pteranodon", "Troodon",],
    "Herbivores": ["Diabloceratops", "Dryosaurus", "Hypsilophodon", "Pachycephalosaurus", "Stegosaurus", "Tenontosaurus"],
    "Omnivores": ["Bepiposaurus", "Gallimimus", ]
}

MUTATIONS = {
    "Carnivores": ["Mutation1", "Mutation2", "Mutation3"],
    "Herbivores": ["Mutation4", "Mutation5", "Mutation6"],
    "Omnivores": ["Mutation7", "Mutation8", "Mutation9"],
    "All": ["Mutation10", "Mutation11", "Mutation12"]
}

class DinoTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('dino_tracker.db')
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                discord_id INTEGER,
                account_name TEXT,
                PRIMARY KEY (discord_id, account_name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dino_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER,
                account_name TEXT,
                server TEXT,
                dinosaur TEXT,
                is_nested BOOLEAN,
                date_updated TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mutations (
                record_id INTEGER,
                mutation TEXT,
                FOREIGN KEY (record_id) REFERENCES dino_records(id)
            )
        ''')
        self.conn.commit()

    @app_commands.command(name="add_alt", description="Add an alternate account")
    async def add_alt(self, interaction: discord.Interaction, account_name: str):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO accounts (discord_id, account_name) VALUES (?, ?)",
                       (interaction.user.id, account_name))
        self.conn.commit()
        await interaction.response.send_message(f"Added alternate account: {account_name}")

    @app_commands.command(name="update_dino", description="Update your dinosaur information")
    async def update_dino(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Check for alt accounts
        cursor = self.conn.cursor()
        cursor.execute("SELECT account_name FROM accounts WHERE discord_id = ?", (interaction.user.id,))
        alt_accounts = cursor.fetchall()

        if alt_accounts:
            account_name = await self.select_account(interaction, alt_accounts)
        else:
            account_name = "main"

        # Select server
        server = await self.select_server(interaction)

        # Select dinosaur
        dinosaur = await self.select_dinosaur(interaction)

        # Check if nested
        is_nested = await self.check_if_nested(interaction)

        # Record mutations if nested
        mutations = []
        if is_nested:
            mutations = await self.select_mutations(interaction, dinosaur)

        # Save to database
        cursor.execute('''
            INSERT INTO dino_records (discord_id, account_name, server, dinosaur, is_nested, date_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (interaction.user.id, account_name, server, dinosaur, is_nested, datetime.now()))
        record_id = cursor.lastrowid

        for mutation in mutations:
            cursor.execute("INSERT INTO mutations (record_id, mutation) VALUES (?, ?)",
                           (record_id, mutation))

        self.conn.commit()

        await interaction.followup.send(f"Updated dinosaur information for {account_name} on {server}")

    async def select_account(self, interaction: discord.Interaction, alt_accounts: List[tuple]) -> str:
        options = [discord.SelectOption(label=account[0], value=account[0]) for account in alt_accounts]
        options.append(discord.SelectOption(label="Main Account", value="main"))

        select_menu = discord.ui.Select(placeholder="Choose an account", options=options)
        view = discord.ui.View()
        view.add_item(select_menu)

        await interaction.followup.send("Select an account:", view=view)

        def check(i):
            return i.user.id == interaction.user.id and i.data["custom_id"] == select_menu.custom_id

        interaction = await self.bot.wait_for("interaction", check=check)
        return interaction.data["values"][0]

    async def select_server(self, interaction: discord.Interaction) -> str:
        options = []
        for region, servers in EVRIMA_SERVERS.items():
            for server in servers:
                options.append(discord.SelectOption(label=server, value=server))

        select_menu = discord.ui.Select(placeholder="Choose a server", options=options)
        view = discord.ui.View()
        view.add_item(select_menu)

        await interaction.followup.send("Select a server:", view=view)

        def check(i):
            return i.user.id == interaction.user.id and i.data["custom_id"] == select_menu.custom_id

        interaction = await self.bot.wait_for("interaction", check=check)
        return interaction.data["values"][0]

    async def select_dinosaur(self, interaction: discord.Interaction) -> str:
        options = []
        for category, dinos in DINOSAURS.items():
            for dino in dinos:
                options.append(discord.SelectOption(label=dino, value=dino))

        select_menu = discord.ui.Select(placeholder="Choose a dinosaur", options=options)
        view = discord.ui.View()
        view.add_item(select_menu)

        await interaction.followup.send("Select a dinosaur:", view=view)

        def check(i):
            return i.user.id == interaction.user.id and i.data["custom_id"] == select_menu.custom_id

        interaction = await self.bot.wait_for("interaction", check=check)
        return interaction.data["values"][0]

    async def check_if_nested(self, interaction: discord.Interaction) -> bool:
        view = discord.ui.View()
        yes_button = discord.ui.Button(label="Yes", style=discord.ButtonStyle.green)
        no_button = discord.ui.Button(label="No", style=discord.ButtonStyle.red)
        view.add_item(yes_button)
        view.add_item(no_button)

        await interaction.followup.send("Is the dinosaur nested?", view=view)

        def check(i):
            return i.user.id == interaction.user.id and i.data["custom_id"] in [yes_button.custom_id, no_button.custom_id]

        interaction = await self.bot.wait_for("interaction", check=check)
        return interaction.data["custom_id"] == yes_button.custom_id

    async def select_mutations(self, interaction: discord.Interaction, dinosaur: str) -> List[str]:
        dino_category = next(category for category, dinos in DINOSAURS.items() if dinosaur in dinos)
        available_mutations = MUTATIONS[dino_category] + MUTATIONS["All"]

        options = [discord.SelectOption(label=mutation, value=mutation) for mutation in available_mutations]
        select_menu = discord.ui.Select(placeholder="Choose mutations", options=options, max_values=len(options))
        view = discord.ui.View()
        view.add_item(select_menu)

        await interaction.followup.send("Select mutations (if any):", view=view)

        def check(i):
            return i.user.id == interaction.user.id and i.data["custom_id"] == select_menu.custom_id

        interaction = await self.bot.wait_for("interaction", check=check)
        return interaction.data["values"]

    @app_commands.command(name="server_info", description="View dinosaur information for a server")
    async def server_info(self, interaction: discord.Interaction, region: str):
        if region not in EVRIMA_SERVERS:
            await interaction.response.send_message("Invalid region. Please choose from: " + ", ".join(EVRIMA_SERVERS.keys()))
            return

        servers = EVRIMA_SERVERS[region]
        cursor = self.conn.cursor()

        embed = discord.Embed(title=f"Dinosaur Information for {region}", color=discord.Color.blue())

        for server in servers:
            cursor.execute('''
                SELECT dinosaur, COUNT(*) as count, GROUP_CONCAT(account_name) as players
                FROM dino_records
                WHERE server = ?
                GROUP BY dinosaur
            ''', (server,))
            results = cursor.fetchall()

            if results:
                server_info = "\n".join([f"{dino}: {count} ({players})" for dino, count, players in results])
                embed.add_field(name=server, value=server_info, inline=False)
            else:
                embed.add_field(name=server, value="No data available", inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(DinoTracker(bot))