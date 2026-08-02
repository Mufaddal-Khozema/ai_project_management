import os
import re
import discord
import requests
from dotenv import load_dotenv
from agent import run_agent
from taiga_client import TaigaClient


load_dotenv()
TOKEN= os.getenv("DISCORD_TOKEN")
TAIGA_URL=os.getenv("TAIGA_URL")
TAIGA_USER = os.getenv("TAIGA_USER")
TAIGA_PASS = os.getenv("TAIGA_PASS")
TAIGA_PROJECT_SLUG = os.getenv("TAIGA_PROJECT_SLUG")
ALLOWED_CHANNEL_NAME = "taiga-bot"
ALLOWED_ROLES = {"Project Manager", "Developer"}
# DELETE_ROLES = {"Project Manager"}

intents = discord.Intents.default()
intents.message_content=True
intents.members =True
client = discord.Client(intents=intents)

taiga = TaigaClient(TAIGA_URL, TAIGA_USER, TAIGA_PASS)
_project_id_cache = None

# initial login
# def taiga_login():
#     resp=requests.post(f"{TAIGA_URL}/auth",json={
#         "type":"normal",
#         "username":TAIGA_USER,
#         "password":TAIGA_PASS
#     })
#     resp.raise_for_status()
#     return resp.json()["auth_token"]

def get_project_id():
    global _project_id_cache
    if _project_id_cache is None:
        _project_id_cache = taiga.get_project_id(TAIGA_PROJECT_SLUG)
    return _project_id_cache

@client.event
async def on_message(message):
    print("=== ON_MESSAGE FIRED ===")
    print(f"[DEBUG] channel={message.channel.name!r} content={message.content!r} author={message.author}")
    ...
    # DEBUG
    print(f"[DEBUG] channel={message.channel.name!r} content={message.content!r} author={message.author}")

    if message.author == client.user:
        return
    
    if message.channel.name != ALLOWED_CHANNEL_NAME:
        return
    
    if not client.user.mentioned_in(message) and not message.content.startswith("!"):
        return
    
    user_roles = {role.name for role in message.author.roles}
    # DEBUG
    print(f"[DEBUG] user_roles={user_roles}")

    if not user_roles & ALLOWED_ROLES:
        # 
        print("[DEBUG] role check failed, sending permission message")

        await message.channel.send("You dont have the permisson to use this bot!")
    return

    content= message.content
    if client.user.mentioned_in(message):
        content = content.replace(f"<@{client.user.id}","").strip()

    # 
    print(f"[DEBUG] about to fetch project_id")

    try:
        project_id = get_project_id()
        # 
        print(f"[DEBUG] project_id={project_id}")

    except Exception as e:
        # 
        print(f"[DEBUG] project_id fetch failed: {e!r}")

        await message.channel.send(f"Could not reach taiga Project: {e}")
        return
    
    # 
    print(f"[DEBUG] calling run_agent with content={content!r}")

    async with message.channel.typing():
        try:
            reply = run_agent(content,project_id)
            # 
            print(f"[DEBUG] reply={reply!r}")

        except Exception as e:
            # 
            print(f"[DEBUG] run_agent raised: {e!r}")

            reply = f"Something went wrong: {e}"

    await message.channel.send(reply[:2000])

client.run(TOKEN)
