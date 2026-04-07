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

# ── AUTHORIZED USERS ──
AUTHORIZED_USERS = {
    976981112100384778,   # ← Replace with your real Discord ID
    1197688708288237599,    # ← Replace with your real Discord ID
}

def is_authorized(interaction: discord.Interaction) -> bool:
    return interaction.user.id in AUTHORIZED_USERS

# ── GitHub Helpers with Better Debugging ──
def get_file_sha():
    if not GITHUB_TOKEN:
        print("[ERROR] GITHUB_TOKEN is missing from environment variables!")
        return None
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"[GitHub GET] Status: {r.status_code}")
        if r.status_code == 200:
            return r.json()["sha"]
        elif r.status_code == 404:
            print("[GitHub] status.json not found in repo!")
        elif r.status_code == 401 or r.status_code == 403:
            print("[GitHub] Authentication failed - check GITHUB_TOKEN permissions")
        return None
    except Exception as e:
        print(f"[GitHub GET Error] {e}")
        return None

def update_status(locked: bool, lock_message: str = ""):
    sha = get_file_sha()
    if not sha:
        print("[ERROR] Could not get SHA - update failed")
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
        print(f"[GitHub PUT] Status: {r.status_code}")
        if r.status_code in (200, 201):
            print(f"[SUCCESS] status.json updated → locked={locked}")
            return True
        else:
            print(f"[GitHub PUT Failed] {r.status_code} - {r.text}")
            return False
    except Exception as e:
        print(f"[GitHub PUT Error] {e}")
        return False

@bot.event
async def on_ready():
    print(f"✅ SNiPR Control Bot ready as {bot.user}")
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN is missing!")
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN is missing!")
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
        await interaction.followup.send("❌ Failed to update status on GitHub. Check Railway logs for details.", ephemeral=True)

@bot.tree.command(name="reopen", description="Reopen SNiPR — app works normally again")
@app_commands.check(is_authorized)
async def reopen(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    success = update_status(False, "")
    if success:
        await interaction.followup.send("✅ **SNiPR REOPENED**\nApp is fully functional again.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to update status on GitHub. Check Railway logs for details.", ephemeral=True)

@bot.tree.command(name="adduser", description="Add authorized user (by Discord ID)")
@app_commands.check(is_authorized)
async def adduser(interaction: discord.Interaction, user_id: str):
    await interaction.response.defer(ephemeral=True)
    try:
        uid = int(user_id)
        if uid in AUTHORIZED_USERS:
            await interaction.followup.send(f"❌ `{uid}` is already authorized.", ephemeral=True)
            return
        AUTHORIZED_USERS.add(uid)
        await interaction.followup.send(f"✅ Added `{uid}` to authorized users.", ephemeral=True)
    except:
        await interaction.followup.send("❌ Invalid User ID.", ephemeral=True)

@bot.tree.command(name="listusers", description="List authorized users")
@app_commands.check(is_authorized)
async def listusers(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    users = "\n".join([f"`{uid}`" for uid in sorted(AUTHORIZED_USERS)])
    await interaction.followup.send(f"**Authorized Users ({len(AUTHORIZED_USERS)}):**\n{users or 'None'}", ephemeral=True)

bot.run(DISCORD_TOKEN)
