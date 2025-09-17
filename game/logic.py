import random
import json
from action import *
from board import Board

# Game Logic file
class Game:
    def __init__(self, game_id):
        self.game_id = game_id
        self.players = {}
        self.bank = {"wood": 19, "brick": 19, "sheep": 19, "wheat": 19, "ore": 19}
        self.development_cards = ["knight"] * 14 + ["victory_point"] * 5 + ["road_building"] * 2 + ["year_of_plenty"] * 2 + ["monopoly"] * 2
        random.shuffle(self.development_cards)
        self.number = None
        self.board = Board()

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

    def start_game(self):
        if len(self.players) < 3 or len(self.players) > 4:
            return False
        current_turn = random.choice(list(self.players.keys()))
        self.players[current_turn]["current_turn"] = True

        # The inital placement phase is done separately, since it requires player interaction
        return self.get_multiplayer_game_state(current_turn)
    
    def call_action(self, player_id: int, action: dict) -> bool | dict:
        success = self.process_action(player_id, action)
        if not success:
            return False
        
        if self.players[player_id]["victory_points"] >= 10:
            return True
        
        # return a list of game states for all players
        result = {}
        for pid in self.players:
            result[pid] = self.get_multiplayer_game_state(pid)
        return result


    def process_action(self, player_id: int, action: dict) -> bool:
        '''
        What can a player do?

        - Roll Dice -> Ressources Distribution / Robber + Steal
        - End Turn

        - Build Road
        - Build Settlement
        - Upgrade to City

        - Play one Development Card 

        - Trade with Bank
        - Propose Trade with Player
        - Accept/Decline Trade with Player
        - Trade with Player (if accepted)
        
        Action dict example:
        'type' (Str)
        'resources' (Dict or List)
        'target_tile' (Int)
        'victim_id' (Int)
        'vertex_id' (Int)
        'edge_id' (Int)
        'trader_id' (Int)
        'offer' (Dict)
        'request' (Dict)
        'edge_ids' (List[Int])
        'resource' (Str)
        '''
        # Validate turn and phase
        if player_id != self.current_turn:
            return False
        action_type = action.get("type")
        
        # Route action (Return False if action is invalid)
        match action_type:
            # General actions
            case "roll_dice": # TODO if seven is rolled ask for discarding ressources and move robber
                self.number = roll_dice(board = self.board, players = self.players, player_id = player_id, bank = self.bank)
                if self.number is False:
                    return False
                return True
            
            case "end_turn":
                return end_turn(player_id = player_id, players = self.players)
            
            case "discard_resources":
                return remove_resources(player_id = player_id, players = self.players, resources = action.get("resources", {}))
            
            case "move_robber":
                if not move_robber(board = self.board, target_tile = int(action.get("target_tile"))):
                    return False
                if not steal_resource(board = self.board, players = self.players, player_id = player_id, target_player_id = int(action.get("victim_id"))):
                    return False
                return True
    
            # Building actions
            case "place_road":
                return place_road(board = self.board, edge_id = int(action.get("edge_id")), player_id = player_id, players = self.players)
            
            case "place_settlement":
                return place_settlement(board = self.board, vertex_id = int(action.get("vertex_id")), player_id = player_id, players = self.players)
            
            case "place_city":
                return place_city(board = self.board, vertex_id = int(action.get("vertex_id")), player_id = player_id, players = self.players)
            
            case "buy_development_card":
                return buy_development_card(player_id= player_id, development_cards = self.development_cards, players = self.players)

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
        
            # Trade actions
            case "trade_with_bank": # Bank Trades skip other players
                if not can_do_trade_bank(player_id = player_id, resource_give = action.get("offer", {}), resource_receive = action.get("request", {}), players = self.players, bank = self.bank):
                    return False
                return complete_trade_bank(player_id = player_id, offer = action.get("offer", {}), request = action.get("request", {}), players = self.players, bank = self.bank)
            
            case "propose_trade": # Dont Forget to check what players can do trade (This only checks if there is atleast one possible trade partner) TODO
                return trade_possible(player_id = player_id, offer = action.get("offer", {}), request = action.get("request", {}), players = self.players, bank = self.bank)
             
            case "accept_trade": # Makes the Trade if both players agreed TODO
                return complete_trade_player(player_id = player_id, trader = int(action.get("trader_id")), offer = action.get("offer", {}), request = action.get("request", {}), players = self.players)

            # Inital Placement Phase actions, Remeber to check if road is attached to the settlement placed (second road cannot be placed next to first settlement)
            case "place_initial_settlement_one":
                return inital_placement_round_one(board = self.board, vertex_id = int(action.get("vertex_id")), player_id = player_id, players = self.players)
            case "place_initial_road":
                return inital_placement_round_road(board = self.board, edge_id = int(action.get("edge_id")), player_id = player_id, players = self.players)
            case "place_initial_settlement_two":
                return inital_placement_round_two(board = self.board, vertex_id = int(action.get("vertex_id")), player_id = player_id, players = self.players, bank = self.bank)


            case _:
                return False


    def get_multiplayer_game_state(self, player_id: int) -> dict:
        # add total development cards and hand size for all players, so it can be used in public state
        for _, pdata in self.players.items():
            pdata["total_hand"] = sum(pdata["hand"].values())
            pdata["total_development_cards"] = sum(pdata["development_cards"].values())
            pdata["victory_points_without_vp_cards"] = pdata["victory_points"] - pdata["development_cards"]["victory_point"]


        player_data = {player_id: json.dumps(self.players[player_id])}
        public_player_data = self.public_player_state(player_id)
        players = {**player_data, **public_player_data}
        return {
            "board": self.board.board_to_json(),
            "players": players,
            "bank": self.bank,
            "development_cards_remaining": len(self.development_cards),
            "current_turn": self.current_turn
        }


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
    