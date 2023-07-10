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


import re
import pandas as pd
import numpy as np
import copy
from graph_tool.all import *
from numpy.random import *
import time
import graph_tool as gt
import dgl
import torch
import pickle
import sys
from helper import (
    read_tables,
    rm_invalid_pins_cells,
    assign_gate_size_class,
    rename_cells,
    rename_nets,
    generate_edge_df,
    get_large_components,
    get_subgraph,
    get_cell_graph,
    get_cell_graph_from_cells,
)

cell_cnt_th = 2000

### extract buffer trees from netlist ###
### inputs: data_root, design name, mcmm name
### output:
### nodes: celll/pin id, v_tree_id, v_BT_height, v_bt_s, v_x, v_y, v_arr, v_tran, v_polarity, v_libcell_id
### edges: src, tar, e_tree_id
def BT_sampling(data_root, design, mcmm):
    pin_df, cell_df, net_df, pin_edge_df, cell_edge_df, net_edge_df, net_cell_edge_df, cell2cell_edge_df, fo4_df = read_tables(data_root, design, mcmm)

    ### add is_macro, is_seq to pin_df, change pin_dir to bool
    cell_type_df = cell_df.loc[:,["name", "is_macro", "is_seq"]]
    cell_type_df = cell_type_df.rename(columns={"name":"cellname"})
    pin_df = pin_df.merge(cell_type_df, on="cellname", how="left")
    pin_df["is_macro"] = pin_df["is_macro"].fillna(False)
    pin_df["is_seq"] = pin_df["is_seq"].fillna(False)
    pin_df["dir"] = (pin_df["dir"] == "input")

    ### remove invalid pins and cells
    pin_df, cell_df = rm_invalid_pins_cells(pin_df, cell_df)

    ### processing fo4 table
    fo4_df["group_id"] = pd.factorize(fo4_df.cell_id)[0] + 1
    fo4_df["HVT"] = fo4_df.cell.str.contains("HVT")
    fo4_df["CK"] = fo4_df.cell.str.contains("CK")
    fo4_df["libcell_id"] = range(fo4_df.shape[0])

    ### assign cell size class and min size libcellname
    fo4_df = assign_gate_size_class(fo4_df)

    ### get min size cell
    cell_fo4 = fo4_df.loc[:,["cell", "min_size_cell"]]
    cell_fo4 = cell_fo4.rename(columns={"cell":"ref"})
    cell_df = cell_df.merge(cell_fo4, on="ref", how="left")
    seq_macro_mask = (cell_df.is_seq == True) | (cell_df.is_macro == True)
    cell_df.loc[seq_macro_mask, ["min_size_cell"]] = cell_df.loc[seq_macro_mask, ["ref"]].values
    idx = cell_df[pd.isna(cell_df.min_size_cell)].index
    cell_df.loc[idx, ["min_size_cell"]] = cell_df.loc[idx, ["ref"]].values

    ### get cell center loc
    cell_df["x"] = 0.5*(cell_df.x0 + cell_df.x1)
    cell_df["y"] = 0.5*(cell_df.y0 + cell_df.y1)

    ### add is_buf is_inv to pin_df
    cell_type_df = cell_df.loc[:,["name", "is_buf", "is_inv"]]
    cell_type_df = cell_type_df.rename(columns={"name":"cellname"})
    pin_df = pin_df.merge(cell_type_df, on="cellname", how="left")
    pin_df["is_buf"] = pin_df["is_buf"].fillna(False)
    pin_df["is_inv"] = pin_df["is_inv"].fillna(False)

    pin_df.loc[pin_df.cap == 0.0, ["cap"]] = -1.0
    pin_df.loc[pin_df.maxcap > 10, ["maxcap"]] = -1.0

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
    pin_edge_df, cell_edge_df, net_edge_df, net_cell_edge_df, cell2cell_edge_df, edge_df = \
        generate_edge_df(pin_df, cell_df, net_df, pin_edge_df, cell_edge_df, net_edge_df, net_cell_edge_df, cell2cell_edge_df)

    ### get edge dimensions
    N_pin_edge, _ = pin_edge_df.shape
    N_cell_edge, _ = cell_edge_df.shape
    N_net_edge, _ = net_edge_df.shape
    N_net_cell_edge, _ = net_cell_edge_df.shape
    N_cell2cell_edge, _ = cell2cell_edge_df.shape
    total_e_cnt = N_pin_edge+N_cell_edge+N_net_edge+N_net_cell_edge+N_cell2cell_edge

    edge_df["e_type"] = 0 # pin
    # edge_df.loc[0:N_pin_edge,["is_net"]] = pin_edge_df.loc[:, "is_net"]
    edge_df.loc[N_pin_edge : N_pin_edge+N_cell_edge, ["e_type"]] = 1 # cell
    edge_df.loc[N_pin_edge+N_cell_edge : N_pin_edge+N_cell_edge+N_net_edge, ["e_type"]] = 2 # net
    edge_df.loc[N_pin_edge+N_cell_edge+N_net_edge : N_pin_edge+N_cell_edge+N_net_edge+N_net_cell_edge, ["e_type"]] = 3 # net_cell
    edge_df.loc[N_pin_edge+N_cell_edge+N_net_edge+N_net_cell_edge : total_e_cnt, ["e_type"]] = 4 # cell2cell

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

    ### add edge props
    e_id = g.new_ep("int")
    e_id.a = range(e_id.a.shape[0])

    ### add pin props
    v_isbuf = g.new_vp("bool")
    v_isinv = g.new_vp("bool")
    v_isseq = g.new_vp("bool")
    v_pin_isport = g.new_vp("bool")
    v_pin_isstart = g.new_vp("bool")
    v_pin_isend = g.new_vp("bool")
    v_dir = g.new_vp("bool")
    v_ismacro = g.new_vp("bool")

    v_isbuf.a[0:N_pin] = pin_df["is_buf"].to_numpy()
    v_isinv.a[0:N_pin] = pin_df["is_inv"].to_numpy()
    v_isseq.a[0:N_pin] = pin_df["is_seq"].to_numpy()
    v_pin_isport.a[0:N_pin] = pin_df["is_port"].to_numpy()
    v_pin_isstart.a[0:N_pin] = pin_df["is_start"].to_numpy()
    v_pin_isend.a[0:N_pin] = pin_df["is_end"].to_numpy()
    v_dir.a[0:N_pin] = pin_df["dir"].to_numpy()
    v_ismacro.a[0:N_pin] = pin_df["is_macro"].to_numpy()

    ### add cell props
    v_isbuf.a[N_pin:N_pin+N_cell] = cell_df["is_buf"].to_numpy()
    v_isinv.a[N_pin:N_pin+N_cell] = cell_df["is_inv"].to_numpy()
    v_isseq.a[N_pin:N_pin+N_cell] = cell_df["is_seq"].to_numpy()
    v_ismacro.a[N_pin:N_pin+N_cell] = cell_df["is_macro"].to_numpy()

    ### add cell id to pin_df
    cell_temp = cell_df.loc[:, ["name", "id"]]
    cell_temp = cell_temp.rename(columns={"name":"cellname", "id":"cell_id"})
    pin_df = pin_df.merge(cell_temp, on="cellname", how="left")
    idx = pin_df[pd.isna(pin_df.cell_id)].index
    pin_df.loc[idx, ["cell_id"]] = pin_df.loc[idx, ["id"]].to_numpy()

    pin_cellid = pin_df.cell_id.to_numpy()
    pin_isseq = v_isseq.a[0:N_pin]
    pin_ismacro = v_ismacro.a[0:N_pin]
    mask = (pin_isseq==True)| (pin_ismacro==True)
    pin_cellid[mask] = pin_df[mask].id ### for pins in macro and seq, pin_cellid = pin id

    ### add net id to pin_df
    net_temp = net_df.loc[:, ["name", "id"]]
    net_temp = net_temp.rename(columns={"name":"netname", "id":"net_id"})
    pin_df = pin_df.merge(net_temp, on="netname", how="left")

    ### generate pin graph
    g_pin = GraphView(g, vfilt=(v_type.a==0), efilt=e_type.a==0)
    print("pin graph: num of nodes, num of edges: ", g_pin.num_vertices(), g_pin.num_edges())

    ### get the large components
    comp, hist = label_components(g_pin, directed=False)
    comp.a[N_pin:] = -1
    labels = get_large_components(hist, th=cell_cnt_th)
    v_valid_pins = g_pin.new_vp("bool")
    for l in labels:
        v_valid_pins.a[comp.a==l] = True
    print(v_valid_pins.a.sum())

    ### get subgraphs
    e_label = g_pin.new_ep("bool")
    e_label.a = False
    e_ar = g_pin.get_edges(eprops=[e_id])
    v_ar = g.get_vertices(vprops=[v_isbuf, v_isinv, v_valid_pins])
    src = e_ar[:,0]
    tar = e_ar[:,1]
    idx = e_ar[:,2]
    mask = (v_ar[src, -1] == True) & (v_ar[tar, -1] == True)
    e_label.a[idx[mask]] = True
    u = get_subgraph(g_pin, v_valid_pins, e_label)

    # ### get pre-opt cell2cell graph
    # u_cells, u_cell_g = get_cell_graph(u, pin_cellid, g, e_type, e_id)

    ### get buffer tree start and end points
    v_bt_s = g.new_vp("bool")
    v_bt_e = g.new_vp("bool")
    v_bt_s.a = False
    v_bt_e.a = False

    e_ar = u.get_edges()
    v_ar = g.get_vertices(vprops=[v_isbuf, v_isinv])
    src = e_ar[:,0]
    tar = e_ar[:,1]
    src_isbuf = v_ar[src,1]
    src_isinv = v_ar[src,2]
    tar_isbuf = v_ar[tar,1]
    tar_isinv = v_ar[tar,2]
    is_s = (tar_isbuf | tar_isinv ) & np.logical_not(src_isbuf) & np.logical_not(src_isinv)
    v_bt_s.a[src[is_s==1]] = True

    src_iss = v_bt_s.a[src]==True
    is_e = (src_isbuf | src_isinv | src_iss) & np.logical_not(tar_isbuf) & np.logical_not(tar_isinv)
    v_bt_e.a[tar[is_e==1]] = True
    print("buf tree start cnt: ", v_bt_s.a.sum(), "buf tree end cnt: ", v_bt_e.a.sum())

    ### mark buffer trees
    v_tree_id = g.new_vp("int")
    v_tree_id.a = 0
    v_polarity = g.new_vp("bool")
    v_polarity.a = True
    e_tree_id = g.new_ep("int")
    e_tree_id.a = 0

    tree_end_list = []
    buf_list = []

    v_all = g.get_vertices()
    l = np.array(list(range(1, int(v_bt_s.a.sum())+1)))
    v_tree_id.a[v_bt_s.a>0] = l
    loc = v_all[v_bt_s.a>0]
    out_v_list = []
    for i in loc:
        out_e = u.get_out_edges(i, eprops=[e_id])
        out_v = out_e[:,1]
        v_tree_cnt = v_tree_id[i]
        e_tree_id.a[out_e[:,-1]] = v_tree_cnt
        v_tree_id.a[out_v] = v_tree_cnt
        tree_end_list.append(out_v[(v_isbuf.a[out_v]==False) & (v_isinv.a[out_v]==False)])
        out_v = out_v[(v_isbuf.a[out_v]==True) | (v_isinv.a[out_v]==True)]
        buf_list.append(out_v)
        out_v_list.append(out_v)
    new_v = np.concatenate(out_v_list, axis=0)
    N,  = new_v.shape
    print("num of buffer tree out pins: ", N)
    while N > 0:
        out_v_list = []
        for i in new_v:
            if v_isbuf[i]:
                out_e = u.get_out_edges(i, eprops=[e_id])
                out_v = out_e[:,1]
                v_tree_cnt = v_tree_id[i]
                v_p = v_polarity.a[i]
                e_tree_id.a[out_e[:,-1]] = v_tree_cnt
                v_tree_id.a[out_v] = v_tree_cnt
                v_polarity.a[out_v] = v_p
                tree_end_list.append(out_v[(v_isbuf.a[out_v]==False) & (v_isinv.a[out_v]==False)])
                out_v = out_v[(v_isbuf.a[out_v]==True) | (v_isinv.a[out_v]==True)]
                buf_list.append(out_v)
                out_v_list.append(out_v)
            else:
                out_e = u.get_out_edges(i, eprops=[e_id])
                out_v = out_e[:,1]
                v_tree_cnt = v_tree_id[i]
                v_p = v_polarity.a[i]
                e_tree_id.a[out_e[:,-1]] = v_tree_cnt
                v_tree_id.a[out_v] = v_tree_cnt
                if v_dir[i]:
                    v_polarity.a[out_v] = not v_p
                else:
                    v_polarity.a[out_v] = v_p
                ###
                tree_end_list.append(out_v[(v_isbuf.a[out_v]==False) & (v_isinv.a[out_v]==False)])
                ###
                out_v = out_v[(v_isbuf.a[out_v]==True) | (v_isinv.a[out_v]==True)]
                ###
                buf_list.append(out_v)
                ###
                out_v_list.append(out_v)
        new_v = np.concatenate(out_v_list, axis=0)
        N, = new_v.shape
        print("num of buffer tree out pins: ", N)

    ### get actual number of BT end pin cnt
    tree_end_list_new = np.concatenate(tree_end_list, axis=0)
    print(tree_end_list_new.shape[0], v_bt_e.a.sum())
    N_bt_e = tree_end_list_new.shape[0]
    v_bt_e = g.new_vp("bool")
    v_bt_e.a = False
    v_bt_e.a[tree_end_list_new] = True
    print(v_bt_e.a.sum())


    ### get all buffer pins in BTs
    mask = (v_tree_id.a>0) & ((v_isbuf.a == True) | (v_isinv.a == True))
    pins = v_all[mask]

    pin_dirs = v_dir.a[pins]
    in_pins = pins[pin_dirs == True]
    in_pin_cells = pin_cellid[in_pins]
    v_polarity.a[in_pin_cells] = v_polarity.a[in_pins]

    ### get buffer cell graph
    cells = pin_cellid[pins]
    v_tree_id.a[cells] = v_tree_id.a[pins]
    cells = np.unique(cells).astype(int)
    buf_cell_g = get_cell_graph_from_cells(cells, g, e_type, e_id)
    e_ar = buf_cell_g.get_edges(eprops=[e_id])
    src = e_ar[:,0]
    e_tree_id.a[e_ar[:,-1]] = v_tree_id.a[src]

    # comp1, hist1 = label_components(buf_cell_g, directed=False)
    # print(len(hist1))

    ### get edge from BT start pin to buf and from buf to BT end pin
    e_ar = u.get_edges(eprops=[e_tree_id, e_type, e_id])
    src = e_ar[:,0]
    tar = e_ar[:,1]
    src_is_start = (v_bt_s.a[src] == True) & ((v_isbuf.a[tar] == True) | (v_isinv.a[tar] == True))
    temp_edge1 = e_ar[src_is_start]
    temp_edge1[:,1] = pin_cellid[temp_edge1[:,1]]
    temp_edge1[:,2] = v_tree_id.a[temp_edge1[:,0]]

    tar_is_end = (v_bt_e.a[tar] == True)  & ((v_isbuf.a[src] == True) | (v_isinv.a[src] == True))
    temp_edge2 = e_ar[tar_is_end]
    temp_edge2[:,2] = v_tree_id.a[temp_edge2[:,0]]
    temp_edge2[:,0] = pin_cellid[temp_edge2[:,0]]

    src_is_start_tar_is_end = (v_bt_s.a[src] == True) & (v_bt_e.a[tar] == True)
    temp_edge3 = e_ar[src_is_start_tar_is_end]

    edges = np.concatenate([temp_edge1, temp_edge2, temp_edge3], axis=0)
    M = edges.shape[0]
    print("# added edgeds: ", M)
    edges[:,3] = 10 ### edge from BT start pin to buf and from buf to BT end pin
    edges[:,-1] = range(total_e_cnt, total_e_cnt+M)
    # total_e_cnt += M
    g.add_edge_list(edges.tolist(), eprops=[e_tree_id, e_type, e_id])

    ### generate BT graphs
    v_mask_BT = g.new_vp("bool")
    v_mask_BT.a = False
    v_mask_BT.a[cells] = True  ### bufs
    v_mask_BT.a[v_bt_s.a == True] = True ### source pins
    v_mask_BT.a[v_bt_e.a == True] = True ### sink pins
    e_mask_BT = g.new_ep("bool")
    e_mask_BT.a = False
    e_mask_BT.a[edges[:,-1]] = True  ### source/sink pins <-> bufs
    temp_e = buf_cell_g.get_edges(eprops=[e_id]) ### bufs <-> bufs
    e_mask_BT.a[temp_e[:,-1]] = True
    BT_g = get_subgraph(g, v_mask_BT, e_mask_BT)
    # comp1, hist1 = label_components(BT_g, directed=False)
    # print(hist1)

    ### get height of nodes in BTs
    v_BT = BT_g.get_vertices()
    name_mapping = {}
    for i in range(v_BT.shape[0]):
        name_mapping[v_BT[i]] = i

    v_BT_height = g.new_vp("int")
    v_out = BT_g.get_out_degrees(v_BT)
    loc = v_BT[v_out == 0]
    v_BT_height.a[loc] = 1
    v_out[v_out == 0] = -1

    N = len(loc)
    height = 2
    while N > 0:
        for i in loc:
            in_e = BT_g.get_in_edges(i)
            if in_e.shape[0] == 0: continue
            in_v = int(in_e[:,0])
            v_out[name_mapping[in_v]] -= 1
        loc = v_BT[v_out == 0]
        N = len(loc)
        v_BT_height.a[loc] = height
        height += 1
        v_out[v_out == 0] = -1


    ### generate features for cells
    in_pins_mask = pin_df.dir == True
    in_pins = pin_df.loc[in_pins_mask, ["name",'new_cellname',"tran"]]
    cell_worst_tran = in_pins.groupby('new_cellname', as_index=False).agg({'tran': ['max']})
    cell_worst_tran.columns = ['_'.join(col).rstrip('_') for col in cell_worst_tran.columns.values]
    cell_df = cell_df.merge(cell_worst_tran, on="new_cellname", how="left")
    pin_df = pin_df.merge(cell_worst_tran, on="new_cellname", how="left")

    in_pins = pin_df.loc[in_pins_mask, ['new_cellname',"cap"]]
    cell_worst_cap = in_pins.groupby('new_cellname', as_index=False).agg({'cap': ['max']})
    cell_worst_cap.columns = ['_'.join(col).rstrip('_') for col in cell_worst_cap.columns.values]
    cell_df = cell_df.merge(cell_worst_cap, on="new_cellname", how="left")
    pin_df = pin_df.merge(cell_worst_cap, on="new_cellname", how="left")

    in_pins = pin_df.loc[in_pins_mask, ['new_cellname',"arr"]]
    cell_worst_arr = in_pins.groupby('new_cellname', as_index=False).agg({'arr': ['max']})
    cell_worst_arr.columns = ['_'.join(col).rstrip('_') for col in cell_worst_arr.columns.values]
    cell_df = cell_df.merge(cell_worst_arr, on="new_cellname", how="left")

    temp = fo4_df.loc[:, ["cell", "libcell_id"]]
    cell_df = cell_df.merge(temp.rename(columns={"cell":"ref"}), on="ref", how="left")
    temp = cell_df.loc[:, ["new_cellname", "libcell_id"]]
    pin_df = pin_df.merge(temp, on="new_cellname", how="left")

    ### add more vertices features
    v_x = g.new_vp("float")
    v_y = g.new_vp("float")
    v_x.a[0:N_pin] = pin_df["x"].to_numpy()
    v_y.a[0:N_pin] = pin_df["y"].to_numpy()
    v_x.a[N_pin:N_pin+N_cell] = cell_df["x"].to_numpy()
    v_y.a[N_pin:N_pin+N_cell] = cell_df["y"].to_numpy()

    v_cap = g.new_vp("float")
    v_cap.a[0:N_pin] = pin_df["cap"].to_numpy()
    v_cap.a[N_pin:N_pin+N_cell] = cell_df["cap_max"].to_numpy()

    v_libcell_id = g.new_vp("int")
    v_libcell_id.a[0:N_pin] = pin_df["libcell_id"].to_numpy()
    v_libcell_id.a[N_pin:N_pin+N_cell] = cell_df["libcell_id"].to_numpy()

    v_arr = g.new_vp("float")
    v_arr.a[0:N_pin] = pin_df["arr"].to_numpy()
    v_arr.a[N_pin:N_pin+N_cell] = cell_df["arr_max"].to_numpy()

    v_tran = g.new_vp("float")
    v_tran.a[0:N_pin] = pin_df["tran"].to_numpy()
    v_tran.a[N_pin:N_pin+N_cell] = cell_df["tran_max"].to_numpy()

    ### get BT features
    v_ar = BT_g.get_vertices(vprops=[v_tree_id, v_BT_height, v_bt_s, v_x, v_y, v_arr, v_tran, v_polarity, v_libcell_id])
    e_ar = BT_g.get_edges(eprops=[e_tree_id]).astype("int")
    v_ar = v_ar[v_ar[:,1].argsort()]
    e_ar = e_ar[e_ar[:,2].argsort()]
    N = int(v_bt_s.a.sum())

    ### split v_ar according to BT ids
    v_tree_ids = v_ar[:,1].astype("int")
    cur_id = 1
    v_cnt_list = []
    cnt = 0
    for i in v_tree_ids:
        if i == cur_id:
            cnt += 1
        else:
            v_cnt_list.append(cnt)
            cur_id = i
            cnt += 1
    v_cnt_list.append(cnt)
    nodes = np.split(v_ar, v_cnt_list)

    ### split e_ar according to BT ids
    e_tree_ids = e_ar[:,2].astype("int")
    cur_id = 1
    e_cnt_list = []
    cnt = 0
    for i in e_tree_ids:
        if i == cur_id:
            cnt += 1
        else:
            e_cnt_list.append(cnt)
            cur_id = i
            cnt += 1
    e_cnt_list.append(cnt)
    edges = np.split(e_ar, e_cnt_list)

    return nodes[:-1], edges[:-1]

if __name__ == "__main__":
    data_root = sys.argv[1]
    design = sys.argv[2]
    mcmm = sys.argv[3]
    output_path = sys.argv[4]
    nodes, edges = BT_sampling(data_root, design, mcmm)
    ### save BTs
    with open(output_path + 'sample_nodes.pkl', 'wb') as f:
        pickle.dump(nodes, f, pickle.HIGHEST_PROTOCOL)
    with open(output_path + 'sample_edges.pkl', 'wb') as f:
        pickle.dump(edges, f, pickle.HIGHEST_PROTOCOL)