import torch
from torch_geometric.data import HeteroData

from game import board

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
            'None': [1, 0, 0],
            'Settlement': [0, 1, 0],
            'City': [0, 0, 1],
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

        self.player_id = None # Find out the player id (1-4), but the RL agent is always Player1 (self) (Needs to be mapped)
        self.player_count = None # Number of players in the game (2-4)
   
        self.data = HeteroData()

        self._init_static_graph(board)




    def _init_static_graph(self, board: dict):
        
        # Tiles
        tiles_tiles = []
        tiles_vertices = []
        tiles_edges = []

        for t in board['tiles']:
            tile = t['id']
            for t in t['tiles']:
                tiles_tiles.append((tile, t))
            for v in t['vertices']:
                tiles_vertices.append((tile, v))
            for e in t['edges']:
                tiles_edges.append((tile, e))
        
        self.data['tile', 'T2T', 'tile'].edge_index = torch.tensor(tiles_tiles, dtype=torch.long).t().contiguous()
        self.data['tile', 'T2V', 'vertex'].edge_index = torch.tensor(tiles_vertices, dtype=torch.long).t().contiguous()
        self.data['tile', 'T2E', 'edge'].edge_index = torch.tensor(tiles_edges, dtype=torch.long).t().contiguous()

        # Vertices
        vertices_tiles = []
        vertices_vertices = []
        vertices_edges = []

        for v in board['vertices']:
            vertex = v['id']
            for t in v['tiles']:
                vertices_tiles.append((vertex, t))
            for vv in v['vertices']:
                vertices_vertices.append((vertex, vv))
            for e in v['edges']:
                vertices_edges.append((vertex, e))
        
        self.data['vertex', 'V2T', 'tile'].edge_index = torch.tensor(vertices_tiles, dtype=torch.long).t().contiguous()
        self.data['vertex', 'V2V', 'vertex'].edge_index = torch.tensor(vertices_vertices, dtype=torch.long).t().contiguous()
        self.data['vertex', 'V2E', 'edge'].edge_index = torch.tensor(vertices_edges, dtype=torch.long).t().contiguous()

        # Edges
        edges_tiles = []
        edges_vertices = []
        edges_edges = []

        for e in board['edges']:
            edge = e['id']
            for t in e['tiles']:
                edges_tiles.append((edge, t))
            for v in e['vertices']:
                edges_vertices.append((edge, v))
            for ee in e['edges']:
                edges_edges.append((edge, ee))

        self.data['edge', 'E2T', 'tile'].edge_index = torch.tensor(edges_tiles, dtype=torch.long).t().contiguous()
        self.data['edge', 'E2V', 'vertex'].edge_index = torch.tensor(edges_vertices, dtype=torch.long).t().contiguous()
        self.data['edge', 'E2E', 'edge'].edge_index = torch.tensor(edges_edges, dtype=torch.long).t().contiguous()

        


    def update_from_state(self):
        pass


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

    def _encode_tile(self, t): # 21 elements
        typeflag = [1, 0, 0]
        rob = 1 if t['robber'] else 0
        resource = self.resource_map[t["resource"]]
        number = self.number_map[t["number"]]
        
        return typeflag + resource + number + [rob]

    def _encode_vertices(self, v): # 18 elements
        typeflag = [0, 1, 0]
        building = self.building_map[v['building']]
        owner = self.owner_map[v['player']]
        port = self.port_map[v['port']]
        return typeflag + owner + building  + port

    def _encode_edge(self, e): # 8 elements
        typeflag = [0, 0, 1]
        owner = self.owner_map[e['player']]
        return typeflag + owner
    
    def _encode_board(self, board: dict):
        tile_features = []
        vertex_features = []
        edge_features = []