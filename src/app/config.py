import os
from dotenv import load_dotenv, set_key, find_dotenv

# Load environment variables from .env file
load_dotenv()

# Matrix Configuration
MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER")
MATRIX_USER_ID = os.getenv("MATRIX_USER_ID")
MATRIX_ACCESS_TOKEN = os.getenv("MATRIX_ACCESS_TOKEN")

# Webhook Configurationss
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Synapse Admin API Configuration
SYNAPSE_ADMIN_URL = os.getenv("MATRIX_HOMESERVER")  # e.g., http://localhost:8008
SYNAPSE_ADMIN_ACCESS_TOKEN = os.getenv("SYNAPSE_ADMIN_ACCESS_TOKEN")

# Web Server Configuration
HOST = os.getenv("WEB_HOST", '0.0.0.0')
PORT = int(os.getenv("WEB_PORT", 8080))

# Basic validation for essential configs
REQUIRED_CONFIGS = {
    "MATRIX_HOMESERVER": MATRIX_HOMESERVER,
    "MATRIX_USER_ID": MATRIX_USER_ID,
    "MATRIX_ACCESS_TOKEN": MATRIX_ACCESS_TOKEN,
    "WEBHOOK_SECRET": WEBHOOK_SECRET,
    "SYNAPSE_ADMIN_URL": SYNAPSE_ADMIN_URL,
    "SYNAPSE_ADMIN_ACCESS_TOKEN": SYNAPSE_ADMIN_ACCESS_TOKEN,
}

missing_configs = [key for key, value in REQUIRED_CONFIGS.items() if value is None]
if missing_configs:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_configs)}")

# Saves bot credentials (MXID and password) to the .env file, prefixed by UUID.
def save_bot_credentials_to_env(uuid: str, bot_mxid: str, bot_password: str):

    env_file_path = find_dotenv(usecwd=True) 

    target_env_file = env_file_path if env_file_path else ".env"

    prefix = uuid.upper().replace('-', '_')
    mxid_key = f"{prefix}_MATRIX_BOT_MXID"
    password_key = f"{prefix}_MATRIX_BOT_PASSWORD"

    print(f"Saved/Updated bot credentials in .env for UUID {uuid}: {mxid_key}, {password_key}")
