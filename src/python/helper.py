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
import dgl
import torch

### generate pandas dataframes by reading csv files
def read_tables(data_root, design, mcmm):
    cell_edge_path = data_root  + design + "_cell_edge.csv"
    cell_path = data_root  + design + "_cell.csv"
    net_edge_path = data_root  + design + "_net_edge.csv"
    net_path = data_root  + design + "_net.csv"
    pin_edge_path = data_root  + design + "_pin_edge.csv"
    pin_path = data_root  + design + "_pin.csv"
    net_cell_edge_path = data_root  + design + "_net_cell_edge.csv"
    cell2cell_edge_path = data_root + design + "_cell2cell_edge.csv"

    mcmm_cell_path = data_root  + design + "_" + mcmm + "_cell.csv"
    mcmm_net_path = data_root  + design + "_" + mcmm + "_net.csv"
    mcmm_pin_path = data_root  + design + "_" + mcmm + "_pin.csv"

    all_fo4_delay_path = data_root + "all_fo4_delay_new.txt"
    median_delay_path = data_root + "median_delay_new.txt"

    ### load tables
    fo4_df = pd.read_table(all_fo4_delay_path, sep=',')
    median_delay_df = pd.read_table(median_delay_path, sep=',')

    pin_df = pd.read_csv(pin_path)
    cell_df = pd.read_csv(cell_path)
    net_df = pd.read_csv(net_path)

    pin_edge_df = pd.read_csv(pin_edge_path)
    cell_edge_df = pd.read_csv(cell_edge_path)
    net_edge_df = pd.read_csv(net_edge_path)
    net_cell_edge_df = pd.read_csv(net_cell_edge_path)
    cell2cell_edge_df = pd.read_csv(cell2cell_edge_path)

    print("fo4_df shape: ", fo4_df.shape)
    print("pin_df.shape: ", pin_df.shape)
    print("cell_df.shape: ", cell_df.shape)
    print("net_df.shape: ", net_df.shape)
    print("pin_edge_df.shape: ", pin_edge_df.shape)
    print("cell_edge_df.shape: ", cell_edge_df.shape)
    print("net_edge_df.shape: ", net_edge_df.shape)
    print("net_cell_edge_df.shape: ", net_cell_edge_df.shape)
    print("cell2cell_edge_df.shape: ", cell2cell_edge_df.shape)

    ### load mcmm table
    mcmm_pin_df = pd.read_csv(mcmm_pin_path)
    mcmm_cell_df = pd.read_csv(mcmm_cell_path)
    mcmm_net_df = pd.read_csv(mcmm_net_path)
    print("mcmm_pin_df.shape: ", mcmm_pin_df.shape)
    print("mcmm_cell_df.shape: ", mcmm_cell_df.shape)
    print("mcmm_net_df.shape: ", mcmm_net_df.shape)

    ### merge mcmm-independent features and mcmm-depedent features
    pin_df = pin_df.merge(mcmm_pin_df, on="name", how="left")
    cell_df = cell_df.merge(mcmm_cell_df, on="name", how="left")
    net_df = net_df.merge(mcmm_net_df, on="name", how="left")

    ### merge fo4_df and median_delay_df
    fo4_df = fo4_df.merge(median_delay_df.loc[:,["cell_id", "num_refs", "mdelay"]], on="cell_id", how="left")
    fo4_df = fo4_df.reset_index()

    return pin_df, cell_df, net_df, pin_edge_df, cell_edge_df, net_edge_df, net_cell_edge_df, cell2cell_edge_df, fo4_df

