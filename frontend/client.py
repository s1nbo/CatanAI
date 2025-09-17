import time
import requests
import websockets
import asyncio
import json

BASE_URL = "localhost:8000"

def create_game():
    response = requests.post(f"http://{BASE_URL}/create")
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to create lobby:", response.text)
        return None

def join_game(game_id: int):
    response = requests.post(f"http://{BASE_URL}/join", json={"game_id": game_id})
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to join lobby:", response.text)
        return None

def list_players(game_id: int):
    response = requests.get(f"http://{BASE_URL}/game/{game_id}/players")
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to list players:", response.text)
        return None

def start_game(game_id: int):
    response = requests.post(f"http://{BASE_URL}/game/{game_id}/start")
    if response.status_code == 200:
        return True
    else:
        print("Failed to start game:", response.text)
        return False 

async def game(game_id: int, player_id: int):
    uri = f"ws://{BASE_URL}/ws/{game_id}/{player_id}"
    async with websockets.connect(uri) as websocket:
        print(f"Connected to game {game_id} as player {player_id}.")
        
        async def recieve():
            while True:
                try:
                    message = await websocket.recv()
                    print(f"Received message: {message}")
                except websockets.ConnectionClosed:
                    print("Connection closed")
                    break

        async def send():
            loop = asyncio.get_event_loop()
            while True:
                try:
                    msg = await loop.run_in_executor(None, input, "Enter message to send (or 'exit' to quit): ")
                    action = {}
                    if msg.startswith("s"): # settlement
                        vertex_id = int(msg.split()[1])
                        action = {
                            "type": "place_settlement",
                            "vertex_id": vertex_id
                        }
                    elif msg.startswith("r"): # road
                        pass
                    elif msg.startswith("c"): # city
                        pass
                    elif msg.startswith("d"): # buy development card
                        pass
                    elif msg.startswith("e"): # end turn
                        action = {
                            "type": "end_turn"
                        }
                    elif msg.startswith("w"): # roll dice (wuerfel)
                        action = {
                            "type": "roll_dice"
                        }
                    # TODO more actions
                    elif msg.startswith("n"):  # start game
                        # Send POST request to server
                        resp = requests.post(f"http://{BASE_URL}/game/{game_id}/start", json={"game_id": game_id})
                        if resp.status_code == 200:
                            print("Game started successfully!")
                        else:
                            print("Failed to start game:", resp.text)
                    else:
                        print("Unknown command")
                        continue
            
                    await websocket.send(json.dumps(action))
                    print(f"Sent action: {action}")
                
                except websockets.ConnectionClosed:
                    print("Connection closed")
                    break
            
        await asyncio.gather(recieve(), send())
    

    
if __name__ == "__main__":
    action = input("create or join game? (c/j): ").strip().lower()
    if action == 'c':
        game_info = create_game()
    elif action == 'j':
        game_id = int(input("Enter game ID to join: ").strip())
        game_info = join_game(game_id)
    else:
        print("Invalid input. Exiting.")
        exit(1)
    
    print(game_info)
    if game_info:
        game_id = game_info["game_id"]
        player_id = game_info["player_id"]
        print(f"Joined lobby {game_id} as player {player_id}.")
    else:
        print("Failed to create or join game. Exiting.")
        exit(1)
    
    #players = list_players(game_id)
    #print(f"Current players in lobby {game_id}: {players}")

    
    print("Waiting for game to start...")
    asyncio.run(game(game_id=int(game_id), player_id=int(player_id)))
    
    
