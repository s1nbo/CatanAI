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
        self.current_turn = random.choice(list(self.players.keys()))
        # First Player sets first settlements and road
        # Second Player sets first settlements and road
        # Third Player sets first settlement and road
        # Fourth Player sets first settlement and road

        # Fourth Player sets second settlement and road and gets ressources
        # Third Player sets second settlement and road and gets ressources
        # Second Player sets second settlement and road and gets ressources
        # First Player sets second settlement and road and gets ressources

        # First Player starts the game
        pass

    def process_action(self, player_id, action):
        '''
        What can a player do?
        - Play one Development Card 
        - Roll Dice -> Ressources Distribution / Robber + Steal

        - Trade with Bank
        - Propose Trade with Player
        - Accept/Decline Trade with Player
        - Trade with Player (if accepted)
        
        - Build Road
        - Build Settlement
        - Upgrade to City

        - End Turn
        
        - After every action check for win condition (if player has 8 victory points)
        '''
        # Validate turn and phase (Return False if not valid)

        # Route action (Return False if action is invalid)

        # Return True or False if action was successful

        # check win condition or turn/phase change

        # return new game state if necessary
        
    

    def get_multiplayer_game_state(self, player_id: int):
        # Return a representation of the current game state as a json
        # From the point of view of player_id
        # Include public information about other players
        # Include private information about player_id
        # Include board state
        # Include bank state
        # Include development card state
        
        return {
            "game_id": self.game_id,
            "players": self.players,
            "current_turn": self.current_turn,
            "bank": self.bank,
            "development_cards_remaining": len(self.development_cards),
            "board": self.board.board_to_json()
        }


    def board_state(self):
        pass
    

    def private_player_state(self, player_id: int):
        pass


    def public_player_state(self, player_id: int):
        pass


    def can_afford(self, player_id: int, element: int) -> list[bool]: # TODO futher implementation
        pass
