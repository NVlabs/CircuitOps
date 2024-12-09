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
from circuitops_classes import *
import dgl
import networkx as nx
import torch

def get_arcs(self, arc_type="net"):
    """
    Method of :class:`PinPinEdge`.
    Return a pin to pin edge class after filtering the arc_type

    :param arc_type: Required. Can be either cell or net
    :type arc_type: str
    :return: PinPinEdge class with filtered pin to pin df
    :rtype: PinPinEdge class 

    Example:
        cell_arcs_class = pin_pin_edge_class.filter_pin_arcs("cell")
    """
    pin_pin_df = self.df
    if (arc_type == "cell"):
        return PinPinEdge(pin_pin_df[pin_pin_df['is_net']==0])
    elif (arc_type == "net"):
        return PinPinEdge(pin_pin_df[pin_pin_df['is_net']==1])
    else:
        return None
PinPinEdge.get_arcs = get_arcs

def calculate_load_cap(self, output_pins, circuit_data):
    """
    Method of :class:`PinPinEdge`.
    Return a PinPinEdge class with output_cap column in its df

    :param output_pins: Required. List of pins for which load cap has to be calculated
    :type output_pins: List
    :param circuit_data: Required. Pass the circuit_data class object
    :type circuit_data: Class object of type CircuitData  
    :return: PinPinEdge class with output_cap column in df
    :rtype: PinPinEdge class

    Example:
        cell_arcs_class = pin_pin_edge_class.calculate_load_cap(output_pins, circuit_data)
    """
    pin_pin_df = self.df
    pin_df = circuit_data.pin_props.df
    
    pin_pin_df["output_cap"] = -1
    for pin_id in output_pins:
        sink_pins = pin_pin_df[(pin_pin_df["src_id"]==pin_id) & (pin_pin_df["is_net"]==1)]["tar_id"]
        if (len(sink_pins) == 0):
            #print("Warn: pin id ",pin_id," doesn't have sinks")
            continue
        total_cap = pin_df[pin_df['id'].isin(sink_pins)]['input_pin_cap']
        pin_pin_df.loc[pin_pin_df['tar_id']==pin_id,'output_cap'] = total_cap.sum()
    return PinPinEdge(pin_pin_df)
PinPinEdge.calculate_load_cap = calculate_load_cap

def merge_tran_cell(self, circuit_data):
    """
    Method of :class:`PinPinEdge`.
    Return a PinPinEdge class after merging tran and cell type columns to its df

    :param circuit_data: Required. Pass the circuit_data class object
    :type circuit_data: Class object of type CircuitData  
    :return: PinPinEdge class with pin_tran, cell_type, cell_type_coded columns in df
    :rtype: PinPinEdge class

    Example:
        mereged_class = pin_pin_edge_class.merge_tran_cell(circuit_data)
    """
    pin_pin_df = self.df
    cell_df = circuit_data.cell_props.df
    pin_df = circuit_data.pin_props.df
    
    pin_pin_df = pin_pin_df.merge(pin_df[['cell_name','pin_tran','id']].rename(columns={"id":"src_id"}), on="src_id", how="left")
    pin_pin_df = pin_pin_df.merge(cell_df[['cell_name','libcell_name']], on="cell_name", how="left")
    pin_pin_df["cell_type"] = pin_pin_df["libcell_name"].str.split('_').str[0]
    letter_to_int = {letter: idx for idx, letter in enumerate(sorted(pin_pin_df['cell_type'].unique()))}
    pin_pin_df['cell_type_coded'] = pin_pin_df['cell_type'].map(letter_to_int)
    return PinPinEdge(pin_pin_df)
PinPinEdge.merge_tran_cell = merge_tran_cell

def get_output_pins(self):
    """
    Method of :class:`PinProperties`.
    Return a list of output pins from a pin properties df.

    :return: List of output pins
    :rtype: List

    Example:
        output_pins = pin_props_class.get_output_pins()
    """
    pin_df = self.df
    out = pin_df['id'][pin_df['dir'] == 0]
    return out
