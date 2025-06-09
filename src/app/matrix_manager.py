import asyncio
from nio import AsyncClient, RoomMessageText, InviteMemberEvent

class MatrixManager:
    def __init__(self, homeserver, user_id, access_token, default_room_id=None):
        self.homeserver = homeserver
        self.user_id = user_id
        self.access_token = access_token
        self.default_room_id = default_room_id

        self.client = AsyncClient(homeserver, user_id)
        self.client.access_token = access_token
        self.message_queue = asyncio.Queue()
        self._register_callbacks()

    def _register_callbacks(self):
        self.client.add_event_callback(self._message_callback, RoomMessageText)
        self.client.add_event_callback(self._invite_callback, InviteMemberEvent)

    async def _message_callback(self, room, event: RoomMessageText):
        if event.sender != self.client.user_id:
            await self.message_queue.put({
                "room_id": room.room_id,
                "sender": event.sender,
                "message": event.body,
                "timestamp": event.server_timestamp,
                "event_id": event.event_id
            })

    async def _invite_callback(self, room, event: InviteMemberEvent):
        if event.state_key == self.client.user_id:
            try:
                await self.client.join(room.room_id)
                print(f"Matrix Action: Successfully joined room: {room.room_id}")
            except Exception as e:
                print(f"Matrix Error: An unexpected error occurred while joining room {room.room_id}: {e}")

    async def start_sync(self):
        print(f"Attempting to sync with Matrix homeserver: {self.homeserver}")
        try:
            await self.client.sync_forever(timeout=30000, full_state=True)
        except Exception as e:
            print(f"Matrix client sync_forever exited with an unexpected error: {e}")
        finally:
            print("Matrix sync loop has ended.")
            await self.close()


    async def close(self):
        if self.client and not self.client.closed:
            print("Closing Matrix client connection...")
            await self.client.close()
            print("Matrix client connection closed.")