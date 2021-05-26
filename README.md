# chat-match
A web API to facilitate conversations between a group of people who'd like to get to know each other better.

## Requirements
- Python 3.7+
- Poetry

## Setup
1. Save firebase secret in repository root as `firebase-secret.json`
2. Run `poetry install`

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
        created: 23/05/2021 12:00:00
        events: [E1, E2]
        nodes:
            1:
                name: Eric
                edges: [2]
            2: 
                name: Nadia
                edges: [1]

events:
    E1:
        graph: G1
        created: 24/05/2021 13:00:00
        edges: [[2, 1]]
    E2:
        graph: G1
        created: 24/05/2021 18:30:00
        edges: [[1, 2]]
```