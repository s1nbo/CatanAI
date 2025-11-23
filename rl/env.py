import functools
from pettingzoo import AECEnv
from pettingzoo.utils import agent_selector
from rl.observation import CatanGraphDat

# This Communicates with the Catan Game Server and provides an Environment for RL agents

class CatanEnv(AECEnv):
    def __init__(self):
        super().__init__()

    def reset(self):
        pass

    def observe(self, agent):
        pass

    def step(self, action):
        pass

    def observation_space(self, agent):
        pass

    def action_space(self, agent):
        pass