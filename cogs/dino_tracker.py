import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
from datetime import datetime
from typing import List, Optional

GENDERS = ["Male", "Female"]

GAME_MODES = ["Hordetest", "Evrima Public Branch",]

SERVERS_BY_MODE = {
    "Hordetest": {
        "Americas": ["NA 1 - West", "NA 2 - West", "NA 3 - East", "NA 4 - East"],
        "Europe": ["EU 1 - West", "EU 2 - Central", "EU 3 - Central"],
    },
    "Evrima Public Branch": {
        "Americas": ["NA 2 - West", "NA 3 - West", "NA 4 - East", "NA 5- East", "CA 1 - Central", "SA 1 - East", "SA 2 - East"],
        "Europe": ["EU 1 - West", "EU 2 - West", "EU 3 - West", "EU 4 - Central", "EU 5 - North", "EU 6 - South"],
        "Asia": ["AS 1 - South East", "AS 2 - South", "AS 3 - East"],
        "Australia": ["AU 1 - East"]
    }
}

DINOSAURS = {
    "Carnivores": ["Carnotaurus", "Ceratosaurus", "Deinosuchus", "Dilophosaurus", "Herrerasaurus", "Omniraptor", "Pteranodon", "Troodon",],
    "Herbivores": ["Diabloceratops", "Dryosaurus", "Hypsilophodon", "Pachycephalosaurus", "Stegosaurus", "Tenontosaurus"],
    "Omnivores": ["Bepiposaurus", "Gallimimus", ]
}

MUTATIONS = {
    "Female": ["Advanced Gestation", "Prolific Reproduction", "Mutation3"],
    "Carnivores": ["Accelerated Prey Drive", "Hypermetabolic Inanition", "Hemomania", "Augmented Tapetum", "Cannibalistic", "Osteophagic"],
    "Herbivores": ["Barometric Sensitivity", "Photosynthetic Regeneration", "Hypervigilance", "Truculency", "Xerocole Adaptation", "Tactile Endurance"],
    "Omnivores": ["Mutation7", "Mutation8", "Mutation9"],
    "All": ["Hematophagy", "Hydrodynamic", "Photosynthetic Tissue", "Reabsorption", "Hydro-regenerative", "Cellular Regeneration", "Congenital Hypoalgesia", "Submerged Optical Retention ", "Efficient Digestion", "Increased Inspiratory Capacity", "Sustained Hydration", "Enlarged Meniscus", "Infrasound Communication", "Epidermal Fibrosis", "Nocturnal", "Wader", "Featherweight", "Osteosclerosis", "Gastronomic Regeneration", "Traumatic Thrombosis", "Heightened Ghrelin", "Multichambered Lungs", "Enhanced Digestion", "Reinforced Tendons", "Reniculate Kidneys",]
}

