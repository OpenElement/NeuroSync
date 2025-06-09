import asyncio
from aiohttp import web

class MessageWebhooks:
    def __init__(self, matrix_client, default_room_id, message_queue):
        self.matrix_client = matrix_client
        self.default_room_id = default_room_id
        self.message_queue = message_queue

    async def handle_send(self, request):
        try:
            data = await request.json()
            room_id = data.get('room_id', self.default_room_id)
            message_content = data.get('message')

            if not room_id:
                return web.json_response({"error": "room_id is required"}, status=400)
            if not message_content:
                return web.json_response({"error": "message content is required"}, status=400)

            await self.matrix_client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": message_content}
            )
            return web.json_response({"status": "success", "detail": f"Message sent to room {room_id}"})
        except KeyError as e:
            return web.json_response({"error": f"Missing field: {str(e)}"}, status=400)
        except Exception as e:
            print(f"Error in handle_send: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_receive(self, request):
        try:
            timeout_str = request.query.get('timeout', '1.0')
            timeout = float(timeout_str)
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=timeout
                )
                self.message_queue.task_done()
                return web.json_response(message)
            except asyncio.TimeoutError:
                return web.json_response({"status": "no_messages"}, status=204)
        except ValueError:
            return web.json_response({"error": "Invalid timeout value"}, status=400)
        except Exception as e:
            print(f"Error in handle_receive: {e}")
            return web.json_response({"error": str(e)}, status=500)

    def add_routes(self, app):
        app.router.add_post('/messages/send', self.handle_send)
        app.router.add_get('/messages/receive', self.handle_receive)