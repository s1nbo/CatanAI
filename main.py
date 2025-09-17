# Game Flow

'''
We can do:
- Create Game 
- Join Game Logic (with code)

- If we are in a lobby we can
- Add Bots
- Start Game (if enough players/bots (2-4))

Once in the game 
Create Board and Game Class
Inital Placement Phase
Main Game Loop (Players send actions to server, server validates and updates game state, then sends updated state to all players)
'''
import server.server as server
import game.board as board_module
import game.action as action_module
import game.static_board as static_board_module
import game.logic as logic_module



if __name__ == "__main__":
    print("Started Server")
    host = "127.0.0.1"
    port = 8000
    server.start_server(host, port)