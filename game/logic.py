import random
from game import Board
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
        pass

    def seven_rolled(self):
        # Logic for when a 7 is rolled (robber movement, discarding cards, etc.)
        pass

    def process_action(self, player_id, action):
        # Logic to process a player's action (build, trade, etc.)
        pass
    

    def get_game_state(self, player_id: int):
        # Return a representation of the current game state as a json
        return {
            "game_id": self.game_id,
            "players": self.players,
            "current_turn": self.current_turn,
            "bank": self.bank,
            "development_cards_remaining": len(self.development_cards),
            "board": self.board.board_to_json()
        }