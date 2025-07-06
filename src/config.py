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

        # General configuration
        self.matrix_homeserver = os.getenv("MATRIX_HOMESERVER")
        self.webhook_secret = os.getenv("WEBHOOK_SECRET")
        self.synapse_admin_token = os.getenv("SYNAPSE_ADMIN_ACCESS_TOKEN")

        if not self.matrix_homeserver or not self.webhook_secret:
            raise ConfigError("Missing required environment variables: MATRIX_HOMESERVER, WEBHOOK_SECRET")

        # Bot-specific configurations
        self.bots = []
        num_bots_str = os.getenv("NUM_BOTS", "0")
        if not num_bots_str.isdigit():
            raise ConfigError("NUM_BOTS environment variable must be an integer.")
        
        num_bots = int(num_bots_str)
        if num_bots == 0:
            print("Warning: NUM_BOTS is set to 0, no bots will be initialized.")

        for i in range(1, num_bots + 1):
            user_id = os.getenv(f"MATRIX_USER_ID_{i}")
            password = os.getenv(f"MATRIX_PASSWORD_{i}")
            store_path = os.getenv(f"CRYPTO_STORE_PATH_{i}", f"./crypto_store/bot_{i}/")

            if not all([user_id, password]):
                raise ConfigError(f"Missing credentials for bot {i}: MATRIX_USER_ID_{i} or MATRIX_PASSWORD_{i}")

            self.bots.append({
                "user_id": user_id,
                "password": password,
                "store_path": store_path
            })