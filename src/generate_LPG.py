import re
import pandas as pd
import numpy as np
from graph_tool.all import *
from numpy.random import *
import graph_tool as gt
import os, sys

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../scripts/")

### generate pandas dataframes by reading csv files
def read_IR_tables(data_root):
    cell_cell_path = data_root + "cell_cell_edge.csv"
    cell_pin_path = data_root  + "cell_pin_edge.csv"
    cell_path = data_root  + "cell_properties.csv"
    net_pin_path = data_root  +  "net_pin_edge.csv"
    net_path = data_root  + "net_properties.csv"
    design_prop_path = data_root  + "design_properties.csv"
    pin_pin_path = data_root  + "pin_pin_edge.csv"
    pin_path = data_root  + "pin_properties.csv"
    net_cell_path = data_root  + "cell_net_edge.csv"
    all_fo4_delay_path = data_root + "libcell_properties.csv"

    ### load tables
    libcell_df = pd.read_csv(all_fo4_delay_path)
    design_df = pd.read_csv(design_prop_path)
    pin_df = pd.read_csv(pin_path)
    cell_df = pd.read_csv(cell_path)
    net_df = pd.read_csv(net_path)
    cell_cell_df = pd.read_csv(cell_cell_path)
    pin_pin_df = pd.read_csv(pin_pin_path)
    cell_pin_df = pd.read_csv(cell_pin_path)
    net_pin_df = pd.read_csv(net_pin_path)
    net_cell_df = pd.read_csv(net_cell_path)

    master_df_dict = {}
    master_df_dict['pin_properties'] = pin_df
    master_df_dict['cell_properties'] = cell_df
    master_df_dict['net_properties'] = net_df
    master_df_dict['design_properties'] = design_df
    master_df_dict['libcell_properties'] = libcell_df
    master_df_dict['pin_pin_edge'] = pin_pin_df
    master_df_dict['cell_pin_edge'] = cell_pin_df
    master_df_dict['net_pin_edge'] = net_pin_df
    master_df_dict['cell_net_edge'] = net_cell_df
    master_df_dict['cell_cell_edge'] = cell_cell_df

    return master_df_dict

### rename cells with cell0, cell1, ... and update the cell names in pin_df
def rename_cells(cell_df, pin_df):
    ### rename cells ###
    cell_name = cell_df[["cell_name"]]
    cell_name.loc[:, ["new_cellname"]] = ["cell" + str(i) for i in range(cell_name.shape[0])]
    pin_df = pin_df.merge(cell_name, on="cell_name", how="left")
    idx = pin_df[pd.isna(pin_df.new_cellname)].index

    port_names = ["port" + str(i) for i in range(len(idx))]
    pin_df.loc[idx, "new_cellname"] = port_names
    cell_df["new_cellname"] = cell_name.new_cellname.values
    return cell_df, pin_df

### rename nets with net0, net1, ... and update the net names in pin_df
def rename_nets(net_df, pin_df):
    ### rename nets ###
    net_name = net_df[["net_name"]]
    net_name.loc[:, ["new_netname"]] = ["net" + str(i) for i in range(net_name.shape[0])]
    pin_df = pin_df.merge(net_name, on="net_name", how="left")
    return net_df, pin_df

