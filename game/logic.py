import random
from game import Board
from game import *
class Game:
    def __init__(self, game_id):
        self.game_id = game_id
        self.players = {}
        self.current_turn = None
        self.bank = {"wood": 19, "brick": 19, "sheep": 19, "wheat": 19, "ore": 19}
        self.development_cards = ["knight"] * 14 + ["victory_point"] * 5 + ["road_building"] * 2 + ["year_of_plenty"] * 2 + ["monopoly"] * 2
        random.shuffle(self.development_cards)
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
                "current_turn": False
            }

    def start_game(self):
        if len(self.players) < 3 or len(self.players) > 4:
            return False
        self.current_turn = random.choice(list(self.players.keys()))
        # The inital placement phase is done separately, since it requires player interaction
        return self.get_start_game_state()

    def process_action(self, player_id, action):
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
        
        - After every action check for win condition (if player has 8 victory points)
        '''
        # Validate turn and phase (Return False if not valid)
        if player_id != self.current_turn:
            return False
        action_type = action.get("type")

        # Route action (Return False if action is invalid)
        match action_type:
            # General actions
            case "roll_dice":
                pass
            case "end_turn":
                pass

            # Building actions
            case "place_road":
                pass
            case "place_settlement":
                pass
            case "place_city":
                pass
            case "buy_development_card":
                pass

            # Development Card actions
            case "play_knight_card":
                pass
            case "play_road_building_card":
                pass
            case "play_year_of_plenty_card":
                pass
            case "play_monopoly_card":
                pass
        
            # Trade actions
            case "trade_with_bank":
                pass
            case "propose_trade":
                pass
            case "trade_response":
                pass
            case "accept_trade":
                pass
            
            case _:
                return False
            
        # check win condition

        # Return win of win condition met
        if self.players[player_id]["victory_points"] >= 10:
            return "Game Won"

        # Return new game state with action applied or trade state for trade actions
        return self.get_multiplayer_game_state(player_id)
            


        
    def get_multiplayer_game_state(self, player_id: int):
        # Return a representation of the current game state as a json
        # From the point of view of player_id
        # Include public information about other players
        # Include private information about player_id
        # Include board state
        # Include bank state
        # Include development card state
        pass 

    def board_state(self):
        # Return the current state of the board
        pass
    

    def private_player_state(self, player_id: int):
        # Return the private state of player_id
        pass


    def public_player_state(self, player_id: int):
        # Return the public state of all players except player_id
        pass
    
    def get_start_game_state(self):
        pass 



    def can_afford(self, player_id: int, element: int) -> list[bool]: # TODO futher implementation
        # Return a list of booleans indicating if player_id can afford to build an element
        pass

