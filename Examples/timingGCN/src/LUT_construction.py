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

from libertyParser.libertyParser import libertyParser                           # https://github.com/liyanqing1987/libertyParser
from circuitops_api import *


def extract_buffer_LUTs(libs):
    arc_types = ['cell_rise', 'cell_fall', 'rise_transition', 'fall_transition']
    parseLUT = lambda tab : np.array([row.split(',') for row in tab.replace(' ', '').replace('(\"','').replace('\")','').split('\",\"')]).astype(float)
    parseLUTidx = lambda idxs : np.array(idxs.replace(' ','').replace('(\"','').replace('\")','').split(',')).astype(float)
    BUFF_LUTs = {}
    for lib in libs:
        # create a mapping from group name to index in lib dict for faster query
        group_names = [group['name' ]for group in lib.libDic['group']]
        group_map = pd.Series(np.arange(len(group_names)), index=group_names)
        for cell in lib.getCellList():
            found = False
            for pref in ['BUFx', 'HB1x', 'HB2x', 'HB3x', 'HB4x']:
                if pref == cell[:4]:
                    found = True
                    break
            if not found:
                continue
            ### Section for extracting LUTs
            # extract the src and tar pin names, and get pin info from liberty
            #src_tar = cell_edges[['src_pin_name', 'tar_pin_name']][cell_edges['libcell_name'] == cell]
            #pin_pairs = set([*zip(src_tar['src_pin_name'], src_tar['tar_pin_name'])])
            pins = lib.getLibPinInfo(cellList=[cell])['cell'][cell]['pin']
            # for each src/tar pin pair, extract the LUT for timing
            pin_pairs = {('A', 'Y')}
            for src_pin, tar_pin in pin_pairs:
                pin_stat = pins[tar_pin]['timing']
                LUTmat, LUTidx = [], []
                for one_arc in pin_stat:
                    # there might be multiple timing arcs for one src/tar pair
                    # try to extract the arc where the 'when' key is not specified
                    if one_arc['related_pin'] != f'\"{src_pin}\"':
                        continue
                    for arc_type in arc_types:
                        LUTidx.append(parseLUTidx(one_arc['table_type'][arc_type]['index_1']))
                        LUTidx.append(parseLUTidx(one_arc['table_type'][arc_type]['index_2']))
                        LUTmat.append(parseLUT(one_arc['table_type'][arc_type]['values']))
                LUTidx = np.array(LUTidx).reshape(-1, 4, 2, 7)
                LUTmat = np.array(LUTmat).reshape(-1, 4, 7, 7)
                # assert lengths are the same
                assert LUTmat.shape[0] == LUTidx.shape[0]
                # all the indices must be the same!
                assert True not in (LUTidx.max(axis=0) != LUTidx.min(axis=0))
                LUTidx = LUTidx[0]
                # take the values of the matrix with the worst average
                worst_ids = LUTmat.mean(axis=(2, 3)).argmax(axis=0)
                LUTmat = np.array([LUTmat[idx1, idx2] for idx1, idx2 in zip(worst_ids, np.arange(len(arc_types)))])
                # save to dict that is indexed with (cell, src_pin, tar_pin)
                BUFF_LUTs[(cell, src_pin, tar_pin)] = {'LUTidx': LUTidx, 'LUTmat': LUTmat}
    return BUFF_LUTs

