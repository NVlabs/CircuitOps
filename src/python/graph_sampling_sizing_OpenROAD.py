import sys
import re

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import copy

from numpy.random import *
import time
from numba import jit
import pickle

import dgl
import torch


def main(data_dir, design, mcmm, num_samples, path_file):
    data_root = "/home/scratch.gpradipta_mobile/ml4eda/data_RJ/" + design + '/'
    cell_edge_path = data_root + design + "_cell_edge.csv"
    cell_path = data_root + design + "_cell.csv"
    net_edge_path = data_root + design + "_net_edge.csv"
    net_path = data_root + design + "_net.csv"
    pin_edge_path = data_root + design + "_pin_edge.csv"
    pin_path = data_root + design + "_pin.csv"
    net_cell_edge_path = data_root + design + "_net_cell_edge.csv"
    cell2cell_edge_path = data_root + design + "_cell2cell_edge.csv"

    mcmm_cell_path = data_root + design + "_" + mcmm + "_cell.csv"
    mcmm_net_path = data_root + design + "_" + mcmm + "_net.csv"
    mcmm_pin_path = data_root + design + "_" + mcmm + "_pin.csv"

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

    HPWL = pin_df.groupby('netname', as_index=False).agg({'x': ['mean', 'min', 'max'], 'y': ['mean', 'min', 'max']})
    HPWL.columns = ['_'.join(col).rstrip('_') for col in HPWL.columns.values]
    HPWL["HPWL"] = 0.5*(HPWL.x_max - HPWL.x_min + HPWL.y_max - HPWL.y_min)
    net_df = net_df.merge(HPWL.rename(columns={"netname":"name"}), on="name", how="left")

    s = pin_df.groupby('netname', as_index=False).size()
    net_df = net_df.merge(s.rename(columns={"netname":"name"}), on="name", how="left")

    mcmm_pin_df = pd.read_csv(mcmm_pin_path)
    mcmm_cell_df = pd.read_csv(mcmm_cell_path)
    mcmm_net_df = pd.read_csv(mcmm_net_path)
    print("mcmm_pin_df.shape: ", mcmm_pin_df.shape)
    print("mcmm_cell_df.shape: ", mcmm_cell_df.shape)
    print("mcmm_net_df.shape: ", mcmm_net_df.shape)

    fo4_df = fo4_df.merge(median_delay_df.loc[:,["cell_id", "num_refs", "mdelay"]], on="cell_id", how="left")
    fo4_df = fo4_df.reset_index()

    pin_df = pin_df.merge(mcmm_pin_df, on="name", how="left")
    cell_df = cell_df.merge(mcmm_cell_df, on="name", how="left")
    net_df = net_df.merge(mcmm_net_df, on="name", how="left")

    ### processing fo4 table
    fo4_df["group_id"] = pd.factorize(fo4_df.cell_id)[0] + 1
    fo4_df["HVT"] = fo4_df.cell.str.contains("HVT")
    fo4_df["CK"] = fo4_df.cell.str.contains("CK")
    fo4_df["libcell_id"] = range(fo4_df.shape[0])
    libcell_np = fo4_df.to_numpy()

    ### assign cell size class
    fo4_df["size_class"] = 0
    fo4_df["size_class2"] = 0
    fo4_df["size_cnt"] = 0
    class_cnt = 50
    for i in range(fo4_df.group_id.min(), fo4_df.group_id.max()+1):
        temp = fo4_df.loc[fo4_df.group_id==i, ["group_id", "cell_delay_fixed_load"]]
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

    # pin_edge_df = pin_edge_df.dropna()
    pin_df["dir"] = (pin_df["dir"] == "input")

    cell_fo4 = fo4_df.loc[:,["cell", "cell_delay", "cell_delay_fixed_load", "worst_incap", "group_id", "HVT", "CK", "libcell_id", "size_class", "size_class2", "size_cnt", "mdelay"]]
    cell_fo4 = cell_fo4.rename(columns={"cell":"ref"})
    cell_df = cell_df.merge(cell_fo4, on="ref", how="left")
    cell_df["libcell_id"] = cell_df["libcell_id"].fillna(-1)

    cell_type_df = cell_df.loc[:,["name", "is_buf", "is_inv", "is_seq", "libcell_id"]]
    cell_type_df = cell_type_df.rename(columns={"name":"cellname"})

    pin_df = pin_df.merge(cell_type_df, on="cellname", how="left")
    pin_df["libcell_id"] = pin_df["libcell_id"].fillna(-1)

    pin_df["is_buf"] = pin_df["is_buf"].fillna(False)
    pin_df["is_inv"] = pin_df["is_inv"].fillna(False)
    pin_df["is_seq"] = pin_df["is_seq"].fillna(False)

    pin_df.loc[pin_df.cap == 0.0, ["cap"]] = -1.0
    pin_df.loc[pin_df.maxcap > 10, ["maxcap"]] = -1.0

    pin_names = pin_df["name"].to_list()
    pin_isport = pin_df["is_port"].to_list()
    N = len(pin_names)
    pin_short_names = []
    for i in range(N):
        if pin_isport[i]:
            pin_short_names.append(pin_names[i])
        else:
            name = pin_names[i].split("/")[-1]
            pin_short_names.append(name)
    pin_df["short_name"] = pin_short_names
    pin_df['node_id'] = pin_df.index

    # temp_df = cell_df.loc[cell_df.num_ref==1, ["mdelay"]]
    # cell_df.loc[cell_df.num_ref==1, ["cell_delay"]] = temp_df["mdelay"]

    cell_df["area"] = (cell_df.x1 - cell_df.x0)*(cell_df.y1 - cell_df.y0)
    cell_df["x"] = 0.5*(cell_df.x0 + cell_df.x1)
    cell_df["y"] = 0.5*(cell_df.y0 + cell_df.y1)

    cell_df["group_id"] = cell_df["group_id"].fillna(0)
    cell_df["HVT"] = cell_df["HVT"].fillna(False)
    cell_df["CK"] = cell_df["CK"].fillna(False)

    print("pin_df.shape: ", pin_df.shape)
    print("cell_df.shape: ", cell_df.shape)
    print("net_df.shape: ", net_df.shape)
    print("pin_edge_df.shape: ", pin_edge_df.shape)
    print("cell_edge_df.shape: ", cell_edge_df.shape)
    print("net_edge_df.shape: ", net_edge_df.shape)
    print("net_cell_edge_df.shape: ", net_cell_edge_df.shape)

    ### get dimensions
    N_pin, N_f_pin = pin_df.shape
    N_cell, N_f_cell = cell_df.shape
    N_net, N_f_net = net_df.shape

    # DGL Graph construction
    G = dgl.DGLGraph()
    G.add_nodes(len(pin_df))

    edge_index = pin_edge_df.loc[((pin_edge_df.src.isin(pin_df.name)) &
                           (pin_edge_df.tar.isin(pin_df.name)))]

    edges_df = pin_edge_df.loc[edge_index.index]

    pin_id_df = pin_df[['name', 'node_id']].set_index('name')

    edges_df['src_id'] = pin_id_df.loc[edges_df['src'].tolist()].node_id.tolist()
    edges_df['tar_id'] = pin_id_df.loc[edges_df['tar'].tolist()].node_id.tolist()

    edges_id = torch.tensor(edges_df[['src_id', 'tar_id']].to_numpy())

    G.add_edges(edges_id[:,0], edges_id[:,1])

    # Calculating weight for each edges
    slack_df = pin_df[['name', 'slack']].set_index('name')

    slacks = slack_df.loc[edges_df['tar'].tolist()].to_numpy()

    slacks = np.clip(slacks, a_min=None, a_max= 100)
    P = np.exp(-50*slacks)+0.001

    G.edata['weight'] = torch.from_numpy(P)

    start_ids = pin_df.index[pin_df.is_start==1].to_numpy()
    start_prob = pin_df.slack[pin_df.is_start==1].to_numpy()
    start_prob = np.clip(start_prob, a_min=None, a_max= 100)
    start_prob = np.exp(-50*start_prob)+0.001
    start_prob = start_prob / np.sum(start_prob)

    start_ids = np.random.choice(start_ids, num_samples)

    paths, _ = dgl.sampling.random_walk(G,  nodes=start_ids, length=50)

    # Cell name, Ref name, Gate type, X, Y, Net HPWL, Num refs, Num fanouts
    # Pin-to-pin distance, Wire cap, Pin-to-pin arc delay, Num reachable endpoints
    # Median FO4 delay

    timing_data = []
    for path in paths:
        if len(np.unique(path)) == 2:
            continue

        skip = False
        path_features = []

        path_start_arrival = 0.0
        path_slack = 0.0
        path_total_delay = 0.0
        tot_net_delay = 0.0

        for idx, pin in enumerate(path):
            if pin == -1:
                break

            data = pin_df.iloc[int(pin)]
            # Skip input of comb cell
            if not (data.is_end==1 or \
                      data.is_start==1) and \
                      data.dir == True:
                continue

            cellname = data.cellname

            refname = data['name']
            # refname for comb cells
            if data.is_port == 1:
                refname = 'NA'
            elif not(data.is_end==1 or                     data.is_start==1):
                refname = cell_df.ref[cell_df['name'] == cellname].item()

            num_refs = 1
            mdelay = 0.0
            reach_end = 0

            fo4_data = fo4_df[fo4_df['cell'] == refname]

            if data.is_port == 1:
                gate_type = 'NA'
            elif data.is_seq == 1:
                gate_type = cellname
            else:
                if len(fo4_data) > 0:
                    gate_type = fo4_data['cell_id'].item()
                    num_refs = fo4_data['num_refs'].item()
                    mdelay = fo4_data.mdelay.item()
                else:
                    gate_type = 'NA'
                    num_refs = 1
                    mdelay = 0.0

            arc_delay = 0.0
            x, y = data.x, data.y
            if data.is_start == 1:
                next_pin_data = pin_df.iloc[int(path[idx+1])]
                next_x, next_y = next_pin_data.x, next_pin_data.y
                path_start_arrival = np.clip(data.arr, a_min=-100, a_max= 100)
            elif data.is_end == 1 or idx >= len(path)-2:
                next_x, next_y = x, y
                path_arrival = np.clip(data.arr, a_min=-100, a_max= 100)
                path_slack = np.clip(path_slack, a_min=-100, a_max= 100)
                path_required = path_arrival - path_slack
            else:
                next_pin_data = pin_df.iloc[int(path[idx+2])]
                next_x, next_y = next_pin_data.x, next_pin_data.y

            arc_delay = round(np.clip(next_pin_data.arr,
                  a_min=-100, a_max= 100) - np.clip(data.arr,
                  a_min=-100, a_max= 100), 4)
            tot_net_delay += arc_delay

            net_data = net_df[net_df['name'] == data.netname]

            if len(net_data) > 0:
                hpwl = round(net_data.HPWL.item(),3)
                fanout = net_data.fanout.item()
                p2p_dist = round(abs(next_x - x) + abs(next_y - y), 3)
                wire_cap = net_data.net_cap.item()
            else:
                hpwl = 0.0
                fanout = 1
                p2p_dist = 1
                wire_cap = 1

            cur_feat = [cellname, refname, gate_type, x ,y, hpwl,
                  num_refs, fanout, p2p_dist, wire_cap, arc_delay,
                  reach_end]
            path_features.extend(cur_feat)

        eof = 'ENDOFPATH'
        path_corner = mcmm
        path_total_delay = path_arrival - path_start_arrival

        pct_net_delay = 0
        if path_total_delay > 0:
              pct_net_delay = tot_net_delay / path_total_delay * 100
        pct_cell_delay = 100 - pct_net_delay

        path_features.extend([eof, path_corner, round(path_slack,6),
                              round(path_arrival,6), round(path_required,6),
                              round(path_total_delay, 6), round(pct_cell_delay, 2),
                              round(pct_net_delay, 2)])

        timing_data.append(path_features)

    # Write into file
    with open(path_file, 'w') as path_out:
        for data in timing_data:
            conv = [str(d) for d in data]
            print(" ".join(conv), file=path_out)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str)
    parser.add_argument("--design", type=str)
    parser.add_argument("--mcmm", type=str)
    parser.add_argument("--num_samples", type=int, default=100000)
    parser.add_argument("--output", type=str, default='paths.test.txt')
    args = parser.parse_args()

    main(args.data_dir, args.design, args.mcmm, args.num_samples, args.output)