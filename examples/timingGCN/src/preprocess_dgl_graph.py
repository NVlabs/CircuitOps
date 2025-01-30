#!/usr/bin/env python
# coding: utf-8
# SPDX-FileCopyrightText: Copyright (c) 2022 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, sys
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))+"/../"
libparser_dir = ""
sys.path.append(ROOT_DIR)
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../src/")

import numpy as np
import pandas as pd
import pickle as pk
import graph_tool as gt
import matplotlib.pyplot as plt
import dgl
import networkx as nx
import torch
import time

from circuitops_api import *

# identical function taken from data_graph.py
def gen_topo(g_hetero):
    torch.cuda.synchronize()
    time_s = time.time()
    na, nb = g_hetero.edges(etype='net_out', form='uv')
    ca, cb = g_hetero.edges(etype='cell_out', form='uv')
    g = dgl.graph((torch.cat([na, ca]).cpu(), torch.cat([nb, cb]).cpu()))
    topo = dgl.topological_nodes_generator(g)
    ### inspect the topography!
    g.ndata['fanout'] = g_hetero.ndata['nf'][:, 1].cpu()
    for li, nodes in enumerate(topo):
        # print(f'level {li}, # nodes = {len(nodes)}')
        # print(g.ndata['fanout'][nodes.numpy()])
        assert (li % 2 == 0 and (g.ndata['fanout'][nodes] == 0).sum() == 0) or (li % 2 == 1 and (g.ndata['fanout'][nodes] == 1).sum() == 0)
    assert len(topo) % 2 == 0
    ret = [t.cuda() for t in topo]
    torch.cuda.synchronize()
    time_e = time.time()
    return ret, time_e - time_s

def generate_ml_data(gs):
    data = {}
    # data preprocessing
    for design_name, des_gs in gs.items():
        for gi, g in enumerate(des_gs):
            g.nodes['node'].data['nf'] = g.nodes['node'].data['nf'].type(torch.float32)
            g.edges['cell_out'].data['ef'] = g.edges['cell_out'].data['ef'].type(torch.float32)
            g.edges['net_out'].data['ef'] = g.edges['net_out'].data['ef'].type(torch.float32)
            g.edges['net_in'].data['ef'] = g.edges['net_in'].data['ef'].type(torch.float32)
            g.ndata['n_tsrf'] = torch.stack([g.ndata['pin_tran'], g.ndata['pin_slack'], g.ndata['pin_rise_arr'], g.ndata['pin_fall_arr']], axis=1).type(torch.float32)
            g = g.to('cuda')
            # print(f'{design_name}, {gi+1}/{len(des_gs)}')
            topo, topo_time = gen_topo(g)
            ts = {'input_nodes': (g.ndata['nf'][:, 1] < 0.5).nonzero().flatten().type(torch.int32),
                'output_nodes': (g.ndata['nf'][:, 1] > 0.5).nonzero().flatten().type(torch.int32),
                'output_nodes_nonpi': torch.logical_and(g.ndata['nf'][:, 1] > 0.5, g.ndata['nf'][:, 0] < 0.5).nonzero().flatten().type(torch.int32),
                'pi_nodes': torch.logical_and(g.ndata['nf'][:, 1] > 0.5, g.ndata['nf'][:, 0] > 0.5).nonzero().flatten().type(torch.int32),
                'po_nodes': torch.logical_and(g.ndata['nf'][:, 1] < 0.5, g.ndata['nf'][:, 0] > 0.5).nonzero().flatten().type(torch.int32),
                'endpoints': (g.ndata['is_endpoint'] > 0.5).nonzero().flatten().type(torch.long),
                'topo': topo,
                'topo_time': topo_time}
            # set nans to zero
            g.ndata['nf'][torch.isnan(g.ndata['nf'])] = 0
            g.ndata['n_tsrf'][torch.isnan(g.ndata['n_tsrf'])] = 0
            # normalize
            g.ndata['nf'][:,2:] = (g.ndata['nf'][:,2:] - g.ndata['nf'][:,2:].mean(axis=0)) / g.ndata['nf'][:,2:].std(axis=0)
            g.ndata['n_tsrf'] = (g.ndata['n_tsrf'] - g.ndata['n_tsrf'].mean(axis=0)) / g.ndata['n_tsrf'].std(axis=0)    
            data[f'{design_name}_{gi}'] = g, ts
            # just for report
            print(gi, design_name, len(g.ndata['nf']), g.ndata['train_mask'].sum().item(), len(g.edata['ef'][('node', 'cell_out', 'node')]), len(g.edata['ef'][('node', 'net_out', 'node')]), len(topo))
    
    data_train = {k: t for k, t in data.items()}
    data_test = data_train
    
    print('[node data] ( = dstdata)')
    for nkey, ndat in g.ndata.items():
        assert type(ndat) == torch.Tensor, 'Type must be torch.Tensor'
        print(f'{nkey:22s} {ndat.shape}')
        if nkey == 'nf':
            nf = ndat
            for fkey, frange in [('is_prim IO', [0,1]), ('fanout(1) or in(0)', [1,2]), ('dis to tlrb', [2,6]), ('RF cap', [6,8])]:
                print(f'  {fkey:20s} {ndat[:, frange[0]:frange[1]].shape}')
    print()
    
    print('[edge data]')
    for ekey, edat in g.edata.items():
        assert type(edat) == dict, 'Type must be dict'
        print(f'{ekey}:')
        for edat_key, edat_dat in edat.items():
            print(f'  {f"{edat_key}":30s} {edat_dat.shape}')

    return data_train, data_test

if __name__ == "__main__":
    # load all datasets in design_names = ['NV_NVDLA_partition_m', 'NV_NVDLA_partition_p', 'ariane136', 'mempool_tile_wrap']
    design_names = ['gcd']
    cops_path = "/home/vgopal18/Circuitops/CircuitOps/IRs/"
    platform = "asap7"

    data_dir = f"{ROOT_DIR}/data/" 
    # read all the graph for all the designs
    gs = {}
    for design_name in design_names:
        gs[design_name] = dgl.load_graphs(f'{data_dir}/graph.dgl')[0]

    data_train, data_test = generate_ml_data(gs)
    with open(f'{data_dir}/data_train.pk', 'wb') as pkf:
        pk.dump(data_train, pkf)
    with open(f'{data_dir}/data_test.pk', 'wb') as pkf:
        pk.dump(data_test, pkf)
