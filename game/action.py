from board import Board
import random

# Basic Actions
def roll_dice(players, player_id: int) -> int:
    if players[player_id]["dice rolled"] == True or players[player_id]["current_turn"] == False:
        return False
    players[player_id]["dice rolled"] = True
    return random.randint(1, 6) + random.randint(1, 6)

def move_robber(board: Board , new_tile_id: int) -> bool:
    if new_tile_id == board.robber_tile:
        return False
    board.robber_tile = new_tile_id
    # Add logic to steal a resource from a player with a settlement/city adjacent to the new tile
    return True

def end_turn(player_id: int, players: dict) -> bool:
    players[player_id]["dice rolled"] = False
    players[player_id]["played_card_this_turn"] = False
    players[player_id]["current_turn"] = False
    players[(player_id + 1) % len(players)]["current_turn"] = True
    return True


# Building Actions
def place_settlement(board, vertex_id: int, player_id: int, players: dict) -> list[str, dict]:
    if players[player_id]["dice rolled"] == False:
        return False
    if players[player_id]["settlements"] <= 0:
        return False
    if players[player_id]["hand"]["brick"] < 1 or players[player_id]["hand"]["wood"] < 1 or players[player_id]["hand"]["sheep"] < 1 or players[player_id]["hand"]["wheat"] < 1:
        return False    
    if not can_place_settlement(board, vertex_id, player_id):
        return False
    
    port_type = None
    if board.vertices[vertex_id].port != None:
        port_type = board.vertices[vertex_id].port

    players[player_id]["settlements"] -= 1
    players[player_id]["hand"]["brick"] -= 1
    players[player_id]["hand"]["wood"] -= 1
    players[player_id]["hand"]["sheep"] -= 1
    players[player_id]["hand"]["wheat"] -= 1
    players[player_id]["victory_points"] += 1
    board.vertices[vertex_id].owner = player_id
    board.vertices[vertex_id].building = "settlement"

    return [port_type, board]

def place_city(board: Board, vertex_id: int, player_id: int, players: dict) -> bool:
    if players[player_id]["dice rolled"] == False:
        return False
    if players[player_id]["cities"] <= 0:
        return False
    if players[player_id]["hand"]["ore"] < 3 or players[player_id]["hand"]["wheat"] < 2:
        return False    
    if not can_place_city(board, vertex_id, player_id):
        return False
    
    players[player_id]["cities"] -= 1
    players[player_id]["settlements"] += 1
    players[player_id]["hand"]["ore"] -= 3
    players[player_id]["hand"]["wheat"] -= 2
    players[player_id]["victory_points"] += 1
    board.vertices[vertex_id].building = "city"

    return True

def place_road(board: Board, edge_id: int, player_id: int, players: dict) -> bool:
    if players[player_id]["dice rolled"] == False:
        return False
    if players[player_id]["roads"] <= 0:
        return False
    if players[player_id]["hand"]["brick"] < 1 or players[player_id]["hand"]["wood"] < 1:
        return False    
    if not can_place_road(edge_id, player_id):
        return False
    
    longest_road(player_id, players)
    
    players[player_id]["roads"] -= 1
    players[player_id]["hand"]["brick"] -= 1
    players[player_id]["hand"]["wood"] -= 1
    board.edges[edge_id].owner = player_id

    return True
    

def can_place_settlement(board: Board, vertex_id: int, player_id: int) -> bool:
    if board.vertices[vertex_id].owner == None and board.vertices[vertex_id].building == None and board.vertices[vertex_id].blocked == False:
        for edge in board.vertices[vertex_id].edges:
            if board.edges[edge].owner == player_id:
                return True
    return False


def can_place_city(board: Board, vertex_id: int, player_id: int) -> bool:
    if board.vertices[vertex_id].owner == player_id and board.vertices[vertex_id].building == "settlement": 
        return True
    return False
    
def can_place_road(board: Board, edge_id: int, player_id: int) -> bool:
    if board.edges[edge_id].owner == None:
        for vertex in board.edges[edge_id].vertices:
            if board.vertices[vertex].owner == player_id:
                return True
        for edge in board.edges[edge_id].edges:
            if edge.owner == player_id:
                return True
    return False


# Development Card Actions
def buy_development_card(self, player_id: int) -> bool:
    pass

def play_development_card(self, player_id: int, card_type: str) -> bool:
    pass


# Trade Actions
def trade_offer(self, player_id: int, resource_give: dict, resource_receive: dict) -> bool:
    pass

def accept_trade(self, player_id: int, resource_give: dict, resource_receive: dict) -> bool:
    pass

def decline_trade(self, player_id: int) -> bool:
    pass

def complete_trade(self, trade_id: int) -> bool:
    pass



# Misc Actions
def longest_road(player_id: int, players: dict) -> None:
    pass
    # Need to take every road of the player as a starting point and do a DFS to find the longest path
    # Need to block paths that go through settlements of other players
