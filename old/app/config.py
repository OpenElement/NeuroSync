# Manages application configuration loaded from environment variables.

import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class AppConfig:
    # Holds application configuration parameters.
    homeserver: str
    user_id: str
    access_token: str
    room_id: str
    webhook_secret: str

# Loads config from environment variables (.env file or system env).
def load_app_config() -> AppConfig:
    
    load_dotenv()

    config_values = {
        "homeserver": os.getenv("MATRIX_HOMESERVER"),
        "user_id": os.getenv("MATRIX_USER_ID"),
        "access_token": os.getenv("MATRIX_ACCESS_TOKEN"),
        "room_id": os.getenv("ROOM_ID"),
        "webhook_secret": os.getenv("WEBHOOK_SECRET"),
    }

    missing_vars = [key for key, value in config_values.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing env vars: {', '.join(missing_vars)}")

    return AppConfig(**config_values)