# Codebase

## Architecture

### Core Components

#### 1. Web Server ([`src/web/server.py`](../src/web/server.py))
The [`WebServer`](../src/web/server.py) class manages the main HTTP application using aiohttp. It handles:
- Authentication middleware for both admin and bot tokens
- Route setup and management
- Bot state management (active instances and tasks)
- HTTP session management

Key features:
- **Authentication**: Uses Bearer token authentication with separate validation for admin vs bot endpoints
- **Token Caching**: Maintains an in-memory cache of bot tokens for efficient authentication
- **State Management**: Tracks active bot instances and their associated asyncio tasks

#### 2. Message Dispatcher ([`src/web/message_dispatcher.py`](../src/web/message_dispatcher.py))
The [`MessageDispatcher`](../src/web/message_dispatcher.py) implements a fan-out message queue pattern:
- Single source queue that receives all messages from Matrix bots
- Multiple subscriber queues for different consumers (webhooks, long-polling clients)
- Automatic cleanup of disconnected subscribers

#### 3. Matrix Bot ([`src/matrix/bot.py`](../src/matrix/bot.py))
The [`MatrixBot`](../src/matrix/bot.py) class wraps simplematrixbotlib functionality:
- Handles Matrix client lifecycle (login, sync, encryption)
- Processes incoming messages and forwards them to the message dispatcher
- Provides message sending capabilities
- Tracks bot uptime statistics

#### 4. Configuration Management ([`src/config/app_config.py`](../src/config/app_config.py))
Contains:
- [`Config`](../src/config/app_config.py) class for environment variable management
- [`Bot`](../src/config/app_config.py) SQLAlchemy model for database schema
- Database initialization and CRUD operations
- Async SQLAlchemy session management

#### 5. Synapse Admin Client ([`src/matrix/synapse_client.py`](../src/matrix/synapse_client.py))
The [`SynapseAdminClient`](../src/matrix/synapse_client.py) provides integration with Synapse's admin API:
- User creation and deletion
- Administrative operations on the Matrix homeserver

## Request Handlers

### Admin Handlers ([`src/web/handlers/admin_handlers.py`](../src/web/handlers/admin_handlers.py))
The [`AdminHandlers`](../src/web/handlers/admin_handlers.py) class manages administrative operations:
- **User Management**: Create/delete Matrix users via Synapse API
- **Bot Management**: Create/delete bot accounts with database persistence
- **Token Management**: Update bot authentication tokens
- **Security**: Generates cryptographically secure passwords and tokens

### Message Handlers ([`src/web/handlers/message_handlers.py`](../src/web/handlers/message_handlers.py))
The [`MessageHandlers`](../src/web/handlers/message_handlers.py) class handles bot operations and messaging:
- **Message Operations**: Send messages via bots, receive with long-polling
- **Bot Lifecycle**: Activate/deactivate bot instances
- **Webhook Management**: Register/unregister webhook endpoints for notifications
- **Status Monitoring**: Provide bot status and health information

## Data Flow

### Message Flow
1. Matrix bot receives message via simplematrixbotlib
2. [`MatrixBot.on_message`](../src/matrix/bot.py) processes and formats message
3. Message is queued in [`MessageDispatcher.source_queue`](../src/web/message_dispatcher.py)
4. [`MessageDispatcher.run`](../src/web/message_dispatcher.py) fans out to all subscribers
5. Subscribers include:
   - Long-polling HTTP clients waiting for messages
   - Webhook notification worker for registered webhooks

### Bot Lifecycle
1. Admin creates bot via `/bot/create` endpoint
2. Bot credentials stored in database, token cached for auth
3. User activates bot via `/bot/activate` endpoint
4. [`MatrixBot`](../src/matrix/bot.py) instance created and started as asyncio task
5. Bot connects to Matrix, joins rooms, begins message processing
6. User can deactivate via `/bot/deactivate` to stop the bot

### Authentication Flow
1. All requests must include `Authorization: Bearer <token>` header
2. [`WebServer.auth_middleware`](../src/web/server.py) validates tokens:
   - Admin endpoints check against global admin token
   - Bot endpoints check against cached bot tokens
3. Authenticated requests include `authenticated_user_id` for bot identification

## Database Schema

### Bot Table
- `user_id` (Primary Key) - Matrix user ID (@user:domain)
- `password` - Generated secure password for Matrix login
- `store_path` - Path for bot's encryption key storage
- `webhook_secret` - Authentication token for API access

## Key Design Patterns

### Fan-Out Messaging
The [`MessageDispatcher`](../src/web/message_dispatcher.py) implements a pub-sub pattern where:
- Single source receives all messages
- Multiple subscribers get copies of relevant messages
- Automatic cleanup prevents memory leaks from disconnected clients

### Async Session Management
Database operations use async SQLAlchemy sessions:
- [`async_session_factory`](../src/config/app_config.py) provides session instances
- Proper transaction handling with rollback on errors
- Connection pooling for performance

### Middleware Architecture
Authentication is handled via aiohttp middleware:
- Centralized token validation logic
- Request preprocessing to inject authenticated user context
- Clean separation of auth logic from business logic

## Configuration

### Environment Variables
- `MATRIX_HOMESERVER` - Matrix homeserver URL
- `NS_ADMIN_TOKEN` - Global admin authentication token
- `SYNAPSE_ADMIN_TOKEN` - Synapse admin API token (optional)

### Database
- SQLite database stored at `data/bots.db`
- Async SQLite driver (`aiosqlite`) for non-blocking operations
- Automatic schema creation on startup

## Error Handling

### Graceful Degradation
- Synapse admin operations are optional (webhooks can work without them)
- Bot failures are isolated (one bot failure doesn't affect others)
- Database errors are caught and returned as HTTP error responses

### Logging
Comprehensive logging throughout the application:
- Structured logging with logger hierarchy
- Error logging with stack traces for debugging
- Info-level logging for operational visibility

## Security Considerations

### Token Management
- Separate admin vs bot token validation
- Tokens can be refreshed

### Input Validation
- JSON payload validation for all endpoints
- URL validation for webhook registrations
- User ID format validation

### Isolation
- Each bot runs in its own asyncio task
- Bot failures are contained and don't affect the web server
- Database transactions