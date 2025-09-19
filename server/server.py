from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
import random
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from game.logic import Game
from game.board import Board
from game.action import *


app = FastAPI()


GAMES = {} # game_id -> {"game_state": game_state, "websockets": {player_id: websocket}}

class GameIdRequest(BaseModel):
    game_id: int

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:8080"] if serving frontend via http.server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/create")
async def create_game():
    game_id = random.randint(1000, 9999)
    while game_id in GAMES:
        game_id = random.randint(1000, 9999)
    print(f"Creating game {game_id}")
    
    GAMES[game_id] = {"game_state": False, "websockets": {}}
    player_id = 1
    GAMES[game_id]["websockets"][player_id] = None  # Placeholder for WebSocket connection
    return {"game_id": game_id, "player_id": player_id}


@app.post("/join")
async def join_game(req: GameIdRequest):
    game_id = req.game_id
    print(f"Joining game {game_id}")
    if game_id not in GAMES:
        return JSONResponse(status_code=404, content={"message": "Game not found"})
    if len(GAMES[game_id]["websockets"]) >= 4:
        return JSONResponse(status_code=400, content={"message": "Game is full"})
    if GAMES[game_id]["game_state"]:
        return JSONResponse(status_code=400, content={"message": "Game has already started"})

    # check existing player ids and assign the lowest available (1,2,3,4)
    player_id = min(set(range(1, 5)) - set(GAMES[game_id]["websockets"].keys()))
    GAMES[game_id]["websockets"][player_id] = None  # Placeholder for WebSocket connection

    for conn in GAMES[game_id]["websockets"].values():
        if conn:
            await conn.send_json({"status": "player_joined", "player_id": player_id})

    return {"player_id": player_id, "game_id": game_id}



@app.post("/game/{game_id}/add_bot")
def add_bot(game_id: str):
    pass # TODO


@app.post("/game/{game_id}/remove_bot")
def remove_bot(game_id: int):
    pass # TODO


@app.post("/game/{game_id}/start")
async def start_game(req: GameIdRequest):
    game_id = req.game_id
    if game_id not in GAMES:
        return JSONResponse(status_code=404, content={"message": "Game not found"})
    if GAMES[game_id]["game_state"]:
        return JSONResponse(status_code=400, content={"message": "Game has already started"})
    if len(GAMES[game_id]["websockets"]) < 2:
        return JSONResponse(status_code=400, content={"message": "Not enough players to start the game"})
    
    GAMES[game_id]["game_state"] = True
    # create new game class instance here
    GAMES[game_id]["game_instance"] = Game()

    for player_id in GAMES[game_id]["websockets"].keys():
        GAMES[game_id]['game_instance'].add_player(player_id)

    for conn in GAMES[game_id]["websockets"].values():
        if conn:
            await conn.send_json({"game_state": "True"})

    # send initial game state to all players
    for player_id, conn in GAMES[game_id]["websockets"].items():
        if conn:
            await conn.send_json(GAMES[game_id]['game_instance'].start_game()[player_id])

    return {"message": "Game started"}



@app.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(ws: WebSocket, game_id: int, player_id: int):
    await ws.accept()

    if game_id not in GAMES or player_id not in GAMES[game_id]["websockets"]:
        await ws.close(code=1008)
        return
    
    GAMES[game_id]["websockets"][player_id] = ws

    try:
        while not GAMES[game_id]["game_state"]:
            await ws.send_json({"type": "ping"})
            await asyncio.sleep(2)
    
        game_instance = GAMES[game_id]["game_instance"]
        await ws.send_json(game_instance.get_multiplayer_game_state()[player_id])

        # Main Game Loop
        while True:
            data = await ws.receive_json()
            
            result = game_instance.call_action(player_id, data)
            # if result is false the aciton failed, if result is true the player_id won, else the new game state is returned
            # as dict for each player (since hidden info)
            if result is False:
                await ws.send_json({"status": "action_failed"})
            elif result is True:
                for conn in GAMES[game_id]["websockets"].values():
                    if conn:
                        await conn.send_json({"status": "game_over", "winner": player_id})
            else:
                for pid, conn in GAMES[game_id]["websockets"].items():
                    if conn:
                        await conn.send_json(result[pid])
    # Here is a BUG TODO: If a player disconnects and reconnects, they are not removed properly
    except WebSocketDisconnect:
        print(f"Player {player_id} disconnected from game {game_id}")

        # Remove the websocket connection
        if player_id in GAMES[game_id]["websockets"]:
            GAMES[game_id]["websockets"].pop(player_id, None)

        # Notify remaining players
        for conn in GAMES[game_id]["websockets"].values():
            if conn:
                await conn.send_json({"status": "player_disconnected", "player_id": player_id})

        # Remove from game instance
        if player_id in game_instance.players:
            game_instance.remove_player(player_id)

        # Check if enough players remain
        if len(game_instance.players) < 2:
            GAMES[game_id]["game_state"] = False
            for conn in GAMES[game_id]["websockets"].values():
                if conn:
                    await conn.send_json({
                        "status": "game_over",
                        "message": "Not enough players to continue the game"
                    })



def start_server(host, port):
    uvicorn.run(app, host=host, port=port)