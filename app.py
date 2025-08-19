# Don't Remove Credits: Fᴛᴍ Dᴇᴠᴇʟᴏᴘᴇʀᴢ
import os
import re
import time
import math
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
from motor.motor_asyncio import AsyncIOMotorClient

# ====== CONFIG ======
API_ID = int(os.getenv("API_ID", "8012239"))
API_HASH = os.getenv("API_HASH", "171e6f1bf66ed8dcc5140fbe827b6b08")
STRING_SESSION = os.getenv("STRING_SESSION", "1BVtsOIIBuy0Pghyup2lOE1yDjXg-mRoTWpCmQ-jxDqBvJXhD4leCcMdVKouFgkWE33a3EH1DZepwVKs8eaPkL3N9uSl_nG469aP94TeoP5FOqcXIvAIXbndK_wmgGkC0UwPHE8enIu8AQogIcwSdf9cbs5Lk1xq2OuLF4uEgXTwulRRrUXlVY0SaSy6T4LZcRPB1EEYLSRDl1-i0Yw8Pg22C8ktSVzGZHovzt2rh51C7BUhv1QaNYqjVTVtDDPo6HO71qyQ2MGOlU7s-gadC_9VcqhrfAgHbRMvuKNnz-2lh2ESuWCxtuTwThHVBZdbSwrLatCyBBc4cBR1ZEkYl2-qUEQckVjQ=")
INVITE_LINK = os.getenv("INVITE_LINK", "https://t.me/+l-llfMQyh245ZWVl")
ALBUM_REGEX = os.getenv("ALBUM_REGEX", r"💽 Album:\s*(\d+)")
SEND_CHAT_ID = int(os.getenv("SEND_CHAT_ID", "-1003017378821"))  # Send results to yourself by default

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ftm:ftm@cluster0.8hbsnml.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = "ftmuserbot"
COLLECTION = "progress"
# ====================

# Mongo setup
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]
progress_col = db[COLLECTION]


async def get_last_processed(channel_id: int):
    doc = await progress_col.find_one({"channel_id": channel_id})
    return doc["last_message_id"] if doc else 0


async def update_last_processed(channel_id: int, message_id: int):
    await progress_col.update_one(
        {"channel_id": channel_id},
        {"$set": {"last_message_id": message_id}},
        upsert=True
    )


async def save_and_send_batch(client, batch, batch_num, channel_name):
    """Save a batch of 500 album IDs to txt and send"""
    filename = f"{channel_name}_batch_{batch_num}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Channel: {channel_name}\n")
        for album in batch:
            f.write(album + "\n")

    await client.send_file(SEND_CHAT_ID, filename, caption=f"📦 Batch {batch_num} (500 IDs)")
    os.remove(filename)


async def save_and_send_final(client, all_albums, channel_name):
    """Save all albums in one united file and send"""
    filename = f"{channel_name}_all_albums.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Channel: {channel_name}\n")
        for album in all_albums:
            f.write(album + "\n")

    await client.send_file(SEND_CHAT_ID, filename, caption=f"✅ All {len(all_albums)} Album IDs Combined")
    os.remove(filename)


async def main(client):
    # Join channel
    try:
        entity = await client.get_entity(INVITE_LINK)
        await client(JoinChannelRequest(entity))
        print("[+] Joined the channel successfully!")
    except UserAlreadyParticipantError:
        print("[+] Already a member of the channel.")
        entity = await client.get_entity(INVITE_LINK)

    channel = await client.get_entity(entity)
    channel_name = channel.title.replace(" ", "_")
    channel_id = channel.id
    print(f"[+] Extracting from channel: {channel_name}")

    history = await client.get_messages(channel, limit=0)
    total_count = history.total
    print(f"[i] Total messages in channel: {total_count}")

    last_processed = await get_last_processed(channel_id)
    print(f"[i] Resuming from message ID: {last_processed}")

    album_ids = []
    batch = []
    batch_num = 1
    processed = 0
    start_time = time.time()

    async for message in client.iter_messages(channel, min_id=last_processed, reverse=True):
        processed += 1
        if message.text:
            match = re.search(ALBUM_REGEX, message.text)
            if match:
                album_id = match.group(1)
                album_ids.append(album_id)
                batch.append(album_id)

                # Send batch after 500
                if len(batch) >= 500:
                    await save_and_send_batch(client, batch, batch_num, channel_name)
                    batch = []
                    batch_num += 1

        await update_last_processed(channel_id, message.id)

        # Progress display
        remaining = total_count - processed
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

    # If leftover batch < 500
    if batch:
        await save_and_send_batch(client, batch, batch_num, channel_name)

    # Send all united file
    await save_and_send_final(client, album_ids, channel_name)

    print(f"\n[+] Extracted {len(album_ids)} album IDs")
    print("[✓] All batches & united file sent successfully.")


client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

with client:
    client.loop.run_until_complete(main(client))
