# NeuroSync: Matrix Bridge
NeuroSync is an application that acts as a bridge to a Matrix homeserver, allowing communication and user management via WebHooks.

## Example Usage
Send message to a specific room:
```bash
curl  -X  POST  https://API_URL/msg/send  \
	-H "Authorization: Bearer KEY" \
	-H  "Content-Type: application/json"  \
	-d '{"message":"Hello Matrix!", "user_id":"@BOT:DOMAIN", "room_id": "ROOM_ID"}'
```

Receive messages from a specific room:
```bash
curl  -X  POST  https://API_URL/msg/receive  \
	-H "Authorization: Bearer KEY" \
	-H  "Content-Type: application/json"  \
	-d '{"room_id": "ROOM_ID"}'
```

Receive messages from all rooms:
```bash
curl  -X  POST  https://API_URL/msg/receive  \
	-H "Authorization: Bearer KEY" \
	-H  "Content-Type: application/json"  \
	-d '{"room_id": "ALL"}'
```

Create a new user
```bash
curl  -X  POST  https://API_URL/create/user  \
	-H "Authorization: Bearer KEY" \
	-H  "Content-Type: application/json"  \
	-d '{"username":"@USER:DOMAIN", "password":"PASSWORD"}'
```

Create a new bot
```bash
curl  -X  POST  https://API_URL/create/user  \
	-H "Authorization: Bearer KEY" \
	-H  "Content-Type: application/json"  \
	-d '{"username":"@BOT:DOMAIN"}'
```

## Setup Instructions
1. Clone the repository. 
```bash
git clone git@github.com:OpenElement/NeuroSync.git
cd NeuroSync/
```

2. Create a `.env` file. 
```bash
# Matrix Configuration
# --- General Settings ---
MATRIX_HOMESERVER=
MATRIX_SERVER_NAME=
WEBHOOK_SECRET=
SYNAPSE_ADMIN_ACCESS_TOKEN=
```

3. Initialise the docker container.
```bash
docker compose up --build -d
```

4. Create your first bot account:
```bash
curl  -X  POST  https://API_URL/create/user  \
	-H "Authorization: Bearer KEY" \
	-H  "Content-Type: application/json"  \
	-d '{"username":"@BOT:DOMAIN"}'
```