PinProperties.get_output_pins = get_output_pins

def get_input_pins(self):
    """
    Method of :class:`PinProperties`.
    Return a list of input pins from a pin properties df.

    :return: List of input pins
    :rtype: List

    Example:
        input_pins = pin_props_class.get_input_pins()
    """
    pin_df = self.df
    in_pins = pin_df['id'][pin_df['dir'] == 1]
    return in_pins
PinProperties.get_input_pins = get_input_pins

def remove_isolated_pins(self, circuit_data):
    """
    Method of :class:`PinProperties`.
    Return a properties class with isolated pins removed from its df.

    :param circuit_data: Required. Pass the circuit_data class object
    :type class object: Class object of type CircuitData
    :return: PinProperties cass with isolated pins removed.
    :rtype: PinProperties class

    Example:
        pin_props_class_new = pin_props_class.remove_isolated_pins(circuit_data)
    """
    pin_df = self.df
    pin_pin_df = circuit_data.pin_pin_edge.df

    isolate_ids = set(pin_df['id']).difference(set(pin_pin_df['src_id']).union(set(pin_pin_df['tar_id'])))
    pin_df.drop(index = pin_df.index[pin_df['id'].isin(isolate_ids)], inplace=True)
    return PinProperties(pin_df)
PinProperties.remove_isolated_pins = remove_isolated_pins

def filter_edge(self, e_type):
    """
    Method of :class:`CircuitGraph`.
    Return a CircuitGraph class with only the mentioned edge type in the graph.

    :param e_type: Required. Pass the edge type to be selected. Can be pin_pin, cell_pin, net_pin, cell_cell or cell_net.
    :type e_type: str
    :return: CircuitGraph class with only given edge type.
    :rtype: CircuitGraph class

    Example:
        graph_filtered = circuit_graph.filter_edge("pin_pin")
    """
    g = self.graph
    if e_type == "pin_pin":
        vfilt_str = (g.vp['v_type'].a==0)
        efilt = (g.ep['e_type'].a==0)
    elif e_type == "cell_pin":
        vfilt_str = (g.vp['v_type'].a==0) | (g.vp['v_type'].a==1)
        efilt = (g.ep['e_type'].a==1)
    elif e_type == "net_pin":
        vfilt_str = (g.vp['v_type'].a==0) | (g.vp['v_type'].a==2)
        efilt = (g.ep['e_type'].a==2)
    elif e_type == "cell_cell":
        vfilt_str = (g.vp['v_type'].a==1)
        efilt = (g.ep['e_type'].a==4)
    elif e_type == "cell_net":
        vfilt_str = (g.vp['v_type'].a==1) | (g.vp['v_type'].a==2)
        efilt = (g.ep['e_type'].a==3)

    return CircuitGraph(GraphView(g, vfilt=vfilt_str, efilt=efilt))
CircuitGraph.filter_edges = filter_edge

def get_libcellname_edge(self, circuit_data):
    """
    Method of :class:`PinPinEdge`.
    Return a pin pin edge class with libcell name column.

    :param circuit_data: Required. Pass the circuit_data class object
    :type class object: Class object of type CircuitData
    :return: PinPinEdge class with libcell_name column added.
    :rtype: PinPinEdge class

    Example:
        pin_pin_edge_class_new = pin_pin_edge_class.get_libcellname(circuit_data)
    """
    cell_df = circuit_data.cell_props.df
    pin_df = circuit_data.pin_props.df
    cell_edges = self.df

    libcell_lookup = pd.Series(cell_df['libcell_name'].values, index=cell_df['cell_name'])
    cell_edges['libcell_name'] = cell_edges['cell_name'].map(libcell_lookup)

    return PinPinEdge(cell_edges)
PinPinEdge.get_libcellname = get_libcellname_edge

