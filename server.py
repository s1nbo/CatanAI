from fastapi import FastAPI, WebSocket
import asyncio
from pydantic import BaseModel
from typing import Dict, List

app = FastAPI()

lobbies: Dict[int, List[int]] = {}

class LobbyInfo(BaseModel):
    lobby_id: int
    players_id : List[int]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Assign player to a lobby
    for lobby_id, players in lobbies.items():
        if len(players) < 4:
            player_id = len(players) + 1
            players.append(player_id)
            break
    else:
        lobby_id = len(lobbies) + 1
        player_id = 1
        lobbies[lobby_id] = [player_id]

    # Send game and player ID to client
    await websocket.send_json({"lobby_id": lobby_id, "player_id": player_id})

    # Wait until the lobby is full
    while len(lobbies[lobby_id]) < 4:
        await asyncio.sleep(1)
    # Notify client that the game is starting
    await websocket.send_json({"status": "game_start", "lobby_id": lobby_id, "players": lobbies[lobby_id]})
    
    # keep client 20 sec connected then close
    await asyncio.sleep(5)
    await websocket.close()