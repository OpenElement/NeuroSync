# src/synapse_client.py
import aiohttp

# A client for interacting with the Synapse Admin API.
class SynapseAdminClient:
    def __init__(self, homeserver_url: str, admin_token: str):
        if not admin_token:
            raise ValueError("Synapse admin token is required.")
        self.base_url = homeserver_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }

    # Creates a new user in Synapse.
    async def create_user(self, username: str, password: str, displayname: str = None, email: str = None, is_admin: bool = False):

        api_endpoint = f"{self.base_url}/_synapse/admin/v2/users/@{username}:{self.base_url.split('://')[1]}"
        
        payload = {
            "password": password,
            "displayname": displayname or username,
            "admin": is_admin,
            "deactivated": False
        }
        if email:
            payload["threepids"] = [{"medium": "email", "address": email}]

        async with aiohttp.ClientSession() as session:
            async with session.put(api_endpoint, headers=self.headers, json=payload) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    error_data = await response.json() if response.content_type == 'application/json' else {}
                    error_msg = error_data.get("errcode") or error_data.get("error", f"HTTP Status {response.status}")
                    
                    # Raise a general exception for the web server to catch
                    raise Exception(f"Failed to create Synapse user: {error_msg}")