import torch
from torch_geometric.data import HeteroData

from game.static_board import *

class CatanData(HeteroData):
    def __init__(self):
        super().__init__()

        self.resource_map = {
            'wood': [1, 0, 0, 0, 0],
            'brick': [0, 1, 0, 0, 0],
            'sheep': [0, 0, 1, 0, 0],
            'wheat': [0, 0, 0, 1, 0],
            'ore': [0, 0, 0, 0, 1],
            'Desert': [0, 0, 0, 0, 0],
        }
        self.number_map = {
            0: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0],
            2: [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.2],
            3: [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0.4],
            4: [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0.6],
            5: [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0.8],
            6: [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1.0],
            8: [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1.0],
            9: [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0.8],
            10: [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0.6],
            11: [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0.4],
            12: [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0.2],
        }

        self.building_map = {
            'Settlement': [1, 0],
            'City': [0, 1],
        }

        self.owner_map = {
            'None': [0, 0, 0, 0],
            'Player1': [1, 0, 0, 0], # SELF 
            'Player2': [0, 1, 0, 0],
            'Player3': [0, 0, 1, 0],
            'Player4': [0, 0, 0, 1],
        }

        self.port_map = {
            'None': [0, 0, 0, 0, 0, 0],
            '3:1': [1, 0, 0, 0, 0, 0],
            '2:1 Wood': [0, 1, 0, 0, 0, 0],
            '2:1 Brick': [0, 0, 1, 0, 0, 0],
            '2:1 Sheep': [0, 0, 0, 1, 0, 0],
            '2:1 Wheat': [0, 0, 0, 0, 1, 0],
            '2:1 Ore': [0, 0, 0, 0, 0, 1],
        }

        self._init_static_graph()

        self.player_id = self.get_relative_id() # Find out the player id (1-4), but the RL agent is always Player1 (self) (Needs to be mapped)
        self.player_count = None # Number of players in the game (2-4)



    def _init_static_graph(self):

        def build_edge_index(adjacency_list):
            src, dst = [], []
            for i, neighbors in enumerate(adjacency_list):
                for n in neighbors:
                    src.append(i)
                    dst.append(n)
            return torch.tensor([src, dst], dtype=torch.long)
    
        self['tile', 'T2T', 'tile'].edge_index = build_edge_index(TILE_TILE)
        self['tile', 'T2V', 'vertex'].edge_index = build_edge_index(TILE_VERTEX)
        self['tile', 'T2E', 'edge'].edge_index = build_edge_index(TILE_EDGE)

        self['vertex', 'V2T', 'tile'].edge_index = build_edge_index(VERTEX_TILE)
        self['vertex', 'V2V', 'vertex'].edge_index = build_edge_index(VERTEX_VERTEX)
        self['vertex', 'V2E', 'edge'].edge_index = build_edge_index(VERTEX_EDGE)

        self['edge', 'E2T', 'tile'].edge_index = build_edge_index(EDGE_TILE)
        self['edge', 'E2V', 'vertex'].edge_index = build_edge_index(EDGE_VERTEX)
        self['edge', 'E2E', 'edge'].edge_index = build_edge_index(EDGE_EDGE)

    def update_from_state(self):
        
        tile_features = []
        for t in game_state['board']['tiles']:
            tile_features.append(self._encode_tile(t))
        self['tile'].x = torch.tensor(tile_features, dtype=torch.float)

        vertex_features = []
        for v in game_state['board']['vertices']:
            vertex_features.append(self._encode_vertices(v))
        self['vertex'].x = torch.tensor(vertex_features, dtype=torch.float)

        edge_features = []
        for e in game_state['board']['edges']:
            edge_features.append(self._encode_edge(e))
        self['edge'].x = torch.tensor(edge_features, dtype=torch.float)


    def get_relative_id(self):
        pass

    def _update_public_state(self):
        pass

    def __inc__(self, key, value, *args, **kwargs):
        pass


    # Placeholder for future version TODO
    def _update_log_sequence(self):
        pass


    # --- HELPER FUNCTIONS ---

    def validate(self):
        pass

    def _encode_tile(self, t): # 20 features
        typeflag = [1, 0, 0]
        resource = self.resource_map[t["resource"]]
        number = self.number_map[t["number"]]
        rob = 1 if t['robber'] else 0
        
        
        return typeflag + resource + number + [rob]

    def _encode_vertices(self, v): # 15 features
        typeflag = [0, 1, 0]
        owner = self.owner_map[v['player']]
        building = self.building_map[v['building']]
        port = self.port_map[v['port']]

        return typeflag + owner + building  + port

    def _encode_edge(self, e): # 7 features
        typeflag = [0, 0, 1]
        owner = self.owner_map[e['player']]

        return typeflag + owner
    