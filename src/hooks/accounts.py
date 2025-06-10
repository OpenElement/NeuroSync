import asyncio
import json
from aiohttp import web
from nio import InviteMemberEvent
from synapse.user_management import create_synapse_user, SynapseAdminError, create_synapse_bot
from app.config import save_bot_credentials_to_env

# Callback for new Matrix room invites.
async def invite_event_callback(bot, room, event):
    if event.state_key == bot.client.user_id:
        print(f"Received invite to room {room.room_id} from {event.sender}.")
        await bot.client.join(room.room_id)
        print(f"Joined new room: {room.room_id}")


# HTTP handler for creating a new bot.
async def handle_create_bot_request(bot, request):
    try:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)
        
        uuid = data.get('uuid')
        username = data.get('username') # Bot's desired username (localpart)
        display_name = data.get('display_name')

        if not uuid:
            return web.json_response({"error": "uuid is required in payload"}, status=400)
        if not username:
            return web.json_response({"error": "username for the bot is required in payload"}, status=400)
        if not display_name:
            display_name = f"Bot ({uuid[:8]}...)"
        
        # Access Synapse admin config from bot.config
        synapse_admin_url = getattr(bot.config, 'SYNAPSE_ADMIN_URL', None)
        synapse_admin_token = getattr(bot.config, 'SYNAPSE_ADMIN_ACCESS_TOKEN', None)
        matrix_homeserver_url = getattr(bot.config, 'MATRIX_HOMESERVER', None)

        if not all([synapse_admin_url, synapse_admin_token, matrix_homeserver_url]):
            print("Error: Synapse admin API configuration is missing or incomplete for bot creation.")
            return web.json_response({"error": "Server configuration error for bot creation."}, status=500)

        try:
            print(f"Attempting Synapse bot creation for username: {username}, UUID: {uuid}, display name: {display_name}")
            # create_synapse_bot returns (full_mxid, password)
            bot_mxid, bot_password = await create_synapse_bot(
                admin_api_url=synapse_admin_url,
                admin_token=synapse_admin_token,
                homeserver_url=matrix_homeserver_url,
                username_localpart=username,
                displayname=display_name
            )
            print(f"Successfully created Synapse bot: {bot_mxid}")

            # Store credentials in .env file
            try:
                save_bot_credentials_to_env(uuid, bot_mxid, bot_password)
                print(f"Bot credentials for {bot_mxid} (UUID: {uuid}) saved to .env file.")
            except Exception as e_env:
                print(f"CRITICAL: Error saving bot credentials to .env for UUID {uuid} (MXID: {bot_mxid}): {e_env}")
                return web.json_response({
                    "status": "error_saving_credentials",
                    "message": "Bot created successfully, but failed to save its credentials. Please check server logs. Manual intervention may be required.",
                    "bot_mxid": bot_mxid,
                }, status=500) 

            return web.json_response({
                "status": "success",
                "message": "Bot created successfully and credentials stored.",
                "bot_mxid": bot_mxid,
            }, status=201) # 201 Created

        except SynapseAdminError as sae:
            print(f"Synapse admin error creating bot for UUID {uuid}: {str(sae)} (Status: {sae.status_code}, Errcode: {sae.errcode})")
            error_message = str(sae)
            if sae.errcode == "M_USER_IN_USE":
                error_message = f"The username '{username}' is already in use. Please choose a different one."
            elif sae.errcode == "M_INVALID_USERNAME":
                 error_message = f"The username '{username}' is invalid according to Synapse rules."
            status_to_return = 400 if sae.status_code == 400 else 502 # 502 if Synapse itself has an issue
            return web.json_response({"error": error_message, "details": str(sae), "errcode": sae.errcode}, status=status_to_return)
        except ValueError as ve: 
            print(f"Configuration error during bot creation for UUID {uuid}: {ve}")
            return web.json_response({"error": f"Server configuration error: {ve}"}, status=500)
        except Exception as e_inner: 
            print(f"Unexpected error creating bot for UUID {uuid} via Synapse: {e_inner}")
            return web.json_response({"error": "Failed to create bot due to an unexpected server error."}, status=500)
    except Exception as e:
        print(f"Outer error in handle_create_bot_request: {e}") 
        return web.json_response({"error": "An unexpected error occurred processing your request."}, status=500)


# HTTP handler for creating a new user.
async def handle_create_user_request(bot, request):
    try:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON payload"}, status=400)

        recovery_email = data.get('recovery_email')
        username = data.get('username')
        password = data.get('password')
        display_name = data.get('display_name', username) # Use username as default display_name

        if not username:
            return web.json_response({"error": "username is required in payload"}, status=400)
        if password is None:
            return web.json_response({"error": "password is required in payload"}, status=400)

        # Access Synapse admin config from bot.config
        synapse_admin_url = getattr(bot.config, 'SYNAPSE_ADMIN_URL', None)
        synapse_admin_token = getattr(bot.config, 'SYNAPSE_ADMIN_ACCESS_TOKEN', None)
        matrix_homeserver_url = getattr(bot.config, 'MATRIX_HOMESERVER', None)

        if not all([synapse_admin_url, synapse_admin_token, matrix_homeserver_url]):
            print("Error: Synapse admin API configuration is missing or incomplete in app config.")
            return web.json_response({"error": "Server configuration error for user creation."}, status=500)

        try:
            print(f"Attempting Synapse user creation for: {username}")
            user_details = await create_synapse_user(
                admin_api_url=synapse_admin_url,
                admin_token=synapse_admin_token,
                homeserver_url=matrix_homeserver_url,
                username=username,
                password=password,
                displayname=display_name,
                email=recovery_email,
                is_admin_user=False  
            )
            created_user_id = user_details.get('name') 
            print(f"Successfully created Synapse user: {created_user_id}")
            return web.json_response({
                "status": "success",
                "message": "User created successfully.",
                "user_id": created_user_id
            }, status=201) # 201 Created

        except SynapseAdminError as sae:
            print(f"Synapse admin error for user {username}: {sae} (Status: {sae.status_code}, Errcode: {sae.errcode})")
            error_message = str(sae)
            if sae.errcode == "M_USER_IN_USE":
                error_message = f"User '{username}' already exists."
            elif sae.errcode == "M_INVALID_USERNAME":
                 error_message = f"Username '{username}' is invalid."
            status_to_return = 400 if sae.status_code == 400 else 502
            return web.json_response({"error": error_message}, status=status_to_return)
        except ValueError as ve: 
            print(f"Configuration error during user creation for {username}: {ve}")
            return web.json_response({"error": f"Server configuration error: {ve}"}, status=500)
        except Exception as e_inner: 
            print(f"Unexpected error creating user {username} via Synapse: {e_inner}")
            return web.json_response({"error": "Failed to create user due to an unexpected server error."}, status=500)

    except Exception as e:
        print(f"Outer error in handle_create_user_request: {e}") # Errors like initial JSON parsing
        return web.json_response({"error": "An unexpected error occurred processing your request."}, status=500)



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
