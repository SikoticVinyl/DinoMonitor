import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
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

class RegionView(discord.ui.View):
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.select(placeholder="Choose a region", options=[discord.SelectOption(label=region, value=region) for region in EVRIMA_SERVERS.keys()])
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()
        self.value = select.values[0]
        self.stop()

class SelectView(discord.ui.View):
    def __init__(self, options, placeholder, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None
        self.select_menu = discord.ui.Select(placeholder=placeholder, options=options)
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        self.value = self.select_menu.values[0]
        self.stop()

class BackView(discord.ui.View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label="Back", style=discord.ButtonStyle.grey)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "back"
        self.stop()

class DinoTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('dino_tracker.db')
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
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

    @app_commands.command(name="update_dino", description="Update your dinosaur information")
    async def update_dino(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Check for alt accounts
        account_name = await self.select_account(interaction)
        if account_name is None:
            return

        # Select region and server
        region = await self.select_region(interaction)
        if region is None:
            return
        
        server = await self.select_server(interaction, region)
        if server is None:
            return

        # Select dinosaur type and specific dinosaur
        dino_type = await self.select_dino_type(interaction)
        if dino_type is None:
            return
        
        dinosaur = await self.select_dinosaur(interaction, dino_type)
        if dinosaur is None:
            return

        # Check if nested
        is_nested = await self.check_if_nested(interaction)
        if is_nested is None:
            return

        # Record mutations if nested
        mutations = []
        if is_nested:
            mutations = await self.select_mutations(interaction, dino_type)
            if mutations is None:
                return

        # Save to database
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM dino_records
            WHERE discord_id = ? AND account_name = ? AND server = ?
        ''', (interaction.user.id, account_name, server))

        cursor.execute('''
            INSERT INTO dino_records (discord_id, account_name, server, dinosaur, is_nested, date_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (interaction.user.id, account_name, server, dinosaur, is_nested, datetime.now()))
        record_id = cursor.lastrowid

        for mutation in mutations:
            cursor.execute("INSERT INTO mutations (record_id, mutation) VALUES (?, ?)",
                           (record_id, mutation))

        self.conn.commit()

        await interaction.followup.send(f"Updated dinosaur information for {account_name} on {server}", ephemeral=True)

    async def select_account(self, interaction: discord.Interaction) -> Optional[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT alt_accounts_enabled FROM user_settings WHERE discord_id = ?", (interaction.user.id,))
        result = cursor.fetchone()
        alt_accounts_enabled = result[0] if result else False

        if alt_accounts_enabled:
            cursor.execute("SELECT account_name FROM alt_accounts WHERE discord_id = ?", (interaction.user.id,))
            alt_accounts = cursor.fetchall()
            if alt_accounts:
                options = [discord.SelectOption(label=account[0], value=account[0]) for account in alt_accounts]
                options.append(discord.SelectOption(label="Main Account", value="main"))
                view = SelectView(options, "Choose an account")
                message = await interaction.followup.send("Select an account:", view=view, ephemeral=True)
                await view.wait()
                await message.delete()
                return view.value
            else:
                return "main"
        else:
            return "main"

    async def select_region(self, interaction: discord.Interaction) -> Optional[str]:
        options = [discord.SelectOption(label=region, value=region) for region in EVRIMA_SERVERS.keys()]
        view = SelectView(options, "Choose a region")
        message = await interaction.followup.send("Select a region:", view=view, ephemeral=True)
        await view.wait()
        await message.delete()
        return view.value

    async def select_server(self, interaction: discord.Interaction, region: str) -> Optional[str]:
        while True:
            options = [discord.SelectOption(label=server, value=server) for server in EVRIMA_SERVERS[region]]
            view = SelectView(options, "Choose a server")
            view.add_item(discord.ui.Button(label="Back", style=discord.ButtonStyle.grey, custom_id="back"))
            message = await interaction.followup.send(f"Select a server in {region}:", view=view, ephemeral=True)
            
            def check(i):
                return i.user.id == interaction.user.id and (i.data["custom_id"] == view.select_menu.custom_id or i.data["custom_id"] == "back")

            try:
                select_interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
                await message.delete()
                
                if select_interaction.data["custom_id"] == "back":
                    new_region = await self.select_region(interaction)
                    if new_region is None:
                        return None
                    region = new_region
                else:
                    return select_interaction.data["values"][0]
            except asyncio.TimeoutError:
                await message.delete()
                await interaction.followup.send("Selection timed out. Please try again.", ephemeral=True)
                return None

    async def select_dino_type(self, interaction: discord.Interaction) -> Optional[str]:
        options = [discord.SelectOption(label=dino_type, value=dino_type) for dino_type in DINOSAURS.keys()]
        view = SelectView(options, "Choose a dinosaur type")
        message = await interaction.followup.send("Select a dinosaur type:", view=view, ephemeral=True)
        await view.wait()
        await message.delete()
        return view.value

    async def select_dinosaur(self, interaction: discord.Interaction, dino_type: str) -> Optional[str]:
        while True:
            options = [discord.SelectOption(label=dino, value=dino) for dino in DINOSAURS[dino_type]]
            view = SelectView(options, "Choose a dinosaur")
            view.add_item(discord.ui.Button(label="Back", style=discord.ButtonStyle.grey, custom_id="back"))
            message = await interaction.followup.send(f"Select a {dino_type}:", view=view, ephemeral=True)
            
            def check(i):
                return i.user.id == interaction.user.id and (i.data["custom_id"] == view.select_menu.custom_id or i.data["custom_id"] == "back")

            try:
                select_interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
                await message.delete()
                
                if select_interaction.data["custom_id"] == "back":
                    new_dino_type = await self.select_dino_type(interaction)
                    if new_dino_type is None:
                        return None
                    dino_type = new_dino_type
                else:
                    return select_interaction.data["values"][0]
            except asyncio.TimeoutError:
                await message.delete()
                await interaction.followup.send("Selection timed out. Please try again.", ephemeral=True)
                return None

    async def check_if_nested(self, interaction: discord.Interaction) -> Optional[bool]:
        view = discord.ui.View()
        yes_button = discord.ui.Button(label="Yes", style=discord.ButtonStyle.green, custom_id="yes")
        no_button = discord.ui.Button(label="No", style=discord.ButtonStyle.red, custom_id="no")
        view.add_item(yes_button)
        view.add_item(no_button)

        message = await interaction.followup.send("Is the dinosaur nested?", view=view, ephemeral=True)

        def check(i):
            return i.user.id == interaction.user.id and i.data["custom_id"] in ["yes", "no"]

        try:
            button_interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
            await message.delete()
            return button_interaction.data["custom_id"] == "yes"
        except asyncio.TimeoutError:
            await message.delete()
            await interaction.followup.send("Selection timed out. Please try again.", ephemeral=True)
            return None

    async def select_mutations(self, interaction: discord.Interaction, dino_type: str) -> Optional[List[str]]:
        available_mutations = MUTATIONS[dino_type] + MUTATIONS["All"]
        options = [discord.SelectOption(label=mutation, value=mutation) for mutation in available_mutations]
        select_menu = discord.ui.Select(placeholder="Choose mutations", options=options, max_values=len(options))
        view = discord.ui.View()
        view.add_item(select_menu)

        message = await interaction.followup.send("Select mutations (if any):", view=view, ephemeral=True)

        def check(i):
            return i.user.id == interaction.user.id and i.data["custom_id"] == select_menu.custom_id

        try:
            select_interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
            await message.delete()
            return select_interaction.data["values"]
        except asyncio.TimeoutError:
            await message.delete()
            await interaction.followup.send("Selection timed out. Please try again.", ephemeral=True)
            return None

    @app_commands.command(name="server_info", description="View dinosaur information for a region")
    async def server_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Select region (this remains ephemeral)
        region = await self.select_region(interaction)

        if not region:
            return

        if region not in EVRIMA_SERVERS:
            await interaction.followup.send("Invalid region. Please choose from: " + ", ".join(EVRIMA_SERVERS.keys()), ephemeral=True)
            return

        servers = EVRIMA_SERVERS[region]
        cursor = self.conn.cursor()

        embed = discord.Embed(title=f"Dinosaur Information for {region}", color=discord.Color.blue())

        for server in servers:
            cursor.execute('''
                SELECT dinosaur, is_nested, COUNT(*) as count
                FROM dino_records
                WHERE server = ?
                GROUP BY dinosaur, is_nested
            ''', (server,))
            results = cursor.fetchall()

            if results:
                server_info = "\n".join([f"{dino}({'N' if nested else ''}) - {count}" for dino, nested, count in results])
                total_dinos = sum([count for _, _, count in results])
                embed.add_field(name=f"{server} - {total_dinos} dinos", value=server_info, inline=False)
            else:
                embed.add_field(name=server, value="No data available", inline=False)

        # Send the final embed as a public message
        await interaction.followup.send(embed=embed, ephemeral=False)

    async def select_region(self, interaction: discord.Interaction) -> Optional[str]:
        view = RegionView()
        message = await interaction.followup.send("Select a region:", view=view, ephemeral=True)

        await view.wait()
        await message.delete()

        if view.value is None:
            await interaction.followup.send("Selection timed out. Please try again.", ephemeral=True)
            return None

        return view.value

    @app_commands.command(name="my_dinos", description="View all your dinosaurs across servers")
    async def my_dinos(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT dr.account_name, dr.server, dr.dinosaur, dr.is_nested, dr.date_updated, GROUP_CONCAT(m.mutation, ', ') as mutations
            FROM dino_records dr
            LEFT JOIN mutations m ON dr.id = m.record_id
            WHERE dr.discord_id = ?
            GROUP BY dr.id
            ORDER BY dr.date_updated DESC
        ''', (interaction.user.id,))
        
        results = cursor.fetchall()

        if not results:
            await interaction.followup.send("You don't have any dinosaurs recorded.", ephemeral=True)
            return

        embeds = []
        for i, (account_name, server, dinosaur, is_nested, date_updated, mutations) in enumerate(results):
            embed = discord.Embed(title=f"Dinosaur {i+1}", color=discord.Color.green())
            embed.add_field(name="Account", value=account_name, inline=True)
            embed.add_field(name="Server", value=server, inline=True)
            embed.add_field(name="Dinosaur", value=dinosaur, inline=True)
            embed.add_field(name="Nested", value="Yes" if is_nested else "No", inline=True)
            embed.add_field(name="Last Updated", value=date_updated, inline=True)
            if mutations:
                embed.add_field(name="Mutations", value=mutations, inline=False)
            embeds.append(embed)

        paginator = pages.Paginator(pages=embeds, timeout=180)
        await paginator.respond(interaction, ephemeral=True)

async def setup(bot):
    await bot.add_cog(DinoTracker(bot))