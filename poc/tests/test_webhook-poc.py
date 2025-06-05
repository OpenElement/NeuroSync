import os
import aiohttp
import pytest
import random
import asyncio

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:8080")
ROOM_ID = os.getenv("ROOM_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
BOT_USER_ID = os.getenv("MATRIX_USER_ID")  # Add this to check sender

@pytest.mark.asyncio
async def test_send_and_receive_message():
    assert ROOM_ID, "ROOM_ID must be set in .env"
    assert WEBHOOK_SECRET, "WEBHOOK_SECRET must be set in .env"
    assert BOT_USER_ID, "MATRIX_USER_ID must be set in .env"

    random_number = random.randint(10000, 99999)
    test_message = f"Test message {random_number}"
    headers = {"Authorization": f"Bearer {WEBHOOK_SECRET}"}

    async with aiohttp.ClientSession() as session:
        # Send message
        send_resp = await session.post(
            f"{WEBHOOK_URL}/send",
            json={"room_id": ROOM_ID, "message": test_message},
            headers=headers
        )
        assert send_resp.status == 200
        send_data = await send_resp.json()
        assert send_data.get("status") == "success"

        # Try to receive the message (retry for up to 10 seconds)
        for _ in range(10):
            recv_resp = await session.get(
                f"{WEBHOOK_URL}/receive",
                headers=headers,
                params={"timeout": 2}
            )
            if recv_resp.status == 200:
                recv_data = await recv_resp.json()
                # Check if this is the message we sent (by message and sender)
                if (
                    recv_data.get("message") == test_message
                    and recv_data.get("sender") == BOT_USER_ID
                ):
                    assert recv_data["room_id"] == ROOM_ID
                    assert str(random_number) in recv_data["message"]
                    return
                # Otherwise, keep polling for the right message
            elif recv_resp.status == 204:
                await asyncio.sleep(1)
                continue
            else:
                recv_data = await recv_resp.text()
                pytest.fail(f"Unexpected status {recv_resp.status}: {recv_data}")
        pytest.fail("Did not receive the sent message from webhook")