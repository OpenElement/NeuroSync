# WebSocket handler for /ws endpoint, bridging to MatrixRTC.

import json
from aiohttp import web, WSMsgType, WSMessage
from matrix.rtc_client import MatrixRTC

class MatrixBridgeWSHandler:

    def __init__(self, matrix_rtc: MatrixRTC):
        #nitializes with a MatrixRTC client instance.
        self.matrix_rtc = matrix_rtc

    async def handle_request(self, request: web.Request) -> web.WebSocketResponse:
        #Handles WebSocket connection, registers with MatrixRTC, processes messages.
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        print(f"WebSocket client connected from {request.remote}.")

        # Link this WS to MatrixRTC for message forwarding
        previous_ws_client_on_rtc = self.matrix_rtc.ws_client
        self.matrix_rtc.ws_client = ws
        
        await ws.send_json({"type": "status", "message": "Connected to Matrix bridge."})

        try:
            async for msg in ws: # type: WSMessage
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        await ws.send_json({"type": "error", "message": "Invalid JSON."})
                        continue

                    if data.get("type") == "send": # Process "send" type messages
                        target_room = data.get("room_id", self.matrix_rtc.room_id)
                        message_body = data.get("message", "")
                        if message_body:
                            try:
                                await self.matrix_rtc.send_to_matrix(target_room, message_body)
                            except Exception as e:
                                await ws.send_json({"type": "error", "message": f"Matrix send failed: {e}"})
                        else: # Empty message
                            await ws.send_json({"type": "error", "message": "Empty message."})
                    else: # Unknown message type
                        await ws.send_json({"type": "error", "message": "Unknown message type."})

                elif msg.type == WSMsgType.ERROR:
                    print(f"ebSocket error: {ws.exception()}")

        
        except ConnectionResetError:
            print(f"WebSocket connection reset by {request.remote}.")
        except Exception as e: # Catch-all for other unexpected errors
            print(f"Unhandled WebSocket exception for {request.remote}: {e}")
        finally:
            print(f"WebSocket client {request.remote} disconnected.")
            # Clean up ws_client on MatrixRTC if this was the active one
            if self.matrix_rtc.ws_client is ws:
                self.matrix_rtc.ws_client = previous_ws_client_on_rtc \
                    if previous_ws_client_on_rtc and not previous_ws_client_on_rtc.closed \
                    else None
        return ws

def register_routes(app: web.Application, matrix_rtc: MatrixRTC):
    handler_instance = MatrixBridgeWSHandler(matrix_rtc=matrix_rtc)
    app.add_routes([web.get("/ws", handler_instance.handle_request)])