### 1) get edge src and tar ids and 2) generate edge_df by merging all edges
def generate_edge_df(circuit_df):
    pin_df = circuit_df["pin_properties"]
    cell_df = circuit_df["cell_properties"]
    net_df = circuit_df["net_properties"]

    pin_df = pin_df.rename(columns={"pin_name":"name"})
    cell_df = cell_df.rename(columns={"cell_name":"name"})
    net_df = net_df.rename(columns={"net_name":"name"})
    edge_id = pd.concat([pin_df.loc[:,["id", "name"]], cell_df.loc[:,["id", "name"]], net_df.loc[:,["id", "name"]]], ignore_index=True)
    src = edge_id.copy()
    src = src.rename(columns={"id":"src_id", "name":"src"})
    tar = edge_id.copy()
    tar = tar.rename(columns={"id":"tar_id", "name":"tar"})

    pin_pin_df = circuit_df["pin_pin_edge"]
    cell_pin_df = circuit_df["cell_pin_edge"]
    net_pin_df = circuit_df["net_pin_edge"]
    net_cell_df = circuit_df["cell_net_edge"]
    cell_cell_df = circuit_df["cell_cell_edge"]

    pin_pin_df = pin_pin_df.merge(src, on="src", how="left")
    pin_pin_df = pin_pin_df.merge(tar, on="tar", how="left")

    cell_pin_df = cell_pin_df.merge(src, on="src", how="left")
    cell_pin_df = cell_pin_df.merge(tar, on="tar", how="left")

    net_pin_df = net_pin_df.merge(src, on="src", how="left")
    net_pin_df = net_pin_df.merge(tar, on="tar", how="left")

    net_cell_df = net_cell_df.merge(src, on="src", how="left")
    net_cell_df = net_cell_df.merge(tar, on="tar", how="left")

    cell_cell_df = cell_cell_df.merge(src, on="src", how="left")
    cell_cell_df = cell_cell_df.merge(tar, on="tar", how="left")

    # drop illegal edges
    idx = pin_pin_df[pd.isna(pin_pin_df.src_id)].index
    pin_pin_df = pin_pin_df.drop(idx)
    idx = pin_pin_df[pd.isna(pin_pin_df.tar_id)].index
    pin_pin_df = pin_pin_df.drop(idx)

    idx = cell_pin_df[pd.isna(cell_pin_df.src_id)].index
    cell_pin_df = cell_pin_df.drop(idx)
    idx = cell_pin_df[pd.isna(cell_pin_df.tar_id)].index
    cell_pin_df = cell_pin_df.drop(idx)

    idx = net_pin_df[pd.isna(net_pin_df.src_id)].index
    net_pin_df = net_pin_df.drop(idx)
    idx = net_pin_df[pd.isna(net_pin_df.tar_id)].index
    net_pin_df = net_pin_df.drop(idx)

    idx = net_cell_df[pd.isna(net_cell_df.src_id)].index
    net_cell_df = net_cell_df.drop(idx)
    idx = net_cell_df[pd.isna(net_cell_df.tar_id)].index
    net_cell_df = net_cell_df.drop(idx)

    idx = cell_cell_df[pd.isna(cell_cell_df.src_id)].index    
    cell_cell_df = cell_cell_df.drop(idx)
    idx = cell_cell_df[pd.isna(cell_cell_df.tar_id)].index
    cell_cell_df = cell_cell_df.drop(idx)

    edge_df = pd.concat([pin_pin_df.loc[:,["src_id", "tar_id"]], cell_pin_df.loc[:,["src_id", "tar_id"]], \
                      net_pin_df.loc[:,["src_id", "tar_id"]], net_cell_df.loc[:,["src_id", "tar_id"]], \
                      cell_cell_df.loc[:,["src_id", "tar_id"]]], ignore_index=True)

    N_pin_pin, _ = pin_pin_df.shape
    N_cell_pin, _ = cell_pin_df.shape
    N_net_pin, _ = net_pin_df.shape
    N_net_cell, _ = net_cell_df.shape
    N_cell_cell, _ = cell_cell_df.shape
    total_e_cnt = N_pin_pin + N_cell_pin + N_net_pin + N_net_cell + N_cell_cell

    edge_df["e_type"] = 0 # pin_pin
    edge_df.loc[N_pin_pin : N_pin_pin+N_cell_pin, ["e_type"]] = 1 # cell_pin
    edge_df.loc[N_pin_pin+N_cell_pin : N_pin_pin+N_cell_pin+N_net_pin, ["e_type"]] = 2 # net_pin
    edge_df.loc[N_pin_pin+N_cell_pin+N_net_pin : N_pin_pin+N_cell_pin+N_net_pin+N_net_cell, ["e_type"]] = 3 # net_cell
    edge_df.loc[N_pin_pin+N_cell_pin+N_net_pin+N_net_cell : N_pin_pin+N_cell_pin+N_net_pin+N_net_cell+N_cell_cell, ["e_type"]] = 4 # cell_cell

    return pin_pin_df, cell_pin_df, net_pin_df, net_cell_df, cell_cell_df, edge_df

