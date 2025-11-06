import numpy as np
import orjson as json

import torch
from torch_geometric.data import Data

class ObservationEncoder:
    def __init__(self):
        self.state = None
        self.player_id = None # 1-4 
        self.player_count = None # 1-4

        self.tile_features = []
        self.vertex_features = []
        self.edge_features = []

        self.resource_map = {
            "wood": [1,0,0,0,0,0],
            "brick": [0,1,0,0,0,0],
            "sheep": [0,0,1,0,0,0],
            "wheat": [0,0,0,1,0,0],
            "ore": [0,0,0,0,1,0],
            "Desert": [0,0,0,0,0,1],
        }

        self.number_map = {
            2: [1,0,0,0,0,0,0,0,0,0,0],
            3: [0,1,0,0,0,0,0,0,0,0,0],
            4: [0,0,1,0,0,0,0,0,0,0,0],
            5: [0,0,0,1,0,0,0,0,0,0,0],
            6: [0,0,0,0,1,0,0,0,0,0,0],
            8: [0,0,0,0,0,1,0,0,0,0,0],
            9: [0,0,0,0,0,0,1,0,0,0,0],
            10:[0,0,0,0,0,0,0,1,0,0,0],
            11:[0,0,0,0,0,0,0,0,1,0,0],
            12:[0,0,0,0,0,0,0,0,0,1,0],
            0: [0,0,0,0,0,0,0,0,0,0,1], # desert
        }

        self.building_map = {
            None: [1,0,0],
            "settlement": [0,1,0],
            "city": [0,0,1],
        }

        self.owner_map = {
            1: [1,0,0,0,0],
            2: [0,1,0,0,0],
            3: [0,0,1,0,0],
            4: [0,0,0,1,0],
            None: [0,0,0,0,1], # no owner
        }

        self.port_map = {
            None: [1,0,0,0,0,0,0],
            "2:1 Wood": [0,1,0,0,0,0,0],
            "2:1 Brick": [0,0,1,0,0,0,0],
            "2:1 Sheep": [0,0,0,1,0,0,0],
            "2:1 Wheat": [0,0,0,0,1,0,0],
            "2:1 Ore": [0,0,0,0,0,1,0],
            "3:1": [0,0,0,0,0,0,1],
        }


        self.tiles_tiles = []
        self.tiles_vertices = []
        self.tiles_edges = []

        self.vertices_tiles = []
        self.vertices_vertices = []
        self.vertices_edges = []

        self.edges_tiles = []
        self.edges_vertices = []
        self.edges_edges = []

    def handle_state_from_server(self, state_json: str):
        state = json.loads(state_json)
        self.observe(state)

    def encode_tile(self, t): # 21 elements
        typeflag = [1, 0, 0]
        rob = 1 if t['robber'] else 0
        resource = self.resource_map[t["resource"]]
        number = self.number_map[t["number"]]
        
        return typeflag + resource + number + [rob]

    def encode_vertices(self, v): # 18 elements
        typeflag = [0, 1, 0]
        building = self.building_map[v['building']]
        owner = self.owner_map[v['player']]
        port = self.port_map[v['port']]
        return typeflag + owner + building  + port

    def encode_edge(self, e): # 8 elements
        typeflag = [0, 0, 1]
        owner = self.owner_map[e['player']]
        return typeflag + owner
    
    def encode_board(self, board: dict):
        for tile in board['tiles']: # 19 tiles
            self.tile_features.append(torch.tensor(self.encode_tile(tile), dtype=torch.float32))
        
        for vertex in board['vertices']: # 54 vertices
            self.vertex_features.append(torch.tensor(self.encode_vertices(vertex), dtype=torch.float32))
        
        for edge in board['edges']: # 72 edges
            self.edge_features.append(torch.tensor(self.encode_edge(edge), dtype=torch.float32))
        
        tile_stack = torch.stack(self.tile_features)  # Shape: [19, 21]
        vertex_stack = torch.stack(self.vertex_features) # Shape: [54, 18])
        edge_stack = torch.stack(self.edge_features) # Shape: [72, 21])

        print(f"Tiles - Shape: {tile_stack.shape}, Dtype: {tile_stack.dtype}")
        print(f"Vertices - Shape: {vertex_stack.shape}, Dtype: {vertex_stack.dtype}")
        print(f"Edges - Shape: {edge_stack.shape}, Dtype: {edge_stack.dtype}")

    def build_graph(self):
        pass
        


    def observe(self, state: dict) -> np.ndarray:
        '''We take the json as it is send to the other players in a multiplayer game 
        and convert it to a state representation'''
        json_board = state['board']
        json_players = state['players']
        json_bank = state['bank']
        # rest that is not in the other categories
        json_misc = None
        
        self.player_count = len(json_players.keys())

        for pid in json_players.keys():
            if dict(json_players[pid]['hand']) is not None:
                self.player_id = int(pid)
                break

        self.encode_board(json_board)


test = ObservationEncoder()
with open('player_state.json', 'r') as f:
    state_json = f.read()
    test.handle_state_from_server(state_json)
    





