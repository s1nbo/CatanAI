import unittest
import random
from game import action, Board


class TestActions(unittest.TestCase):
    def setUp(self):
        self.bank = {"wood": 19, "brick": 19, "sheep": 19, "wheat": 19, "ore": 19}
        self.board = Board()
        self.players = {
            1: {"hand": {"wood": 2, "brick": 2, "sheep": 2, "wheat": 2, "ore": 2},
                "dice_rolled": False, "current_turn": True, "settlements": 5, "cities": 4, "roads": 15,
                "development_cards": {"knight": 2, "victory_point": 0, "road_building": 1, "year_of_plenty": 1, "monopoly": 1},
                "played_knights": 0, "longest_road": 0, "victory_points": 0, "ports": [], "played_card_this_turn": False, "largest_army": False},
            2: {"hand": {"wood": 1, "brick": 1, "sheep": 1, "wheat": 1, "ore": 1},
                "dice_rolled": False, "current_turn": False, "settlements": 5, "cities": 4, "roads": 15,
                "development_cards": {"knight": 0, "victory_point": 0, "road_building": 0, "year_of_plenty": 0, "monopoly": 0},
                "played_knights": 0, "longest_road": 0, "victory_points": 0, "ports": [], "played_card_this_turn": False, "largest_army": False}
        }
        self.development_cards = ["knight", "victory_point", "road_building", "year_of_plenty", "monopoly"]

    def test_roll_dice(self):
        result = action.roll_dice(self.board, self.players, 1, self.bank)
        self.assertIn(result, range(2,13))

    def test_amount_lose_resource(self):
        self.assertEqual(action.amount_lose_resource(1, self.players), 5)
        self.assertEqual(action.amount_lose_resource(2, self.players), 0)

    def test_remove_resources(self):
        self.assertTrue(action.remove_resources(1, self.players, {"wood": 1}))
        self.assertFalse(action.remove_resources(2, self.players, {"wood": 2}))

    def test_move_robber(self):
        self.assertTrue(action.move_robber(self.board, 0))
        action.move_robber(self.board, 3)
        self.assertFalse(action.move_robber(self.board, 3))

    def test_end_turn(self):
        self.assertTrue(action.end_turn(1, self.players))

    def test_place_settlement(self):
        self.players[1]["dice_rolled"] = True
        self.board.edges[0].owner = 1
        self.assertTrue(action.place_settlement(self.board, 0, 1, self.players))

    def test_place_city(self):
        self.players[1]["dice_rolled"] = True
        self.board.vertices[0].owner = 1
        self.board.vertices[0].building = 'settlement'
        self.players[1]["hand"]["ore"] += 1
        self.assertTrue(action.place_city(self.board, 0, 1, self.players))

    def test_place_road(self):
        self.players[1]["dice_rolled"] = True
        self.board.edges[1].owner = 1
        self.assertTrue(action.place_road(self.board, 0, 1, self.players))

    def test_can_place_settlement(self):
        self.assertFalse(action.can_place_settlement(self.board, 0, 1))

    def test_can_place_city(self):
        self.assertFalse(action.can_place_city(self.board, 0, 1))

    def test_can_place_road(self):
        self.board.vertices[0].owner = 1
        self.board.vertices[0].building = 'settlement'
        self.assertTrue(action.can_place_road(self.board, 0, 1))

    def test_buy_development_card(self):
        self.players[1]["dice_rolled"] = True
        self.assertTrue(action.buy_development_card(1, self.development_cards, self.players))

    def test_play_knight(self):
        self.players[1]["dice_rolled"] = True
        self.players[1]["played_card_this_turn"] = False

        self.assertTrue(action.play_knight(self.board, 1, 0, self.players))

    def test_play_road_building(self):
        self.players[1]["dice_rolled"] = True
        self.players[1]["played_card_this_turn"] = False
        self.board.vertices[0].owner = 1
        self.board.vertices[1].building = 'settlement'
        self.assertTrue(action.play_road_building(self.board, 1, [0], self.players))

    def test_play_year_of_plenty(self):
        self.players[1]["played_card_this_turn"] = True
        self.assertFalse(action.play_year_of_plenty(1, ["wood"], self.players, self.bank))
        self.players[1]["dice_rolled"] = True
        self.players[1]["played_card_this_turn"] = False
        self.assertTrue(action.play_year_of_plenty(1, ["wood"], self.players, self.bank))

    def test_play_monopoly(self):
        self.players[1]["dice_rolled"] = True
        self.assertTrue(action.play_monopoly(1, "wood", self.players))

    def test_trade_possible(self):
        self.players[1]["dice_rolled"] = True
        self.assertTrue(action.trade_possible(1, {"wood": 1}, {"brick": 1}, self.players, self.bank))

    def test_complete_trade_player(self):
        self.assertTrue(action.complete_trade_player(1, 2, {"wood": 1}, {"brick": 1}, self.players))

    def test_complete_trade_bank(self):
        self.assertTrue(action.complete_trade_bank(1, {"wood": 1}, {"brick": 1}, self.players, self.bank))

    def test_longest_road(self):
        action.longest_road(self.board, 1, self.players)
        self.assertIn("longest_road_length", self.players[1])

    def test_steal_resource(self):
        target_tile = self.board.robber_tile
        vertex = self.board.tiles[target_tile].vertices[0]
        self.board.vertices[vertex].owner = 2
        self.board.vertices[vertex].building = 'settlement'
        self.board.vertices[vertex].blocked = True
        self.assertTrue(action.steal_resource(self.board, 1, 2, self.players))

    def test_can_steal(self):
        # place a settlement for player 2 on a tile adjacent to the robber
        self.assertFalse(action.can_steal(self.board, 1, 1, self.players))
        target_tile = self.board.robber_tile
        vertex = self.board.tiles[target_tile].vertices[0]
        self.board.vertices[vertex].owner = 2
        self.board.vertices[vertex].building = 'settlement'
        self.board.vertices[vertex].blocked = True
        self.assertTrue(action.can_steal(self.board, 1, 2, self.players))

if __name__ == "__main__":
    unittest.main()
