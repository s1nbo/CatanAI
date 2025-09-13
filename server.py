from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import asyncio
import uvicorn
import random
from pydantic import BaseModel


app = FastAPI()


BASE_URL = "localhost:8000"
games = {} # game_id -> {"game_state": game_state, "websockets": {player_id: websocket}}

class GameIdRequest(BaseModel):
    game_id: int




@app.post("/create_game")
async def create_game():
    game_id = 1000
    while game_id in games:
        game_id = random.randint(1000, 9999)
    
    games[game_id] = {"game_state": False, "websockets": {}}
    player_id = 1
    games[game_id]["websockets"][player_id] = None  # Placeholder for
    
    return {"game_id": game_id, "player_id": player_id}


@app.post("/join_game")
async def join_game(req: GameIdRequest):
    game_id = req.game_id
    if game_id not in games:
        return JSONResponse(status_code=404, content={"message": "Game not found"})
    if len(games[game_id]["websockets"]) >= 4:
        return JSONResponse(status_code=400, content={"message": "Game is full"})
    if games[game_id]["game_state"]:
        return JSONResponse(status_code=400, content={"message": "Game has already started"})

    # check existing player ids and assign the lowest available (1,2,3,4)
    player_id = min(set(range(1, 5)) - set(games[game_id]["websockets"].keys()))
    games[game_id]["websockets"][player_id] = None  # Placeholder for WebSocket connection

    for conn in games[game_id]["websockets"].values():
        if conn:
            await conn.send_json({"status": "player_joined", "player_id": player_id})

    return {"player_id": player_id, "game_id": game_id}

@app.get("/game/{game_id}/players")
async def list_players(req: GameIdRequest):
    game_id = req.game_id
    if game_id not in games:
        return JSONResponse(status_code=404, content={"message": "Game not found"})
    
    players = list(games[game_id]["websockets"].keys())
    return {"players": players}

@app.post("/game/{game_id}/start")
async def start_game(req: GameIdRequest):
    game_id = req.game_id
    if game_id not in games:
        return JSONResponse(status_code=404, content={"message": "Game not found"})
    if games[game_id]["game_state"]:
        return JSONResponse(status_code=400, content={"message": "Game has already started"})
    if len(games[game_id]["websockets"]) < 2:
        return JSONResponse(status_code=400, content={"message": "Not enough players to start the game"})
    
    games[game_id]["game_state"] = True

    for conn in games[game_id]["websockets"].values():
        if conn:
            await conn.send_json({"status": "game_started"})

    return {"message": "Game started"}


@app.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: int, player_id: int):
    if game_id not in games or player_id not in games[game_id]["websockets"]:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    games[game_id]["websockets"][player_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            
            # GAME LOGIC
            continue
            await websocket.send_text(f"Message text was: {data}") # TEST ECHO
    

    except WebSocketDisconnect:
        games[game_id]["websockets"].pop(player_id, None)
        for conn in games[game_id]["websockets"].values():
            if conn:
                await conn.send_json({"type": "player_disconnect", "player_id": player_id})







if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

