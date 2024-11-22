# DinoTracker Bot - User Guide and Deployment Instructions

## Overview
DinoTracker is a Discord bot designed to help players track their dinosaurs across different servers in The Isle. The bot supports multiple accounts per user and provides rough server population information based on user input. This information is only as acurate as those updating and using it. (For now?)

## User Guide

### Getting Started
1. First-time setup:
   - Use `/toggle_alt_accounts` to enable/disable alt account tracking
   - If enabled, you'll be prompted to set up your alt accounts (up to 10)
   - Each alt account needs a unique name

### Managing Alt Accounts
- `/set_num_alts` - Change number of alt accounts (0-10)
- `/name_alt` - Name or rename specific alt accounts
- `/list_alts` - View all your configured alt accounts

### Tracking Your Dinosaurs
1. Adding/Updating a dinosaur:
   - Use `/update_dino`
   - Select account (main or alt)
   - Choose game mode (Hordetest/Evrima)
   - Select region and server
   - Pick dinosaur type and specific dinosaur
   - Set gender and nested status
   
2. Viewing your dinosaurs:
   - Use `/my_dinos` to see all your tracked dinosaurs
   - Switch between accounts using the dropdown
   - Use Previous/Next buttons to navigate multiple entries

### Server Information
- Use `/server_info` to view dinosaur populations
- Shows number of dinosaurs per server
- Indicates nested status with (N)
- Displays total dinosaur count per server