### remove pins and cell with arrival time > 1000 or infinite slack
def rm_invalid_pins_cells(pin_df, cell_df):
    invalid_mask = (np.isinf(pin_df.slack)) | (pin_df.arr>1000)
    pin_df["invalid"] = False
    pin_df.loc[invalid_mask, ["invalid"]] = True

    cell_invalid = pin_df.groupby('cellname', as_index=False).agg({'invalid': ['sum']})
    cell_invalid.columns = ['_'.join(col).rstrip('_') for col in cell_invalid.columns.values]
    cell_invalid["invalid_sum"] = cell_invalid["invalid_sum"] > 0

    pin_df = pin_df.merge(cell_invalid, on="cellname", how="left")
    cell_df = cell_df.merge(cell_invalid.rename(columns={"cellname":"name"}), on="name", how="left")
    cell_df["invalid_sum"] = cell_df["invalid_sum"].fillna(True)

    special_mask = (pin_df["is_port"]== True) | (pin_df["is_macro"]== True) | (pin_df["is_seq"]== True)
    valid_mask = ((special_mask) & (~pin_df["invalid"])) | ((~special_mask) & (~pin_df["invalid_sum"]))
    pin_df["cell_invalid"] = ~valid_mask

    pin_df = pin_df.loc[(pin_df["cell_invalid"]==False)]
    special_mask = (cell_df["is_macro"]) | (cell_df["is_seq"])
    valid_mask = (special_mask) | ((~special_mask) & (~cell_df["invalid_sum"]))
    cell_df = cell_df.loc[valid_mask]

    pin_df = pin_df.reset_index()
    pin_df = pin_df.drop(columns=["index"])

    cell_df = cell_df.reset_index()
    cell_df = cell_df.drop(columns=["index"])
    return pin_df, cell_df

### assign cell size class and get minimum size libcellname
def assign_gate_size_class(fo4_df):
    ### assign cell size class and min size libcellname
    fo4_df["size_class"] = 0
    fo4_df["size_class2"] = 0
    fo4_df["size_cnt"] = 0
    class_cnt = 50
    for i in range(fo4_df.group_id.min(), fo4_df.group_id.max()+1):
        temp = fo4_df.loc[fo4_df.group_id==i, ["group_id", "cell", "cell_delay_fixed_load"]]
        temp = temp.sort_values(by=['cell_delay_fixed_load'], ascending=False)
        fo4_df.loc[temp.index, ["size_class"]] = range(len(temp))
        fo4_df.loc[temp.index, ["size_cnt"]] = len(temp)

        temp["size_cnt"] = 0
        MIN = temp.cell_delay_fixed_load.min()
        MAX = temp.cell_delay_fixed_load.max()
        interval = (MAX-MIN)/class_cnt
        for j in range(1, class_cnt):
            delay_h = MAX - j*interval
            delay_l = MAX - (j+1)*interval
            if j == (class_cnt-1):
                delay_l = MIN
            temp.loc[(temp.cell_delay_fixed_load < delay_h) & (temp.cell_delay_fixed_load >= delay_l), ["size_cnt"]] = j
        fo4_df.loc[temp.index, ["size_class2"]] = temp["size_cnt"]

        ### add min size libcellname
        fo4_df.loc[temp.index, ["min_size_cell"]] = temp.cell.to_list()[0]
    return fo4_df

### rename cells with cell0, cell1, ... and update the cell names in pin_df
def rename_cells(cell_df, pin_df):
    ### rename cells ###
    cell_name = cell_df[["name"]]
    cell_name.loc[:, ["new_cellname"]] = ["cell" + str(i) for i in range(cell_name.shape[0])]
    pin_df = pin_df.merge(cell_name.rename(columns={"name":"cellname"}), on="cellname", how="left")
    idx = pin_df[pd.isna(pin_df.new_cellname)].index

    port_names = ["port" + str(i) for i in range(len(idx))]
    pin_df.loc[idx, "new_cellname"] = port_names
    cell_df["new_cellname"] = cell_name.new_cellname.values
    return cell_df, pin_df

