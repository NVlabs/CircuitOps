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
import sys, os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn import preprocessing
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../src/")
from circuitops_api import *

def generate_dataset(IR_path):

    # Generate LPG
    circuit_data = CircuitData(IR_path)

    # Extract required dataframes from master class
    pin_props = circuit_data.pin_props
    pin_pin_edge = circuit_data.pin_pin_edge
    cell_props = circuit_data.cell_props
    net_props = circuit_data.net_props

    circuit_graph = circuit_data.graph

    N_pin, _ = pin_props.df.shape
    N_cell, _ = cell_props.df.shape
    N_net, _ = net_props.df.shape
    
    ### add cell id to pin_df
    pin_props.df = pin_props.df.merge(cell_props.df[["cell_name", "id"]].rename(columns={"id": "cell_id"}), on="cell_name", how="left")
    idx = pin_props.df[pd.isna(pin_props.df.cell_id)].index
    pin_props.df.loc[idx, ["cell_id"]] = pin_props.df.loc[idx, ["id"]].to_numpy()
    
    ### add net id to pin_df
    pin_props.df = pin_props.df.merge(net_props.df[["net_name", "id"]].rename(columns={"id": "net_id"}), on="net_name", how="left")
    
    ### generate pin-pin graph ###
    pin_graph = circuit_graph.filter_edges("pin_pin")
    print("pin graph: num of nodes, num of edges: ", pin_graph.graph.num_vertices(), pin_graph.graph.num_edges())
    
    ### threshold to remove small components in the netlist
    cell_cnt_th = 200
    
    ### get the large components
    components = pin_graph.get_connected_components()
    large_components = []

    for g1 in components:
        if g1.num_vertices() > cell_cnt_th:
            large_components.append(g1)

    pin_graph_only_large_components = pin_graph.merge_graphs(large_components)
        
    ### mark selected pins
    pin_props.df["selected"] = pin_graph_only_large_components.graph.vp["vertex_mask"].a[0:N_pin]
    circuit_data.pin_props = pin_props
    return circuit_data


