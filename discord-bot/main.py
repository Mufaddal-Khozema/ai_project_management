import os
import re
import discord
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN= os.getenv("DISCORD_TOKEN")
TAIGA_URL=os.getenv("TAIGA_URL")
TAIGA_USER = os.getenv("TAIGA_USER")
TAIGA_PASS = os.getenv("TAIGA_PASS")
TAIGA_PROJECT_SLUG = os.getenv("TAIGA_PROJECT_SLUG")
ALLOWED_CHANNEL_NAME = "taiga-bot"
ALLOWED_ROLES = {"Project Manager", "Developer"}

intents = discord.Intents.default()
intents.message_content=True
intents.members =True
client = discord.Client(intents=intents)
_cached_token = None

# initial login
def taiga_login():
    resp=requests.post(f"{TAIGA_URL}/auth",json={
        "type":"normal",
        "username":TAIGA_USER,
        "password":TAIGA_PASS
    })
    resp.raise_for_status()
    return resp.json()["auth_token"]

def get_project_id(token):
    headers= {"Authorization": f"Bearer {token}"}
    resp=requests.get(
        f"{TAIGA_URL}/projects/by_slug?",
        params={"slug": TAIGA_PROJECT_SLUG},
        headers=headers
    )
    resp.raise_for_status()
    return resp.json()["id"]

def get_taiga_token():
    global _cached_token
    if _cached_token is None:
        _cached_token = taiga_login()
    return _cached_token

def create_taiga_issue(subject, description=""):
    token=get_taiga_token()
    try:
        project_id = get_project_id(token)
    except requests.HTTPError as e:
        # token was expired needs to login again
        if e.response.status_code == 401:  
            token = taiga_login()
            _cached_token = token
            project_id = get_project_id(token)
        else:
            raise

    headers = {"Authorization": f"Bearer {token}"}
    payload={
        "project": project_id,
        "subject": subject,
        "description":description
    }
    resp = requests.post(f"{TAIGA_URL}/issues", json= payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):

    # check for roles
    print(message.author.roles)

    if message.author == client.user:
        return
    
    if message.channel.name!=ALLOWED_CHANNEL_NAME:
        return
    
    if message.content.strip() == "!issue":
        await message.channel.send("Usage: `!issue Title | Optional description`")
        return
    
    # matches a discord message that starts with !issue, followed by one or more whitespaces and captures what ever is written afterwords.
    match=re.match(r"!issue\s+(.+)", message.content)

    if match:
        # check if the user role exists in the defined roles 
        user_roles = {role.name for role in message.author.roles}

        if not user_roles & ALLOWED_ROLES:
            await message.channel.send("You don't have permission to proceed with the action.")
            return
        # to match the first regex group only
        content= match.group(1)

        # if user writes "Login Button | Doesnt work" then split from | and separate it into title and description
        if "|" in content:
            title, description = content.split("|", 1)
        else:
            title, description= content, ""

        try:
            issue= create_taiga_issue(title.strip(), description.strip())
            await message.channel.send(f"Issue was successfully created in Taiga #{issue['ref']}:{issue['subject']}")
        except Exception as e:
            await message.channel.send(f"Failed to create issue: {e}")

client.run(TOKEN)