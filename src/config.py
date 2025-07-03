# src/config.py
import os
from dotenv import load_dotenv

# Custom exception for configuration errors.
class ConfigError(Exception):
    pass

# Handles application configuration from environment variables.
class Config:
    def __init__(self):
        load_dotenv()
        
        required_vars = ["MATRIX_HOMESERVER", "MATRIX_USER_ID", "MATRIX_PASSWORD", "WEBHOOK_SECRET"]
        
        self.matrix_homeserver = os.getenv("MATRIX_HOMESERVER")
        self.matrix_user_id = os.getenv("MATRIX_USER_ID")
        self.matrix_password = os.getenv("MATRIX_PASSWORD")
        self.webhook_secret = os.getenv("WEBHOOK_SECRET")
        self.synapse_admin_token = os.getenv("SYNAPSE_ADMIN_ACCESS_TOKEN")
        self.store_path = os.getenv("CRYPTO_STORE_PATH", "./crypto_store/")

        missing_vars = [var for var in required_vars if not getattr(self, var.lower())]
        if missing_vars:
            raise ConfigError(f"Missing required environment variables: {missing_vars}")