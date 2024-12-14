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

from circuitops_api import *
from LUT_construction import *
from construct_dgl import *
from preprocess_dgl_graph import *
from train_gnn import *
from model import TimingGCN

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Options to run timingGCN, give design name and tech node.")
    parser.add_argument("-d", default="gcd", help="Give the design name")
    parser.add_argument("-t", default="asap7", help="Give the technology node")
    parser.add_argument("-design_path", default="/home/vgopal18/OpenROAD/OpenROAD-flow-scripts/flow/results/asap7/gcd/base/", help="Give the path to the folder contianing .v and .def files of the design")
    args = parser.parse_args()

    # Set the Circuitops path
    cops_path = os.path.dirname(os.path.abspath(__file__))+"/../../../IRs/"
    design_name = args.d
    design_names = [design_name]
    platform = args.t
    IR_path = f"{cops_path}/{platform}/{design_name}/"
    design_path = args.design_path

    construct_LUT_files(IR_path, design_path)

    print("Constructing DGL graph")
    data_dir = f"{ROOT_DIR}/data/"
    construct_dgl_main(data_dir)

    print("Preprocessing DGL graph")
    gs = {}
    for design_name in design_names:
        gs[design_name] = dgl.load_graphs(f'{data_dir}/graph.dgl')[0]

    data_train, data_test = generate_ml_data(gs)

    with open(f'{data_dir}/data_train.pk', 'wb') as pkf:
        pk.dump(data_train, pkf)
    with open(f'{data_dir}/data_test.pk', 'wb') as pkf:
        pk.dump(data_test, pkf)
    
    print("Training model")
    model = TimingGCN()
    model.cuda()
    model = train_model(model, data_dir)