### rename nets with net0, net1, ... and update the net names in pin_df
def rename_nets(net_df, pin_df):
    ### rename nets ###
    net_name = net_df[["name"]]
    net_name.loc[:, ["new_netname"]] = ["net" + str(i) for i in range(net_name.shape[0])]
    pin_df = pin_df.merge(net_name.rename(columns={"name":"netname"}), on="netname", how="left")
    return net_df, pin_df

### 1) get edge src and tar ids and 2) generate edge_df by merging all edges
def generate_edge_df(pin_df, cell_df, net_df, pin_edge_df, cell_edge_df, net_edge_df, net_cell_edge_df, cell2cell_edge_df):
    edge_id = pd.concat([pin_df.loc[:,["id", "name"]], cell_df.loc[:,["id", "name"]], net_df.loc[:,["id", "name"]]], ignore_index=True)
    src = edge_id.copy()
    src = src.rename(columns={"id":"src_id", "name":"src"})
    tar = edge_id.copy()
    tar = tar.rename(columns={"id":"tar_id", "name":"tar"})

    pin_edge_df = pin_edge_df.merge(src, on="src", how="left")
    pin_edge_df = pin_edge_df.merge(tar, on="tar", how="left")

    cell_edge_df = cell_edge_df.merge(src, on="src", how="left")
    cell_edge_df = cell_edge_df.merge(tar, on="tar", how="left")

    net_edge_df = net_edge_df.merge(src, on="src", how="left")
    net_edge_df = net_edge_df.merge(tar, on="tar", how="left")

    net_cell_edge_df = net_cell_edge_df.merge(src, on="src", how="left")
    net_cell_edge_df = net_cell_edge_df.merge(tar, on="tar", how="left")

    cell2cell_edge_df = cell2cell_edge_df.merge(src, on="src", how="left")
    cell2cell_edge_df = cell2cell_edge_df.merge(tar, on="tar", how="left")

    # drop illegal edges
    print("pin_edge shape: ")
    print(pin_edge_df.shape)
    idx = pin_edge_df[pd.isna(pin_edge_df.src_id)].index
    pin_edge_df = pin_edge_df.drop(idx)
    print(pin_edge_df.shape)
    idx = pin_edge_df[pd.isna(pin_edge_df.tar_id)].index
    pin_edge_df = pin_edge_df.drop(idx)
    print(pin_edge_df.shape)

    print("cell_edge shape: ")
    print(cell_edge_df.shape)
    idx = cell_edge_df[pd.isna(cell_edge_df.src_id)].index
    cell_edge_df = cell_edge_df.drop(idx)
    print(cell_edge_df.shape)
    idx = cell_edge_df[pd.isna(cell_edge_df.tar_id)].index
    cell_edge_df = cell_edge_df.drop(idx)
    print(cell_edge_df.shape)

    print("net_edge shape: ")
    print(net_edge_df.shape)
    idx = net_edge_df[pd.isna(net_edge_df.src_id)].index
    net_edge_df = net_edge_df.drop(idx)
    print(net_edge_df.shape)
    idx = net_edge_df[pd.isna(net_edge_df.tar_id)].index
    net_edge_df = net_edge_df.drop(idx)
    print(net_edge_df.shape)

    print("net_cell_edge shape: ")
    print(net_cell_edge_df.shape)
    idx = net_cell_edge_df[pd.isna(net_cell_edge_df.src_id)].index
    net_cell_edge_df = net_cell_edge_df.drop(idx)
    print(net_cell_edge_df.shape)
    idx = net_cell_edge_df[pd.isna(net_cell_edge_df.tar_id)].index
    net_cell_edge_df = net_cell_edge_df.drop(idx)
    print(net_cell_edge_df.shape)

    print("cell2cell_edge shape: ")
    print(cell2cell_edge_df.shape)
    idx = cell2cell_edge_df[pd.isna(cell2cell_edge_df.src_id)].index
    cell2cell_edge_df = cell2cell_edge_df.drop(idx)
    print(cell2cell_edge_df.shape)
    idx = cell2cell_edge_df[pd.isna(cell2cell_edge_df.tar_id)].index
    cell2cell_edge_df = cell2cell_edge_df.drop(idx)
    print(cell2cell_edge_df.shape)

    edge_df = pd.concat([pin_edge_df.loc[:,["src_id", "tar_id"]], cell_edge_df.loc[:,["src_id", "tar_id"]], \
                     net_edge_df.loc[:,["src_id", "tar_id"]], net_cell_edge_df.loc[:,["src_id", "tar_id"]], cell2cell_edge_df.loc[:,["src_id", "tar_id"]]], ignore_index=True)

    return pin_edge_df, cell_edge_df, net_edge_df, net_cell_edge_df, cell2cell_edge_df, edge_df

