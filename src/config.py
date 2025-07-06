import os
from dotenv import load_dotenv

# Custom exception for configuration errors.
class ConfigError(Exception):
    pass

# Handles application configuration from environment variables.
class Config:
    def __init__(self):
        load_dotenv()

        # General configuration
        self.matrix_homeserver = os.getenv("MATRIX_HOMESERVER")
        self.webhook_secret = os.getenv("WEBHOOK_SECRET")
        self.synapse_admin_token = os.getenv("SYNAPSE_ADMIN_ACCESS_TOKEN")

        if not self.matrix_homeserver or not self.webhook_secret:
            raise ConfigError("Missing required environment variables: MATRIX_HOMESERVER, WEBHOOK_SECRET")