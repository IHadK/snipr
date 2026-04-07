import os
import json
import base64
import requests
import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ── CONFIG ──
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

REPO_OWNER = "skibidieli6236"
REPO_NAME = "qwfqwaf"
FILE_PATH = "status.json"
BRANCH = "main"

# ── AUTHORIZED USERS (starts with these, can be modified with commands) ──
AUTHORIZED_USERS = {
    976981112100384778,   # ← CHANGE THESE TO YOUR REAL DISCORD IDs
    983834,
    # Add more here if you want initial users
}

def is_authorized(interaction: discord.Interaction) -> bool:
    return interaction.user.id in AUTHORIZED_USERS

# ── GitHub Helpers ──
def get_file_sha():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()["sha"]
        print(f"[GitHub] GET failed: {r.status_code}")
        return None
    except Exception as e:
        print(f"[GitHub] Error getting SHA: {e}")
        return None

def update_status(locked: bool, lock_message: str = ""):
    if not GITHUB_TOKEN:
        print("[ERROR] GITHUB_TOKEN is missing!")
        return False
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

    try:
        r = requests.put(url, headers=headers, json=data, timeout=10)
        if r.status_code in (200, 201):
            print(f"[GitHub] Success → locked={locked}")
            return True
        else:
            print(f"[GitHub] PUT failed: {r.status_code} {r.text}")
            return False
    except Exception as e:
        print(f"[GitHub] Error updating status: {e}")
        return False

@bot.event
async def on_ready():
    if not DISCORD_TOKEN:
        print("[CRITICAL ERROR] DISCORD_TOKEN is missing from environment variables!")
        return
    if not GITHUB_TOKEN:
        print("[CRITICAL ERROR] GITHUB_TOKEN is missing from environment variables!")
        return

    print(f"✅ SNiPR Control Bot ready as {bot.user}")
    print(f"🔐 Authorized users: {len(AUTHORIZED_USERS)}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Sync error: {e}")

# ── COMMANDS ──

@bot.tree.command(name="lockdown", description="Lock SNiPR — logs everyone out + shows maintenance popup")
@app_commands.check(is_authorized)
async def lockdown(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    success = update_status(True, "under mainteneince contact owners if persists")
    if success:
        await interaction.followup.send("✅ **SNiPR LOCKED DOWN**\nAll users logged out.\nMaintenance popup active.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to update status on GitHub.", ephemeral=True)

@bot.tree.command(name="reopen", description="Reopen SNiPR — app works normally again")
@app_commands.check(is_authorized)
async def reopen(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    success = update_status(False, "")
    if success:
        await interaction.followup.send("✅ **SNiPR REOPENED**\nApp is fully functional again.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to update status on GitHub.", ephemeral=True)

@bot.tree.command(name="adduser", description="Add a user to authorized list (Owner only)")
@app_commands.check(is_authorized)
async def adduser(interaction: discord.Interaction, user_id: str):
    await interaction.response.defer(ephemeral=True)
    try:
        uid = int(user_id.strip())
        if uid in AUTHORIZED_USERS:
            await interaction.followup.send(f"❌ User `{uid}` is already authorized.", ephemeral=True)
            return
        AUTHORIZED_USERS.add(uid)
        await interaction.followup.send(f"✅ Added user `{uid}` to authorized list.", ephemeral=True)
        print(f"[Bot] Added user {uid} by {interaction.user}")
    except ValueError:
        await interaction.followup.send("❌ Invalid User ID. Must be a number.", ephemeral=True)

@bot.tree.command(name="removeuser", description="Remove a user from authorized list (Owner only)")
@app_commands.check(is_authorized)
async def removeuser(interaction: discord.Interaction, user_id: str):
    await interaction.response.defer(ephemeral=True)
    try:
        uid = int(user_id.strip())
        if uid not in AUTHORIZED_USERS:
            await interaction.followup.send(f"❌ User `{uid}` is not in the list.", ephemeral=True)
            return
        AUTHORIZED_USERS.remove(uid)
        await interaction.followup.send(f"✅ Removed user `{uid}` from authorized list.", ephemeral=True)
        print(f"[Bot] Removed user {uid} by {interaction.user}")
    except ValueError:
        await interaction.followup.send("❌ Invalid User ID. Must be a number.", ephemeral=True)

@bot.tree.command(name="listusers", description="List all authorized users")
@app_commands.check(is_authorized)
async def listusers(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    users = "\n".join([f"`{uid}`" for uid in sorted(AUTHORIZED_USERS)])
    await interaction.followup.send(f"**Authorized Users ({len(AUTHORIZED_USERS)}):**\n{users}", ephemeral=True)

bot.run(DISCORD_TOKEN)
