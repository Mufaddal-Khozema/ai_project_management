import os
import discord
import logging
from dotenv import load_dotenv
from taiga_client import TaigaClient
from agent import run_agent

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TAIGA_URL = os.getenv("TAIGA_URL")
TAIGA_USER = os.getenv("TAIGA_USER")
TAIGA_PASS = os.getenv("TAIGA_PASS")
TAIGA_PROJECT_SLUG = os.getenv("TAIGA_PROJECT_SLUG")
TRIGGER_ROLE_NAME = os.getenv("DISCORD_TRIGGER_ROLE_NAME", "FYP")

ALLOWED_ROLES = {"Project Manager", "Developer"}
DELETE_ROLES = {"Project Manager"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("discord_bot")

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
    logger.info("Logged in as %s", client.user)


@client.event
async def on_message(message):
    bot_mentioned = client.user.mentioned_in(message)
    role_mentions = [role.name for role in getattr(message, "role_mentions", [])]
    role_triggered = TRIGGER_ROLE_NAME in role_mentions
    logger.info(
        "on_message received author=%s channel=%s content=%r user_mentions=%s role_mentions=%s bot_mentioned=%s role_triggered=%s",
        message.author,
        getattr(message.channel, "name", "unknown"),
        message.content,
        [str(user) for user in getattr(message, "mentions", [])],
        role_mentions,
        bot_mentioned,
        role_triggered,
    )

    if message.author == client.user:
        logger.info("Ignoring own message")
        return

    if not bot_mentioned and not role_triggered and not message.content.startswith("!"):
        logger.info("Ignoring message because it was not a bot mention, trigger role mention, or command")
        return 

    logger.info("Message passed trigger gate")

    content = message.content
    if bot_mentioned or role_triggered:
        mention_variants = (
            f"<@{client.user.id}>",
            f"<@!{client.user.id}>",
        )

        for mention in mention_variants:
            content = content.replace(mention, "")

        for role in getattr(message, "role_mentions", []):
            content = content.replace(f"<@&{role.id}>", "")

        content = content.strip()

    logger.info("Normalized message content: %r", content)

    try:
        project_id = get_project_id()
        logger.info("Resolved Taiga project id: %s", project_id)
    except Exception as e:
        logger.exception("Failed to resolve Taiga project id")
        await message.channel.send(f"Could not reach Taiga project: {e}")
        return

    async with message.channel.typing():
        try:
            reply = run_agent(content, project_id)
            logger.info("Agent reply length: %s", len(reply) if reply else 0)
        except Exception as e:
            logger.exception("Agent execution failed")
            reply = f"Something went wrong: {e}"

    if not reply or not str(reply).strip():
        logger.warning("Agent returned an empty reply for message: %r", content)
        reply = "No response was generated. Check the bot logs for details."

    try:
        await message.channel.send(str(reply)[:2000])
        logger.info("Sent reply to Discord successfully")
    except Exception:
        logger.exception("Failed to send Discord reply")


client.run(TOKEN)