def get_buffer_caps(libs):
    RiseCaps, FallCaps = pd.Series(), pd.Series()
    for lib in libs:
        # create a mapping from group name to index in lib dict for faster query
        group_names = [group['name' ]for group in lib.libDic['group']]
        group_map = pd.Series(np.arange(len(group_names)), index=group_names)
        for cell in lib.getCellList():
            found = False
            for pref in ['BUFx', 'HB1x', 'HB2x', 'HB3x', 'HB4x']:
                if pref == cell[:4]:
                    found = True
                    break
            if not found:
                continue
            ### Section for extracting rise/fall capacitances for input pins (dir = 1)
            # extract the src pin names, and get pin info from liberty
            # src_pins = set(pin_df['pinname'][(pin_df['ref'] == cell) & (pin_df['dir'] == 1)])
            src_pins = {'A'}
            cell_group = lib.libDic['group'][group_map[cell]]['group']
            found_src_pins = []
            for cell_attr in cell_group:
                if cell_attr['name'] in src_pins:
                    src_pin = cell_attr['name']
                    found_src_pins.append(src_pin)
                    RiseCaps[cell] = cell_attr['rise_capacitance']
                    FallCaps[cell] = cell_attr['fall_capacitance']
            # assert that we can find all input pins
            assert set(found_src_pins) == src_pins
    BUFF_rise_fall_caps = pd.concat([pd.DataFrame(RiseCaps, columns=['rise_cap']), pd.DataFrame(FallCaps, columns=['fall_cap'])], axis=1)
    return BUFF_rise_fall_caps

def get_cell_LUTs(libs, cell_edges, info_cells):
    arc_types = ['cell_rise', 'cell_fall', 'rise_transition', 'fall_transition']
    parseLUT = lambda tab : np.array([row.split(',') for row in tab.replace(' ', '').replace('(\"','').replace('\")','').split('\",\"')]).astype(float)
    parseLUTidx = lambda idxs : np.array(idxs.replace(' ','').replace('(\"','').replace('\")','').split(',')).astype(float)
    LUTs = {}
    for lib in libs:
        # create a mapping from group name to index in lib dict for faster query
        group_names = [group['name' ]for group in lib.libDic['group']]
        group_map = pd.Series(np.arange(len(group_names)), index=group_names)
        for cell in lib.getCellList():
            if cell not in info_cells:
                print("here:",cell)
                continue
            ### Section for extracting LUTs
            # extract the src and tar pin names, and get pin info from liberty
            print("Outside loop")
            src_tar = cell_edges[['src_pin_name', 'tar_pin_name']][cell_edges['libcell_name'] == cell]
            pin_pairs = set([*zip(src_tar['src_pin_name'], src_tar['tar_pin_name'])])
            pins = lib.getLibPinInfo(cellList=[cell])['cell'][cell]['pin']
            # for each src/tar pin pair, extract the LUT for timing
            print(src_tar)
            for src_pin, tar_pin in pin_pairs:
                pin_stat = pins[tar_pin]['timing']
                LUTmat, LUTidx = [], []
                for one_arc in pin_stat:
                    # there might be multiple timing arcs for one src/tar pair
                    # try to extract the arc where the 'when' key is not specified
                    if one_arc['related_pin'] != f'\"{src_pin}\"':
                        continue
                    for arc_type in arc_types:
                        LUTidx.append(parseLUTidx(one_arc['table_type'][arc_type]['index_1']))
                        LUTidx.append(parseLUTidx(one_arc['table_type'][arc_type]['index_2']))
                        LUTmat.append(parseLUT(one_arc['table_type'][arc_type]['values']))
                LUTidx = np.array(LUTidx).reshape(-1, 4, 2, 7)
                LUTmat = np.array(LUTmat).reshape(-1, 4, 7, 7)
                # assert lengths are the same
                assert LUTmat.shape[0] == LUTidx.shape[0]
                # all the indices must be the same!
                assert True not in (LUTidx.max(axis=0) != LUTidx.min(axis=0))
                LUTidx = LUTidx[0]
                # take the values of the matrix with the worst average
                worst_ids = LUTmat.mean(axis=(2, 3)).argmax(axis=0)
                LUTmat = np.array([LUTmat[idx1, idx2] for idx1, idx2 in zip(worst_ids, np.arange(len(arc_types)))])
                # save to dict that is indexed with (cell, src_pin, tar_pin)
                LUTs[(cell, src_pin, tar_pin)] = {'LUTidx': LUTidx, 'LUTmat': LUTmat}
    return LUTs

