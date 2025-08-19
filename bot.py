# Don't Remove Credits: Fᴛᴍ Dᴇᴠᴇʟᴏᴘᴇʀᴢ
import os
import re
import time
import asyncio
import logging
import importlib
from datetime import date, datetime

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest

from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
import pytz
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from pyrogram import utils as pyroutils

from plugins import web_server
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL, PORT


# ====== CONFIG ======
STRING_SESSION = os.getenv("STRING_SESSION", "1BVtsOJIBuy0HiKgTZ3M_CF_qjxM5QIyzKGj5GlvfXqOvDlAey91e7rchIxQOa6pYslzhhuU7sVU3K7u_G2uXFe4lgD1igdcVVkFZXMKXr8gjVLxe21IKznzGFfrKk1dKi42j96DwUMAGJCsnjlI8Bi_h-ASMmX1zZ6fBwYw4NrHAeMO5rhMJ6pAMKkvHpBSpmQb6NqciKSDAC5qxXHeY3K_WWYM8IPZwnWtqPEzeuwEK-dHHIJPa7SyvSGfU2_bP2EyEVxkAjPe7xMRruKlFdXJwfmbRHASvFsjd3OWUHuFcypo5Zq6VbDFXGa2bOeLV-YlbOEP5TpcTb72ypCeQ0p-_-65ZkyQ=")
INVITE_LINK   = os.getenv("INVITE_LINK", "https://t.me/+l-llfMQyh245ZWVl")
ALBUM_REGEX   = os.getenv("ALBUM_REGEX", r"💽 Album:\s*(\d+)")
SEND_CHAT_ID  = int(os.getenv("SEND_CHAT_ID", "-1003017378821"))

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME   = "ftmuserbot"
COLLECTION = "progress"
# ====================

# ------------ Mongo setup ------------
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
    filename = f"{channel_name}_batch_{batch_num}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Channel: {channel_name}\n")
        for album in batch:
            f.write(album + "\n")

    await client.send_file(SEND_CHAT_ID, filename, caption=f"📦 Batch {batch_num} (500 IDs)")
    os.remove(filename)


async def save_and_send_final(client, all_albums, channel_name):
    filename = f"{channel_name}_all_albums.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Channel: {channel_name}\n")
        for album in all_albums:
            f.write(album + "\n")

    await client.send_file(SEND_CHAT_ID, filename, caption=f"✅ All {len(all_albums)} Album IDs Combined")
    os.remove(filename)


# ============ Telethon Userbot (Album Extractor) =============
tele_userbot = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def album_extractor():
    client = tele_userbot

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

    album_ids  = []
    batch      = []
    batch_num  = 1
    processed  = 0
    start_time = time.time()

    async for message in client.iter_messages(channel, min_id=last_processed, reverse=True):
        processed += 1
        if message.text:
            match = re.search(ALBUM_REGEX, message.text)
            if match:
                album_id = match.group(1)
                album_ids.append(album_id)
                batch.append(album_id)
                if len(batch) >= 500:
                    await save_and_send_batch(client, batch, batch_num, channel_name)
                    batch = []
                    batch_num += 1

        await update_last_processed(channel_id, message.id)

        remaining = total_count - processed
        elapsed   = time.time() - start_time
        rate      = processed / elapsed if elapsed > 0 else 0
        eta       = remaining / rate if rate > 0 else float("inf")
        percent   = (processed / total_count) * 100 if total_count > 0 else 0
        bar       = '█' * int(30 * percent / 100) + '-' * (30 - int(30 * percent / 100))

        print(f"\rProgress |{bar}| {percent:.2f}% ({processed}/{total_count}) "
              f"| Remaining: {remaining} | ETA: {eta:.1f}s",
              end="", flush=True)

    if batch:
        await save_and_send_batch(client, batch, batch_num, channel_name)
    await save_and_send_final(client, album_ids, channel_name)

    print(f"\n[+] Extracted {len(album_ids)} album IDs")
    print("[✓] All batches & united file sent successfully.")



# =================== Pyrogram Bot ===================
logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
pyroutils.MIN_CHAT_ID    = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

class Bot(Client):
    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"},
            workers=50
        )

    async def start(self):
        await super().start()
        me  = await self.get_me()
        tz  = pytz.timezone("Asia/Kolkata")
        now = datetime.now(tz)
        await self.send_message(
            chat_id=LOG_CHANNEL,
            text=f"✅ Bot Restarted! 📅 Date: {date.today()} 🕒 Time: {now.strftime('%H:%M:%S %p')}"
        )
        runner = web.AppRunner(await web_server())
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", PORT).start()
        logging.info(f"🌐 Web Server Running on PORT {PORT}")

app = Bot()

# ============== STARTUP ==============
async def main():
    await app.start()
    print("🤖 Pyrogram Bot started!")

    await tele_userbot.start()
    print("👤 Telethon Userbot started!")

    # start album extractor
    asyncio.create_task(album_extractor())

    # load plugins
    for file in os.listdir("./plugins"):
        if file.endswith(".py"):
            importlib.import_module(f"plugins.{file[:-3]}")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
  
