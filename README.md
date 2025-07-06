# NeuroSync: Matrix Bridge
NeuroSync is an application that acts as a bridge to a Matrix homeserver, allowing communication and user management via WebHooks.

## Example Usage
Send message to a specific room:
```bash
curl  -X  POST  https://API_URL/msg/send  \
	-H "Authorization: Bearer KEY" \
	-H  "Content-Type: application/json"  \
	-d '{"message":"Hello Matrix!", "user_id":"@USER:DOMAIN", "room_id": "ROOM_ID"}'
```

Receive messages from a specific room:
```bash
curl  -X  POST  https://API_URL/msg/receive  \
	-H "Authorization: Bearer KEY" \
	-H  "Content-Type: application/json"  \
	-d '{"room_id": "ROOM_ID"}'
```
Create a new user
```bash
curl  -X  POST  https://API_URL/create/user  \
	-H "Authorization: Bearer apples" \
	-H  "Content-Type: application/json"  \
	-d '{"username":"@USER:DOMAIN", "password":"PASSWORD"}'
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
MATRIX_HOMESERVER=
MATRIX_USER_ID=
MATRIX_PASSWORD=

# Webhook Configuration
WEBHOOK_SECRET=

# Synapse Config
SYNAPSE_ADMIN_ACCESS_TOKEN=
```

3. Initialise the docker container.
```bash
docker compose up --build -d
```

4. Test the webhooks
```bash
python3 test/remote_test.py -url URL -u USERNAME -p PASSWORD -r MATRIX_ROOM_ID
```

## Structure
|Directory		  |File 					      |Contents                     |
|---------------|---------------------|-----------------------------|
|.devcontainer	|`devcontainer.json`	|Docker environment for remote development.|
|src			      |`config.py`			    |The main entry point that initialises and runs all the components of the application.|
| 				      |`main.py`				    |Manages application configuration by loading settings from environment variables.|
|				        |`matrix_bridge.py`		|Contains the logic for the Matrix bot, handling message events and interactions within Matrix rooms.|
|				        |`webserver.py`			  |Implements an `aiohttp` web server that exposes endpoints to send and receive Matrix messages, and to create users.|
|				        |`synapse_client.py`	|A client library for interacting with the Synapse Admin API, specifically for user creation.|
||||
|			        	|`.env`					      |Holds all login credentials, must be created by the user.|
|				        |`Dockerfile`			    ||
|			        	|`docker-compose.yml`	||


