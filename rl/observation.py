import numpy as np
import orjson as json

import torch
from torch_geometric.data import Data, HeteroData
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import HeteroConv, GATv2Conv, global_mean_pool
class ObservationEncoder:
    def __init__(self):

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

        self.data = HeteroData()

        self.state = None
        self.player_id = None # 1-4 
        self.player_count = None # 1-4

        self._topology_built = False



    def _build_static_topology(self, board: dict):
        """
        Builds the static graph topology (all the edge_index tensors).
        This should only be run ONCE.
        """

        def _symmetrize(ei: torch.Tensor) -> torch.Tensor:
            return torch.cat([ei, ei.flip(0)], dim=1).contiguous() if ei.numel() else ei

        # --- Tile Relationships ---
        tiles_tiles = []
        tiles_vertices = []
        tiles_edges = []
        for t in board['tiles']:
            t_id = t['id']
            for v_id in t['tiles']:
                tiles_tiles.append((t_id, v_id))
            for v_id in t['vertices']:
                tiles_vertices.append((t_id, v_id))
            for n_id in t['edges']:
                tiles_edges.append((t_id, n_id))
        
        # (tile -> tile)
        self.data['tile', 'T2T', 'tile'].edge_index = torch.tensor(tiles_tiles, dtype=torch.long).t().contiguous()
        self.data['tile','T2T','tile'].edge_index   = _symmetrize(self.data['tile','T2T','tile'].edge_index)
        # (tile -> vertex)
        self.data['tile', 'T2V', 'vertex'].edge_index = torch.tensor(tiles_vertices, dtype=torch.long).t().contiguous()
        # (tile -> edge)
        self.data['tile', 'T2E', 'edge'].edge_index = torch.tensor(tiles_edges, dtype=torch.long).t().contiguous()

        # --- Vertex Relationships ---
        vertices_tiles = []
        vertices_vertices = []
        vertices_edges = []
        for v in board['vertices']:
            v_id = v['id']
            for t_id in v['tiles']:
                vertices_tiles.append((v_id, t_id))
            for e_id in v['vertices']:
                vertices_vertices.append((v_id, e_id))
            for n_id in v['edges']:
                vertices_edges.append((v_id, n_id))

        # (vertex -> tile)
        self.data['vertex', 'V2T', 'tile'].edge_index = torch.tensor(vertices_tiles, dtype=torch.long).t().contiguous()
        # (vertex -> vertex)
        self.data['vertex', 'V2V', 'vertex'].edge_index = torch.tensor(vertices_vertices, dtype=torch.long).t().contiguous()
        self.data['vertex','V2V','vertex'].edge_index = _symmetrize(self.data['vertex','V2V','vertex'].edge_index)
        # (vertex -> edge)
        self.data['vertex', 'V2E', 'edge'].edge_index = torch.tensor(vertices_edges, dtype=torch.long).t().contiguous()

        # --- Edge Relationships ---
        edges_tiles = []
        edges_vertices = []
        edges_edges = []
        for e in board['edges']:
            e_id = e['id']
            for t_id in e['tiles']:
                edges_tiles.append((e_id, t_id))
            for v_id in e['vertices']:
                edges_vertices.append((e_id, v_id))
            for n_id in e['edges']:
                edges_edges.append((e_id, n_id))

        # (edge -> tile)
        self.data['edge', 'E2T', 'tile'].edge_index = torch.tensor(edges_tiles, dtype=torch.long).t().contiguous()
        # (edge -> vertex)
        self.data['edge', 'E2V', 'vertex'].edge_index = torch.tensor(edges_vertices, dtype=torch.long).t().contiguous()
        # (edge -> edge)
        self.data['edge', 'E2E', 'edge'].edge_index = torch.tensor(edges_edges, dtype=torch.long).t().contiguous()
        self.data['edge','E2E','edge'].edge_index   = _symmetrize(self.data['edge','E2E','edge'].edge_index)


        self._topology_built = True


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


        for tile in board['tiles']: # 19 tiles
            tile_features.append(torch.tensor(self._encode_tile(tile), dtype=torch.float32))
        
        for vertex in board['vertices']: # 54 vertices
            vertex_features.append(torch.tensor(self._encode_vertices(vertex), dtype=torch.float32))
        
        for edge in board['edges']: # 72 edges
            edge_features.append(torch.tensor(self._encode_edge(edge), dtype=torch.float32))
        
        self.data['tile'].x   = torch.stack(tile_features)  # Shape: [19, 21]
        self.data['vertex'].x = torch.stack(vertex_features) # Shape: [54, 18])
        self.data['edge'].x   = torch.stack(edge_features) # Shape: [72, 21])

        self.data['tile'].num_nodes   = self.data['tile'].x.size(0)
        self.data['vertex'].num_nodes = self.data['vertex'].x.size(0)
        self.data['edge'].num_nodes   = self.data['edge'].x.size(0)


    def observe(self, state_json: str) -> HeteroData:
        '''We take the json as it is send to the other players in a multiplayer game 
        and convert it to a state representation'''

        state = json.loads(state_json)

        json_board = state['board']
        json_players = state['players']
        # rest that is not in the other categories
        json_misc = None

        #static topology build
        if not self._topology_built:
            self._build_static_topology(json_board)

        
        self.player_count = len(json_players.keys())

        for pid in json_players.keys():
            if dict(json_players[pid]['hand']) is not None:
                self.player_id = int(pid)
                break

        # board encoding
        self._encode_board(json_board)

        # player encoding

        # rest encoding

        return self.data



