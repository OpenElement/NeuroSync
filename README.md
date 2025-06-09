# NeuroSync: Matrix Bridge

NeuroSync is an application that acts as a bridge to a Matrix homeserver, allowing communication via WebHooks. 

Send message to a specific room:
```bash
curl -X POST https://ns.danoneill.uk/msg/send \
  -H "Authorization: Bearer KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello Matrix!", "room_id": "!XHeRqyJpfoWhPGLdKN:matrix.danoneill.uk"}'
```

Receive messages from a specific room: 
```bash
curl -X POST https://ns.danoneill.uk/msg/receive \
  -H "Authorization: Bearer KEY" \
  -H "Content-Type: application/json" \
  -d '{"room_id": "!XHeRqyJpfoWhPGLdKN:matrix.danoneill.uk"}'
```
