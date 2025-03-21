from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import os
import redis.asyncio as aioredis
import asyncio

app = FastAPI()

# Get Redis URL from environment
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = aioredis.from_url(redis_url, decode_responses=True)

@app.websocket("/ws/trades")
async def websocket_trades(websocket: WebSocket):
    await websocket.accept()
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("trade_notifications")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        await pubsub.unsubscribe("trade_notifications")

@app.websocket("/ws/orderbook")
async def websocket_orderbook(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Retrieve the latest order book snapshot from Redis
            snapshot = await redis_client.get("latest_orderbook_snapshot")
            if snapshot:
                await websocket.send_text(snapshot)
            await asyncio.sleep(1)  # Wait for 1 second before sending the next snapshot
    except WebSocketDisconnect:
        print("WebSocket disconnected")