def get_libcellname_pin(self, circuit_data):
    """
    Method of :class:`PinProperties`.
    Return a pin properties class with libcell name column.

    :param circuit_data: Required. Pass the circuit_data class object
    :type class object: Class object of type CircuitData
    :return: PinProperties class with libcell_name column added.
    :rtype: PinProperties class

    Example:
        pin_props_class_new = pin_props_class.get_libcellname(circuit_data)
    """
    cell_df = circuit_data.cell_props.df
    pin_df = self.df

    libcell_lookup = pd.Series(cell_df['libcell_name'].values, index=cell_df['cell_name'])
    pin_df['libcell_name'] = pin_df['cell_name'].map(libcell_lookup)

    return PinProperties(pin_df)
PinProperties.get_libcellname = get_libcellname_pin

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

def get_large_components(hist, th=2000):
    """
    Returns the labels for connected components that is larger than threshold

    :param hist: Required. Historgram list from label_components function
    :type hist: List
    :param th: Optional. Threshold of component size. Default: 2000
    :type th: int
    :return: List of labels of large components
    :rtype: List

    Examples:
        comp, hist = label_components(graph, directed=False)
        labels = get_large_components(hist, 500)
    """
    labels = []
    for i in range(len(hist)):
        if hist[i] > th:
            labels.append(i)
    return labels

def filter_graph(self, v_mask, e_mask):
    """
    Method of :class:`CircuitGraph`.
    Return a CircuitGraph class after filtering vertices and edge according to input masks.

    :param v_mask: Required. Mask with 1 in only vertices to be selected.
    :type v_mask: Array
    :param e_mask: Required. Mask with 1 in only edges to be selected.
    :type e_mask: Array
    :return: CircuitGraph class with only selected vertices and edges.
    :rtype: CircuitGraph class

    Example:
        graph_filtered = circuit_graph.filter_graph(v_mask, e_mask)
    """
    g_old = self.graph
    u = GraphView(g_old, vfilt=v_mask, efilt=e_mask)
    print("connected component graph: num of edge; num of nodes", u.num_vertices(), u.num_edges())
    ### check whether subgraph is connected and is DAG
    _, hist2 = label_components(u, directed=False)
    return CircuitGraph(u)
CircuitGraph.filter_graph = filter_graph

def get_connected_components(self):
    """
    Method of :class:`CircuitGraph`.
    Return a list of connected component graphs in main graph.

    :return: A list of graph objects, each representing a connected component.
    :rtype: list[graph_tool.Graph]

    Example:
        connected_components = circuit_graph.get_connected_components()
    """
    graph = self.graph
    component_labels, hist = label_components(graph, directed=False)
    components = []

    for comp_id in range(len(hist)):
        vertex_mask = graph.new_vp("bool", val=False)
        edge_mask = graph.new_ep("bool", val=False)
    
        for v in graph.get_vertices():
            if component_labels[v] == comp_id:
                vertex_mask[v] = True
    
        e_ar = graph.get_edges(eprops=[graph.ep["e_id"]])
        v_ar = graph.get_vertices(vprops=[vertex_mask])
        src = e_ar[:,0]
        tar = e_ar[:,1]
        idx = e_ar[:,2]
        mask = (v_ar[src, -1] == True) & (v_ar[tar, -1] == True)
        edge_mask.a[idx[mask]] = True
    
        u = GraphView(graph, vfilt=vertex_mask, efilt=edge_mask)
        components.append(u)

    return components
CircuitGraph.get_connected_components = get_connected_components

def merge_graphs(self, graph_list):
    """
    Method of :class:`CircuitGraph`.
    Merge multiple graph_tool.Graph objects into a single graph.

    :param graph_list: List of graphs to merge.
    :type graph_list: list[graph_tool.Graph]

    :return: A single merged graph containing all the vertices and edges from input graphs.
    :rtype: CircuitGraph class
    """
    g = self.graph

    vertex_mask = g.new_vp("bool", val=False)
    edge_mask = g.new_ep("bool", val=False)

    for component in graph_list:
        for v in component.get_vertices():
            vertex_mask[v] = True

    e_ar = g.get_edges(eprops=[g.ep["e_id"]])
    v_ar = g.get_vertices(vprops=[vertex_mask])
    src = e_ar[:,0]
    tar = e_ar[:,1]
    idx = e_ar[:,2]
    mask = (v_ar[src, -1] == True) & (v_ar[tar, -1] == True)
    edge_mask.a[idx[mask]] = True

    u = self.filter_graph(vertex_mask, edge_mask).graph
    
    u.vp['vertex_mask'] = vertex_mask
    u.ep['edge_mask'] = edge_mask
    
    return CircuitGraph(u)