def get_cell_caps(libs, pin_df, info_cells):
    RiseCaps, FallCaps = pd.Series(), pd.Series()
    
    for lib in libs:
        # create a mapping from group name to index in lib dict for faster query
        group_names = [group['name' ]for group in lib.libDic['group']]
        group_map = pd.Series(np.arange(len(group_names)), index=group_names)
        for cell in lib.getCellList():
            if cell not in info_cells:
                continue
            ### Section for extracting rise/fall capacitances for input pins (dir = 1)
            # extract the src pin names, and get pin info from liberty
            src_pins = set(pin_df['pin_name'][(pin_df['libcell_name'] == cell) & (pin_df['dir'] == 1)])
            cell_group = lib.libDic['group'][group_map[cell]]['group']
            found_src_pins = []
            for cell_attr in cell_group:
                if cell_attr['name'] in src_pins:
                    src_pin = cell_attr['name']
                    found_src_pins.append(src_pin)
                    RiseCaps[f'{cell}/{src_pin}'] = cell_attr['rise_capacitance']
                    FallCaps[f'{cell}/{src_pin}'] = cell_attr['fall_capacitance']
            # assert that we can find all input pins
            assert set(found_src_pins) == src_pins
    
    # ### set the rise/fall capacitances by mapping
    pin_df['rise_cap'] = pin_df['libcell_name'].str.cat(pin_df['pin_name'], sep='/').map(RiseCaps)
    pin_df['fall_cap'] = pin_df['libcell_name'].str.cat(pin_df['pin_name'], sep='/').map(FallCaps)
    assert False not in (pin_df['rise_cap'].isna() == pin_df['fall_cap'].isna())
    return pin_df

