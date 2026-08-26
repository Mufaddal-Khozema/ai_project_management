import logging
import os
from dotenv import load_dotenv

try:
    from taiga_client import TaigaClient
except ImportError:
    from .taiga_client import TaigaClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("discord_bot.taiga_test")


taiga_url = os.getenv("TAIGA_URL")
taiga_user = os.getenv("TAIGA_USER")
taiga_pass = os.getenv("TAIGA_PASS")

client = TaigaClient(base_url=taiga_url, username=taiga_user, password=taiga_pass)


# def create_item(resource, subject, description=None):
#     payload = {"subject": subject, "description": description}
#     return client.create(resource, payload)

def create_item(resource, subject, description=None):
    logger.info("Creating test item resource=%s subject=%s", resource, subject)
    project_id = client.get_project_id("ghulam_hasnain-fyp")

    payload = {
        "project": project_id,
        "subject": subject,
        "description": description,
    }

    return client.create(resource, payload)

if __name__ == "__main__":
    logger.info("Starting taiga-test sanity check")
    client.login()  # Authenticate and get the token

    # Example usage
    resource = "issues"  # or "tasks", "userstories", "epics
    subject = "Sample Issue"
    description = "This is a sample issue created via the TaigaClient."
    response = create_item(resource, subject, description)
    logger.info("Created item response: %s", response)
    print("Created item:", response)
