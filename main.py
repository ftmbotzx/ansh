# Don't Remove Credits: Fᴛᴍ Dᴇᴠᴇʟᴏᴘᴇʀᴢ
import os
import re
import time
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
from motor.motor_asyncio import AsyncIOMotorClient

# ====== CONFIG ======
API_ID = int(os.getenv("API_ID", "8012239"))
API_HASH = os.getenv("API_HASH", "171e6f1bf66ed8dcc5140fbe827b6b08")
STRING_SESSION = os.getenv("STRING_SESSION")
INVITE_LINK = os.getenv("INVITE_LINK", "https://t.me/+l-llfMQyh245ZWVl")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "albums.txt")
ALBUM_REGEX = os.getenv("ALBUM_REGEX", r"💽 Album:\s*(\d+)")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "telegram_scraper"
COLLECTION = "progress"
# ====================

# Mongo setup
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]
progress_col = db[COLLECTION]

async def get_last_processed(channel_id: int):
    """Fetch last processed message ID from MongoDB."""
    doc = await progress_col.find_one({"channel_id": channel_id})
    return doc["last_message_id"] if doc else 0

async def update_last_processed(channel_id: int, message_id: int):
    """Update last processed message ID in MongoDB."""
    await progress_col.update_one(
        {"channel_id": channel_id},
        {"$set": {"last_message_id": message_id}},
        upsert=True
    )

async def main(client):
    # Join channel if not already
    try:
        entity = await client.get_entity(INVITE_LINK)
        await client(JoinChannelRequest(entity))
        print("[+] Joined the channel successfully!")
    except UserAlreadyParticipantError:
        print("[+] Already a member of the channel.")
        entity = await client.get_entity(INVITE_LINK)

    channel = await client.get_entity(entity)
    channel_name = channel.title
    channel_id = channel.id
    print(f"[+] Extracting from channel: {channel_name}")

    # Total messages
    history = await client.get_messages(channel, limit=0)
    total_count = history.total
    print(f"[i] Total messages in channel: {total_count}")

    # Resume from Mongo
    last_processed = await get_last_processed(channel_id)
    print(f"[i] Resuming from message ID: {last_processed}")

    album_ids = []
    processed = 0
    start_time = time.time()

    async for message in client.iter_messages(channel, min_id=last_processed, reverse=True):
        processed += 1
        remaining = total_count - processed

        # Progress calculation
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        eta = remaining / rate if rate > 0 else float("inf")

        percent = (processed / total_count) * 100 if total_count > 0 else 0
        bar_length = 30
        filled_length = int(bar_length * processed // total_count) if total_count > 0 else 0
        bar = '█' * filled_length + '-' * (bar_length - filled_length)

        print(f"\rProgress |{bar}| {percent:.2f}% "
              f"({processed}/{total_count}) | Remaining: {remaining} | ETA: {eta:.1f}s",
              end="", flush=True)

        if message.text:
            match = re.search(ALBUM_REGEX, message.text)
            if match:
                album_id = match.group(1)
                album_ids.append(album_id)

        # Save progress in Mongo
        await update_last_processed(channel_id, message.id)

    # Save results to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"Channel: {channel_name}\n")
        for album in album_ids:
            f.write(album + "\n")

    print(f"\n[+] Extracted {len(album_ids)} album IDs")
    print(f"[+] Saved to {OUTPUT_FILE}")
    print(f"[✓] Progress saved in MongoDB for resume support.")

# ✅ Correct session usage
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

with client:
    client.loop.run_until_complete(main(client))
