import aiohttp
from typing import Dict, Any

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
    async def create_user(self, username: str, password: str, displayname: str = None, email: str = None) -> Dict[str, Any]:
        api_endpoint = f"{self.base_url}/_synapse/admin/v2/users/@{username}:{self.base_url.split('://')[1]}"
        
        payload = {
            "password": password,
            "displayname": displayname or username,
            "admin": False,
            "deactivated": False
        }
        if email:
            payload["threepids"] = [{"medium": "email", "address": email}]

        async with aiohttp.ClientSession() as session:
            async with session.put(api_endpoint, headers=self.headers, json=payload) as response:
                response_data = await response.json()
                if response.status in [200, 201]:
                    return response_data
                else:
                    error_msg = response_data.get("errcode") or response_data.get("error", f"HTTP Status {response.status}")
                    raise Exception(f"Failed to create Synapse user: {error_msg}")