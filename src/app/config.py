import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Matrix Configuration
MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER")
MATRIX_USER_ID = os.getenv("MATRIX_USER_ID")
MATRIX_ACCESS_TOKEN = os.getenv("MATRIX_ACCESS_TOKEN")

# Webhook Configurationss
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Web Server Configuration
HOST = os.getenv("WEB_HOST", '0.0.0.0')
PORT = int(os.getenv("WEB_PORT", 8080))

# Basic validation for essential configs
REQUIRED_CONFIGS = {
    "MATRIX_HOMESERVER": MATRIX_HOMESERVER,
    "MATRIX_USER_ID": MATRIX_USER_ID,
    "MATRIX_ACCESS_TOKEN": MATRIX_ACCESS_TOKEN,
    "WEBHOOK_SECRET": WEBHOOK_SECRET,
}

missing_configs = [key for key, value in REQUIRED_CONFIGS.items() if value is None]
if missing_configs:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_configs)}")