### assign cell size class and get minimum size libcellname
def assign_gate_size_class(fo4_df):
    ### assign cell size class and min size libcellname
    fo4_df["size_class"] = 0
    fo4_df["size_class2"] = 0
    fo4_df["size_cnt"] = 0
    class_cnt = 50
    for i in range(fo4_df.group_id.min(), fo4_df.group_id.max()+1):
        temp = fo4_df.loc[fo4_df.group_id==i, ["group_id", "libcell_name", "fix_load_delay"]]
        temp = temp.sort_values(by=['fix_load_delay'], ascending=False)
        fo4_df.loc[temp.index, ["size_class"]] = range(len(temp))
        fo4_df.loc[temp.index, ["size_cnt"]] = len(temp)
        temp["size_cnt"] = 0
        MIN = temp.fix_load_delay.min()
        MAX = temp.fix_load_delay.max()
        interval = (MAX-MIN)/class_cnt
        for j in range(1, class_cnt):
            delay_h = MAX - j*interval
            delay_l = MAX - (j+1)*interval
            if j == (class_cnt-1):
                delay_l = MIN
            temp.loc[(temp.fix_load_delay < delay_h) & (temp.fix_load_delay >= delay_l), ["size_cnt"]] = j
        fo4_df.loc[temp.index, ["size_class2"]] = temp["size_cnt"]
        ### add min size libcellname
        fo4_df.loc[temp.index, ["min_size_cell"]] = temp.libcell_name.to_list()[0]
    return fo4_df

def add_columns_pindf(pin_df, cell_df):
    ### add is_macro, is_seq to pin_df, change pin_dir to bool
    pin_df = pin_df.merge(cell_df[["cell_name", "is_macro", "is_seq", "is_buf", "is_inv"]], on="cell_name", how="left")
    pin_df["is_macro"] = pin_df["is_macro"].fillna(False)
    pin_df["is_seq"] = pin_df["is_seq"].fillna(False)
    pin_df["dir"] = (pin_df["dir"] == 0)
    pin_df["is_buf"] = pin_df["is_buf"].fillna(False)
    pin_df["is_inv"] = pin_df["is_inv"].fillna(False)

    return pin_df


def add_ids(pin_df, cell_df, net_df, libcell_df):
    libcell_df["libcell_id"] = range(libcell_df.shape[0])
    ### get dimensions
    N_pin, _ = pin_df.shape
    N_cell, _ = cell_df.shape
    N_net, _ = net_df.shape
    total_v_cnt = N_pin+N_cell+N_net
    pin_df['id'] = range(N_pin)
    cell_df['id'] = range(N_pin, N_pin+N_cell)
    net_df['id'] = range(N_pin+N_cell, total_v_cnt)

    return pin_df, cell_df, net_df, libcell_df


def add_pin_props_to_graph(g, pin_df):
    N_pin, _ = pin_df.shape

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
    v_is_start.a[0:N_pin] = pin_df["is_startpoint"].to_numpy()
    v_is_end.a[0:N_pin] = pin_df["is_endpoint"].to_numpy()
    v_dir.a[0:N_pin] = pin_df["dir"].to_numpy()
    v_maxcap.a[0:N_pin] = pin_df["maxcap"].to_numpy()
    v_maxtran.a[0:N_pin] = pin_df["maxtran"].to_numpy()
    v_num_reachable_endpoint.a[0:N_pin] = pin_df["num_reachable_endpoint"].to_numpy()
    v_tran.a[0:N_pin] = pin_df["pin_tran"].to_numpy()
    v_slack.a[0:N_pin] = pin_df["pin_slack"].to_numpy()
    v_risearr.a[0:N_pin] = pin_df["pin_rise_arr"].to_numpy()
    v_fallarr.a[0:N_pin] = pin_df["pin_fall_arr"].to_numpy()
    v_cap.a[0:N_pin] = pin_df["input_pin_cap"].to_numpy()
    v_is_macro.a[0:N_pin] = pin_df["is_macro"].to_numpy()
    v_is_seq.a[0:N_pin] = pin_df["is_seq"].to_numpy()
    v_is_buf.a[0:N_pin] = pin_df["is_buf"].to_numpy()
    v_is_inv.a[0:N_pin] = pin_df["is_inv"].to_numpy()

    g.vp["v_x"] = v_x
    g.vp["v_y"] = v_y
    g.vp["v_is_in_clk"] = v_is_in_clk
    g.vp["v_is_port"] = v_is_port
    g.vp["v_is_start"] = v_is_start
    g.vp["v_is_end"] = v_is_end
    g.vp["v_dir"] = v_dir
    g.vp["v_maxcap"] = v_maxcap
    g.vp["v_maxtran"] = v_maxtran
    g.vp["v_num_reachable_endpoint"] = v_num_reachable_endpoint
    g.vp["v_tran"] = v_tran
    g.vp["v_slack"] = v_slack
    g.vp["v_risearr"] = v_risearr
    g.vp["v_fallarr"] = v_fallarr
    g.vp["v_cap"] = v_cap
    g.vp["v_is_macro"] = v_is_macro
    g.vp["v_is_seq"] = v_is_seq
    g.vp["v_is_buf"] = v_is_buf
    g.vp["v_is_inv"] = v_is_inv

    return g