class GameModeView(discord.ui.View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.select(placeholder="Choose a game mode", options=[discord.SelectOption(label=mode, value=mode) for mode in GAME_MODES])
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()
        self.value = select.values[0]
        self.stop()

class RegionView(discord.ui.View):
    def __init__(self, game_mode: str, timeout=180):
        super().__init__(timeout=timeout)
        self.value = None
        self.game_mode = game_mode
        # Set up options immediately in __init__
        self.setup_options()

    def setup_options(self):
        # Get regions for the selected game mode
        regions = SERVERS_BY_MODE[self.game_mode].keys()
        # Create options for each region
        options = [discord.SelectOption(label=region, value=region) for region in regions]
        # Add the select menu with these options
        self.select_menu = discord.ui.Select(
            placeholder="Choose a region",
            options=options
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.value = self.select_menu.values[0]
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

class DinoTrackerView(discord.ui.View):
    def __init__(self, cog: 'DinoTracker', user_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.user_id = user_id
        self.current_account = None
        self.current_page = 0
        self.embeds = []
        
        # Initialize account select with main account
        self.account_select = discord.ui.Select(
            placeholder="Select an account",
            options=[discord.SelectOption(label="Main Account", value="main")]
        )
        self.account_select.callback = self.account_select_callback
        self.add_item(self.account_select)

    async def account_select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.current_account = self.account_select.values[0]
        self.current_page = 0
        await self.update_dino_display(interaction)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray, disabled=True, row=1)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = max(0, self.current_page - 1)
        await self.update_dino_display(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray, disabled=True, row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        await self.update_dino_display(interaction)

    @discord.ui.button(label="Done", style=discord.ButtonStyle.red, row=1)
    async def done_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    async def update_dino_display(self, interaction: discord.Interaction):
        if self.current_account:
            self.embeds = await self.cog.get_account_dinos(self.user_id, self.current_account)
            if self.embeds:
                embed = self.embeds[self.current_page]
                embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.embeds)}")
                self.previous_button.disabled = (self.current_page == 0)
                self.next_button.disabled = (self.current_page == len(self.embeds) - 1)
                await interaction.edit_original_response(embed=embed, view=self)
            else:
                await interaction.edit_original_response(content=f"No dinosaurs found for account: {self.current_account}", embed=None, view=self)
        else:
            await interaction.edit_original_response(content="Please select an account", embed=None, view=self)

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
                game_mode TEXT,
                server TEXT,
                dinosaur TEXT,
                gender TEXT,
                is_nested BOOLEAN,
                date_updated TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mutations (
                record_id INTEGER,
                mutation TEXT,
                is_inherited BOOLEAN,
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

        # Select game mode first
        game_mode = await self.select_game_mode(interaction)
        if game_mode is None:
            return

        # Select region and server based on game mode
        region = await self.select_region(interaction, game_mode)
        if region is None:
            return
        
        server = await self.select_server(interaction, game_mode, region)
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
            INSERT INTO dino_records 
            (discord_id, account_name, game_mode, server, dinosaur, is_nested, date_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (interaction.user.id, account_name, game_mode, server, dinosaur, is_nested, datetime.now()))
        record_id = cursor.lastrowid

        for mutation in mutations:
            cursor.execute("INSERT INTO mutations (record_id, mutation) VALUES (?, ?)",
                           (record_id, mutation))

        self.conn.commit()

        await interaction.followup.send(f"Updated dinosaur information for {account_name} on {server}", ephemeral=True)

    async def select_account(self, interaction: discord.Interaction) -> Optional[str]:
        cursor = self.conn.cursor()
    
        # Check if alt accounts are enabled for this user
        cursor.execute("""
            SELECT alt_accounts_enabled, num_alt_accounts 
            FROM user_settings 
            WHERE discord_id = ?
        """, (interaction.user.id,))
    
        result = cursor.fetchone()
        if not result or not result[0]:  # If no settings or alt accounts disabled
            return "main"
    
        # Get all alt accounts
        cursor.execute("""
            SELECT account_name 
            FROM alt_accounts 
            WHERE discord_id = ?
        """, (interaction.user.id,))
    
        alt_accounts = cursor.fetchall()
        if not alt_accounts:
            return "main"
        
        # Create options for account selection
        options = [discord.SelectOption(label="Main Account", value="main")]
        options.extend([
            discord.SelectOption(label=account[0], value=account[0]) 
            for account in alt_accounts
            ])
    
        view = SelectView(options, "Choose an account")
        message = await interaction.followup.send(
            "Select an account:", 
            view=view, 
            ephemeral=True
            )
    
        await view.wait()
        await message.delete()
    
        if view.value is None:
            await interaction.followup.send(
                "Selection timed out. Please try again.", 
                ephemeral=True
            )
            return None
        return view.value

    async def select_game_mode(self, interaction: discord.Interaction) -> Optional[str]:
        view = GameModeView()
        message = await interaction.followup.send("Select a game mode:", view=view, ephemeral=True)
        await view.wait()
        await message.delete()
        return view.value

    async def select_region(self, interaction: discord.Interaction, game_mode: str) -> Optional[str]:
        try:
            view = RegionView(game_mode)
            message = await interaction.followup.send("Select a region:", view=view, ephemeral=True)
        
            await view.wait()
            await message.delete()
        
            if view.value is None:
                await interaction.followup.send("Selection timed out. Please try again.", ephemeral=True)
                return None
            
            return view.value
        
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
        return None

    async def select_server(self, interaction: discord.Interaction, game_mode: str, region: str) -> Optional[str]:
        while True:
            options = [
                discord.SelectOption(label=server, value=server)
                for server in SERVERS_BY_MODE[game_mode][region]
            ]
            view = SelectView(options, "Choose a server")
            view.add_item(discord.ui.Button(label="Back", style=discord.ButtonStyle.grey, custom_id="back"))
            message = await interaction.followup.send(f"Select a server in {region}:", view=view, ephemeral=True)
            
            def check(i):
                return i.user.id == interaction.user.id and (
                    i.data["custom_id"] == view.select_menu.custom_id or 
                    i.data["custom_id"] == "back"
                )

            try:
                select_interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
                await message.delete()
                
                if select_interaction.data["custom_id"] == "back":
                    new_region = await self.select_region(interaction, game_mode)
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
    
    # Select game mode first
        game_mode = await self.select_game_mode(interaction)
        if game_mode is None:
            return

    # Select region based on game mode
        region = await self.select_region(interaction, game_mode)  # Now passing game_mode
        if region is None:
            return

        if region not in SERVERS_BY_MODE[game_mode]:
            await interaction.followup.send(
                "Invalid region. Please choose from: " + 
                ", ".join(SERVERS_BY_MODE[game_mode].keys()), 
                ephemeral=True
            )
            return

        servers = SERVERS_BY_MODE[game_mode][region]
        cursor = self.conn.cursor()

        embed = discord.Embed(title=f"Dinosaur Information for {region} ({game_mode})", color=discord.Color.blue())

        for server in servers:
            cursor.execute('''
                SELECT dinosaur, is_nested, COUNT(*) as count
                FROM dino_records
                WHERE server = ? AND game_mode = ?
                GROUP BY dinosaur, is_nested
            ''', (server, game_mode))
            results = cursor.fetchall()

            if results:
                server_info = "\n".join([f"{dino}({'N' if nested else ''}) - {count}" for dino, nested, count in results])
                total_dinos = sum([count for _, _, count in results])
                embed.add_field(name=f"{server} - {total_dinos} dinos", value=server_info, inline=False)
            else:
                embed.add_field(name=server, value="No data available", inline=False)

        # Send the final embed as a public message
        await interaction.followup.send(embed=embed, ephemeral=False)
    
    @app_commands.command(name="my_dinos", description="View your dinosaurs across accounts and servers")
    async def my_dinos(self, interaction: discord.Interaction):
        # Check if alt accounts are enabled
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT alt_accounts_enabled 
            FROM user_settings 
            WHERE discord_id = ?
        """, (interaction.user.id,))
    
        result = cursor.fetchone()
        alt_accounts_enabled = result[0] if result else False
    
        if alt_accounts_enabled:
            # Get all accounts including main
            cursor.execute("""
                SELECT account_name 
                FROM alt_accounts 
                WHERE discord_id = ?
            """, (interaction.user.id,))
        
            accounts = ["main"] + [row[0] for row in cursor.fetchall()]
        else:
            accounts = ["main"]
    
        view = DinoTrackerView(self, interaction.user.id)
        view.account_select.options = [
            discord.SelectOption(label=account, value=account) 
            for account in accounts
        ]
    
        await interaction.response.send_message(
            "Loading your dinosaurs...", 
            view=view, 
            ephemeral=True
        )
        await view.update_dino_display(interaction)

async def get_user_accounts(self, user_id: int) -> list:
    cursor = self.conn.cursor()
    
    # Check if alt accounts are enabled
    cursor.execute("""
        SELECT alt_accounts_enabled 
        FROM user_settings 
        WHERE discord_id = ?
    """, (user_id,))
    
    result = cursor.fetchone()
    if not result or not result[0]:
        return ["main"]
    
    # Get all alt accounts
    cursor.execute("""
        SELECT account_name 
        FROM alt_accounts 
        WHERE discord_id = ?
    """, (user_id,))
    
    accounts = ["main"] + [row[0] for row in cursor.fetchall()]
    return accounts


    async def get_account_dinos(self, user_id: int, account_name: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT dr1.server, dr1.dinosaur, dr1.is_nested, dr1.date_updated, GROUP_CONCAT(m.mutation, ', ') as mutations
            FROM dino_records dr1
            LEFT JOIN mutations m ON dr1.id = m.record_id
            WHERE dr1.discord_id = ? AND dr1.account_name = ?
            AND dr1.date_updated = (
                SELECT MAX(dr2.date_updated)
                FROM dino_records dr2
                WHERE dr2.discord_id = dr1.discord_id
                AND dr2.account_name = dr1.account_name
                AND dr2.server = dr1.server
            )
            GROUP BY dr1.server
            ORDER BY dr1.date_updated DESC
        ''', (user_id, account_name))
        
        results = cursor.fetchall()
        embeds = []
        for server, dinosaur, is_nested, date_updated, mutations in results:
            embed = discord.Embed(title=f"Dinosaur on {server}", color=discord.Color.green())
            embed.add_field(name="Account", value=account_name, inline=True)
            embed.add_field(name="Dinosaur", value=dinosaur, inline=True)
            embed.add_field(name="Nested", value="Yes" if is_nested else "No", inline=True)
            embed.add_field(name="Last Updated", value=date_updated, inline=True)
            if mutations:
                embed.add_field(name="Mutations", value=mutations, inline=False)
            embeds.append(embed)
        return embeds


async def setup(bot):
    await bot.add_cog(DinoTracker(bot))