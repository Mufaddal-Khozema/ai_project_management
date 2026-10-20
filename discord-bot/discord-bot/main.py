import os
import asyncio
import discord
import logging
from dotenv import load_dotenv
from identity import get_taiga_integration, get_taiga_token, resolve
import requests
from agent import run_agent, get_taiga_client
import traceback
from discord_reply_format import build_messages

load_dotenv()
import memory
# from taiga_client import TaigaClient

TOKEN = os.getenv("DISCORD_TOKEN")
# TAIGA_URL = os.getenv("TAIGA_URL")
# TAIGA_USER = os.getenv("TAIGA_USER")
# TAIGA_PASS = os.getenv("TAIGA_PASS")
TAIGA_PROJECT_SLUG = os.getenv("TAIGA_PROJECT_SLUG")
TRIGGER_ROLE_NAME = os.getenv("DISCORD_TRIGGER_ROLE_NAME", "FYP")
HISTORY_TURNS = int(os.getenv("AGENT_HISTORY_TURNS", "10"))
MEMORY_MIN_SCORE = float(os.getenv("MEMORY_MIN_SCORE", "0.5"))

ALLOWED_ROLES = {"Project Manager", "Developer"}
DELETE_ROLES = {"Project Manager"}

logging.basicConfig(
    level =logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("discord_bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    logger.info("Logged in as %s", client.user)


@client.event
async def on_message(message):
    if message.author.bot:
        return
    
    bot_mentioned = client.user in message.mentions # this ignore everyother mentions
    # 
    role_triggered = any(r.name == TRIGGER_ROLE_NAME for r in message.role_mentions)

    if not (bot_mentioned or role_triggered or message.content.startswith("!")):
        return

    member_roles = {r.name for r in getattr(message.author, "roles", [])}
    if not member_roles & ALLOWED_ROLES:
        await message.channel.send("You don't have permissions to use this bot.")
        return

    # stripping mentions to normalize the text
    content = message.content 
    # 
    for mention in (f"<@{client.user.id}>", f"<@!{client.user.id}>"):
        content= content.replace(mention, "")
    for role in message.role_mentions:
        # 
        content= content.replace(f"<@&{role.id}>", "")
    content= content.strip()

    if not content:
        await message.channel.send("What would you like me to do?")
        return
    
    logger.info("Normalied message content: %r", content)

    try:
        ident= await asyncio.to_thread(
            resolve,
            message.author.id,
            getattr(message.guild, "id", None),
            message.channel.id,
        )
        logger.info(f"Type: {type(ident)}")
        logger.info(f"Identity: {ident}")

    except requests.exceptions.Timeout:
        await message.channel.send("The identity service isn't responding right now. Please try again shortly.")
        return
    
    except Exception:
        # traceback.print_exc()
        logger.exception("Identity lookup failed")
        await message.channel.send("Couldn't verify your account right now. Try again shortly.")
        return

    if not ident.linked or not ident.user:
        await message.channel.send("Your Discord account isn't linked yet. Please link it from the Dashboard")
        return

    taiga_integration = get_taiga_integration(ident)
    if not taiga_integration:
        await message.channel.send("Taiga isn't connected for your account. Please connect it from the dashboard")
        return

    try:
        token = get_taiga_token(taiga_integration)
    except Exception:
        logger.exception("Taiga token could not be read")
        token = None
    if not token:
        logger.error("Taiga integration for user %s has no usable token", ident.user.uuid)
        await message.channel.send("Your Taiga connection isn't usable right now. Please reconnect it from the dashboard.")
        return

    taiga = get_taiga_client(ident.user.uuid, token)
    
    try:
        project_id= await asyncio.to_thread(taiga.get_project_id, TAIGA_PROJECT_SLUG)
    except Exception as e:
        logger.exception("Failed to resolve Taiga project id")
        await message.channel.send(f"Could not reach Taiga project: {e}")
        return
    
    # memory lookup before saving, so the message can't match itself
    history, related = [],[]
    try:
        history = await asyncio.to_thread(memory.recent_history, message.channel.id, HISTORY_TURNS)
        # 
        related= await asyncio.to_thread(memory.search_similar, content, message.channel.id, 5)
        seen = {h.content for h in history}
        # 
        related = [r for r in related if r.content not in seen]
    except Exception:
        logger.exception("Memory lookup failed; continuing without it")

    # agent runs only once
    reply_ok = True
    async with message.channel.typing():
        try:
            reply = await asyncio.to_thread(run_agent, content, taiga, project_id, history, related)
        except Exception as e:
            logger.exception("Agent execution failed")
            reply=f"Something went wrong:{e}"
            reply_ok= False

    # 
    if not reply or not str(reply).strip():
        logger.warning("Agent returned an empty reply for message: %r", content)
        reply = "No response was generated"
        reply_ok=False

    reply =str(reply)

    # messages are sent once in chunks
    sent_messages = []
    try:
        for piece in build_messages(reply):
            sent_messages.append(await message.channel.send(piece))
    except Exception:
        logger.exception("Failed to send Discord reply")

    # only save when reply ok true and sent messages 
    if reply_ok and sent_messages:
        try:
            await asyncio.to_thread(
                memory.save_message,
                discord_message_id=message.id,
                guild_id= getattr(message.guild,"id", None),
                channel_id=message.channel.id, author_id=message.author.id,
                author_name=message.author.display_name, role="user", content=content)
            await asyncio.to_thread(
                memory.save_message,
                discord_message_id=sent_messages[0].id, guild_id=getattr(message.guild, "id", None),
                channel_id=message.channel.id, author_id=client.user.id,
                author_name=client.user.display_name, role="assistant", content=str(reply))
        except Exception:
            logger.exception("Failed to save messages")

if __name__=="__main__":
    memory.init_db()
    client.run(TOKEN)