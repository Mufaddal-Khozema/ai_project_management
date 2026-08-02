import os
import discord
from dotenv import load_dotenv
from taiga_client import TaigaClient
from agent import run_agent

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TAIGA_URL = os.getenv("TAIGA_URL")
TAIGA_USER = os.getenv("TAIGA_USER")
TAIGA_PASS = os.getenv("TAIGA_PASS")
TAIGA_PROJECT_SLUG = os.getenv("TAIGA_PROJECT_SLUG")

ALLOWED_CHANNEL_NAME = "taiga-bot"
ALLOWED_ROLES = {"Project Manager", "Developer"}
DELETE_ROLES = {"Project Manager"}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

taiga = TaigaClient(TAIGA_URL, TAIGA_USER, TAIGA_PASS)
_project_id_cache = None

def get_project_id():
    global _project_id_cache
    if _project_id_cache is None:
        _project_id_cache = taiga.get_project_id(TAIGA_PROJECT_SLUG)
    return _project_id_cache


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.name != ALLOWED_CHANNEL_NAME:
        return

    if not client.user.mentioned_in(message) and not message.content.startswith("!"):
        return 

    user_roles = {role.name for role in message.author.roles}
    if not user_roles & ALLOWED_ROLES:
        await message.channel.send("You don't have permission to use this bot.")
        return

    content = message.content
    if client.user.mentioned_in(message):
        content = content.replace(f"<@{client.user.id}>", "").strip()

    try:
        project_id = get_project_id()
    except Exception as e:
        await message.channel.send(f"Could not reach Taiga project: {e}")
        return

    async with message.channel.typing():
        try:
            reply = run_agent(content, project_id)
        except Exception as e:
            reply = f"Something went wrong: {e}"

    await message.channel.send(reply[:2000])


client.run(TOKEN)