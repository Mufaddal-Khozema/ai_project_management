import os, time, requests
from dotenv import load_dotenv
load_dotenv()

url = os.getenv("IDENTITY_URL")
print("URL:", url)

t = time.time()
try:
    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {os.getenv('IDENTITY_TOKEN')}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "provider": "discord",
            "external_id": "1319579537012424797",
            "guild_id": None,
            "channel_id": None,
        },
        timeout=(5, 90),
    )
    print(r.status_code, f"{time.time() - t:.1f}s")
    print(r.text[:500])
except Exception as e:
    print("FAILED after", f"{time.time() - t:.1f}s", type(e).__name__, e)