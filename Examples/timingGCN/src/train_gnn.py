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

import time
import argparse
import tee
import pickle as pk
import random
import numpy as np
from sklearn.metrics import r2_score
import dgl
import torch
import torch.nn.functional as F
from model import TimingGCN
import matplotlib.pyplot as plt

def test(model, data_train):
    model.eval()
    with torch.no_grad():
        def test_dict(data):
            for k, (g, ts) in data.items():
                torch.cuda.synchronize()
                time_s = time.time()
                pred = model(g, ts, groundtruth=False)[2]
                torch.cuda.synchronize()
                time_t = time.time()
                truth = g.ndata['n_tsrf']
                train_mask = g.ndata['train_mask'].type(torch.bool)
                r2 = r2_score(pred[train_mask].cpu().numpy().reshape(-1),
                              truth[train_mask].cpu().numpy().reshape(-1))
                # notice: there is a typo in the parameter order of r2 calculator.
                # please see https://github.com/TimingPredict/TimingPredict/issues/7.
                # for exact reproducibility of experiments in paper, we will not directly fix the typo here.
                # the experimental conclusions are not affected.
                # r2 = r2_score(pred.cpu().numpy().reshape(-1),
                #               truth.cpu().numpy().reshape(-1))
                print('{:15} r2 {:1.5f}, time {:2.5f}'.format(k, r2, time_t - time_s))
                # print('{}'.format(time_t - time_s + ts['topo_time']))
        print('======= Training dataset ======')
        test_dict(data_train)

def train_model(model, data_dir):
    with open(f'{data_dir}/data_train.pk', 'rb') as pkf:
        data_train = pk.load(pkf)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)
    batch_size = 1
    
    loss_tsrf_all = []
    for e in range(5000):
        model.train()
        train_loss_tot_tsrf = 0
        optimizer.zero_grad()
    
        for k, (g, ts) in random.sample(sorted(data_train.items()), batch_size):
    
            if e < 100:
                _, _, pred_tsrf = model(g, ts, groundtruth=True)
            else:
                _, _, pred_tsrf = model(g, ts, groundtruth=False)
    
            train_mask = g.ndata['train_mask'].type(torch.bool)
            
            loss_tsrf = F.mse_loss(pred_tsrf[train_mask], g.ndata['n_tsrf'][train_mask])
            train_loss_tot_tsrf += loss_tsrf.item()
            loss_tsrf.backward()
    
        loss_tsrf_all.append(train_loss_tot_tsrf)
        if e % 10 == 9:
            print(f'Ep {e}, Trn Loss {np.mean(loss_tsrf_all[-10:])}')
    
        if e % 100 == 0:
            test(model, data_train)
    
        optimizer.step()
    plt.plot(loss_tsrf_all[:100], label='train loss (w/ ground truth)')
    plt.yscale('log')
    plt.xlabel('epoch')
    plt.ylabel('loss')
    plt.show()
    return model

if __name__ == "__main__":
    data_dir = f"{ROOT_DIR}/data/"
    model = TimingGCN()
    model.cuda()
    model = train_model(model,data_dir)
