# SPDX-FileCopyrightText: Copyright (c) 2022 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import pandas as pd
import numpy as np
from graph_tool.all import *
from numpy.random import *
import time
import graph_tool as gt
import sys
from helper import (
    read_tables_OpenROAD,
    rename_cells,
    rename_nets,
    generate_edge_df_OpenROAD,
)

def generate_LPG_from_tables(data_root):
    pin_df, cell_df, net_df, pin_edge_df, cell_edge_df, net_edge_df, net_cell_edge_df, fo4_df = read_tables_OpenROAD(data_root)

    #### rename dfs
    pin_df = pin_df.rename(columns={"pin_name":"name", "cell_name":"cellname", "net_name":"netname", \
                                   "pin_tran":"tran", "pin_slack":"slack", "pin_arr":"arr", "input_pin_cap":"cap"})
    cell_df = cell_df.rename(columns={"cell_name":"name", "libcell_name":"ref"})
    net_df = net_df.rename(columns={"net_name":"name"})

    ### add is_macro, is_seq to pin_df, change pin_dir to bool
    cell_type_df = cell_df.loc[:,["name", "is_macro", "is_seq"]]
    cell_type_df = cell_type_df.rename(columns={"name":"cellname"})
    pin_df = pin_df.merge(cell_type_df, on="cellname", how="left")
    pin_df["is_macro"] = pin_df["is_macro"].fillna(False)
    pin_df["is_seq"] = pin_df["is_seq"].fillna(False)
    pin_df["dir"] = (pin_df["dir"] == 0)

    fo4_df["libcell_id"] = range(fo4_df.shape[0])

    ### get cell center loc
    cell_df["x"] = 0.5*(cell_df.x0 + cell_df.x1)
    cell_df["y"] = 0.5*(cell_df.y0 + cell_df.y1)

    ### add is_buf is_inv to pin_df
    cell_type_df = cell_df.loc[:,["name", "is_buf", "is_inv"]]
    cell_type_df = cell_type_df.rename(columns={"name":"cellname"})
    pin_df = pin_df.merge(cell_type_df, on="cellname", how="left")
    pin_df["is_buf"] = pin_df["is_buf"].fillna(False)
    pin_df["is_inv"] = pin_df["is_inv"].fillna(False)

    ### rename cells and nets
    cell_df, pin_df = rename_cells(cell_df, pin_df)
    net_df, pin_df = rename_nets(net_df, pin_df)

    ### get dimensions
    N_pin, _ = pin_df.shape
    N_cell, _ = cell_df.shape
    N_net, _ = net_df.shape
    total_v_cnt = N_pin+N_cell+N_net
    pin_df['id'] = range(N_pin)
    cell_df['id'] = range(N_pin, N_pin+N_cell)
    net_df['id'] = range(N_pin+N_cell, total_v_cnt)

    ### generate edge_df
    pin_edge_df, cell_edge_df, net_edge_df, net_cell_edge_df, edge_df = \
        generate_edge_df_OpenROAD(pin_df, cell_df, net_df, pin_edge_df, cell_edge_df, net_edge_df, net_cell_edge_df)

    ### get edge dimensions
    N_pin_edge, _ = pin_edge_df.shape
    N_cell_edge, _ = cell_edge_df.shape
    N_net_edge, _ = net_edge_df.shape
    N_net_cell_edge, _ = net_cell_edge_df.shape
    total_e_cnt = N_pin_edge+N_cell_edge+N_net_edge+N_net_cell_edge

    edge_df["e_type"] = 0 # pin
    # edge_df.loc[0:N_pin_edge,["is_net"]] = pin_edge_df.loc[:, "is_net"]
    edge_df.loc[N_pin_edge : N_pin_edge+N_cell_edge, ["e_type"]] = 1 # cell
    edge_df.loc[N_pin_edge+N_cell_edge : N_pin_edge+N_cell_edge+N_net_edge, ["e_type"]] = 2 # net
    edge_df.loc[N_pin_edge+N_cell_edge+N_net_edge : N_pin_edge+N_cell_edge+N_net_edge+N_net_cell_edge, ["e_type"]] = 3 # net_cell

    ### generate graph
    g = Graph()
    g.add_vertex(total_v_cnt)
    v_type = g.new_vp("int")
    v_type.a[0:N_pin] = 0 # pin
    v_type.a[N_pin:N_pin+N_cell] = 1 # cell
    v_type.a[N_pin+N_cell:total_v_cnt] = 2 # net

    ### add edge to graph
    e_type = g.new_ep("int")

    print("num of nodes, num of edges: ", g.num_vertices(), g.num_edges())
    g.add_edge_list(edge_df.values.tolist(), eprops=[e_type])
    print("num of nodes, num of edges: ", g.num_vertices(), g.num_edges())

    return g, pin_df, cell_df, net_df, fo4_df, pin_edge_df, cell_edge_df, net_edge_df, net_cell_edge_df, edge_df, v_type, e_type