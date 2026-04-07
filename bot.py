import os
import json
import base64
import requests
import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ── CONFIG (set these in Railway environment variables) ──
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

REPO_OWNER = "skibidieli6236"
REPO_NAME = "qwfqwaf"
FILE_PATH = "status.json"
BRANCH = "main"

# ── AUTHORIZED USERS (add as many Discord User IDs as you want here) ──
AUTHORIZED_USERS = {
    976981112100384778,          # example ID 1
    1197688708288237599,           # example ID 2
    # Add more here, one per line:
    # 123456789012345678,
    # 987654321098765432,
}

def is_authorized(interaction: discord.Interaction) -> bool:
    return interaction.user.id in AUTHORIZED_USERS

# Helper functions (get_file_sha, update_status) stay exactly the same as before...

def get_file_sha():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        return r.json()["sha"]
    print(f"[GitHub] GET failed: {r.status_code} {r.text}")
    return None

def update_status(locked: bool, lock_message: str):
    sha = get_file_sha()
    if not sha:
        return False

    payload = {
        "locked": locked,
        "lock_message": lock_message if locked else "",
        "version": "1.0"
    }

    content = json.dumps(payload, indent=2)
    b64_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "message": f"{'Lockdown' if locked else 'Reopen'} via Discord bot",
        "content": b64_content,
        "sha": sha,
        "branch": BRANCH
    }

    r = requests.put(url, headers=headers, json=data, timeout=10)
    if r.status_code in (200, 201):
        print(f"[GitHub] Updated status.json → locked={locked}")
        return True
    print(f"[GitHub] PUT failed: {r.status_code} {r.text}")
    return False

@bot.event
async def on_ready():
    print(f"✅ SNiPR Control Bot ready as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Sync error: {e}")

# ── COMMANDS (now support multiple authorized users) ──
@bot.tree.command(name="lockdown", description="Lock SNiPR — logs everyone out + shows maintenance popup")
@app_commands.check(is_authorized)
async def lockdown(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    success = update_status(True, "under mainteneince contact owners if persists")
    if success:
        await interaction.followup.send("✅ **SNiPR LOCKED DOWN**\nAll online users have been logged out.\nMaintenance popup is now showing.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to update status.json", ephemeral=True)

@bot.tree.command(name="reopen", description="Reopen SNiPR — app works normally again")
@app_commands.check(is_authorized)
async def reopen(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    success = update_status(False, "")
    if success:
        await interaction.followup.send("✅ **SNiPR REOPENED**\nApp is now fully functional again.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to update status.json", ephemeral=True)

bot.run(DISCORD_TOKEN)
