from game import Board
import random

# Basic Actions
def roll_dice(board: Board, players, player_id: int, bank: dict) -> int: 
    if players[player_id]["dice_rolled"] == True or players[player_id]["current_turn"] == False:
        return False
    players[player_id]["dice_rolled"] = True

    # distribute resources
    # we have to check if there are enough resources in the bank and then distribute accordingly
    number = random.randint(1, 6) + random.randint(1, 6)
    if number == 7: return 7 # Robber 

    total_ressource = {"wood": 0, "brick": 0, "sheep": 0, "wheat": 0, "ore": 0}
    for tile in board.tiles:
        if tile.number == number and tile.robber == False:
            for vertex in tile.vertices:
                if board.vertices[vertex].owner != None:
                    if board.vertices[vertex].building == "settlement":
                        total_ressource[tile.resource] += 1
                    elif board.vertices[vertex].building == "city":
                        total_ressource[tile.resource] += 2
    
    for resource, amount in total_ressource.items():
        if bank[resource] >= amount:
            bank[resource] -= amount
            # Distribute resources to players if enough in bank
            for tile in board.tiles:
                if tile.number == number and tile.robber == False and tile.resource == resource:
                    for vertex in tile.vertices:
                        if board.vertices[vertex].owner != None:
                            owner = board.vertices[vertex].owner
                            if board.vertices[vertex].building == "settlement":
                                players[owner]["hand"][resource] += 1
                            elif board.vertices[vertex].building == "city":
                                players[owner]["hand"][resource] += 2
    
    # If not enough resources in bank, no resources are distributed
    return number


def remove_resources(player_id: int, players: dict, resources: dict, bank: dict) -> bool:
    for resource, amount in resources.items():
        if players[player_id]["hand"].get(resource, 0) < amount:
            return False
    for resource, amount in resources.items():
        players[player_id]["hand"][resource] -= amount
        bank[resource] += amount
    return True
 

def move_robber(board: Board , new_tile_id: int) -> bool: 
    if new_tile_id == board.robber_tile:
        return False
    
    for vertex in board.tiles[board.robber_tile].vertices:
        board.vertices[vertex].blocked = False
    
    board.tiles[board.robber_tile].robber = False
    board.robber_tile = new_tile_id
    board.tiles[new_tile_id].robber = True 

    for vertex in board.tiles[new_tile_id].vertices:
        board.vertices[vertex].blocked = True

    # Steal logic is handled in steal_resource function
    return True


def end_turn(player_id: int, players: dict) -> bool: 
    if players[player_id]["dice_rolled"] == False or players[player_id]["current_turn"] == False:
        return False
    players[player_id]["dice_rolled"] = False
    players[player_id]["played_card_this_turn"] = False
    players[player_id]["current_turn"] = False
    players[player_id % len(players) + 1]["current_turn"] = True
    return True


# Building Actions
def place_settlement(board, vertex_id: int, player_id: int, players: dict, bank: dict) -> bool: 
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
    bank["brick"] += 1
    bank["wood"] += 1
    bank["sheep"] += 1
    bank["wheat"] += 1
    board.vertices[vertex_id].owner = player_id
    board.vertices[vertex_id].building = "settlement"

    return True


def place_city(board: Board, vertex_id: int, player_id: int, players: dict, bank: dict) -> bool: 
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
    bank["ore"] += 3
    bank["wheat"] += 2
    board.vertices[vertex_id].building = "city"

    return True


def place_road(board: Board, edge_id: int, player_id: int, players: dict, bank: dict) -> bool: 
    if players[player_id]["dice_rolled"] == False:
        return False
    if players[player_id]["roads"] <= 0:
        return False
    if players[player_id]["hand"]["brick"] < 1 or players[player_id]["hand"]["wood"] < 1:
        return False    
    if not can_place_road(board, edge_id, player_id):
        return False
        
    players[player_id]["roads"] -= 1
    players[player_id]["hand"]["brick"] -= 1
    players[player_id]["hand"]["wood"] -= 1
    bank["brick"] += 1
    bank["wood"] += 1
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
        for edge_id2 in board.edges[edge_id].edges:
            if board.edges[edge_id2].owner == player_id:
                return True
    return False


# Development Card Actions
def buy_development_card(player_id: int, development_cards: list, players: dict, bank: dict) -> bool:
    '''
    player_id: ID of the player buying the card
    development_cards: list of available development cards in the game
    players: dict of all players in the game
    ''' 
    if players[player_id]["dice_rolled"] == False:
        return False
    if players[player_id]["hand"]["sheep"] < 1 or players[player_id]["hand"]["wheat"] < 1 or players[player_id]["hand"]["ore"] < 1:
        return False
    if len(development_cards) == 0:
        return False
    
    card = development_cards.pop()
    players[player_id]["development_cards"][card] += 1
    players[player_id]["hand"]["sheep"] -= 1
    players[player_id]["hand"]["wheat"] -= 1
    players[player_id]["hand"]["ore"] -= 1
    bank["sheep"] += 1
    bank["wheat"] += 1
    bank["ore"] += 1

    if card == "victory_point":
        players[player_id]["victory_points"] += 1
    return card
        

