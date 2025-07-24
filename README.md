# NeuroSync: Matrix Bridge
NeuroSync is an application that acts as a bridge to a Matrix homeserver, allowing communication and user management via WebHooks.

## Features

- **Matrix Bot Management**: Create, activate, and manage multiple Matrix bot accounts
- **User Administration**: Full user lifecycle management via Synapse Admin API
- **Message Routing**: Fan-out message distribution with long-polling and webhook support
- **Authentication**: Token-based authentication with separate admin and bot access levels
- **Real-time Communication**: WebSocket-like long-polling for real-time message reception
- **Webhook Integration**: Register webhooks for automated message notifications
- **Encryption Support**: Full Matrix end-to-end encryption support
- **Scalable Architecture**: Async-first design with proper error handling and isolation

## Architecture Overview

### Core Components

- **Web Server**: aiohttp-based REST API with authentication middleware
- **Message Dispatcher**: Fan-out messaging system for distributing messages to multiple subscribers
- **Matrix Bots**: Individual bot instances using simplematrixbotlib with encryption support
- **Database Layer**: Async SQLAlchemy with SQLite for bot configuration persistence
- **Synapse Integration**: Admin API client for user and bot management

### Key Design Patterns

- **Fan-Out Messaging**: Single source queue distributing to multiple subscribers
- **Async Session Management**: Non-blocking database operations with proper transaction handling
- **Middleware Architecture**: Centralized authentication and request preprocessing
- **Graceful Degradation**: Isolated bot failures and optional Synapse admin operations

## API Endpoints

| Category | Endpoint | Description | Authorization |
|----------|----------|-------------|---------------|
| **Admin** | `/admin/auth` | Provide Synapse Admin Token | Admin Token |
| **Admin** | `/user/create` | Create a new user account | Admin Token |
| **Admin** | `/bot/create` | Create a new bot account | Admin Token |
| **Admin** | `/user/delete` | Delete a user account | Admin Token |
| **Admin** | `/bot/delete` | Delete a bot account | Admin Token |
| **Admin** | `/bot/auth` | Update a bot's token | Admin Token |
| **Bot** | `/bot/activate` | Activate a bot account | Bot Token |
| **Bot** | `/bot/deactivate` | Deactivate a bot account | Bot Token |
| **Bot** | `/bot/status` | Get a bot's status | Bot Token |
| **Messaging** | `/webhook/register` | Register a webhook for message notifications | Bot Token |
| **Messaging** | `/webhook/deregister` | Remove webhook registration | Bot Token |
| **Messaging** | `/msg/send` | Send a message to a specific room | Bot Token |
| **Messaging** | `/msg/receive` | Receive messages from a specific room | Bot Token |



## Setup Instructions
1. Clone the repository. 
```bash
git clone git@github.com:OpenElement/NeuroSync.git
cd NeuroSync/
```

2. Create a `.env` file. 
```bash
# Settings
MATRIX_HOMESERVER=http://synapse:8008
NS_ADMIN_TOKEN=
SYNAPSE_ADMIN_TOKEN=
```

3. Initialise the docker container.
```bash
docker compose up --build -d
```

4. Create your first bot account:
```bash
curl  -X  POST  https://API_URL/create/bot  \
	-H "Authorization: Bearer KEY" \
	-H  "Content-Type: application/json"  \
	-d '{"username":"@BOT:DOMAIN"}'
```