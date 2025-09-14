from board import Board
import random

# Basic Actions
def roll_dice(board: Board, players, player_id: int) -> int: 
    if players[player_id]["dice_rolled"] == True or players[player_id]["current_turn"] == False:
        return False
    players[player_id]["dice_rolled"] = True

    # distribute resources
    # we have to check if there are enough resources in the bank and then distribute accordingly
    number = random.randint(1, 6) + random.randint(1, 6)
    if number == 7: return 7 # Robber 

    total_ressource = {"wood": 0, "brick": 0, "sheep": 0, "wheat": 0, "ore": 0}
    for tile_id, tile in board.tiles.items():
        if tile.number == number and tile.robber_tile == False:
            for vertex in tile.vertices:
                if board.vertices[vertex].owner != None:
                    if board.vertices[vertex].building == "settlement":
                        total_ressource[tile.resource] += 1
                    elif board.vertices[vertex].building == "city":
                        total_ressource[tile.resource] += 2
    
    for resource, amount in total_ressource.items():
        if board.bank[resource] >= amount:
            board.bank[resource] -= amount
            # Distribute resources to players if enough in bank
            for _, tile in board.tiles.items():
                if tile.number == number and tile.robber_tile == False and tile.resource == resource:
                    for vertex in tile.vertices:
                        if board.vertices[vertex].owner != None:
                            owner = board.vertices[vertex].owner
                            if board.vertices[vertex].building == "settlement":
                                players[owner]["hand"][resource] += 1
                            elif board.vertices[vertex].building == "city":
                                players[owner]["hand"][resource] += 2
    
    # If not enough resources in bank, no resources are distributed
    return number


def amount_lose_resource(player_id: int, players: dict) -> int: 
    total_cards = sum(players[player_id]["hand"].values())
    if total_cards <= 7: return 0
    return total_cards // 2


def remove_resources(player_id: int, players: dict, resources: dict) -> bool:
    for resource, amount in resources.items():
        if players[player_id]["hand"].get(resource, 0) < amount:
            return False
    for resource, amount in resources.items():
        players[player_id]["hand"][resource] -= amount
    return True
 

def move_robber(board: Board , new_tile_id: int) -> bool: 
    if new_tile_id == board.robber_tile:
        return False
    
    for vertex in board.tiles[board.robber_tile].vertices:
        board.vertices[vertex].blocked = False
    
    board.robber_tile = new_tile_id

    for vertex in board.tiles[new_tile_id].vertices:
        board.vertices[vertex].blocked = True

    # Steal logic is handled in steal_resource function
    return True


def end_turn(player_id: int, players: dict) -> bool: 
    players[player_id]["dice_rolled"] = False
    players[player_id]["played_card_this_turn"] = False
    players[player_id]["current_turn"] = False
    players[(player_id + 1) % len(players)]["current_turn"] = True
    return True


# Building Actions
def place_settlement(board, vertex_id: int, player_id: int, players: dict) -> bool: 
    if players[player_id]["dice_rolled"] == False:
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
    players[player_id]["ports"].append(port_type)

    players[player_id]["settlements"] -= 1
    players[player_id]["hand"]["brick"] -= 1
    players[player_id]["hand"]["wood"] -= 1
    players[player_id]["hand"]["sheep"] -= 1
    players[player_id]["hand"]["wheat"] -= 1
    players[player_id]["victory_points"] += 1
    board.vertices[vertex_id].owner = player_id
    board.vertices[vertex_id].building = "settlement"

    return True


def place_city(board: Board, vertex_id: int, player_id: int, players: dict) -> bool: 
    if players[player_id]["dice_rolled"] == False:
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
    if players[player_id]["dice_rolled"] == False:
        return False
    if players[player_id]["roads"] <= 0:
        return False
    if players[player_id]["hand"]["brick"] < 1 or players[player_id]["hand"]["wood"] < 1:
        return False    
    if not can_place_road(board, edge_id, player_id):
        return False
    
    longest_road(board, player_id)
    
    players[player_id]["roads"] -= 1
    players[player_id]["hand"]["brick"] -= 1
    players[player_id]["hand"]["wood"] -= 1
    board.edges[edge_id].owner = player_id

    return True
    

