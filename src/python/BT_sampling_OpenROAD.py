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
from graph_tool.all import *
from numpy.random import *
import graph_tool as gt
import pickle
import sys
from helper import (
    get_large_components,
    get_subgraph,
    get_cell_graph_from_cells,
)
from generate_LPG_from_tables import generate_LPG_from_tables

cell_cnt_th = 20

### extract buffer trees from netlist ###
### inputs: data_root, design name
### output:
### nodes: celll/pin id, v_tree_id, v_BT_height, v_bt_s, v_x, v_y, v_arr, v_tran, v_polarity, v_libcell_id
### edges: src, tar, e_tree_id
def BT_sampling(data_root):
    g, pin_df, cell_df, net_df, fo4_df, pin_pin_df, cell_pin_df, \
        net_pin_df, net_cell_df, cell_cell_df, edge_df, v_type, e_type \
        = generate_LPG_from_tables(data_root)

    ### get dimensions
    N_pin, _ = pin_df.shape
    N_cell, _ = cell_df.shape
    N_net, _ = net_df.shape
    total_v_cnt = N_pin+N_cell+N_net

    N_pin_pin, _ = pin_pin_df.shape
    N_cell_pin, _ = cell_pin_df.shape
    N_net_pin, _ = net_pin_df.shape
    N_net_cell, _ = net_cell_df.shape
    N_cell_cell, _ = cell_cell_df.shape
    total_e_cnt = N_pin_pin + N_cell_pin + N_net_pin + N_net_cell + N_cell_cell

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
    # v_pin_isport.a[0:N_pin] = pin_df["is_port"].to_numpy()
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

    in_pins = pin_df.loc[in_pins_mask, ['new_cellname',"risearr"]]
    cell_worst_risearr = in_pins.groupby('new_cellname', as_index=False).agg({'risearr': ['max']})
    cell_worst_risearr.columns = ['_'.join(col).rstrip('_') for col in cell_worst_risearr.columns.values]
    cell_df = cell_df.merge(cell_worst_risearr, on="new_cellname", how="left")

    in_pins = pin_df.loc[in_pins_mask, ['new_cellname',"fallarr"]]
    cell_worst_fallarr = in_pins.groupby('new_cellname', as_index=False).agg({'fallarr': ['max']})
    cell_worst_fallarr.columns = ['_'.join(col).rstrip('_') for col in cell_worst_fallarr.columns.values]
    cell_df = cell_df.merge(cell_worst_fallarr, on="new_cellname", how="left")   

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

    v_risearr = g.new_vp("float")
    v_risearr.a[0:N_pin] = pin_df["risearr"].to_numpy()
    v_risearr.a[N_pin:N_pin+N_cell] = cell_df["risearr_max"].to_numpy()

    v_fallarr = g.new_vp("float")
    v_fallarr.a[0:N_pin] = pin_df["fallarr"].to_numpy()
    v_fallarr.a[N_pin:N_pin+N_cell] = cell_df["fallarr_max"].to_numpy()

    v_tran = g.new_vp("float")
    v_tran.a[0:N_pin] = pin_df["tran"].to_numpy()
    v_tran.a[N_pin:N_pin+N_cell] = cell_df["tran_max"].to_numpy()

    ### get BT features
    v_ar = BT_g.get_vertices(vprops=[v_tree_id, v_BT_height, v_bt_s, v_x, v_y, v_risearr, v_fallarr, v_tran, v_polarity, v_libcell_id])
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
    output_path = sys.argv[2]
    nodes, edges = BT_sampling(data_root)
    ### save BTs
    with open(output_path + 'BT_nodes.pkl', 'wb') as f:
        pickle.dump(nodes, f, pickle.HIGHEST_PROTOCOL)
    with open(output_path + 'BT_edges.pkl', 'wb') as f:
        pickle.dump(edges, f, pickle.HIGHEST_PROTOCOL)

    print("------------Done------------")