def play_knight(player_id: int, players: dict, this_turn_cards: dict) -> bool:
    if not can_play_knight(player_id, players):
        return False
    
    if players[player_id]["development_cards"]["knight"] <= this_turn_cards["knight"]:
        return False

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
        else:
            players[player_id]["largest_army"] = True
            players[player_id]["victory_points"] += 2
    return True


def play_road_building(player_id: int, players: dict, this_turn_cards: list) -> bool:
    if not can_play_road_building(player_id, players):
        return False
    
    if players[player_id]["development_cards"]["road_building"] <= this_turn_cards["road_building"]:
        return False

    players[player_id]["development_cards"]["road_building"] -= 1
    players[player_id]["played_card_this_turn"] = True

    return True


def play_year_of_plenty(player_id: int, players: dict, this_turn_cards: list) -> bool:
    if not can_play_year_of_plenty(player_id, players):
        return False
    
    if players[player_id]["development_cards"]["year_of_plenty"] <= this_turn_cards["year_of_plenty"]:
        return False

    players[player_id]["development_cards"]["year_of_plenty"] -= 1
    players[player_id]["played_card_this_turn"] = True
    return True


def play_monopoly(player_id: int, players: dict, this_turn_cards: list) -> bool:
    if not can_play_monopoly(player_id, players):
        return False
    
    if players[player_id]["development_cards"]["monopoly"] <= this_turn_cards["monopoly"]:
        return False
    
    players[player_id]["development_cards"]["monopoly"] -= 1
    players[player_id]["played_card_this_turn"] = True
    return True
    

def can_play_knight(player_id: int, players: dict) -> bool:
    if players[player_id]["development_cards"]["knight"] <= 0:
        return False
    if players[player_id]["played_card_this_turn"] == True:
        return False
    if players[player_id]["current_turn"] == False:
        return False
    return True


def can_play_road_building(player_id: int, players: dict) -> bool:
    if players[player_id]["development_cards"]["road_building"] <= 0:
        return False
    if players[player_id]["played_card_this_turn"] == True:
        return False
    if players[player_id]["current_turn"] == False:
        return False
    return True


def can_play_year_of_plenty(player_id: int, players: dict) -> bool: 
    if players[player_id]["development_cards"]["year_of_plenty"] <= 0:
        return False
    if players[player_id]["played_card_this_turn"] == True:
        return False
    if players[player_id]["current_turn"] == False:
        return False
    return True


def can_play_monopoly(player_id: int, players: dict) -> bool: 
    if players[player_id]["development_cards"]["monopoly"] <= 0:
        return False
    if players[player_id]["played_card_this_turn"] == True:
        return False
    if players[player_id]["current_turn"] == False:
        return False
    return True


# Trade Actions

def can_do_trade_player(player_id: int, resource_give: dict, players: dict) -> bool:
    # player must have enough of each offered resource
    for resource, amount in resource_give.items():
        if resource not in ["wood", "brick", "sheep", "wheat", "ore"]:
            return False
        if amount <= 0:
            return False
        if amount > players[player_id]["hand"].get(resource, 0):
            return False
    return True


def port_ratios_for_player(player_id: int, players: dict) -> dict:
    # defaults
    ratios = {r: 4 for r in ["wood", "brick", "sheep", "wheat", "ore"]}
    ports = players[player_id].get("ports", []) or []
    for port in ports:
        if port is None:
            continue
        if port == "3:1":
            for k in ratios:
                ratios[k] = min(ratios[k], 3)
        else:
            port_name = port.split(" ")[1].lower()
            if port_name in ratios and ratios[port_name] > 2:
                ratios[port_name] = 2
    return ratios


def can_do_trade_bank(player_id: int, resource_give: dict, resource_receive: dict, players: dict, bank: dict) -> bool:
    # validate receive side (bank must have enough)
    for resource, amount in resource_receive.items():
        if resource not in ["wood", "brick", "sheep", "wheat", "ore"]:
            return False
        if amount <= 0:
            return False
        if bank.get(resource, 0) < amount:
            return False

    # validate offer side against ratios and player’s hand
    ratios = port_ratios_for_player(player_id, players)
    # while not strictly required by rules, enforce that offer converts to an integer number of receive cards
    total_receivable = 0
    for resource, amount in resource_give.items():
        if resource not in ratios or amount <= 0:
            return False
        if players[player_id]["hand"].get(resource, 0) < amount:
            return False
        if amount % ratios[resource] != 0:
            return False
        total_receivable += amount // ratios[resource]

    ask_total = sum(resource_receive.values())
    if ask_total != total_receivable:
        return False

    return True


def complete_trade_player(trader_id: int, partner_id: int, offer: dict, request: dict, players: dict) -> bool:
    # final validation (both sides still have cards)
    if not can_do_trade_player(trader_id, offer, players):
        return False
    if not can_do_trade_player(partner_id, request, players):
        return False

    # execute transfer
    for r, a in offer.items():
        players[trader_id]["hand"][r] -= a
        players[partner_id]["hand"][r] += a
    for r, a in request.items():
        players[partner_id]["hand"][r] -= a
        players[trader_id]["hand"][r] += a
    return True


