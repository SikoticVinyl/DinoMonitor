import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import asyncio
from datetime import datetime
from typing import Optional, List

GENDERS = ["Male", "Female"]

GAME_MODES = ["Hordetest", "Evrima Public Branch"]

SERVERS_BY_MODE = {
    "Hordetest": {
        "Americas": ["NA 1 - West", "NA 2 - West No AI", "NA 3 - East", "NA 4 - East"],
        "Europe": ["EU 1 - West", "EU 2 - Central", "EU 3 - Central No AI", "EU 4 - Central"],
    },
    "Evrima Public Branch": {
        "Americas": ["NA 2 - West", "NA 3 - West", "NA 4 - East", "NA 5- East", "CA 1 - Central", "SA 1 - East", "SA 2 - East"],
        "Europe": ["EU 1 - West", "EU 2 - West", "EU 3 - West", "EU 4 - Central", "EU 5 - North", "EU 6 - South", "EU 7 - South"],
        "Asia": ["AS 1 - South East", "AS 2 - South", "AS 3 - East"],
        "Australia": ["AU 1 - East", "AU 2 - East"]
    }
}

DINOSAURS = {
    "Carnivores": ["Carnotaurus", "Ceratosaurus", "Deinosuchus", "Dilophosaurus", "Herrerasaurus", "Omniraptor", "Pteranodon", "Troodon"],
    "Herbivores": ["Diabloceratops", "Dryosaurus", "Hypsilophodon", "Pachycephalosaurus", "Stegosaurus", "Tenontosaurus", "Maiasaura"],
    "Omnivores": ["Bepiposaurus", "Gallimimus"]
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
        self.setup_options()

    def setup_options(self):
        regions = SERVERS_BY_MODE[self.game_mode].keys()
        options = [discord.SelectOption(label=region, value=region) for region in regions]
        self.select_menu = discord.ui.Select(placeholder="Choose a region", options=options)
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
        await interaction.response.defer()
        self.value = self.select_menu.values[0]
        self.stop()

class DinoTrackerView(discord.ui.View):
    def __init__(self, cog: 'DinoTracker', user_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.current_account = None
        self.current_page = 0
        self.embeds = []
        
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
            cursor = self.cog.conn.cursor()
            cursor.execute('''
                SELECT server, dinosaur, gender, is_nested, date_updated, game_mode
                FROM dino_records
                WHERE discord_id = ? AND account_name = ?
                ORDER BY date_updated DESC
            ''', (self.user_id, self.current_account))
            
            results = cursor.fetchall()
            self.embeds = []
            
            if results:
                for server, dinosaur, gender, is_nested, date_updated, game_mode in results:
                    embed = discord.Embed(
                        title=f"Dinosaur on {server}",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Account", value=self.current_account, inline=True)
                    embed.add_field(name="Game Mode", value=game_mode, inline=True)
                    embed.add_field(name="Dinosaur", value=dinosaur, inline=True)
                    embed.add_field(name="Gender", value=gender, inline=True)
                    embed.add_field(name="Nested", value="Yes" if is_nested else "No", inline=True)
                    embed.add_field(name="Last Updated", value=date_updated, inline=True)
                    self.embeds.append(embed)
                
                embed = self.embeds[self.current_page]
                embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.embeds)}")
                self.previous_button.disabled = (self.current_page == 0)
                self.next_button.disabled = (self.current_page == len(self.embeds) - 1)
                await interaction.edit_original_response(embed=embed, view=self)
            else:
                await interaction.edit_original_response(
                    content=f"No dinosaurs found for account: {self.current_account}",
                    embed=None,
                    view=self
                )
        else:
            await interaction.edit_original_response(
                content="Please select an account",
                embed=None,
                view=self
            )

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
        self.conn.commit()

    @app_commands.command(name="update_dino", description="Update your dinosaur information")
    async def update_dino(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        account_name = await self.select_account(interaction)
        if account_name is None:
            return

        game_mode = await self.select_game_mode(interaction)
        if game_mode is None:
            return

        region = await self.select_region(interaction, game_mode)
        if region is None:
            return
    
        server = await self.select_server(interaction, game_mode, region)
        if server is None:
            return

        dino_type = await self.select_dino_type(interaction)
        if dino_type is None:
            return
    
        dinosaur = await self.select_dinosaur(interaction, dino_type)
        if dinosaur is None:
            return

        gender = await self.select_gender(interaction)
        if gender is None:
            return

        is_nested = await self.check_if_nested(interaction)
        if is_nested is None:
            return

        cursor = self.conn.cursor()
    
        cursor.execute('''
            DELETE FROM dino_records
            WHERE discord_id = ? AND account_name = ? AND server = ?
        ''', (interaction.user.id, account_name, server))

        cursor.execute('''
            INSERT INTO dino_records 
            (discord_id, account_name, game_mode, server, dinosaur, gender, is_nested, date_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (interaction.user.id, account_name, game_mode, server, dinosaur, gender, is_nested, datetime.now()))
    
        self.conn.commit()

        await interaction.followup.send(
            f"Updated dinosaur information for {account_name} on {server}", 
            ephemeral=True
        )

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
    
    async def select_gender(self, interaction: discord.Interaction) -> Optional[str]:
        options = [discord.SelectOption(label=gender, value=gender) for gender in GENDERS]
        view = SelectView(options, "Choose gender")
        message = await interaction.followup.send("Select gender:", view=view, ephemeral=True)
        await view.wait()
        await message.delete()
        return view.value

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

    @app_commands.command(name="server_info", description="View dinosaur information for a region")
    async def server_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
    
        game_mode = await self.select_game_mode(interaction)
        if game_mode is None:
            return

        region = await self.select_region(interaction, game_mode)
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

        embed = discord.Embed(
            title=f"Dinosaur Information for {region} ({game_mode})",
            color=discord.Color.blue()
        )

        for server in servers:
            cursor.execute('''
                SELECT dinosaur, is_nested, COUNT(*) as count
                FROM dino_records
                WHERE server = ? AND game_mode = ?
                GROUP BY dinosaur, is_nested
            ''', (server, game_mode))
            
            results = cursor.fetchall()

            if results:
                server_info = "\n".join([
                    f"{dino}({'N' if nested else ''}) - {count}"
                    for dino, nested, count in results
                ])
                total_dinos = sum([count for _, _, count in results])
                embed.add_field(
                    name=f"{server} - {total_dinos} dinos",
                    value=server_info,
                    inline=False
                )
            else:
                embed.add_field(name=server, value="No data available", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=False)
    
    @app_commands.command(name="my_dinos", description="View your dinosaurs across accounts and servers")
    async def my_dinos(self, interaction: discord.Interaction):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT alt_accounts_enabled 
            FROM user_settings 
            WHERE discord_id = ?
        """, (interaction.user.id,))
    
        result = cursor.fetchone()
        alt_accounts_enabled = result[0] if result else False
    
        if alt_accounts_enabled:
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

async def setup(bot):
    await bot.add_cog(DinoTracker(bot))