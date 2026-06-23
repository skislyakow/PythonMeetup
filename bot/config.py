import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in .env")

ORGANIZER_IDS: list[int] = [
    int(x.strip()) for x in os.getenv("ORGANIZER_IDS", "").split(",") if x.strip()
]