def complete_trade_bank(player_id: int, resource_give: dict, resource_receive: dict, players: dict, bank: dict) -> bool:
    for resource, amount in resource_give.items():
        players[player_id]["hand"][resource] -= amount
        bank[resource] += amount
    for resource, amount in resource_receive.items():
        players[player_id]["hand"][resource] += amount
        bank[resource] -= amount
    return True


def trade_possible(player_id: int, offer: dict, request: dict, players: dict, bank: dict) -> bool:
    # proposer must be able to pay offer
    if not can_do_trade_player(player_id, offer, players):
        return False
    # at least one other player must be able to pay the request
    for pid in players:
        if pid == player_id:
            continue
        if can_do_trade_player(pid, request, players):
            return True
    return False


# Misc Actions
def calculate_longest_road(board, player_id: int, players: dict) -> None: 
    max_length = 0
    for vertex in board.vertices:
        for edge in vertex.edges:
            if board.edges[edge].owner == player_id:
                stack = [(edge, vertex.id, 1)]  # (current_edge, visited_edges and current vertex, current_length)
                visited_edges = {edge}
                while stack:
                    current_edge, last_vertex, length = stack.pop()
                    max_length = max(max_length, length)

                    for vertex_2 in board.edges[current_edge].vertices:
                        if vertex_2 == last_vertex or (board.vertices[vertex_2].owner not in (None, player_id)):
                            continue

                        for next_edge in board.vertices[vertex_2].edges:
                            if board.edges[next_edge].owner == player_id and next_edge not in visited_edges:
                                visited_edges.add(next_edge)
                                stack.append((next_edge, vertex_2, length + 1))
                
    players[player_id]["longest_road_length"] = max_length


def update_longest_road(players: dict) -> None:
    # find the player with the longest road
    longest_road_length = 0
    longest_road_player = None
    longest_road_holder = None
    for player_id in players.keys():
        if players[player_id]["longest_road_length"] > longest_road_length:
            longest_road_length = players[player_id]["longest_road_length"]
            longest_road_player = player_id
        if players[player_id]["longest_road"] == True:
            longest_road_holder = player_id
    
    # check if we need to update
    if longest_road_length < 5 and longest_road_holder is not None:
        players[longest_road_holder]["longest_road"] = False
        players[longest_road_holder]["victory_points"] -= 2
        return

    elif longest_road_length >= 5:
        if longest_road_holder is None:
            players[longest_road_player]["longest_road"] = True
            players[longest_road_player]["victory_points"] += 2
            return
        elif longest_road_holder != longest_road_player and players[longest_road_holder]["longest_road_length"] < longest_road_length:
            players[longest_road_holder]["longest_road"] = False
            players[longest_road_holder]["victory_points"] -= 2
            players[longest_road_player]["longest_road"] = True
            players[longest_road_player]["victory_points"] += 2
            return


def steal_resource(board: Board, stealer_id: int, victim_id: int, players: dict) -> bool: 
    if not can_steal(board, stealer_id, victim_id):
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


def can_steal(board: Board, stealer_id: int, victim_id: int) -> bool: 
    # robber must be on a tile adjacent to a settlement/city of the victim
    if stealer_id == victim_id:
        return False
    if board.robber_tile == None:
        return False
    for vertex in board.tiles[board.robber_tile].vertices:
        if board.vertices[vertex].owner == victim_id:
            return True
    return False 

def robbable_players_on_tile(board: Board, players: dict, tile_id: int, current: int) -> list[int]:
    vertices = board.tiles[tile_id].vertices
    seen = set()
    for vertex in vertices:
        if board.vertices[vertex].building is not None and board.vertices[vertex].owner != current:
            if sum(players[board.vertices[vertex].owner]["hand"].values()) > 0:
                seen.add(board.vertices[vertex].owner)
    
    return sorted(seen)


def initial_placement_round(board: Board, vertex_id: int, player_id: int, players: dict) -> bool:
    if board.vertices[vertex_id].owner != None and board.vertices[vertex_id].building != None:
        return False
    for neighbor in board.vertices[vertex_id].vertices:
        if board.vertices[neighbor].building != None or board.vertices[neighbor].owner != None:
            return False
    board.vertices[vertex_id].owner = player_id
    board.vertices[vertex_id].building = "settlement"
    players[player_id]["settlements"] -= 1
    players[player_id]["victory_points"] += 1
    
    if board.vertices[vertex_id].port != None:
        players[player_id]["ports"].append(board.vertices[vertex_id].port)
    return True

def initial_placement_round_road(board: Board, edge_id: int, player_id: int, players: dict, vertex_id: int) -> bool:
    if board.edges[edge_id].owner != None:
        return False
    if vertex_id not in board.edges[edge_id].vertices:
        return False
    if board.vertices[vertex_id].owner != player_id:
        return False
    board.edges[edge_id].owner = player_id
    players[player_id]["roads"] -= 1
    return True