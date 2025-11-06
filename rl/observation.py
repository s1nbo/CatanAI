import numpy as np
import orjson as json

import torch
from torch_geometric.data import Data, HeteroData
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import HeteroConv, GATv2Conv, global_mean_pool
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
        
        self.tile = torch.stack(self.tile_features)  # Shape: [19, 21]
        self.vertex = torch.stack(self.vertex_features) # Shape: [54, 18])
        self.edge = torch.stack(self.edge_features) # Shape: [72, 21])


    def to_heterodata(self):
        """Return a torch_geometric HeteroData graph from the current buffers."""
        return self.hetero_data(
            self.tiles_tiles, self.tiles_vertices, self.tiles_edges,
            self.vertices_vertices, self.vertices_edges, self.edges_edges
        )
    
    def hetero_data(self):
        data = HeteroData()
        data['tile'].x   = self.tile            # [19, F_t]
        data['vertex'].x = self.vertex          # [54, F_v]
        data['edge'].x   = self.edge            # [72, F_r]

        def ei(pairs):                       # pairs: List[Tuple[int,int]]
            return torch.tensor(pairs, dtype=torch.long).t().contiguous()

        # add both directions for undirected behavior
        data['tile','adjacent','tile'].edge_index     = ei(self.tiles_tiles + [(j,i) for i,j in self.tiles_tiles])
        data['tile','touches','vertex'].edge_index    = ei(self.tiles_vertices)
        data['vertex','touched_by','tile'].edge_index = ei([(v,t) for t,v in self.tiles_vertices])

        data['tile','borders','edge'].edge_index      = ei(self.tiles_edges)
        data['edge','bordered_by','tile'].edge_index  = ei([(r,t) for t,r in self.tiles_edges])

        data['vertex','incident','edge'].edge_index   = ei(self.vertices_edges)
        data['edge','incident_to','vertex'].edge_index= ei([(r,v) for v,r in self.vertices_edges])

        data['vertex','adjacent','vertex'].edge_index = ei(self.vertices_vertices + [(j,i) for i,j in self.vertices_vertices])
        data['edge','adjacent','edge'].edge_index     = ei(self.edges_edges + [(j,i) for i,j in self.edges_edges])

        return data


    def build_graph(self, board: dict):
        tile, vertex, edge = self.encode_board(board)

        # tiles
        for t in board['tiles']:
            t_id = t['id']
            for v_id in (t.get('tiles') or t.get('neighbors') or t.get('neighbours') or []):
                self.tiles_tiles.append((t_id, v_id))
            for v_id in t.get('vertices', []):
                self.tiles_vertices.append((t_id, v_id))
            for n_id in t['edges']:
                self.tiles_edges.append((t_id, n_id))

        # vertices
        for v in board['vertices']:
            v_id = v['id']
            for t_id in v['tiles']:
                self.vertices_tiles.append((v_id, t_id))
            for e_id in v['vertices']:
                self.vertices_vertices.append((v_id, e_id))
            for n_id in v['edges']:
                self.vertices_edges.append((v_id, n_id))
        
        # edges
        for e in board['edges']:
            e_id = e['id']
            for t_id in e['tiles']:
                self.edges_tiles.append((e_id, t_id))
            for v_id in e['vertices']:
                self.edges_vertices.append((e_id, v_id))
            for n_id in e['edges']:
                self.edges_edges.append((e_id, n_id))
        
        edge_index_tiles = torch.tensor(self.tiles_tiles + self.vertices_tiles + self.edges_tiles, dtype=torch.long).t().contiguous()
        edge_index_vertices = torch.tensor(self.tiles_vertices + self.vertices_vertices + self.edges_vertices, dtype=torch.long).t().contiguous()
        edge_index_edges = torch.tensor(self.tiles_edges + self.vertices_edges + self.edges_edges, dtype=torch.long).t().contiguous()
        
        print(f"Edge Index Tiles - Shape: {edge_index_tiles.shape}, Dtype: {edge_index_tiles.dtype}")
        print(f"Edge Index Vertices - Shape: {edge_index_vertices.shape}, Dtype: {edge_index_vertices.dtype}")
        print(f"Edge Index Edges - Shape: {edge_index_edges.shape}, Dtype: {edge_index_edges.dtype}")




    def observe(self, state: dict) -> np.ndarray:
        '''We take the json as it is send to the other players in a multiplayer game 
        and convert it to a state representation'''
        json_board = state['board']
        json_players = state['players']
        # rest that is not in the other categories
        json_misc = None
        
        self.player_count = len(json_players.keys())

        for pid in json_players.keys():
            if dict(json_players[pid]['hand']) is not None:
                self.player_id = int(pid)
                break

        # board encoding
        self.build_graph(json_board)

        # player encoding

        # rest encoding

   

class CatanGNN(nn.Module):
    def __init__(self, in_t, in_v, in_r, hid=128, out=128, heads=2):
        super().__init__()
        self.in_proj = nn.ModuleDict({
            'tile':   nn.Linear(in_t, hid),
            'vertex': nn.Linear(in_v, hid),
            'edge':   nn.Linear(in_r, hid),
        })

        def layer():
            return HeteroConv({
                ('tile','adjacent','tile'):    GATv2Conv(hid, hid//heads, heads=heads, add_self_loops=False),
                ('tile','touches','vertex'):   GATv2Conv(hid, hid//heads, heads=heads, add_self_loops=False),
                ('vertex','touched_by','tile'):GATv2Conv(hid, hid//heads, heads=heads, add_self_loops=False),
                ('tile','borders','edge'):     GATv2Conv(hid, hid//heads, heads=heads, add_self_loops=False),
                ('edge','bordered_by','tile'): GATv2Conv(hid, hid//heads, heads=heads, add_self_loops=False),
                ('vertex','incident','edge'):  GATv2Conv(hid, hid//heads, heads=heads, add_self_loops=False),
                ('edge','incident_to','vertex'):GATv2Conv(hid, hid//heads, heads=heads, add_self_loops=False),
                ('vertex','adjacent','vertex'):GATv2Conv(hid, hid//heads, heads=heads, add_self_loops=False),
                ('edge','adjacent','edge'):    GATv2Conv(hid, hid//heads, heads=heads, add_self_loops=False),
            }, aggr='sum')


        self.gnn1 = layer()
        self.gnn2 = layer()

    

if __name__ == '__main__':
    test = ObservationEncoder()
    with open('player_state.json', 'r') as f:
        state_json = f.read()
    test.handle_state_from_server(state_json)
    print('State handled successfully.')

    hetero_data = test.to_heterodata()
    print('HeteroData constructed successfully.')

    model = CatanGNN(in_t=21, in_v=18, in_r=8)
    logits, x, g = model(hetero_data)
    print('Model forward pass successful.')