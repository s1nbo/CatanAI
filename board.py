import random



class Board:
    def __init__(self) -> None:
        self.players = []
        self.current_turn = 0

        self.tiles = {} # id -> Tile
        self.vertices = {} # id -> Vertex
        self.edges = {} # id -> Edge

        self.create_board()


    def create_board(self) -> None:
       
        '''
        Analysis:
        A board has 19 Hexagon:
        - 4 Wool
        - 4 Grain
        - 4 Lumber
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
        
        Numbers {3, ... ,11} \ 7 exist 2x. {2, 12} exist once. 1 Knight (Desert). 
        Check sum: 8*2 + 2 + 1 = 19

        Maybe Longest Road and Largest Army can be stored as part of the game state.
        Dice should be 2 random six-sided dice. (can be implented as random.randint(1, 6) + random.randint(1, 6))

        In total we have 72 street tiles and 54 settlement tiles. Each of them will be saved in an adjacency list.
        '''
        HEXES = [
            'Wool', 'Wool', 'Wool', 'Wool',
            'Grain', 'Grain', 'Grain', 'Grain',
            'Lumber', 'Lumber', 'Lumber', 'Lumber',
            'Brick', 'Brick', 'Brick',
            'Ore', 'Ore', 'Ore',
            'Desert'
        ]
        PORTS = [
            '3:1', '3:1', '3:1', '3:1',
            '2:1 Wool', '2:1 Grain', '2:1 Lumber', '2:1 Brick', '2:1 Ore'
            ''
        ]
        NUMBERS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]


        # Vertex_id -> tile ids (1-3)
        VERTEX_TILE = {
            0 : [0],
            1 : [0],
            2 : [0, 1],
            3 : [1],
            4 : [1, 2],
            5 : [2],
            6 : [2],
            7 : [3],
            8 : [0, 3],
            9 : [0, 3, 4],
            10 : [0, 1, 4],
            11 : [1, 4, 5],
            12 : [1, 2, 5],
            13 : [2, 5, 6],
            14 : [2, 6],
            15 : [6],
            16 : [7],
            17 : [3, 7],
            18 : [3, 7, 8],
            19 : [3, 4, 8],
            20 : [4, 8, 9],
            21 : [4, 5, 9],
            22 : [5, 9, 10],
            23 : [5, 6, 10],
            24 : [6, 10, 11],
            25 : [6, 11],
            26 : [11],
            27 : [7],
            28 : [7, 12],
            29 : [7, 8, 12],
            30 : [8, 12, 13],
            31 : [8, 9, 13],
            32 : [9, 13, 14],
            33 : [9, 10, 14],
            34 : [10, 14, 15],
            35 : [10, 11, 15],
            36 : [11, 15],
            37 : [11],
            38 : [12],
            39 : [12, 16],
            40 : [12, 13, 16],
            41 : [13, 16, 17],
            42 : [13, 14, 17],
            43 : [14, 17, 18],
            44 : [14, 15, 18],
            45 : [15, 18],
            46 : [15],
            47 : [16],
            48 : [16],
            49 : [16, 17],
            50 : [17],
            51 : [17, 18],
            52 : [18],
            53 : [18]
        }

        # Edge_id -> (vertex1_id, vertex2_id) (2)
        EDGE_VERTEX = {
            0 : (0, 1),
            1 : (1, 2),
            2 : (2, 3),
            3 : (3, 4),
            4 : (4, 5),
            5 : (5, 6),
            6 : (0, 8),
            7 : (2, 10),
            8 : (4, 12),
            9 : (6, 14),
            10 : (7, 8),
            11 : (8, 9),
            12 : (9, 10),
            13 : (10, 11),
            14 : (11, 12),
            15 : (12, 13),
            16 : (13, 14),
            17 : (14, 15),
            18 : (7, 17),
            19 : (9, 19),
            20 : (11, 21),
            21 : (13, 23),
            22 : (15, 25),
            23 : (16, 17),
            24 : (17, 18),
            25 : (18, 19),
            26 : (19, 20),
            27 : (20, 21),
            28 : (21, 22),
            29 : (22, 23),
            30 : (23, 24),
            31 : (24, 25),
            32 : (25, 26),
            33 : (16, 27),
            34 : (18, 29),
            35 : (20, 31),
            36 : (22, 33),
            37 : (24, 35),
            38 : (26, 37),
            39 : (27, 28),
            40 : (28, 29),
            41 : (29, 30),
            42 : (30, 31),
            43 : (31, 32),
            44 : (32, 33),
            45 : (33, 34),
            46 : (34, 35),
            47 : (35, 36),
            48 : (36, 37),
            49 : (28, 38),
            50 : (30, 40),
            51 : (32, 42),
            52 : (34, 44),
            53 : (36, 46),
            54 : (38, 39),
            55 : (39, 40),
            56 : (40, 41),
            57 : (41, 42),
            58 : (42, 43),
            59 : (43, 44),
            60 : (44, 45),
            61 : (45, 46),
            62 : (39, 47),
            63 : (41, 49),
            64 : (43, 51),
            65 : (45, 53),
            66 : (47, 48),
            67 : (48, 49),
            68 : (49, 50),
            69 : (50, 51),
            70 : (51, 52),
            71 : (52, 53)
        }

        # Vertex_id -> Edge_ids (2-3)
        VERTEX_EDGE = {
            0 : [0, 6],
            1 : [0, 1],
            2 : [1, 2, 7],
            3 : [2, 3],
            4 : [3, 4, 8],
            5 : [4, 5],
            6 : [5, 9],
            7 : [10, 18],
            8 : [6, 10, 11],
            9 : [11, 12, 19],
            10 : [7, 12, 13],
            11 : [13, 14, 20],
            12 : [8, 14, 15],
            13 : [15, 16, 21],
            14 : [9, 16, 17],
            15 : [17, 22],
            16 : [23, 33],
            17 : [18, 23, 24],
            18 : [24, 25],
            19 : [19, 25, 26],
            20 : [26, 27],
            21 : [20, 27, 28],
            22 : [28, 29],
            23 : [21, 29, 30],
            24 : [30, 31],
            25 : [22, 31, 32],
            26 : [32, 38],
            27 : [33, 39],
            28 : [39, 40, 49],
            29 : [34, 40, 41],
            30 : [41, 42, 50],
            31 : [35, 42, 43],
            32 : [43, 44, 51],
            33 : [36, 44, 45],
            34 : [45, 46, 52],
            35 : [37, 46, 47],
            36 : [47, 48, 53],
            37 : [38, 48],
            38 : [49, 54],
            39 : [54, 55, 62],
            40 : [50, 55, 56],
            41 : [56, 57, 63],
            42 : [51, 57, 58],
            43 : [58, 59, 64],
            44 : [52, 59, 60],
            45 : [60, 61, 65],
            46 : [53, 61],
            47 : [62, 66],
            48 : [66, 67],
            49 : [63, 67, 68],
            50 : [68, 69],
            51 : [64, 69, 70],
            52 : [70, 71],
            53 : [65, 71]
        }


        random.shuffle(HEXES)
        random.shuffle(PORTS)
        random.shuffle(NUMBERS)


        # Create Tiles
        for tile_id in range(19):
            resource = HEXES[tile_id]
            number = NUMBERS[tile_id] if resource != 'Desert' else None
            tile = Tile(resource, number, tile_id)
            if resource == 'Desert':
                tile.has_robber = True
            self.tiles[tile_id] = tile
        
        # Create Vertices
        for vertex_id in range(54):
            vertex = Vertex(vertex_id)
            self.vertices[vertex_id] = vertex





     


    def roll_dice(self) -> int:
        return random.randint(1, 6) + random.randint(1, 6)

    def place_ports(self) -> None:
        pass