def can_place_settlement(board: Board, vertex_id: int, player_id: int) -> bool: 
    if board.vertices[vertex_id].owner != None and board.vertices[vertex_id].building != None:
        return False
    has_connection = False
    for edge in board.vertices[vertex_id].edges:
        if board.edges[edge].owner == player_id:
                has_connection = True
                break
    if not has_connection:
        return False
    # Blocked by distance rule
    for neighbor in board.vertices[vertex_id].vertices:
        if board.vertices[neighbor].building != None or board.vertices[neighbor].owner != None:
            return False
    return True


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
def buy_development_card(player_id: int, development_cards: list, players: dict) -> bool: 
    if players[player_id]["hand"]["sheep"] < 1 or players[player_id]["hand"]["wheat"] < 1 or players[player_id]["hand"]["ore"] < 1:
        return False
    if len(development_cards) == 0:
        return False
    
    card = development_cards.pop()
    players[player_id]["development_cards"][card] += 1
    players[player_id]["hand"]["sheep"] -= 1
    players[player_id]["hand"]["wheat"] -= 1
    players[player_id]["hand"]["ore"] -= 1
    if card == "victory_point":
        players[player_id]["victory_points"] += 1
    return True
        

def play_knight(board: Board, player_id: int, target_tile: int, players: dict) -> bool:
    if not can_play_knight(board, player_id, target_tile, players):
        return False
    move_robber(board, target_tile)
    # stealing is handled in steal_resource function
    players[player_id]["played_card_this_turn"] = True
    players[player_id]["played_knights"] += 1
    players[player_id]["development_cards"]["knight"] -= 1

    # check largest army
    if players[player_id]["played_knights"] >= 3:
        for opponent_id in players:
            if players[opponent_id]["largest_army"] == True:
                if players[opponent_id]["played_knights"] < players[player_id]["played_knights"]:
                    players[opponent_id]["largest_army"] = False
                    players[player_id]["largest_army"] = True
                    players[opponent_id]["victory_points"] -= 2
                    players[player_id]["victory_points"] += 2
                break
    return True


def play_road_building(board: Board, player_id: int, roads: list[int], players: dict) -> bool:
    if not can_play_road_building(board, player_id, roads, players):
        return False
    for road in roads:
        place_road(board, road, player_id, players)
    players[player_id]["development_cards"]["road_building"] -= 1
    players[player_id]["played_card_this_turn"] = True
    return True


def play_year_of_plenty(player_id: int, resources: list[str], players: dict, bank: dict) -> bool:
    if not can_play_year_of_plenty(player_id, resources, players):
        return False
    for resource in resources:
        players[player_id]["hand"][resource] += 1
    players[player_id]["development_cards"]["year_of_plenty"] -= 1
    players[player_id]["played_card_this_turn"] = True
    return True


def play_monopoly(player_id: int, resource: str, players: dict) -> bool:
    if not can_play_monopoly(player_id, resource, players):
        return False
    total_collected = 0
    for opponent_id in players:
        if opponent_id != player_id:
            total_collected += players[opponent_id]["hand"].get(resource, 0)
            players[opponent_id]["hand"][resource] = 0
    players[player_id]["hand"][resource] += total_collected
    players[player_id]["development_cards"]["monopoly"] -= 1
    players[player_id]["played_card_this_turn"] = True
    return True
    

def can_play_knight(board: Board, player_id: int, target_tile: int, players: dict) -> bool:
    if target_tile == board.robber_tile:
        return False
    if players[player_id]["development_cards"]["knight"] <= 0:
        return False
    if players[player_id]["played_card_this_turn"] == True:
        return False
    return True


