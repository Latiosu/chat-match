# chat-match
A web API to facilitate conversations between a group of people who'd like to get to know each other better.

## Requirements
- Python 3.7+
- Poetry
- Firebase (Cloud Firestore)

## Setup
1. Save firebase secret in repository root as `firebase-secret.json`
2. Run `poetry install`
3. When testing, Firebase composite index must be created for Events collections (follow link when querying GET Events endpoint)

## Run
```
export FLASK_APP=chat_match
export FLASK_ENV=development
poetry run flask run
```

## Testing via Postman
Download collection from https://www.getpostman.com/collections/88e16a9148bef8bd794c

## Design

### Use Case
When creating a breakout room in Zoom and organising 1-on-1 chats, who should each person speak to such that everyone has spoken to everyone else after X events.

### Features
- View/Add/Delete undirected graph
- View/Add/Delete/Update node
- View/Add/Delete events
- Match nodes (event)
- Show list of previous matches (30 days)

### Current Limitations
- Missing ability to add/remove edges from graph/event (GET/POST/DELETE edges)
- Matching odd number of nodes (algorithm)
- Adding/removing nodes later (GET/DELETE nodes)
- Marking nodes as absent for a session (POST events param)
- Renaming nodes (PUT nodes)

### Matching Rules
1. No two lines connecting the same nodes
2. No line connecting node to itself
3. Order of lines being connected matters
4. Reset a node's connections once all other nodes connected
5. Lines only drawn and updated algorithm triggered

## Data Layout
```
graphs:
    G1:
        graph_id: G1
        created: 23/05/2021 12:00:00
        events: [UUID_E1, UUID_E2]
        nodes: [
            {
                node_id: 0
                name: Eric
                edges: [1, 2]
            }
            {
                node_id: 1
                name: Nadia
                edges: [0]
            }
            {
                node_id: 2
                name: Charizard
                edges: [0]
            }
        ]

events:
    UUID_E1:
        event_id: UUID_1
        graph_id: G1
        created: 24/05/2021 13:00:00
        edges: [
            {
                node_a: 0
                node_b: 1
                name_a: Eric
                name_b: Nadia
            }
        ]
    UUID_E2:
        event_id: UUID_2
        graph_id: G1
        created: 24/05/2021 18:30:00
        edges: [
            {
                node_a: 0
                node_b: 2
                name_a: Eric
                name_b: Charizard
            }
        ]
```