import asyncio
import json
from aiohttp import web
from nio import RoomMessageText # Ensure nio types are available if needed directly

# Callback for new Matrix messages.
async def message_event_callback(bot, room, event):
    if event.sender != bot.client.user_id:
        await bot.message_queue.put({
            "room_id": room.room_id,
            "sender": event.sender,
            "message": event.body,
            "timestamp": event.server_timestamp
        })

# HTTP handler to send a message to a Matrix room.
async def handle_send_request(bot, request):
    try:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        room_id = data.get('room_id')
        message_body = data.get('message')

        if not room_id:
            return web.json_response({"error": "room_id is required in payload"}, status=400)
        if message_body is None:  # Allow empty string, but not missing key
            return web.json_response({"error": "message is required in payload"}, status=400)

        await bot.client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": message_body}
        )
        return web.json_response({"status": "success"})
    except Exception as e:
        print(f"Error in handle_send_request: {e}")
        return web.json_response({"error": "Failed to send message"}, status=500)

# HTTP handler to receive a message from the queue.
async def handle_receive_request(bot, request):
    
    timeout_val = 1.0 

    try:
        if request.method == 'POST':
            try:
                data = await request.json()
                desired_room_id = data.get('room_id')
                timeout_val = float(data.get('timeout', timeout_val))
            except json.JSONDecodeError:
                return web.json_response({"error": "Invalid JSON payload"}, status=400)
            except ValueError:
                return web.json_response({"error": "Invalid timeout value in payload"}, status=400)
        elif request.method == 'GET':
            desired_room_id = request.query.get('room_id')
            try:
                timeout_val = float(request.query.get('timeout', str(timeout_val)))
            except ValueError:
                return web.json_response({"error": "Invalid timeout value in query"}, status=400)
        else:
            return web.json_response({"error": "Method not allowed"}, status=405)


        if not desired_room_id:
            return web.json_response({"error": "room_id is required"}, status=400)

        start_time = asyncio.get_event_loop().time()
        local_deferred_messages = []

        try:
            while True:
                current_loop_time = asyncio.get_event_loop().time()
                elapsed_time = current_loop_time - start_time
                if elapsed_time >= timeout_val:
                    break

                remaining_time_for_get = max(0.01, timeout_val - elapsed_time)

                try:
                    message = await asyncio.wait_for(
                        bot.message_queue.get(),
                        timeout=remaining_time_for_get
                    )
                    if message.get("room_id") == desired_room_id:
                        for m_deferred in local_deferred_messages:
                            await bot.message_queue.put(m_deferred) # Re-queue other room messages
                        return web.json_response(message)
                    else:
                        local_deferred_messages.append(message)
                except asyncio.TimeoutError:
                    break
            
            for m_deferred in local_deferred_messages: # Re-queue all deferred if no match or timeout
                await bot.message_queue.put(m_deferred)
            return web.json_response({"status": "no_messages_for_room_or_timeout", "room_id": desired_room_id}, status=204)
        
        except Exception as e_inner:
            for m_deferred in local_deferred_messages:
                await bot.message_queue.put(m_deferred)
            raise e_inner

    except Exception as e:
        print(f"Error in handle_receive_request: {e}")
        return web.json_response({"error": str(e)}, status=500)

def register_messaging_hooks(bot, web_app):
    """Registers messaging-related web routes and Matrix event callbacks."""
    # Register HTTP routes
    web_app.add_routes([
        web.post('/msg/send', lambda r: handle_send_request(bot, r)),
        web.get('/msg/receive', lambda r: handle_receive_request(bot, r)),
        web.post('/msg/receive', lambda r: handle_receive_request(bot, r)), # Allow POST for consistency
    ])

    # Register Matrix event callbacks
    bot.client.add_event_callback(
        lambda room, event: message_event_callback(bot, room, event),
        RoomMessageText
    )
