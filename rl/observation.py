import torch
from torch_geometric.data import HeteroData
import copy
from game.static_board import *

# Takes in the game state dict and converts it to a graph data structure suitable for GNNs

# TODO: Normalize features, add more features if necessary (log) (Transformer), Add the player state as a node in the graph
# TODO: Add validate method
# TODO: Action mask method

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
            None: [0, 0],
            'Settlement': [1, 0],
            'City': [0, 1],
        }

        self.owner_map = {
            None: [0, 0, 0, 0],
            1: [1, 0, 0, 0], # SELF 
            2: [0, 1, 0, 0],
            3: [0, 0, 1, 0],
            4: [0, 0, 0, 1],
        }

        self.port_map = {
            None: [0, 0, 0, 0, 0, 0],
            '3:1': [1, 0, 0, 0, 0, 0],
            '2:1 Wood': [0, 1, 0, 0, 0, 0],
            '2:1 Brick': [0, 0, 1, 0, 0, 0],
            '2:1 Sheep': [0, 0, 0, 1, 0, 0],
            '2:1 Wheat': [0, 0, 0, 0, 1, 0],
            '2:1 Ore': [0, 0, 0, 0, 0, 1],
        }

        self._init_static_graph()

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

    def update_data(self, game_state: dict, current_pid: int, total_players: int):
        
        game_state = copy.deepcopy(game_state) # TODO instead of deep copy we only create a mapping and call that everywhere
        # so we don't modify the original game_state, can be changed for efficiency later
        
        # Convert to relative ids
        game_state = self._convert_to_relative_ids(game_state, current_pid, total_players)

        # _update player states
        self._update_player_state(game_state, total_players)
        
        # update board state
        self._update_board_state(game_state)

        # update misc state
        self._update_misc_state(game_state)

        # update action mask
        self.action_mask(game_state)


    def _update_player_state(self, game_state: dict, total_players: int):
        
        player_features = []
        features = []
        
        # self
        features.append(game_state['players'][1]['resources']['wood'])
        features.append(game_state['players'][1]['resources']['brick'])
        features.append(game_state['players'][1]['resources']['sheep'])
        features.append(game_state['players'][1]['resources']['wheat'])
        features.append(game_state['players'][1]['resources']['ore'])
        features.append(game_state['players'][1]['development_cards']['knight'])
        features.append(game_state['players'][1]['development_cards']['victory_point'])
        features.append(game_state['players'][1]['development_cards']['road_building'])
        features.append(game_state['players'][1]['development_cards']['year_of_plenty'])
        features.append(game_state['players'][1]['development_cards']['monopoly'])
        # public info
        for player in [1, 2, 3, 4]:
            features.append(game_state['players'][player]['played_knights'])
            features.append(game_state['players'][player]['longest_road_length'])
            features.append(game_state['players'][player]['victory_points'])
            features.append(game_state['players'][player]['settlements'])
            features.append(game_state['players'][player]['cities'])
            features.append(game_state['players'][player]['roads'])
            features.append(1.0 if game_state['players'][player]['longest_road'] else 0.0)
            features.append(1.0 if game_state['players'][player]['largest_army'] else 0.0)
            features.append(game_state['players'][player]['played_cards_this_turn'])
            features.append(game_state['players'][player]['dice_rolled'])
            features.append(game_state['players'][player]['current_turn'])
            features.append(game_state['players'][player]['total_hand'])
            features.append(game_state['players'][player]['total_development_cards'])
            features.append(game_state['players'][player]['victory_points_without_vp_cards'])
            for port in ['3:1', '2:1 Wood', '2:1 Brick', '2:1 Sheep', '2:1 Wheat', '2:1 Ore']:
                if port in game_state['players'][player]['ports']:
                    features.append(1.0)
                else:
                    features.append(0.0)
            
            player_features.append(features)
            features = [0]*10 # padding for opponent players
        
        self['player'].x = torch.tensor(player_features, dtype=torch.float)



    def _update_board_state(self, game_state: dict):
        # we only need to update tile: robber, vertex: owner, building, edge: owner
        
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

        

    def _update_misc_state(self, game_state):
        features = []
        # bank resources
        features.append(game_state['bank']['wood'] / 19.0)
        features.append(game_state['bank']['brick'] / 19.0)
        features.append(game_state['bank']['sheep'] / 19.0)
        features.append(game_state['bank']['wheat'] / 19.0)
        features.append(game_state['bank']['ore'] / 19.0)

        features.append(game_state['development_cards_remaining'] / 25.0)
        features.append(game_state['current_turn'])
        features.append(game_state['current_roll'] if game_state['current_roll'] is not None else 0)
        features.append(game_state['initial_placement_order']) # is a int, from which we can calculate turn order
        features.append(1.0 if game_state['forced_action'] else 0.0)
        features.append(1.0 if game_state['must_discard'] > 0 else 0.0)

        # safe the features in the global observation tensor 
        self['misc'].x = torch.tensor(features, dtype=torch.float).unsqueeze(0)
    

    def action_mask(self, mask: dict): # TODO
        pass # we will get a action mask from the environment directly and then convert into tensor here

    # Placeholder for future version TODO
    def _update_log_sequence(self):
        pass


    # --- HELPER FUNCTIONS ---

    def validate(self): # TODO
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
    
    def _convert_to_relative_ids(self, game_state: dict, current_pid: int, total_players: int):
        '''
        Convert all player ids in game_state to relative ids based on current_pid
        4 players assumed
        1: -> 1,2,3,4 (stays same)
        2: -> 4,1,2,3
        3: -> 3,4,1,2
        4: -> 2,3,4,1
        3 players
        1: -> 1,2,3
        2: -> 3,1,2
        3: -> 2,3,1
        2 players
        1: -> 1,2
        2: -> 2,1
        
        Where does it appear:
        - board vertices (owner)
        - board edges (owner)
        - player states (player id)
        - current turn
        - inital_placement order
        '''
        mapping = {}
        for pid in range(1, total_players + 1):
            rel_id = (pid - current_pid) % total_players + 1

            mapping[pid] = rel_id
        
        # Update board vertices
        for v in game_state['board']['vertices']:
            p = v['player']
            if p in mapping:
                v['player'] = mapping[int(p)]
        # Update board edges
        for e in game_state['board']['edges']:
            p = e['player']
            if p in mapping:    
                e['player'] = mapping[int(p)]
        
        # Current turn and initial placement order
        game_state['current_turn'] = mapping[int(game_state['current_turn'])]
        game_state['initial_placement_order'] = mapping[int(game_state['initial_placement_order'])]

        # Update player states it is a hashmap with each player's id as key
        game_state['players'] = {
            mapping[int(pid)]: pdata 
            for pid, pdata in 
            game_state['players'].items()
            if pid in mapping
        }
        return game_state