def can_play_road_building(board: Board, player_id: int, roads: list[int], players: dict) -> bool:
    if len(roads) != 2 or len(roads) != 1:
        return False
    if players[player_id]["development_cards"]["road_building"] <= 0:
        return False
    if players[player_id]["played_card_this_turn"] == True:
        return False
    if not can_place_road(board, roads[0], player_id):
        return False
    if len(roads) == 2 and not can_place_road(board, roads[1], player_id):
        return False
    if players[player_id]["roads"] < len(roads):
        return False
    return True


def can_play_year_of_plenty(player_id: int, resources: list[str], players: dict, bank: dict) -> bool: 
    if len(resources) != 2 or len(resources) != 1:
        return False
    if players[player_id]["development_cards"]["year_of_plenty"] <= 0:
        return False
    if players[player_id]["played_card_this_turn"] == True:
        return False
    if resources[0] not in ["wood", "brick", "sheep", "wheat", "ore"]:
        return False
    if len(resources) == 2 and resources[1] not in ["wood", "brick", "sheep", "wheat", "ore"]:
        return False
    if bank[resources[0]] <= 0:
        return False
    if len(resources) == 2:
        if resources[0] == resources[1]:
            if bank[resources[0]] < 2:
                return False
        else:
            if bank[resources[1]] <= 0:
                return False
    return True


def can_play_monopoly(player_id: int, resource: str, players: dict) -> bool: 
    if resource not in ["wood", "brick", "sheep", "wheat", "ore"]:
        return False
    if players[player_id]["development_cards"]["monopoly"] <= 0:
        return False
    if players[player_id]["played_card_this_turn"] == True:
        return False
    return True


# Trade Actions
def trade_possible(player_id: int, resource_0: dict, resource_1: dict, players: dict, bank: dict) -> bool: # could the trade be possible
    if not can_do_trade_player(player_id, resource_0, players):
        return False
    for trader in players:
        if trader != player_id:
            if can_do_trade_player(trader, resource_1, players):
               return True
    if can_do_trade_bank(player_id, resource_0, resource_1, players, bank):
        return True

    return False
    

def can_do_trade_player(player_id: int, resource_give: dict, players: dict) -> bool:
    for resource, amount in resource_give.items():
        if resource not in ["wood", "brick", "sheep", "wheat", "ore"]:
            return False
        if amount <= 0:
            return False
        if resource_give[resource] > players[player_id]["hand"].get(resource, 0):
            return False
    return True


def can_do_trade_bank(player_id: int, resource_give: dict, resource_receive: dict, players: dict, bank: dict) -> bool:
    # Check what ports the player has if any
    if players[player_id]["ports"] == []:
        wood_ratio = 4
        brick_ratio = 4
        sheep_ratio = 4
        wheat_ratio = 4
        ore_ratio = 4
    else:
        for port in players[player_id]["ports"]:
            if port == None:
                continue
            elif port == "3:1":
                wood_ratio = min(wood_ratio, 3)
                brick_ratio = min(brick_ratio, 3)
                sheep_ratio = min(sheep_ratio, 3)
                wheat_ratio = min(wheat_ratio, 3)
                ore_ratio = min(ore_ratio, 3)
            elif port == "wood":
                wood_ratio = min(wood_ratio, 2)
            elif port == "brick":
                brick_ratio = min(brick_ratio, 2)
            elif port == "sheep":
                sheep_ratio = min(sheep_ratio, 2)
            elif port == "wheat":
                wheat_ratio = min(wheat_ratio, 2)
            elif port == "ore":
                ore_ratio = min(ore_ratio, 2)
    
    # check if enough resources are in the bank
    for resource, amount in resource_receive.items():
        if resource not in ["wood", "brick", "sheep", "wheat", "ore"]:
            return False
        if amount <= 0:
            return False
        if bank.get(resource, 0) < amount:
            return False
    
    # check if player has correct ratios of resources to give
    for resource, amount in resource_give.items():
        if resource not in ["wood", "brick", "sheep", "wheat", "ore"]:
            return False
        if amount <= 0:
            return False
        if resource == "wood":
            ratio = wood_ratio
        elif resource == "brick":
            ratio = brick_ratio
        elif resource == "sheep":
            ratio = sheep_ratio
        elif resource == "wheat":
            ratio = wheat_ratio
        elif resource == "ore":
            ratio = ore_ratio
        if amount % ratio != 0:
            return False
        if players[player_id]["hand"].get(resource, 0) < amount:
            return False
    
    return True


