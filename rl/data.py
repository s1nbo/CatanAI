import torch
from torch_geometric.data import HeteroData

class CatanData(HeteroData):
    def __init__(self):
        super.__init__()


    def _init_static_graph(self):
        pass


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