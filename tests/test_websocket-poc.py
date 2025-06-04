import os
import aiohttp
import pytest
import random
import asyncio
import json

# python


WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:8080")
ROOM_ID = os.getenv("ROOM_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
BOT_USER_ID = os.getenv("MATRIX_USER_ID")

@pytest.mark.asyncio
async def test_websocket_send_and_receive():
    assert ROOM_ID, "ROOM_ID must be set in .env"
    assert WEBHOOK_SECRET, "WEBHOOK_SECRET must be set in .env"
    assert BOT_USER_ID, "MATRIX_USER_ID must be set in .env"

    random_number = random.randint(10000, 99999)
    test_message = f"Test message {random_number}"
    headers = {"Authorization": f"Bearer {WEBHOOK_SECRET}"}

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(
            f"{WEBHOOK_URL}/ws",
            headers=headers
        ) as ws:
            # Wait for initial status message
            status_msg = await ws.receive(timeout=5)
            assert status_msg.type == aiohttp.WSMsgType.TEXT
            status_data = json.loads(status_msg.data)
            assert status_data.get("type") == "status"
            assert "Connected" in status_data.get("message", "")

            # Send a message to Matrix via WebSocket
            await ws.send_json({
                "type": "send",
                "room_id": ROOM_ID,
                "message": test_message
            })

            # Listen for the echo/forwarded message from Matrix
            for _ in range(20):  # up to 10 seconds (0.5s per loop)
                try:
                    msg = await ws.receive(timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if (
                        data.get("type") == "matrix_message"
                        and data.get("room_id") == ROOM_ID
                        and data.get("message") == test_message
                        and data.get("sender") == BOT_USER_ID
                    ):
                        assert str(random_number) in data["message"]
                        return
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    pytest.fail(f"WebSocket error: {ws.exception()}")
            pytest.fail("Did not receive the sent message from websocket")