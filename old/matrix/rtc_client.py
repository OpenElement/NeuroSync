# Defines MatrixRTC class for Matrix homeserver interaction.

import asyncio
import json
from nio import (AsyncClient, RoomMessageText, InviteMemberEvent,
                 RoomSendError, LocalProtocolError, LoginError)

class MatrixRTC:

    # Initializes MatrixRTC client.
    def __init__(self, homeserver: str, user_id: str, access_token: str, room_id: str):
        self.client = AsyncClient(homeserver, user_id)
        self.client.access_token = access_token
        self.room_id = room_id
        self.ws_client = None  # Attached by WebSocket handler

    async def start(self):
        # Registers Matrix event callbacks and starts the sync loop.
        self.client.add_event_callback(self.on_message, RoomMessageText)
        self.client.add_event_callback(self.on_invite, InviteMemberEvent)

        # Log in to ensure the token is valid and to get a device ID
        try:
            login_response = await self.client.login(self.client.access_token, device_name="NeuroSyncBridge")
            if isinstance(login_response, LoginError): # nio can return LoginError on failure
                print(f"Login failed: {login_response.message}")
                return
            print(f"Login successful. Device ID: {self.client.device_id}")
        # Stop if login fails catastrophically
        except Exception as e:
            print(f"Exception during login: {e}")
            return 

        asyncio.create_task(self.client.sync_forever(timeout=30000, full_state=True))

    async def on_message(self, room, event: RoomMessageText):
        # Handles incoming Matrix messages, forwards to ws_client if connected.
        if event.sender == self.client.user_id:
            return # Ignore self-sent messages

        print(f"Msg in {room.room_id} from {event.sender}: {event.body:.50}...")

        if self.ws_client and not self.ws_client.closed:
            payload = {
                "type": "matrix_message", "room_id": room.room_id,
                "sender": event.sender, "message": event.body,
                "timestamp": event.server_timestamp
            }
            try:
                await self.ws_client.send_json(payload)
            except Exception as e:
                if isinstance(e, ConnectionResetError): self.ws_client = None
        elif self.ws_client and self.ws_client.closed:
            self.ws_client = None # Clear closed client

    async def on_invite(self, room, event: InviteMemberEvent):
        # Auto-joins rooms upon invitation.
        if event.state_key == self.client.user_id:
            print(f"Invited to room {room.room_id} by {event.sender}.")
            try:
                await self.client.join(room.room_id)
                print(f"Auto-joined room: {room.room_id}")
            except (LocalProtocolError, RoomSendError) as e: # More specific error handling
                print(f"Error joining {room.room_id}: {e}")
            except Exception as e:
                print(f"Unexpected error joining {room.room_id}: {e}")


    async def send_to_matrix(self, room_id: str, message: str):
        #Sends a message to a Matrix room.
        target_room = room_id or self.room_id
        try:
            await self.client.room_send(
                room_id=target_room,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": message}
            )
        except RoomSendError as e:
            print(f"Failed to send to Matrix room {target_room}: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error sending to Matrix: {e}")
            raise

    async def stop(self):
        # Logs out and closes the Matrix client connection.
        print("Stopping Matrix client...")
        if self.client:
            try:
                if self.client.logged_in: # Check if logged in before trying to logout
                    await self.client.logout()
            except Exception as e: # Catch errors during logout
                print(f"Error during Matrix logout: {e}")
            finally: # Always try to close connection
                await self.client.close()