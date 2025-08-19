# server.py
import os
import threading
import uvicorn
from fastapi import FastAPI
from app import main, client   # Import from app.py

app = FastAPI()

@app.get("/")
async def home():
    return {"status": "running", "message": "Album Extractor is alive"}

# Run Telethon bot in background
def run_bot():
    with client:
        client.loop.run_until_complete(main(client))

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
