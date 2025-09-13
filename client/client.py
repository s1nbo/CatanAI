import requests
import websockets
import asyncio
import json

BASE_URL = "localhost:8000"

def create_game():
    response = requests.post(f"http://{BASE_URL}/create_game")
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to create lobby:", response.text)
        return None

def join_game(game_id: int):
    response = requests.post(f"http://{BASE_URL}/join_game", params={"game_id": game_id})
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

        while True:
            try:
                message = await websocket.recv()
                print(f"Received message: {message}")
            except websockets.ConnectionClosed:
                print("Connection closed")
                break
            
            continue
            # GAME LOGIC
            if message["type"] == "your_turn":
                pass
            elif message["type"] == "roll_results":
                pass
            elif message["type"] == "robber_move":
                pass
            elif message["type"] == "build_action":
                pass
            elif message["type"] == "ressource_update":
                pass
            elif message["type"] == "development_card_buy":
                pass
            elif message["type"] == "development_card_play":
                pass
            elif message["type"] == "trade_request":
                pass
            elif message["type"] == "victory_point_update":
                pass
            elif message["type"] == "longest_road_update":
                pass
            elif message["type"] == "largest_army_update":
                pass
            elif message["type"] == "player_disconnect":
                pass
            elif message["type"] == "player_joined":
                pass
            elif message["type"] == "board_update":
                pass
            elif message["type"] == "game_start":
                pass
            elif message["type"] == "game_over":
                pass
    

    
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
    
    players = list_players(game_id)
    print(f"Current players in lobby {game_id}: {players}")
    
    '''
    while True:
        start = input("Start game? (y/n): ").strip().lower()
        if start == 'y':
            if start_game(game_id):
                print("Game started!")
                break
            else:
                print("Failed to start game. Try again.")
        elif start == 'n':
            print("Waiting for more players...")
    '''
    print("Waiting for game to start...")
    asyncio.run(game(game_id=int(game_id), player_id=int(player_id)))
    
    
