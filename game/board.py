import random
from game import static_board
'''
Analysis:
A board has 19 Hexagon: (TILES)
- 4 Sheep
- 4 Wheat
- 4 Wood
- 3 Brick
- 3 Ore
- 1 Desert 
There are 9 Ports:
- 4x: 3:1
- 5x: 2:1 (One for each resource type)
- For the field it is always one water tile one port tile in the imaginary outer row
- ports always point to the longest chain of land tiles.
- The chain length follows the pattern (4-4-5)*3 

The Bank (part of the board) has every resource exactly 19 times 
The Bank has 25 Development Cards.
- 14 Knights
- 2 Monopolies
- 2 Year of Plenty
- 2 Road Building
- 5 Victory Points

Numbers {3, ... ,11} without 7 exist 2x. {2, 12} exist once. 1 Knight (Desert). 
Check sum: 8*2 + 2 + 1 = 19

Maybe Longest Road and Largest Army can be stored as part of the game state.
Dice should be 2 random six-sided dice. (can be implented as random.randint(1, 6) + random.randint(1, 6))

In total we have 72 street tiles and 54 settlement tiles. Each of them will be saved in an adjacency list.
'''
class Board:
    def __init__(self) -> None:
        # The index is also the id of the object, each element is a reference to the object
        self.tiles = [None]*19 # id -> Tile
        self.vertices = None # id -> Vertex
        self.edges = None # id -> Edge
        self.port_config = random.randint(0, 1)
        self.robber_tile = 0 # Tile id where the robber is located, starts on the desert tile
        self.create_board()
       
    def create_board(self) -> None:
        # Setup Board

        HEXES = [
            'sheep', 'sheep', 'sheep', 'sheep',
            'wheat', 'wheat', 'wheat', 'wheat',
            'wood', 'wood', 'wood', 'wood',
            'brick', 'brick', 'brick',
            'ore', 'ore', 'ore',
        ]
        PORTS = [
            '3:1', '3:1', '3:1', '3:1',
            '2:1 Sheep', '2:1 Wheat', '2:1 Wood', '2:1 Brick', '2:1 Ore'
        ]

        NUMBERS = [0, 2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
        
        random.shuffle(HEXES)
        random.shuffle(PORTS)

        # Check that 6 and 8 are not adjacent
        def six_eight_placement() -> bool:
            idx_six_eight = {i for i, v in enumerate(NUMBERS) if v in (6,8)}

            return not any(
                (neighbor in idx_six_eight)
                for idx in idx_six_eight
                for neighbor in static_board.TILE_TILE[idx]
            ) # for every idx in idx_six_eight check if any neighbor is also in idx_six_eight

          
        valid_tiles_numbers = False
        while not valid_tiles_numbers:
            random.shuffle(NUMBERS)
            valid_tiles_numbers = six_eight_placement()
          

        for i in range(19):
            number = NUMBERS[i]


            if number == 0:
                resource = 'Desert'
                self.robber_tile = i
            else:
                resource = HEXES.pop()
                
            
            self.tiles[i] = static_board.Tile(resource, number, i)

        
        self.vertices = [static_board.Vertex(i) for i in range(54)]
        self.edges = [static_board.Edge(i) for i in range(72)]


        # Store connections

        for tile in self.tiles:
            tile.tiles = static_board.TILE_TILE[tile.id]
            tile.vertices = static_board.TILE_VERTEX[tile.id]
            tile.edges = static_board.TILE_EDGE[tile.id]
        
        for vertex in self.vertices:
            vertex.tiles = static_board.VERTEX_TILE[vertex.id]
            vertex.edges = static_board.VERTEX_EDGE[vertex.id]
            vertex.vertices = static_board.VERTEX_VERTEX[vertex.id]
        
        for edge in self.edges:
            edge.tiles = static_board.EDGE_TILE[edge.id]
            edge.vertices = static_board.EDGE_VERTEX[edge.id]
            edge.edges = static_board.EDGE_EDGE[edge.id]

        # Place Ports
        # There are only two possible configurations for the ports
        if self.port_config:
            port_positions = [[0, 1], [3, 4], [14,  15], [26, 37], [45, 46], [50, 51], [47, 48], [28, 38], [7, 17]]
        else:
            port_positions = [[5, 6], [15, 25], [36, 46], [52, 53], [49, 50], [38, 39], [16, 27], [7, 8], [2, 3]]
        
        for i in range(9):
                port_pos = port_positions[i]
                for vertex_id in port_pos:
                    self.vertices[vertex_id].port = PORTS[i]

    
    # Just for Network Transmission
    def board_to_json(self) -> dict:
        return {
            "tiles": [
                {
                    "id": tile.id,
                    "resource": tile.resource,
                    "number": tile.number,
                    "robber": tile.robber,
                    "tiles": tile.tiles,
                    "vertices": tile.vertices,
                    "edges": tile.edges
                }
                for tile in self.tiles
            ],
            "vertices": [
                {
                    "id": vertex.id,
                    "building": vertex.building,
                    "player": vertex.owner,
                    "port": vertex.port,
                    "tiles": vertex.tiles,
                    "vertices": vertex.vertices,
                    "edges": vertex.edges
                }
                for vertex in self.vertices
            ],
            "edges": [
                {
                    "id": edge.id,
                    "player": edge.owner,
                    "tiles": edge.tiles,
                    "vertices": edge.vertices,
                    "edges": edge.edges
                }
                for edge in self.edges
            ]
        }

    def reset_board(self) -> None:
        self.tiles = [None]*19
        self.create_board()

    def print_board(self) -> None:
        for tile in self.tiles:
            print(f"Tile {tile.id}: {tile.resource} ({tile.number})")
            print(f"  Adjacent Tiles: {tile.tiles}")
            print(f"  Vertices: {tile.vertices}")
            print(f"  Edges: {tile.edges}")
            print()
        
        for vertex in self.vertices:
            print(f"Vertex {vertex.id}:")
            print(f"  Adjacent Tiles: {vertex.tiles}")
            print(f"  Adjacent Vertices: {vertex.vertices}")
            print(f"  Adjacent Edges: {vertex.edges}")
            if vertex.port:
                print(f"  Port: {vertex.port}")
            print()
        
        for edge in self.edges:
            print(f"Edge {edge.id}:")
            print(f"  Adjacent Tiles: {edge.tiles}")
            print(f"  Adjacent Vertices: {edge.vertices}")
            print(f"  Adjacent Edges: {edge.edges}")
            print()
    