class CatanGNN(nn.Module):
    def __init__(self, hidden_channels=128, out_channels=256):
        super().__init__()

        self.id_emb = nn.ModuleDict({
        'tile': nn.Embedding(19, 16),
        'vertex': nn.Embedding(54, 16),
        'edge': nn.Embedding(72, 16),
        })
        


        def make_layer():
            return HeteroConv({
                ('tile', 'T2T', 'tile'): GATv2Conv((-1, -1), hidden_channels, add_self_loops=True),
                ('tile', 'T2V', 'vertex'): GATv2Conv((-1, -1), hidden_channels, add_self_loops=False),
                ('tile', 'T2E', 'edge'): GATv2Conv((-1, -1), hidden_channels, add_self_loops=False),

                ('vertex', 'V2T', 'tile'): GATv2Conv((-1, -1), hidden_channels, add_self_loops=False),
                ('vertex', 'V2V', 'vertex'): GATv2Conv((-1, -1), hidden_channels, add_self_loops=True),
                ('vertex', 'V2E', 'edge'): GATv2Conv((-1, -1), hidden_channels, add_self_loops=False),

                ('edge', 'E2T', 'tile'): GATv2Conv((-1, -1), hidden_channels, add_self_loops=False),
                ('edge', 'E2V', 'vertex'): GATv2Conv((-1, -1), hidden_channels, add_self_loops=False),
                ('edge', 'E2E', 'edge'): GATv2Conv((-1, -1), hidden_channels, add_self_loops=True),
            
            }, aggr='sum') # 'sum', 'mean', 'max'

        self.conv1 = make_layer()
        self.conv2 = make_layer()


        # project per-type to a common size before pooling
        self.proj = nn.ModuleDict({
            'tile':   nn.Linear(hidden_channels, out_channels),
            'vertex': nn.Linear(hidden_channels, out_channels),
            'edge':   nn.Linear(hidden_channels, out_channels),
        })

        # graph-level readout (board embedding)
        self.readout = nn.Sequential(
            nn.Linear(out_channels *3, out_channels),
            nn.ReLU(),
            nn.Linear(out_channels, out_channels)
        )

    def forward(self, data: HeteroData):
        x = {k: v.x for k, v in data.node_items()}

        ids = {
            'tile':   torch.arange(data['tile'].num_nodes,   device=data['tile'].x.device),
            'vertex': torch.arange(data['vertex'].num_nodes, device=data['vertex'].x.device),
            'edge':   torch.arange(data['edge'].num_nodes,   device=data['edge'].x.device),
        }
        x = {
            'tile':   torch.cat([data['tile'].x,   self.id_emb['tile'](ids['tile'])], dim=-1),
            'vertex': torch.cat([data['vertex'].x, self.id_emb['vertex'](ids['vertex'])], dim=-1),
            'edge':   torch.cat([data['edge'].x,   self.id_emb['edge'](ids['edge'])], dim=-1),
        }
        

        x = self.conv1(x, data.edge_index_dict)
        x = {k: F.elu(v) for k,v in x.items()}
        x = self.conv2(x, data.edge_index_dict)
        x = {k: F.elu(v) for k,v in x.items()}

        pooled = []
        for ntype in ['tile','vertex','edge']:
            h = self.proj[ntype](x[ntype])
            batch = torch.zeros(h.size(0), dtype=torch.long, device=h.device)
            pooled.append(global_mean_pool(h, batch))
        board_emb = torch.cat(pooled, dim=-1)
        return self.readout(board_emb)  # [1, out_channels]



    

if __name__ == '__main__':
    test = ObservationEncoder()
    with open('player_state.json', 'r') as f:
        state_json = f.read()
    data = test.observe(state_json)

    catan = CatanGNN(hidden_channels=64, out_channels=128)
    out = catan.forward(data)
    print(out)

    