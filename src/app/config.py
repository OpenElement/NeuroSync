import os
from dotenv import load_dotenv

load_dotenv()

class AppConfig:
    MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER")
    MATRIX_USER_ID = os.getenv("MATRIX_USER_ID")
    MATRIX_ACCESS_TOKEN = os.getenv("MATRIX_ACCESS_TOKEN")
    DEFAULT_ROOM_ID = os.getenv("ROOM_ID")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
    HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
    HTTP_PORT = int(os.getenv("HTTP_PORT", 8080))

    @staticmethod
    def validate():
        required_vars = [
            AppConfig.MATRIX_HOMESERVER,
            AppConfig.MATRIX_USER_ID,
            AppConfig.MATRIX_ACCESS_TOKEN,
            AppConfig.WEBHOOK_SECRET
        ]
        if not all(required_vars):
            missing = [
                name for name, value in {
                    "MATRIX_HOMESERVER": AppConfig.MATRIX_HOMESERVER,
                    "MATRIX_USER_ID": AppConfig.MATRIX_USER_ID,
                    "MATRIX_ACCESS_TOKEN": AppConfig.MATRIX_ACCESS_TOKEN,
                    "WEBHOOK_SECRET": AppConfig.WEBHOOK_SECRET
                }.items() if not value
            ]
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

try:
    AppConfig.validate()
except ValueError as e:
    print(f"Configuration Error: {e}")
    exit(1)