# NeuroSync: Matrix Bridge and Extensible Server

NeuroSync is an application that acts as a bridge to a Matrix homeserver, allowing communication via WebSockets. 

## Project Structure

The project is organized into the following main directories:

-   **`src/`**: Root directory of the project.
    -   **`main.py`**: The main entry point to start the application.
    -   **`app/`**: Contains core application setup logic.
        -   `config.py`: Handles loading and providing application configuration from environment variables.
        -   `app_setup.py`: Responsible for creating the `aiohttp` web application instance, setting up middleware (like authentication), and registering routes from various modules.
    -   **`matrix/`**: Logic related to Matrix communication.
        -   `rtc_client.py`: Defines the `MatrixRTC` class, which interacts with the Matrix homeserver (sending/receiving messages, handling invites).
    -   **`webhooks/`**: Modules for different HTTP webhook endpoints.
        -   `send_hook.py`: Implements the `/send` HTTP POST webhook.
    -   **`websockets/`**: Modules for different WebSocket endpoints.
        -   `matrix_bridge_ws.py`: Implements the `/ws` WebSocket endpoint for bridging communication with `MatrixRTC`.
    -   **`.env`**: (You need to create this) File for storing environment variables (secrets, connection details).
    -   **`README.md`**: This documentation file.

## Setup and Installation

**Set Up Environment Variables**
Create a `.env` file in the root `neurosync/` directory. This file stores sensitive information and configuration specific to your deployment. Add the following variables, replacing the placeholder values with your actual details:

```env
MATRIX_HOMESERVER=your_homeserver_url_e.g._[https://matrix.org](https://matrix.org)
MATRIX_USER_ID=@your_bot_username:your_homeserver.com
MATRIX_ACCESS_TOKEN=your_matrix_bot_access_token
ROOM_ID=!your_default_matrix_room_id:your_homeserver.com
WEBHOOK_SECRET=your_strong_shared_secret_for_authentication
```
-   `MATRIX_HOMESERVER`: URL of your Matrix homeserver.
-   `MATRIX_USER_ID`: Full Matrix ID of the user (bot) this application will use.
-   `MATRIX_ACCESS_TOKEN`: Access token for the Matrix user.
-   `ROOM_ID`: The default Matrix room ID the application will primarily interact with.
-   `WEBHOOK_SECRET`: A strong, unique secret key used for Bearer token authentication across all webhooks and WebSocket connections.