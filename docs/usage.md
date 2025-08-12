

## Admin Endpoints
These require the admin access token.

Add synapse admin token.
```bash
curl -X POST https://API_URL/admin/auth \
    -H "Authorization: Bearer NS_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"token":"SYNAPSE_ADMIN_TOKEN"}'
```

Create a new user account.
```bash
curl  -X  POST  https://API_URL/user/create  \
	-H "Authorization: Bearer NS_ADMIN_TOKEN" \
	-H  "Content-Type: application/json"  \
	-d '{"username":"@USERNAME:HOMESERVER", "password":"PASSWORD"}'
```

Create a new bot account.
```bash
curl  -X  POST  https://API_URL/bot/create  \
	-H "Authorization: Bearer NS_ADMIN_TOKEN" \
	-H  "Content-Type: application/json"  \
	-d '{"username":"@USERNAME:HOMESERVER", "token":"NS_BOT_TOKEN"}'
```

Delete a user account.
```bash
curl  -X  POST  https://API_URL/user/delete  \
	-H "Authorization: Bearer NS_ADMIN_TOKEN" \
	-H  "Content-Type: application/json"  \
	-d '{"username":"@USERNAME:HOMESERVER"}'
```

Delete a bot account.
```bash
curl -X POST https://API_URL/bot/delete \
    -H "Authorization: Bearer NS_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"username":"@USERNAME:HOMESERVER"}'
```

Update a bots token.
```bash
curl  -X  POST  https://API_URL/bot/auth  \
	-H "Authorization: Bearer NS_ADMIN_TOKEN" \
	-H  "Content-Type: application/json"  \
	-d '{"username":"@USERNAME:HOMESERVER", "token":"NS_BOT_TOKEN"}'
```

## Bot Endpoints
These require the bot access token.

Activate a bot account.
```bash
curl -X POST https://API_URL/bot/activate \
    -H "Authorization: Bearer NS_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"username":"@USERNAME:HOMESERVER"}'
```

Deactivate a bot account.
```bash
curl -X POST https://API_URL/bot/deactivate \
    -H "Authorization: Bearer NS_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"username":"@USERNAME:HOMESERVER"}'
```

Get a bots status.
```bash
curl -X POST https://API_URL/bot/status \
    -H "Authorization: Bearer NS_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"username":"@USERNAME:HOMESERVER"}'
```

## Send / Receive Endpoints
These require the bot access token.

Register a webhook.
```bash
curl -X POST https://API_URL/webhook/register \
    -H "Authorization: Bearer NS_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"username":"@USERNAME:HOMESERVER", "webhook_url": "WEBHOOK_URL"}' 
```

Deregister a webhook.
```bash
curl -X POST https://API_URL/webhook/deregister \
    -H "Authorization: Bearer NS_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"username":"@USERNAME:HOMESERVER", "webhook_url": "WEBHOOK_URL"}'
```

Send a message to a specific room.
```bash
curl  -X  POST  https://API_URL/msg/send  \
    -H "Authorization: Bearer NS_BOT_TOKEN" \
    -H  "Content-Type: application/json"  \
    -d '{"message":"MSG", "username":"@USERNAME:HOMESERVER", "room_id": "!ROOM:HOMESERVER"}'
```

Receive messages from a specific room.
```bash
curl  -X  POST  https://API_URL/msg/receive  \
    -H "Authorization: Bearer NS_BOT_TOKEN" \
    -H  "Content-Type: application/json"  \
    -d '{"room_id": "!ROOM:HOMESERVER"}'
```



## API Endpoints Summary

| Category | Endpoint | Description | Authorization |
|----------|----------|-------------|---------------|
| **Admin** | `/user/create` | Create a new user account | Admin Token |
| **Admin** | `/bot/create` | Create a new bot account | Admin Token |
| **Admin** | `/user/delete` | Delete a user account | Admin Token |
| **Admin** | `/bot/delete` | Delete a bot account | Admin Token |
| **Admin** | `/bot/auth` | Update a bot's token | Admin Token |
| **Bot** | `/bot/activate` | Activate a bot account | Bot Token |
| **Bot** | `/bot/deactivate` | Deactivate a bot account | Bot Token |
| **Bot** | `/bot/status` | Get a bot's status | Bot Token |
| **Messaging** | `/msg/register` | Register a webhook for message notifications | Bot Token |
| **Messaging** | `/msg/deregister` | Remove webhook registration | Bot Token |
| **Messaging** | `/msg/send` | Send a message to a specific room | Bot Token |
| **Messaging** | `/msg/receive` | Receive messages from a specific room | Bot Token |