CircuitGraph.merge_graphs = merge_graphs

def get_large_connected_components(self, th=0):
    """
    Method of :class:`CircuitGraph`.
    Return a CircuitGraph class after removing connected components with number of vertices less than threshold.

    :param th: Min number of vertices to be present in a connected component.
    :type th: int
    :return: CircuitGraph class with only components with size above threshold.
    :rtype: CircuitGraph class

    Example:
        graph_filtered = circuit_graph.get_large_connected_components(100)
    """
    g = self.graph
    N_pin = g.num_vertices()
    comp, hist = label_components(g, directed=False)
    comp.a[N_pin:] = -1
    labels = get_large_components(hist, th=th)
    v_valid_pins = g.new_vp("bool")
    for l in labels:
        v_valid_pins.a[comp.a==l] = True
    e_label = g.new_ep("bool")
    e_label.a = False
    e_ar = g.get_edges(eprops=[g.ep["e_id"]])
    v_ar = g.get_vertices(vprops=[v_valid_pins])
    src = e_ar[:,0]
    tar = e_ar[:,1]
    idx = e_ar[:,2]
    mask = (v_ar[src, -1] == True) & (v_ar[tar, -1] == True)
    e_label.a[idx[mask]] = True
    u = self.filter_graph(v_valid_pins, e_label).graph
    u.vp['v_valid_pins'] = v_valid_pins
    u.ep['e_label'] = e_label
    return CircuitGraph(u)
CircuitGraph.get_large_connected_components = get_large_connected_components

def get_port_nets(netlist_path: str):
    """
    A quick parser to extract all I/O netnames from verilog netlist.

    :param netlist_path: Requied. Pass the path of the netlist file to be parsed.
    :type netlist_path: str
    :return: List of port net names.
    :rtype: List

    Example:
        IOnets = get_port_nets("/path/to/netlist")
    """
    start_reading_IO = False
    with open(netlist_path, 'r') as file:
        while not start_reading_IO:
            line = file.readline().replace('\n', '')
            if 'input' in line.split(' ') or 'output'in line.split(' '):
                start_reading_IO = True
        IOnets = [line.split(' ')[-1].replace(';','')]
        while True:
            line = file.readline().replace('\n', '')
            if 'input' in line.split(' ') or 'output'in line.split(' '):
                IOnets += [line.split(' ')[-1].replace(';','')]
            elif 'wire' in line.split(' '):
                break
    return IOnets

def get_die_boundaries(def_path: str):
    """
    A quick parser to extract die boundaries from DEF.

    :param def_path: Requied. Pass the path of the DEF file to be parsed.
    :type netlist_path: str
    :return: llx, lly, urx, ury coordinates.
    :rtype: Float

    Example:
        llx, lly, urx, ury = get_die_boundaries("/path/to/design.def")
    """
    with open(def_path, 'r') as file:
        while True:
            line = file.readline()
            if 'DIEAREA' in line:
                lx, by, rx, ty = np.array(line.split(' '))[[2,3,6,7]]
                return float(lx), float(by), float(rx), float(ty)

def create_singular_graph(g):
    """
    Function to combine two edge type in a graph and form a singular graph.

    :param g: Required. Graph to be merged.
    :type g: DGL graph object.
    :return: Singular graph
    :rtype: DGL graph object

    Example:
        g_homo = create_singular_graph(g)
    """
    na, nb = g.edges(etype='net_out', form='uv')
    ca, cb = g.edges(etype='cell_out', form='uv')
    g_homo = dgl.graph((torch.cat([na, ca]).cpu(), torch.cat([nb, cb]).cpu()))
    return g_homo

