import asyncio
import json
from aiohttp import web
from nio import InviteMemberEvent

# Callback for new Matrix room invites.
async def invite_event_callback(bot, room, event):
    if event.state_key == bot.client.user_id:
        print(f"Received invite to room {room.room_id} from {event.sender}.")
        await bot.client.join(room.room_id)
        print(f"Joined new room: {room.room_id}")


# HTTP handler for creating a new bot (placeholder).
async def handle_create_bot_request(bot, request):
    try:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        display_name = data.get('display_name')    
        username = data.get('username')
        uuid = data.get('uuid')

        if not username:
            return web.json_response({"error": "username is required in payload"}, status=400)
        if uuid is None:
            return web.json_response({"error": "uuid is required in payload"}, status=400)
        
        print(f"Bot creation requested for user: {username}.")

        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"error": "Failed to process /create/bot request"}, status=500)


# HTTP handler for creating a new user (placeholder).
async def handle_create_user_request(bot, request):
    try:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        recovery_email = data.get('recovery_email')
        username = data.get('username')
        password = data.get('password')

        if not username:
            return web.json_response({"error": "username is required in payload"}, status=400)
        if password is None:
            return web.json_response({"error": "password is required in payload"}, status=400)

        print(f"User creation requested for user: {username}.")

        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"error": "Failed to process /create/user request"}, status=500)

# Registers account-related web routes and Matrix event callbacks.
def register_account_hooks(bot, web_app):

    # Register HTTP routes
    web_app.add_routes([
        web.post('/create/bot', lambda r: handle_create_bot_request(bot, r)),
        web.post('/create/user', lambda r: handle_create_user_request(bot, r)),
    ])

    bot.client.add_event_callback(
        lambda room, event: invite_event_callback(bot, room, event),
        InviteMemberEvent
    )