def complete_trade_player(player_0: int, player_1: int, resource_0: dict, resource_1: dict, players: dict) -> bool:
    for resource, amount in resource_0.items():
        players[player_0]["hand"][resource] -= amount
        players[player_1]["hand"][resource] += amount
    for resource, amount in resource_1.items():
        players[player_1]["hand"][resource] -= amount
        players[player_0]["hand"][resource] += amount
    return True


def complete_trade_bank(player_id: int, resource_give: dict, resource_receive: dict, players: dict, bank: dict) -> bool:
    for resource, amount in resource_give.items():
        players[player_id]["hand"][resource] -= amount
        bank[resource] += amount
    for resource, amount in resource_receive.items():
        players[player_id]["hand"][resource] += amount
        bank[resource] -= amount
    return True


# Misc Actions
def longest_road(board, player_id: int, players: dict) -> None: 
    # First Part is caluclate longest road of current player DFS
    # Need to block paths that go through settlements of other players

    max_length = 0
    
    for edge_id, edge in board.edges.items():
        if edge.owner != player_id:
            continue

        stack = [(edge_id, {edge_id}, 1)]  # (current_edge, visited_edges, current_length)

        while stack:
            current_edge, visited, length = stack.pop()
            max_length = max(max_length, length)

            for vertex_id in board.edges[current_edge].vertices:
                # Vertex is blocked by other player's settlement/city
                if board.vertices[vertex_id].owner not in (None, player_id):
                    continue

                for next_edge in board.vertices[vertex_id].edges:
                    if board.edges[next_edge].owner == player_id and next_edge not in visited:
                        new_visited = visited | {next_edge}
                        stack.append((next_edge, new_visited, length + 1))
                
    
    players[player_id]["longest_road_length"] = max_length

    # Second Part is to check if longest road needs to be updated
    if players[player_id]["longest_road_length"] >= 5:
        for opponent_id in players:
            if players[opponent_id]["longest_road"] == True:
                if players[opponent_id]["longest_road_length"] < players[player_id]["longest_road_length"]:
                    players[opponent_id]["longest_road"] = False
                    players[player_id]["longest_road"] = True
                    players[opponent_id]["victory_points"] -= 2
                    players[player_id]["victory_points"] += 2
                break


def steal_resource(board: Board, stealer_id: int, victim_id: int, players: dict) -> bool: 
    if not can_steal(board, stealer_id, victim_id, players):
        return False
    if sum(players[victim_id]["hand"].values()) == 0: # No resources to steal
        return True
    
    resource = random.choices(
        population=list(players[victim_id]["hand"].keys()),
        weights=list(players[victim_id]["hand"].values()),
        k=1
    )[0]
    players[victim_id]["hand"][resource] -= 1
    players[stealer_id]["hand"][resource] += 1
    return True


def can_steal(board: Board, stealer_id: int, victim_id: int, players: dict) -> bool: 
    # robber must be on a tile adjacent to a settlement/city of the victim
    if stealer_id == victim_id:
        return False
    if board.robber_tile == None:
        return False
    for vertex in board.tiles[board.robber_tile].vertices:
        if board.vertices[vertex].owner == victim_id:
            return True
    return False 