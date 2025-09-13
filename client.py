import asyncio
import websockets
import json

async def websocket_client():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Receive lobby and player ID
        msg = await websocket.recv()
        info = json.loads(msg)
        print(f"Lobby: {info['lobby_id']} Player: {info['player_id']}")

        # Wait for game start
        msg = await websocket.recv()
        start_info = json.loads(msg)
        if start_info.get("status") == "game_start":
            print(f"Game starting in lobby: {start_info['lobby_id']} with players: {start_info['players']}")

        # keep client 20 sec connected then close
        await asyncio.sleep(5)
        await websocket.close()


asyncio.run(websocket_client())
