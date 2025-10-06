import random
import json
from game.action import *
from game.board import Board

NEXT_ACTION = ["Discard", "Move Robber", "Steal Resource", "Pick Monopoly Target", "Pick Year of Plenty Resources", "Place Road 2", "Place Road 1", None]

# Game Logic file
class Game:
    def __init__(self):
        self.players = {}
        self.bank = {"wood": 19, "brick": 19, "sheep": 19, "wheat": 19, "ore": 19}
        self.development_cards = ["knight"] * 14 + ["victory_point"] * 5 + ["road_building"] * 2 + ["year_of_plenty"] * 2 + ["monopoly"] * 2
        random.shuffle(self.development_cards)
        self.number = None
        self.board = Board()
        self.initial_placement_order = None
        self.counter = 0
        self.last_vertex_initial_placement = None

        # Forced Actions (These have to be done before any other action can be taken)
        self.pending_discard: dict[int, int] = {}  # player_id -> number of cards to discard 
        self.forced_action: str | None = None  # One of NEXT_ACTION

        self.robber_candidates: list[int] = []
        self.pending_robber_tile: int | None = None

    def add_player(self, player_id):
        if player_id not in self.players:
            self.players[player_id] = {
                "hand": {"wood": 0, "brick": 0, "sheep": 0, "wheat": 0, "ore": 0},
                "development_cards": {"knight": 0, "victory_point": 0, "road_building": 0, "year_of_plenty": 0, "monopoly": 0},
                "played_knights": 0,
                "longest_road_length": 0,
                "victory_points": 0,
                "settlements": 5,
                "cities": 4,
                "roads": 15,
                "ports": [],
                "longest_road": False,
                "largest_army": False,
                "played_card_this_turn": False,
                "dice_rolled": False,
                "current_turn": False,
                
                "total_hand": 0,  # For public state
                "total_development_cards": 0,  # For public state
                "victory_points_without_vp_cards": 0  # For public state
            }
    
    def remove_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]

    def start_game(self):
        if len(self.players) < 2 or len(self.players) > 4:
            return False
        current_turn = random.choice(list(self.players.keys()))
        self.players[current_turn]["current_turn"] = True
        # make initial placement phase pattern  (1,2,3,4,4,3,2,1) (based on player ids) (1 = current turn player)
        order = list(range(1, len(self.players)+1))
        order = order[current_turn-1:] + order[:current_turn-1]
        order += order[::-1]
        self.initial_placement_order = [i for i in order for _ in (range(2))]

        # The initial placement phase is done separately, since it requires player interaction
        self.current_turn = current_turn
        return self.get_multiplayer_game_state()
    

    def initial_placement_phase(self, player_id: int, action: dict) -> dict:
        # check if action is from the correct player
        if player_id != self.initial_placement_order[self.counter]:
                return False
                    
        # check if action is even (settlement) or odd (road)
        if self.counter % 2 == 0: # settlement
            if not action.get("type") == "place_settlement":
                return False
            if not initial_placement_round(board = self.board, vertex_id = int(action.get("vertex_id")), player_id = player_id, players = self.players):
                return False
            
            # check if second round of initial placement
            if self.counter >= len(self.initial_placement_order)//2:
                # give resources for the settlement placed
                for tile in self.board.vertices[int(action.get("vertex_id"))].tiles:
                    resource = self.board.tiles[tile].resource
                    if resource != "Desert":
                        self.players[player_id]["hand"][resource.lower()] += 1
                        self.bank[resource.lower()] -= 1
            
            self.last_vertex_initial_placement = int(action.get("vertex_id"))
        
        else: # road
            if not action.get("type") == "place_road":
                return False
            
            # check if edge is connected to last placed settlement
            if self.last_vertex_initial_placement is None:
                return False
            connected_edges = self.board.vertices[self.last_vertex_initial_placement].edges
            if int(action.get("edge_id")) not in connected_edges:
                return False
            
            if not initial_placement_round_road(board = self.board, edge_id = int(action.get("edge_id")), player_id = player_id, players = self.players, vertex_id=self.last_vertex_initial_placement):
                return False
            
            self.last_vertex_initial_placement = None
        
        
        
        self.counter += 1
        return True
            

 

    
    
    def call_action(self, player_id: int, action: dict) -> bool | dict:
        
        if self.counter < len(self.initial_placement_order): # only allow initial placement actions
            success = self.initial_placement_phase(player_id, action)
        else:
            success = self.process_action(player_id, action)
        
        if not success:
            return False

        # Calculate longest road, as it can change after any action
        for player_id in self.players.keys():
            calculate_longest_road(self.board, player_id, self.players)
        update_longest_road(self.players)
        
        if self.players[player_id]["victory_points"] >= 10:
            return player_id  # player_id won
        
        # return a list of game states for all players
        print(self.get_multiplayer_game_state()) # DEBUG
        print("\n ---- \n")
        return self.get_multiplayer_game_state()


    def process_action(self, player_id: int, action: dict) -> bool:
        # Validate turn and phase

        action_type = action.get("type")

        # Unless action is accept trade, decline trade or discard resources (These can be done out of turn) TODO
        if self.forced_action == "Discard" and action_type == "discard_resources":
            pass
        elif player_id != self.current_turn:
            return False
      

        
        # Route action (Return False if action is invalid)
        # TODO so for the multi input actions we can have one bool that switchws between modes  (e.g. after rolling a 7, discarding resources and moving robber are the only valid actions)
        match action_type:
            # General actions
            case "roll_dice": # TODO if seven is rolled ask for discarding ressources and move robber, Game Logic has to be here not the server.
                self.number = roll_dice(board = self.board, players = self.players, player_id = player_id, bank = self.bank)
                if self.number is False:
                    return False
                
                if self.number == 7:
                    self.pending_discard.clear()
                    for pid, pdata in self.players.items():
                        total_cards = sum(pdata["hand"].values())
                        if total_cards > 7:
                            self.pending_discard[pid] = total_cards // 2
                        
                    if self.pending_discard:
                        self.forced_action = "Discard"
                    else:
                        self.forced_action = "Move Robber"

                return True
            
            case "end_turn":
                if end_turn(player_id = player_id, players = self.players):
                    self.number = None
                    self.current_turn = (self.current_turn % len(self.players)) + 1
                    return True
                else:
                    return False
            
            case "discard_resources":
                 # Only valid during forced Discard phase and only for players who still owe
                if self.forced_action != "Discard" or player_id not in self.pending_discard or self.pending_discard[player_id] <= 0:
                    return False
                owed = self.pending_discard.get(player_id, 0)
                if owed <= 0:
                    return False

                # Validate total matches owed
                resources = action.get("resources", {}) or {}
                total_to_remove = sum(int(resources.get(k, 0)) for k in ["wood","brick","sheep","wheat","ore"])
                if total_to_remove != owed:
                    return False

                ok = remove_resources(player_id = player_id, players = self.players, resources = resources, bank = self.bank)
                if not ok:
                    return False

                # Mark this player's discard as satisfied
                self.pending_discard[player_id] = 0

                # If all finished, advance to robber placement
                if all(v <= 0 for v in self.pending_discard.values()):
                    self.forced_action = "Move Robber"

                return True
            
            case "move_robber":
                # Only current player resolves robber
                if player_id != self.current_turn or self.forced_action != "Move Robber":
                    return False
                
                target_tile = int(action.get("target_tile"))
                # Step 1: placing the robber (always allowed when called)
                if not move_robber(board=self.board, new_tile_id=target_tile):
                    return False

                # Figure out eligible victims at this tile (exclude self)
                cands = self._robbable_players_on_tile(target_tile, player_id)
                self.pending_robber_tile = target_tile
                self.robber_candidates = cands
                self.forced_action = "Steal Resource" if cands else None
                return True

            case "robber_steal":
                # Current player must pick among announced candidates
                if self.forced_action != "Steal Resource" or player_id != self.current_turn:
                    return False
                
                victim = int(action.get("victim_id"))
                if victim not in (self.robber_candidates or []):
                    return False
                if not steal_resource(board=self.board, players=self.players, stealer_id=player_id, victim_id=victim):
                    return False
                
                self.robber_candidates = []
                self.pending_robber_tile = None
                return True

            # Building actions
            case "place_road":
                return place_road(board = self.board, edge_id = int(action.get("edge_id")), player_id = player_id, players = self.players, bank = self.bank)
            
            case "place_settlement":
                return place_settlement(board = self.board, vertex_id = int(action.get("vertex_id")), player_id = player_id, players = self.players, bank = self.bank)
            
            case "place_city":
                return place_city(board = self.board, vertex_id = int(action.get("vertex_id")), player_id = player_id, players = self.players, bank = self.bank)
            
            case "buy_development_card":
                return buy_development_card(player_id= player_id, development_cards = self.development_cards, players = self.players, bank = self.bank)

            # Development Card actions
            case "play_knight_card":
                if not play_knight(board = self.board, player_id = player_id, players = self.players, target_tile=int(action.get("target_tile"))):
                    return False
                if not steal_resource(board = self.board, players = self.players, stealer_id = player_id, victim_id = int(action.get("victim_id"))):
                    return False
                return True
                
            case "play_road_building_card":
                return play_road_building(board = self.board, player_id = player_id, players = self.players, roads = action.get("edge_ids", []))
    
            case "play_year_of_plenty_card":
                return play_year_of_plenty(player_id = player_id, resources = action.get("resources", []), players = self.players, bank = self.bank)
            
            case "play_monopoly_card":
                return play_monopoly(player_id = player_id, resource = action.get("resource"), players = self.players)
        
            # Trade actions TODO (Trades are not yet fully implemented)
            case "bank_trade": # Bank Trades skip other players
                if not can_do_trade_bank(player_id = player_id, resource_give = action.get("offer", {}), resource_receive = action.get("request", {}), players = self.players, bank = self.bank):
                    return False
                return complete_trade_bank(player_id = player_id, offer = action.get("offer", {}), request = action.get("request", {}), players = self.players, bank = self.bank)
            
            case "propose_trade": # Dont Forget to check what players can do trade (This only checks if there is atleast one possible trade partner) TODO
                return trade_possible(player_id = player_id, offer = action.get("offer", {}), request = action.get("request", {}), players = self.players, bank = self.bank)
             
            case "accept_trade":
                return complete_trade_player(player_id = player_id, trader = int(action.get("trader_id")), offer = action.get("offer", {}), request = action.get("request", {}), players = self.players)

            case _:
                return False
            
    def _robbable_players_on_tile(self, tile_id: int, current: int) -> list[int]:
        vertices = self.board.tiles[tile_id].vertices
        seen = set()
        for vertex in vertices:
            if self.board.vertices[vertex].building is not None and self.board.vertices[vertex].owner != current:
                if sum(self.players[self.board.vertices[vertex].owner]["hand"].values()) > 0:
                    seen.add(self.board.vertices[vertex].owner)
        
        return sorted(seen)
    
    # Update we always want the full game state for each player (since hidden info) (And send it to everyone)
    def get_multiplayer_game_state(self) -> dict:
        # add total development cards and hand size for all players, so it can be used in public state
        for _, pdata in self.players.items():
            pdata["total_hand"] = sum(pdata["hand"].values())
            pdata["total_development_cards"] = sum(pdata["development_cards"].values())
            pdata["victory_points_without_vp_cards"] = pdata["victory_points"] - pdata["development_cards"]["victory_point"]

        result = {}
        for player in self.players.keys():
            player_data = {player: json.dumps(self.players[player])}
            public_player_data = self.public_player_state(player)
            players = {**player_data, **public_player_data}
            must_discard = self.pending_discard.get(player, 0) if self.forced_action == "Discard" else 0

            result[player] = {
                "board": self.board.board_to_json(),
                "players": players,
                "bank": self.bank,
                "development_cards_remaining": len(self.development_cards),
                "current_turn": self.current_turn,
                "current_roll": self.number,
                "initial_placement_order": self.initial_placement_order[self.counter] if self.counter < len(self.initial_placement_order) else -1,
                
                "forced_action": self.forced_action,
                "must_discard": must_discard,
                "robber_candidates": self.robber_candidates,         # [] or [2,3,...]
                "pending_robber_tile": self.pending_robber_tile,     # int or None
            }
        return result


    def public_player_state(self, player_id: int) -> dict:
        # all players except player_id
        player_id_public_state = {}
        for pid, pdata in self.players.items():
            if pid == player_id:
                continue
            player_id_public_state[pid] = {
                "total_hand": pdata["total_hand"],
                "total_development_cards": pdata["total_development_cards"],
                "victory_points_without_vp_cards": pdata["victory_points_without_vp_cards"],

                "played_knights": pdata["played_knights"],
                "longest_road_length": pdata["longest_road_length"],
                "victory_points": pdata["victory_points"] - pdata["development_cards"]["victory_point"],
                "settlements": pdata["settlements"],
                "cities": pdata["cities"],
                "roads": pdata["roads"],
                "ports": pdata["ports"],
                "longest_road": pdata["longest_road"],
                "largest_army": pdata["largest_army"],
                "played_card_this_turn": pdata["played_card_this_turn"],
                "dice_rolled": pdata["dice_rolled"],
                "current_turn": pdata["current_turn"]
            }
        return player_id_public_state


        