def add_cell_props_to_graph(g, cell_df, N_pin):
    N_cell, _ = cell_df.shape

    v_x0 = g.new_vp("float")
    v_y0 = g.new_vp("float")
    v_x1 = g.new_vp("float")
    v_y1 = g.new_vp("float")
    v_staticpower = g.new_vp("float")
    v_dynamicpower = g.new_vp("float")    
    
    g.vp["v_is_seq"].a[N_pin:N_pin+N_cell] = cell_df["is_seq"].to_numpy()
    g.vp["v_is_macro"].a[N_pin:N_pin+N_cell] = cell_df["is_macro"].to_numpy()
    g.vp["v_is_in_clk"].a[N_pin:N_pin+N_cell] = cell_df["is_in_clk"].to_numpy()
    v_x0.a[N_pin:N_pin+N_cell] = cell_df["x0"].to_numpy()
    v_y0.a[N_pin:N_pin+N_cell] = cell_df["y0"].to_numpy()
    v_x1.a[N_pin:N_pin+N_cell] = cell_df["x1"].to_numpy()
    v_y1.a[N_pin:N_pin+N_cell] = cell_df["y1"].to_numpy()
    g.vp["v_is_buf"].a[N_pin:N_pin+N_cell] = cell_df["is_buf"].to_numpy()
    g.vp["v_is_inv"].a[N_pin:N_pin+N_cell] = cell_df["is_inv"].to_numpy()
    v_staticpower.a[N_pin:N_pin+N_cell] = cell_df["cell_static_power"].to_numpy()
    v_dynamicpower.a[N_pin:N_pin+N_cell] = cell_df["cell_dynamic_power"].to_numpy()
    g.vp["v_x"].a[N_pin:N_pin+N_cell] = cell_df["x"].to_numpy()
    g.vp["v_y"].a[N_pin:N_pin+N_cell] = cell_df["y"].to_numpy()

    g.vp["v_x0"] = v_x0
    g.vp["v_y0"] = v_y0
    g.vp["v_x1"] = v_x1
    g.vp["v_y1"] = v_y1
    g.vp["v_staticpower"] = v_staticpower
    g.vp["v_dynamicpower"] = v_dynamicpower

    return g

def add_net_props_to_graph(g, net_df, N_pin_cell):
    N_net, _ = net_df.shape

    v_net_route_length = g.new_vp("float")
    v_net_steiner_length = g.new_vp("float")
    v_fanout = g.new_vp("int")
    v_total_cap = g.new_vp("float")
    v_net_cap = g.new_vp("float")
    v_net_coupling = g.new_vp("float")
    v_net_res = g.new_vp("float")
    
    v_net_route_length.a[N_pin_cell:N_pin_cell+N_net] = net_df["net_route_length"].to_numpy()
    v_net_steiner_length.a[N_pin_cell:N_pin_cell+N_net] = net_df["net_steiner_length"].to_numpy()
    v_fanout.a[N_pin_cell:N_pin_cell+N_net] = net_df["fanout"].to_numpy()
    v_total_cap.a[N_pin_cell:N_pin_cell+N_net] = net_df["total_cap"].to_numpy()
    v_net_cap.a[N_pin_cell:N_pin_cell+N_net] = net_df["net_cap"].to_numpy()
    v_net_coupling.a[N_pin_cell:N_pin_cell+N_net] = net_df["net_coupling"].to_numpy()
    v_net_res.a[N_pin_cell:N_pin_cell+N_net] = net_df["net_res"].to_numpy()

    g.vp["v_net_route_length"] = v_net_route_length
    g.vp["v_net_steiner_length"] = v_net_steiner_length
    g.vp["v_fanout"] = v_fanout
    g.vp["v_total_cap"] = v_total_cap
    g.vp["v_net_cap"] = v_net_cap
    g.vp["v_net_coupling"] = v_net_coupling
    g.vp["v_net_res"] = v_net_res

    return g

