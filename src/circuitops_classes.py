import os, sys
from generate_LPG import generate_LPG_from_tables


# This file contains CircuitOps class definitions

class PinProperties:
    def __init__(self, df):
        self.df = df

class CellProperties:
    def __init__(self, df):
        self.df = df

class LibcellProperties:
    def __init__(self, df):
        self.df = df

class NetProperties:
    def __init__(self, df):
        self.df = df

class DesignProperties:
    def __init__(self, df):
        self.df = df

class EdgeProperties:
    def __init__(self, edge_df):
        self.df = edge_df

class CircuitGraph:
    def __init__(self, graph):
        self.graph = graph

class PinPinEdge:
    def __init__(self, df):
        self.df = df

class CellPinEdge:
    def __init__(self, df):
        self.df = df

class NetPinEdge:
    def __init__(self, df):
        self.df = df

class CellCellEdge:
    def __init__(self, df):
        self.df = df

class CellNetEdge:
    def __init__(self, df):
        self.df = df

class CircuitData:
    """
    Master class which holds all the dataframes and graph

    :ivar data_root: Required attribute. Need the IR tables directory path.
    :vartype data_root: str
    :ivar use_python_api: Optional. If true generates the IR tables using OpenRoad.
    :vartype use_python_api: bool
    """
    def __init__(self, data_root, use_python_api=False):
        self.data_root = data_root
        self.use_python_api = use_python_api
        self.master_dataframes = {}
        self.graph = None

        self.init_dataframes(data_root, use_python_api)
         
    def init_dataframes(self, data_root, use_python_api):
        g, self.master_dataframes = generate_LPG_from_tables(data_root, use_python_api)
        self.graph = CircuitGraph(g)
        self.pin_props = PinProperties(self.master_dataframes['pin_df'])
        self.cell_props = CellProperties(self.master_dataframes['cell_df'])
        self.design_props = DesignProperties(self.master_dataframes['design_df'])
        self.libcell_props = LibcellProperties(self.master_dataframes['fo4_df'])
        self.net_props = NetProperties(self.master_dataframes['net_df'])

        self.pin_pin_edge = PinPinEdge(self.master_dataframes['pin_pin_df'])
        self.cell_pin_edge = CellPinEdge(self.master_dataframes['cell_pin_df'])
        self.net_pin_edge = NetPinEdge(self.master_dataframes['net_pin_df'])
        self.cell_cell_edge = CellCellEdge(self.master_dataframes['cell_cell_df'])
        self.cell_net_edge = CellNetEdge(self.master_dataframes['cell_net_df'])