def add_pseudo_fanout_nodes(g,level,num_pins):
    """
    Adds pseudo fan-out nodes at required level

    :param g: Graph in which nodes are to be added
    :type g: DGL graph object
    :param level: Level at which pseudo nodes have to be inserted
    :type level: int
    :param num_pins: Number of pin nodes in graph
    :type num_pins: int

    :return: Graph with pseudo nodes added
    :rtype: DGL graph object

    Example:
        graph_mod = add_pseudo_nodes(og_graph, 0, N_pin)
    """
    g_homo = create_singular_graph(g)
    topo = dgl.topological_nodes_generator(g_homo)
    fanin_nodes = topo[level-1][g.ndata['nf'][topo[level-1], 1] == 0]
    
    g.add_nodes(len(fanin_nodes))
    for feat in g.ndata.keys():
        g.ndata[feat][-len(fanin_nodes):] = g.ndata[feat][fanin_nodes]
        if feat == 'nf':
            g.ndata[feat][-len(fanin_nodes):, 1] = 1
    
    ef_feats = g.edata['ef'][('node', 'net_out', 'node')].shape[1]
    pseudo_node_ids = np.arange(num_pins, num_pins+len(fanin_nodes))
    g.add_edges(pseudo_node_ids, fanin_nodes.numpy(), etype=('node', 'net_out', 'node'), data={'ef': torch.zeros(len(fanin_nodes), ef_feats, dtype=torch.float64)})
    return g

def get_connected_components(g, threshold=0):
    """
    Returns the connected components in a graph with node count above the threshold.

    :param g: Graph in which nodes are to be added
    :type g: DGL graph object
    :param threshold: Min number of nodes to be in a connected component
    :type threshold: int

    :return: List of connected component graphs
    :rtype: List

    Example:
        sub_gs = get_connected_components(og_graph, 100)
    """
    na, nb = g.edges(etype='net_out', form='uv')
    ca, cb = g.edges(etype='cell_out', form='uv')
    g_homo = dgl.graph((torch.cat([na, ca]).cpu(), torch.cat([nb, cb]).cpu()))
    nx_g = g_homo.to_networkx().to_undirected()
    comps = nx.connected_components(nx_g)
    comps = [np.array(sorted(list(comp))) for comp in comps]
    sub_gs = [g.subgraph(nodes) for nodes in comps if len(nodes) >= threshold]
    return sub_gs

def change_graph_bidirectional(g):
    """
    Changes the cell to cell edges as bi-directional

    :param g: Graph which has to be changed to bi directional
    :type g: DGL graph object
    :return: bidir_g, graph with bi-directional edges
    :rtype: DGL graph object

    Example:
        bidir_graph = change_graph_bidirectional(og_graph)
    """
    net_out_src, net_out_dst = g.edges(etype='net_out')
    data_dict = {
        ('node', 'cell_out', 'node'): g.edges(etype='cell_out'),
        ('node', 'net_out', 'node'): g.edges(etype='net_out'),
        ('node', 'net_in', 'node'): (net_out_dst, net_out_src)
    }
    bidir_g = dgl.heterograph(data_dict, idtype=torch.int32)
    for key in g.ndata.keys():
        bidir_g.ndata[key] = g.ndata[key]
    bidir_g.edata['ef'] = {
        ('node', 'cell_out', 'node'): g.edata['ef'][('node', 'cell_out', 'node')],
        ('node', 'net_out', 'node'): g.edata['ef'][('node', 'net_out', 'node')],
        ('node', 'net_in', 'node'): -g.edata['ef'][('node', 'net_out', 'node')]
    }
    bidir_g.edata['cell_id'] = {
        ('node', 'cell_out', 'node'): g.edata['cell_id'][('node', 'cell_out', 'node')]
    }
    return bidir_g