def construct_LUT_files(IR_path, design_path):
    circuit_data = CircuitData(IR_path)
    
    pin_props = circuit_data.pin_props
    pin_pin_edge = circuit_data.pin_pin_edge

    # discard pins that are not connected to anything
    pin_props = pin_props.remove_isolated_pins(circuit_data)
    
    # reset indices
    pin_props.df.reset_index(inplace=True, drop=True)
    pin_pin_edge.df.reset_index(inplace=True, drop=True)
    
    # create new columns for original ids
    pin_props.df['org_id'] = pin_props.df['id']
    pin_pin_edge.df['org_src_id'] = pin_pin_edge.df['src_id']
    pin_pin_edge.df['org_tar_id'] = pin_pin_edge.df['tar_id']
    
    # create mapping from original id to new id
    map_pin_id = pd.Series(pin_props.df.index, pin_props.df['org_id'])
    pin_props.df['id'] = pin_props.df['org_id'].map(map_pin_id)
    pin_pin_edge.df['src_id'] = pin_pin_edge.df['src_id'].map(map_pin_id)
    pin_pin_edge.df['tar_id'] = pin_pin_edge.df['tar_id'].map(map_pin_id)

    ### modify is_port
    IOnets = get_port_nets(f'{design_path}/1_synth.v')
    
    print('[s_port] property in pin_df is invalid. Extract from .v file')
    print('split [netname] by \'[\' and take first item')
    pin_props.df['netname_prefix'] = pin_props.df['net_name'].str.replace('\\', '').str.split('[', expand=True)[0]
    pin_props.df['is_port'] = pin_props.df['netname_prefix'].isin(IOnets)
    print('There are', pin_props.df['is_port'].sum(), 'port pins')
    
    ### add to-boundary distances
    lx, by, rx, ty = get_die_boundaries(f'{design_path}/6_final.def')
    print(f'Boundary ({lx} {by}) - ({rx} {ty})')
    
    pin_props.df['to_top'] = ty - pin_props.df['y']
    pin_props.df['to_left'] = pin_props.df['x'] - lx
    pin_props.df['to_right'] = rx - pin_props.df['x']
    pin_props.df['to_bottom'] = pin_props.df['y'] - by
        
    # LUT extraction for edges
    lib_dir = '/home/vgopal18/OpenROAD/OpenROAD-flow-scripts/flow/platforms/asap7/lib/'
    libfiles = [libfile for libfile in sorted(os.listdir(lib_dir)) if libfile[:5] != 'sram_'] # discard macros
    libs = []
    for libfile in libfiles:
        if libfile[-4:] == '.lib':
            print(f'Parsing {libfile}')
            libs.append(libertyParser(lib_dir+libfile))
    print(libs)
    
    cell_edges = pin_pin_edge.get_arcs("cell")
    cell_edges.df['src_pin_name'] = cell_edges.df['src'].str.split('/').str[-1]
    cell_edges.df['tar_pin_name'] = cell_edges.df['tar'].str.split('/').str[-1]
    cell_edges.df['cell_name'] = cell_edges.df['src'].str.split('/').str[:-1].str.join('/')
    
    cell_edges = cell_edges.get_libcellname(circuit_data)
    pin_props = pin_props.get_libcellname(circuit_data)
    
    # save cell_edge additional information to pin_pin_df
    for col in cell_edges.df.columns:
        if col not in pin_pin_edge.df.columns:
            pin_pin_edge.df[col] = None
            pin_pin_edge.df.loc[pin_pin_edge.df['is_net'] == 0, col] = cell_edges.df[col]
    
    print(pin_pin_edge.df.loc[0])
    
    # get cells used in this design
    print(pin_props.df)
    used_refs = set(pin_props.df['libcell_name'][pin_props.df['is_macro'] == 0].values)
    info_cells = []
    for lib in libs:
        for cell in lib.getCellList():
            if cell in used_refs:
                info_cells.append(cell)
    info_cells = set(info_cells)
    no_info_refs = used_refs.difference(info_cells) 
    
    # extract the LUTs for BUFFER!!!
    BUFF_LUTs = extract_buffer_LUTs(libs)
    print(f'{len(BUFF_LUTs.keys())} different BUFF_LUTs, indexed by (cell, src, tar), are constructed')
    with open(f'{ROOT_DIR}/data/BUFF_LUTs.pk', 'wb') as pkf:
        pk.dump(BUFF_LUTs, pkf)
    
    BUFF_rise_fall_caps = get_buffer_caps(libs)
    BUFF_rise_fall_caps.to_csv(f'{ROOT_DIR}/data/BUFF_rise_fall_caps.csv')
        
    # extract the LUTs
    LUTs = get_cell_LUTs(libs, cell_edges.df, info_cells)
    print(f'{len(LUTs.keys())} different LUTs, indexed by (cell, src, tar), for are constructed')
    
    # extract rise/fall capacitances
    pin_props.df['pin_name'] = [lst[-1] for lst in pin_props.df['pin_name'].str.split('/')]
    pin_props.df = get_cell_caps(libs, pin_props.df, info_cells)
    
    # save pin_df, pin_pin_df, LUTs  
    with open(f'{ROOT_DIR}/data/LUTs.pk', 'wb') as pkf:
        pk.dump(LUTs, pkf)
    
    pin_props.df.to_csv(f'{ROOT_DIR}/data/pin_df.csv')
    pin_pin_edge.df.to_csv(f'{ROOT_DIR}/data/pin_pin_df.csv')
    circuit_data.net_props.df.to_csv(f'{ROOT_DIR}/data/net_df.csv')
    circuit_data.cell_props.df.to_csv(f'{ROOT_DIR}/data/cell_df.csv')
    circuit_data.libcell_props.df.to_csv(f'{ROOT_DIR}/data/fo4_df.csv')

if __name__ == "__main__":

    # Set the Circuitops path
    cops_path = "/home/vgopal18/Circuitops/CircuitOps/IRs/"
    design_name = "gcd"
    platform = "asap7"

    IR_path = f"{cops_path}/{platform}/{design_name}/"
    design_path = "/home/vgopal18/OpenROAD/OpenROAD-flow-scripts/flow/results/asap7/gcd/base/"

    construct_LUT_files(IR_path, design_path)