# Board Components
class Tile:
    def __init__(self, resource: str, number: int, id: int) -> None:
        self.resource = resource
        self.number = number
        self.has_robber = False
        self.id = id  # Unique identifier for the tile
        self.adjacent_settlements = []  # List of Settlement objects
        self.adjacent_roads = []  # List of Road objects

class Vertex:
    def __init__(self, id: int) -> None:
        self.id = id # Id from 0 to 53
        self.adjacent_tiles = []  # List of Tile objects
        self.adjacent_roads = []  # List of Road objects
        self.adjacent_vertices = []  # List of Vertex objects
        self.building = None  # None, 'Settlement', or 'City'
        self.owner = None  # Player object who owns the building
        self.port = None  # None or Port type (e.g., '3:1', '2:1 Wool', etc.)
        self.blocked = False  # True if blocked by the distance rule for buildings
        self.can_build_settlement = {} # Player -> Bool (if player can build settlement here , needs road connection and not blocked by distance rule)

class Edge:
    def __init__(self, id: int, vertex1: Vertex, vertex2: Vertex) -> None:
        self.id = id # Id from 0 to 71
        self.vertex1 = vertex1  # One end of the road
        self.vertex2 = vertex2  # Other end of the road
        self.owner = None  # Player object who owns the road
        self.can_build_road = {} # Player -> Bool (if player can build road here