def generate_ML_data(circuit_data):
    #Gathering dataset for training and testing
    pin_df = circuit_data.pin_props.df
    cell_df = circuit_data.cell_props.df
    libcell_df = circuit_data.libcell_props.df
    pin_pin_df = circuit_data.pin_pin_edge.df

    ### get selected pins ###
    selected_pin_df = pin_df[(pin_df.selected == True) & (pin_df.is_buf == False) & (pin_df.is_inv == False)]
    ### get driver pins and related properties ###
    driver_pin = selected_pin_df[selected_pin_df.dir==0]
    driver_pin_info = driver_pin.loc[:, ["id", "net_id", "x", "y", "cell_id", "pin_rise_arr", "pin_fall_arr"]]
    driver_pin_info = driver_pin_info.rename(columns={"id":"driver_pin_id", "x":"driver_x", "y":"driver_y", "cell_id":"driver_id", "pin_rise_arr":"driver_risearr", "pin_fall_arr":"driver_fallarr"})
    cell_df = cell_df.merge(libcell_df,on="libcell_name",how="left")
    cell_info = cell_df.loc[:, ["id", "libcell_id", "fo4_delay", "fix_load_delay"]]
    cell_info = cell_info.rename(columns={"id":"driver_id"})
    driver_pin_info = driver_pin_info.merge(cell_info, on="driver_id", how="left")
    
    ### get sink pins and related properties ###
    sink_pin = selected_pin_df[selected_pin_df.dir==1]
    sink_pin_info = sink_pin.loc[:, ["id", "x", "y", "input_pin_cap", "net_id", "cell_id", "pin_rise_arr", "pin_fall_arr"]]
    sink_pin_info = sink_pin_info.merge(driver_pin_info, on="net_id", how="left")
    
    sink_pin_info.x = sink_pin_info.x - sink_pin_info.driver_x
    sink_pin_info.y = sink_pin_info.y - sink_pin_info.driver_y
    idx = sink_pin_info[pd.isna(sink_pin_info.driver_x)].index
    sink_pin_info = sink_pin_info.drop(idx)
    
    ### get context sink locations ###
    sink_loc = sink_pin_info.groupby('net_id', as_index=False).agg({'x': ['mean', 'min', 'max', 'std'], 'y': ['mean', 'min', 'max', 'std'], 'input_pin_cap': ['sum']})
    sink_loc.columns = ['_'.join(col).rstrip('_') for col in sink_loc.columns.values]
    sink_loc['x_std'] = sink_loc['x_std'].fillna(0)
    sink_loc['y_std'] = sink_loc['y_std'].fillna(0)
    
    ### merge information and rename ###
    sink_pin_info = sink_pin_info.merge(sink_loc, on="net_id", how="left")
    sink_pin_info = sink_pin_info.rename(columns={"libcell_id":"driver_libcell_id", "fo4_delay":"driver_fo4_delay", "fix_load_delay":"driver_fix_load_delay", \
                                                  "x_mean": "context_x_mean", "x_min": "context_x_min", "x_max": "context_x_max", "x_std": "context_x_std", \
                                                 "y_mean": "context_y_mean", "y_min": "context_y_min", "y_max": "context_y_max", "y_std": "context_y_std", \
                                                 "pin_rise_arr":"sink_risearr", "pin_fall_arr":"sink_fallarr"})
    sink_pin_info["sink_arr"] = sink_pin_info[["sink_risearr", "sink_fallarr"]].min(axis=1)
    sink_pin_info["driver_arr"] = sink_pin_info[["driver_risearr", "driver_fallarr"]].min(axis=1)
    
    ### get cell arc delays ###
    cell_arc = pin_pin_df.groupby('tar_id', as_index=False).agg({'arc_delay': ['mean', 'min', 'max']})
    cell_arc.columns = ['_'.join(col).rstrip('_') for col in cell_arc.columns.values]
    cell_arc = cell_arc.rename(columns={"tar_id":"driver_pin_id"})
    sink_pin_info = sink_pin_info.astype({"driver_pin_id":"int"})
    sink_pin_info = sink_pin_info.merge(cell_arc, on="driver_pin_id", how="left")
    idx = sink_pin_info[pd.isna(sink_pin_info.arc_delay_mean)].index
    sink_pin_info = sink_pin_info.drop(idx)
    
    ### get net delay ###
    cell_arc = cell_arc.rename(columns={"driver_pin_id":"id", "arc_delay_mean":"net_delay_mean", "arc_delay_min":"net_delay_min", "arc_delay_max":"net_delay_max"})
    sink_pin_info = sink_pin_info.merge(cell_arc, on="id", how="left")
    
    ### stage delay = driver cell arc delay + net delay ###
    sink_pin_info["stage_delay"] = sink_pin_info.arc_delay_max + sink_pin_info.net_delay_max
    
    print("Reference data frame")
    print(sink_pin_info)
    
    # x, y: distance between driver and the target sink
    # cap, cap_sum: sink capacitance
    # driver_fo4_delay driver_fix_load_delay: driving strength of the driver cell
    # context_x_mean", context_x_min, context_x_max, context_x_std, context_y_mean, context_y_min, context_y_max, context_y_std: Context sink locations
    features = sink_pin_info.loc[:, ["x", "y", "input_pin_cap", "input_pin_cap_sum", "driver_fo4_delay", "driver_fix_load_delay", \
                                     "context_x_mean", "context_x_min", "context_x_max", "context_x_std", \
                                    "context_y_mean", "context_y_min", "context_y_max", "context_y_std"]].to_numpy().astype(float)
    labels = sink_pin_info.loc[:, ["stage_delay"]].to_numpy().astype(float)
    
    features = preprocessing.normalize(features, axis=0)
    labels = preprocessing.normalize(labels, axis=0)
    labels = labels.reshape([-1,])
    
    nb_samples = features.shape[0]
    nb_feat = features.shape[1]
    
    train_x, test_x, train_y, test_y = train_test_split(features, labels, test_size=0.05)
    
    return train_x, test_x, train_y, test_y

def train_model(train_x, train_y):
    nb_train_samples = train_x.shape[0]
    nb_test_samples = train_y.shape[0]
    
    print("Training Machine Learning Model")
    
    nb_estim = 500
    max_feat = 0.5
    model = RandomForestRegressor(n_estimators=nb_estim, max_features=max_feat)
    model.fit(train_x, train_y)
    return model

def evaluate_model(model, train_x, train_y, test_x, test_y):
    pred = model.predict(train_x)
    
    plt.figure()
    plt.scatter(pred, train_y, label = "Training")

    pred = model.predict(test_x)
    plt.scatter(pred, test_y, label = "Testing")
    
    data_range = np.arange(min(np.min(train_y), np.min(test_y)), 
                           max(np.max(train_y), np.max(test_y)),
                           0.005
                          )
    plt.plot(data_range, data_range, label="Reference")
    
    plt.title("Accuracy on trianing data and testing data")
    
    plt.legend()
    plt.xlabel("Reference")
    plt.ylabel("Predicted")
    plt.show()

if __name__ == "__main__":

     # Set the Circuitops path
    cops_path = "/home/vgopal18/Circuitops/CircuitOps/IRs/"
    design_name = "gcd"
    platform = "nangate45"

    IR_path = f"{cops_path}/{platform}/{design_name}/"
    
    circuit_data = generate_dataset(IR_path)

    X_train, X_test, Y_train, Y_test = generate_ML_data(circuit_data)

    model = train_model(X_train, Y_train)

    evaluate_model(model, X_train, Y_train, X_test, Y_test)
