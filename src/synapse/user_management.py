import aiohttp
import json
import secrets
from urllib.parse import urlparse

class SynapseAdminError(Exception):
    def __init__(self, message, status_code=None, errcode=None):
        super().__init__(message)
        self.status_code = status_code
        self.errcode = errcode

# Creates a new user in Synapse via the Admin API.
async def create_synapse_user(
    admin_api_url: str,
    admin_token: str,
    homeserver_url: str,
    username: str,
    password: str,
    displayname: str = None,
    email: str = None,
    is_admin_user: bool = False
):

    parsed_homeserver_url = urlparse(homeserver_url)
    server_name = parsed_homeserver_url.netloc
    
    api_endpoint = f"{admin_api_url.rstrip('/')}/_synapse/admin/v2/users/{username}"

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "password": password,
        "displayname": displayname if displayname else username,
        "admin": is_admin_user,
        "deactivated": False
    }
    if email:
        payload["threepids"] = [{"medium": "email", "address": email}]

    async with aiohttp.ClientSession() as session:
        async with session.put(api_endpoint, headers=headers, json=payload) as response:
            response_body = await response.text()
            try:
                response_data = json.loads(response_body) if response_body else {}
            except json.JSONDecodeError:
                response_data = {} 

            if response.status == 200 or response.status == 201:
                return response_data 
            else:
                errcode = response_data.get("errcode")
                error_message = response_data.get("error", f"Failed to create user. Raw response: {response_body}")
                raise SynapseAdminError(error_message, status_code=response.status, errcode=errcode)

# Creates a new bot in Synapse via the Admin API.
async def create_synapse_bot(
    admin_api_url: str,
    admin_token: str,
    homeserver_url: str,
    username_localpart: str,
    displayname: str
) -> tuple[str, str]: 

    Generate a secure password
    password = secrets.token_urlsafe(16)

    # Use the existing create_synapse_user function to perform the actual user creation
    try:
        user_details = await create_synapse_user(
            admin_api_url=admin_api_url,
            admin_token=admin_token,
            homeserver_url=homeserver_url,
            username=username_localpart, 
            password=password,
            displayname=displayname,
            email=None,
            is_admin_user=False 
        )
    except SynapseAdminError as e:
        print(f"Error during underlying create_synapse_user call for bot {username_localpart}: {str(e)} (Status: {e.status_code}, Errcode: {e.errcode})")
        raise 

    full_mxid = user_details.get('name')
    
    return full_mxid, password