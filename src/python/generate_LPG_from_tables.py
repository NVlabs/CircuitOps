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
    pin_df, cell_df, net_df, pin_pin_df, cell_pin_df, net_pin_df, net_cell_df, cell_cell_df, fo4_df = read_tables_OpenROAD(data_root)

    #### rename dfs
    pin_df = pin_df.rename(columns={"pin_name":"name", "cell_name":"cellname", "net_name":"netname", \
                                    "pin_tran":"tran", "pin_slack":"slack", "pin_rise_arr":"risearr", \
                                    "pin_fall_arr":"fallarr", "input_pin_cap":"cap", "is_startpoint":"is_start", \
                                    "is_endpoint":"is_end"})
    cell_df = cell_df.rename(columns={"cell_name":"name", "libcell_name":"ref", "cell_static_power":"staticpower", \
                                    "cell_dynamic_power":"dynamicpower"})
    net_df = net_df.rename(columns={"net_name":"name"})
    
    fo4_df = fo4_df.rename(columns={"libcell_name":"ref"})

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
    pin_pin_df, cell_pin_df, net_pin_df, net_cell_df, cell_cell_df, edge_df = \
        generate_edge_df_OpenROAD(pin_df, cell_df, net_df, pin_pin_df, cell_pin_df, net_pin_df, net_cell_df, cell_cell_df)

    ### get edge dimensions
    N_pin_pin, _ = pin_pin_df.shape
    N_cell_pin, _ = cell_pin_df.shape
    N_net_pin, _ = net_pin_df.shape
    N_net_cell, _ = net_cell_df.shape
    N_cell_cell, _ = cell_cell_df.shape
    total_e_cnt = N_pin_pin + N_cell_pin + N_net_pin + N_net_cell + N_cell_cell

    edge_df["e_type"] = 0 # pin_pin
    # edge_df.loc[0:N_pin_edge,["is_net"]] = pin_edge_df.loc[:, "is_net"]
    edge_df.loc[N_pin_pin : N_pin_pin+N_cell_pin, ["e_type"]] = 1 # cell_pin
    edge_df.loc[N_pin_pin+N_cell_pin : N_pin_pin+N_cell_pin+N_net_pin, ["e_type"]] = 2 # net_pin
    edge_df.loc[N_pin_pin+N_cell_pin+N_net_pin : N_pin_pin+N_cell_pin+N_net_pin+N_net_cell, ["e_type"]] = 3 # net_cell
    edge_df.loc[N_pin_pin+N_cell_pin+N_net_pin+N_net_cell : N_pin_pin+N_cell_pin+N_net_pin+N_net_cell+N_cell_cell, ["e_type"]] = 4 # cell_cell

    #HERERERERE
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

    ### add properties to LPG
    ### processing fo4 table
    fo4_df["group_id"] = pd.factorize(fo4_df.func_id)[0] + 1
    fo4_df["libcell_id"] = range(fo4_df.shape[0])
    libcell_np = fo4_df.to_numpy()
    
    ### assign cell size class
    fo4_df["size_class"] = 0
    fo4_df["size_class2"] = 0
    fo4_df["size_cnt"] = 0
    class_cnt = 50
    for i in range(fo4_df.group_id.min(), fo4_df.group_id.max()+1):
        temp = fo4_df.loc[fo4_df.group_id==i, ["group_id", "libcell_delay_fixed_load"]]
        temp = temp.sort_values(by=['libcell_delay_fixed_load'], ascending=False)
        fo4_df.loc[temp.index, ["size_class"]] = range(len(temp))
        fo4_df.loc[temp.index, ["size_cnt"]] = len(temp)
    
        temp["size_cnt"] = 0
        MIN = temp.libcell_delay_fixed_load.min()
        MAX = temp.libcell_delay_fixed_load.max()
        interval = (MAX-MIN)/class_cnt
        for j in range(1, class_cnt):
            delay_h = MAX - j*interval
            delay_l = MAX - (j+1)*interval
            if j == (class_cnt-1):
                delay_l = MIN
            temp.loc[(temp.libcell_delay_fixed_load < delay_h) & (temp.libcell_delay_fixed_load >= delay_l), ["size_cnt"]] = j
        fo4_df.loc[temp.index, ["size_class2"]] = temp["size_cnt"]
    
    cell_fo4 = fo4_df.loc[:,["ref", "fo4_delay", "libcell_delay_fixed_load",  "group_id", "libcell_id", "size_class", "size_class2", "size_cnt"]]
    cell_df = cell_df.merge(cell_fo4, on="ref", how="left")
    cell_df["libcell_id"] = cell_df["libcell_id"].fillna(-1)

    ### add node and edge ids
    v_id = g.new_ep("int")
    v_id.a = range(v_id.a.shape[0])
    
    e_id = g.new_ep("int")
    e_id.a = range(e_id.a.shape[0])

    ### add pin properties to LPG ###
    v_x = g.new_vp("float")
    v_y = g.new_vp("float")
    v_is_in_clk = g.new_vp("bool")
    v_is_port = g.new_vp("bool")
    v_is_start = g.new_vp("bool")
    v_is_end = g.new_vp("bool")
    v_dir = g.new_vp("bool")
    v_maxcap = g.new_vp("float")
    v_maxtran = g.new_vp("float")
    v_num_reachable_endpoint = g.new_vp("int")
    v_tran = g.new_vp("float")
    v_slack = g.new_vp("float")
    v_risearr = g.new_vp("float")
    v_fallarr = g.new_vp("float")
    v_cap = g.new_vp("float")
    v_is_macro = g.new_vp("bool")
    v_is_seq = g.new_vp("bool")
    v_is_buf = g.new_vp("bool")
    v_is_inv = g.new_vp("bool")
    
    
    v_x.a[0:N_pin] = pin_df["x"].to_numpy()
    v_y.a[0:N_pin] = pin_df["y"].to_numpy()
    v_is_in_clk.a[0:N_pin] = pin_df["is_in_clk"].to_numpy()
    v_is_port.a[0:N_pin] = pin_df["is_port"].to_numpy()
    v_is_start.a[0:N_pin] = pin_df["is_start"].to_numpy()
    v_is_end.a[0:N_pin] = pin_df["is_end"].to_numpy()
    v_dir.a[0:N_pin] = pin_df["dir"].to_numpy()
    v_maxcap.a[0:N_pin] = pin_df["maxcap"].to_numpy()
    v_maxtran.a[0:N_pin] = pin_df["maxtran"].to_numpy()
    v_num_reachable_endpoint.a[0:N_pin] = pin_df["num_reachable_endpoint"].to_numpy()
    v_tran.a[0:N_pin] = pin_df["tran"].to_numpy()
    v_slack.a[0:N_pin] = pin_df["slack"].to_numpy()
    v_risearr.a[0:N_pin] = pin_df["risearr"].to_numpy()
    v_fallarr.a[0:N_pin] = pin_df["fallarr"].to_numpy()
    v_cap.a[0:N_pin] = pin_df["cap"].to_numpy()
    v_is_macro.a[0:N_pin] = pin_df["is_macro"].to_numpy()
    v_is_seq.a[0:N_pin] = pin_df["is_seq"].to_numpy()
    v_is_buf.a[0:N_pin] = pin_df["is_buf"].to_numpy()
    v_is_inv.a[0:N_pin] = pin_df["is_inv"].to_numpy()

    ### add cell properties to LPG ###
    v_x0 = g.new_vp("float")
    v_y0 = g.new_vp("float")
    v_x1 = g.new_vp("float")
    v_y1 = g.new_vp("float")
    v_staticpower = g.new_vp("float")
    v_dynamicpower = g.new_vp("float")
    
    v_fo4_delay = g.new_vp("float")
    v_libcell_delay_fixed_load = g.new_vp("float")
    v_group_id = g.new_ep("int")
    v_libcell_id = g.new_ep("int")
    v_size_class = g.new_ep("int")
    v_size_class2 = g.new_ep("int")
    v_size_cnt = g.new_ep("int")
    
    
    v_is_seq.a[N_pin:N_pin+N_cell] = cell_df["is_seq"].to_numpy()
    v_is_macro.a[N_pin:N_pin+N_cell] = cell_df["is_macro"].to_numpy()
    v_is_in_clk.a[N_pin:N_pin+N_cell] = cell_df["is_in_clk"].to_numpy()
    v_x0.a[N_pin:N_pin+N_cell] = cell_df["x0"].to_numpy()
    v_y0.a[N_pin:N_pin+N_cell] = cell_df["y0"].to_numpy()
    v_x1.a[N_pin:N_pin+N_cell] = cell_df["x1"].to_numpy()
    v_y1.a[N_pin:N_pin+N_cell] = cell_df["y1"].to_numpy()
    v_is_buf.a[N_pin:N_pin+N_cell] = cell_df["is_buf"].to_numpy()
    v_is_inv.a[N_pin:N_pin+N_cell] = cell_df["is_inv"].to_numpy()
    v_staticpower.a[N_pin:N_pin+N_cell] = cell_df["staticpower"].to_numpy()
    v_dynamicpower.a[N_pin:N_pin+N_cell] = cell_df["dynamicpower"].to_numpy()
    v_x.a[N_pin:N_pin+N_cell] = cell_df["x"].to_numpy()
    v_y.a[N_pin:N_pin+N_cell] = cell_df["y"].to_numpy()
    
    v_fo4_delay.a[N_pin:N_pin+N_cell] = cell_df["fo4_delay"].to_numpy()
    v_libcell_delay_fixed_load.a[N_pin:N_pin+N_cell] = cell_df["libcell_delay_fixed_load"].to_numpy()
    v_group_id.a[N_pin:N_pin+N_cell] = cell_df["group_id"].to_numpy()
    v_libcell_id.a[N_pin:N_pin+N_cell] = cell_df["libcell_id"].to_numpy()
    v_size_class.a[N_pin:N_pin+N_cell] = cell_df["size_class"].to_numpy()
    v_size_class2.a[N_pin:N_pin+N_cell] = cell_df["size_class2"].to_numpy()
    v_size_cnt.a[N_pin:N_pin+N_cell] = cell_df["size_cnt"].to_numpy()

    ### add net properties to LPG ###
    v_net_route_length = g.new_vp("float")
    v_net_steiner_length = g.new_vp("float")
    v_fanout = g.new_vp("int")
    v_total_cap = g.new_vp("float")
    v_net_cap = g.new_vp("float")
    v_net_coupling = g.new_vp("float")
    v_net_res = g.new_vp("float")
    
    v_net_route_length.a[N_pin+N_cell:N_pin+N_cell+N_net] = net_df["net_route_length"].to_numpy()
    v_net_steiner_length.a[N_pin+N_cell:N_pin+N_cell+N_net] = net_df["net_steiner_length"].to_numpy()
    v_fanout.a[N_pin+N_cell:N_pin+N_cell+N_net] = net_df["fanout"].to_numpy()
    v_total_cap.a[N_pin+N_cell:N_pin+N_cell+N_net] = net_df["total_cap"].to_numpy()
    v_net_cap.a[N_pin+N_cell:N_pin+N_cell+N_net] = net_df["net_cap"].to_numpy()
    v_net_coupling.a[N_pin+N_cell:N_pin+N_cell+N_net] = net_df["net_coupling"].to_numpy()
    v_net_res.a[N_pin+N_cell:N_pin+N_cell+N_net] = net_df["net_res"].to_numpy()

    return g, pin_df, cell_df, net_df, fo4_df, pin_pin_df, cell_pin_df, net_pin_df, net_cell_df, cell_cell_df, edge_df, v_type, e_type
