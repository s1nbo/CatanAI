import random
'''
Analysis:
A board has 19 Hexagon: (TILES)
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
class Board:
    def __init__(self) -> None:
        self.tiles = {} # id -> Tile
        self.vertices = {} # id -> Vertex
        self.edges = {} # id -> Edge
        self.create_board()

    def create_board(self) -> None:
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
        ]
        WATER = ['Water' for _ in range(9)]
        NUMBERS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
        

        random.shuffle(HEXES)
        random.shuffle(PORTS)
        random.shuffle(NUMBERS)

        for i in range(9):
            PORTS.insert(i*2, WATER[i])

        # Create Objects
        

        # Store connections

  
        


    def place_ports(self) -> None:
        pass