def generate_LPG_from_tables(data_root = None, use_python_api = False, write_table = False):
    if not use_python_api:
        circuit_df = read_IR_tables(data_root)
    else:
        from openroad_helpers import get_tables_OpenROAD_API    
        circuit_df = get_tables_OpenROAD_API(data_root = data_root, write_table = write_table, return_df = use_python_api)

    pin_df = circuit_df["pin_properties"]
    cell_df = circuit_df["cell_properties"]
    net_df = circuit_df["net_properties"]
    libcell_df = circuit_df["libcell_properties"]

    pin_df = add_columns_pindf(pin_df, cell_df)

    ### get cell center loc
    cell_df["x"] = 0.5*(cell_df.x0 + cell_df.x1)
    cell_df["y"] = 0.5*(cell_df.y0 + cell_df.y1)

    ### rename cells and nets
    cell_df, pin_df = rename_cells(cell_df, pin_df)
    net_df, pin_df = rename_nets(net_df, pin_df)

    ### Add ids
    pin_df, cell_df, net_df, libcell_df = add_ids(pin_df, cell_df, net_df, libcell_df)

    circuit_df["pin_properties"] = pin_df
    circuit_df["cell_properties"] = cell_df
    circuit_df["net_properties"] = net_df

    ### generate edge_df
    pin_pin_df, cell_pin_df, net_pin_df, cell_net_df, cell_cell_df, edge_df = generate_edge_df(circuit_df)

    N_pin, _ = pin_df.shape
    N_cell, _ = cell_df.shape
    N_net, _ = net_df.shape
    total_v_cnt = N_pin+N_cell+N_net

    ### generate graph
    g = Graph()
    g.add_vertex(total_v_cnt)
    v_type = g.new_vp("int")
    v_type.a[0:N_pin] = 0 # pin
    v_type.a[N_pin:N_pin+N_cell] = 1 # cell
    v_type.a[N_pin+N_cell:total_v_cnt] = 2 # net

    ### add edge to graph
    e_type = g.new_ep("int")

    g.add_edge_list(edge_df.values.tolist(), eprops=[e_type])
    print("num of nodes : %d, num of edges: %d"%(g.num_vertices(), g.num_edges()))

    ### add properties to LPG
    ### processing fo4 table
    libcell_df["group_id"] = pd.factorize(libcell_df.func_id)[0] + 1
    libcell_df["libcell_id"] = range(libcell_df.shape[0])
    libcell_np = libcell_df.to_numpy()
    
    ### assign cell size class
    fo4_df = assign_gate_size_class(libcell_df)
    
    ### add node and edge ids
    v_id = g.new_vp("int")
    v_id.a = range(v_id.a.shape[0])
    
    e_id = g.new_ep("int")
    e_id.a = range(e_id.a.shape[0])

    ### add pin properties to LPG ###
    g = add_pin_props_to_graph(g, pin_df)

    ### add cell properties to LPG ###
    g = add_cell_props_to_graph(g, cell_df, N_pin)

    ### add net properties to LPG ###
    g = add_net_props_to_graph(g, net_df, N_pin+N_cell)

    g.ep["e_id"] = e_id
    g.vp["v_id"] = v_id
    g.ep["e_type"] = e_type
    g.vp["v_type"] = v_type
    
    master_df_dict = {}
    master_df_dict['pin_df'] = pin_df
    master_df_dict['cell_df'] = cell_df
    master_df_dict['design_df'] = circuit_df["design_properties"]
    master_df_dict['net_df'] = net_df
    master_df_dict['fo4_df'] = fo4_df
    master_df_dict['pin_pin_df'] = pin_pin_df
    master_df_dict['cell_pin_df'] = cell_pin_df
    master_df_dict['net_pin_df'] = net_pin_df
    master_df_dict['cell_net_df'] = cell_net_df
    master_df_dict['cell_cell_df'] = cell_cell_df
    master_df_dict['edge_df'] = edge_df

    return g, master_df_dict