### get the largest component's id
def get_largest_idx(hist):
    largest_idx = -1
    largest_cnt = 0
    labels = []
    for i in range(len(hist)):
        if hist[i] > largest_cnt:
            largest_cnt = hist[i]
            largest_idx = i
        if hist[i] > 2000:
            labels.append(i)
    return largest_idx

### get large components' ids
def get_large_components(hist, th=2000):
    labels = []
    for i in range(len(hist)):
        if hist[i] > th:
            labels.append(i)
            print(i, hist[i])
    return labels

### generate subgraph
def get_subgraph(g_old, v_mask, e_mask):
    u = GraphView(g_old, vfilt=v_mask, efilt=e_mask)
    print("connected component graph: num of edge; num of nodes", u.num_vertices(), u.num_edges())
    ### check whether subgraph is connected and is DAG
    _, hist2 = label_components(u, directed=False)
    print(hist2, is_DAG(u))
    return u

### generate cell graph from pin graph
def get_cell_graph(pin_g, pin_cellid, g, e_type, e_id):
    ### new mask cell graph: pre-opt
    u_pins = pin_g.get_vertices()
    u_cells = pin_cellid[u_pins]
    u_cells = np.unique(u_cells).astype(int)
    print(u_cells.shape)

    # add cell2cell edge
    v_mask_cell = g.new_vp("bool")
    e_mask_cell = g.new_ep("bool")
    v_mask_cell.a[u_cells] = True

    e_ar = g.get_edges(eprops=[e_type, e_id])
    mask = e_ar[:,2]==4 # edge type == 4: cell2cell
    e_ar = e_ar[mask]
    e_src = e_ar[:,0]
    e_tar = e_ar[:,1]
    e_mask = (v_mask_cell.a[e_src] == True) & (v_mask_cell.a[e_tar] == True)
    e_mask_cell.a[e_ar[:,-1][e_mask]] = True
    print("num of edges to add", e_mask.sum())
    print("num of edges", e_mask_cell.a.sum())

    ### construct and check u_cell_g
    u_cell_g = get_subgraph(g, v_mask_cell, e_mask_cell)
    return u_cells, u_cell_g

### generate cell graph from cell ids
def get_cell_graph_from_cells(u_cells, g, e_type, e_id):
    u_cells = np.unique(u_cells).astype(int)
    print(u_cells.shape)

    # add cell2cell edge
    v_mask_cell = g.new_vp("bool")
    e_mask_cell = g.new_ep("bool")
    v_mask_cell.a[u_cells] = True

    e_ar = g.get_edges(eprops=[e_type, e_id])
    mask = e_ar[:,2]==4 # edge type == 4: cell2cell
    e_ar = e_ar[mask]
    e_src = e_ar[:,0]
    e_tar = e_ar[:,1]
    e_mask = (v_mask_cell.a[e_src] == True) & (v_mask_cell.a[e_tar] == True)
    e_mask_cell.a[e_ar[:,-1][e_mask]] = True
    print("num of edges to add", e_mask.sum())
    print("num of edges", e_mask_cell.a.sum())

    ### construct and check u_cell_g
    u_cell_g = get_subgraph(g, v_mask_cell, e_mask_cell)
    return u_cell_g