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

from openroad_helpers import CircuitOps_File_DIR, CircuitOps_Tables
from openroad_helpers import load_design, print_cell_property_entry, print_pin_property_entry, print_ip_op_cell_pairs
from openroad_helpers import print_ip_op_pairs, get_net_route_length, print_net_property_entry
from openroad_helpers import print_libcell_property_entry, Pin_X, Pin_Y
from openroad_helpers import Pin_Num_Reachable_Endpoint
import openroad as ord
import pdn, odb, utl
from openroad import Tech, Design, Timing
from collections import defaultdict
import argparse

parser = argparse.ArgumentParser(description="Option to store the IR tables as .csv files.")
parser.add_argument("-w", default=False, action = 'store_true')
args = parser.parse_args()

_CircuitOps_File_DIR = CircuitOps_File_DIR()
tech_design, design = load_design(_CircuitOps_File_DIR)
timing = Timing(design)

db = ord.get_db()
chip = db.getChip()
block = ord.get_db_block()
tech = ord.get_db_tech()
insts = block.getInsts()
nets = block.getNets()
###########################
#get default design corner#
###########################
corner = timing.getCorners()[0]

if args.w:
  header = "cell_name,is_seq,is_macro,is_in_clk,x0,y0,x1,y1,is_buf,is_inv,libcell_name,cell_static_power,cell_dynamic_power"
  with open(_CircuitOps_File_DIR.cell_file, "w") as file:
    file.write(header + "\n")
  
  header = "pin_name,x,y,is_in_clk,is_port,is_startpoint,is_endpoint,dir,maxcap,maxtran,num_reachable_endpoint,cell_name,net_name,pin_tran,pin_slack,pin_rise_arr,pin_fall_arr,input_pin_cap"
  with open(_CircuitOps_File_DIR.pin_file, "w") as file:
    file.write(header + "\n")
  
  with open(_CircuitOps_File_DIR.cell_pin_file, "w") as file:
    file.write("src,tar,src_type,tar_type\n")
  with open(_CircuitOps_File_DIR.cell_net_file, "w") as file:
    file.write("src,tar,src_type,tar_type\n")
  with open(_CircuitOps_File_DIR.pin_pin_file, "w") as file:
    file.write("src,tar,src_type,tar_type,is_net,arc_delay\n")
  with open(_CircuitOps_File_DIR.cell_cell_file, "w") as file:
    file.write("src,tar,src_type,tar_type\n")  

_CircuitOps_Tables = CircuitOps_Tables()

print(" NUMBER OF INSTANCES [" + str(len(insts)) + "]")

############################################
#iterate through each instance and its pins#
#for the properties                        #
############################################
for inst in insts:
  cell_dict = defaultdict()
  cell_name = inst.getName()
  cell_dict["cell_name"] = cell_name
  
  # cell properties
  #location
  BBox = inst.getBBox()
  cell_dict["x0"] = BBox.xMin()
  cell_dict["y0"] = BBox.yMin()
  cell_dict["x1"] = BBox.xMax()
  cell_dict["y1"] = BBox.yMax()

  master_cell = inst.getMaster()
  master_name = master_cell.getName()
  cell_dict["libcell_name"] = master_name
  is_seq = 1 if ("DFF" in master_name) else 0
  cell_dict["is_seq"] = is_seq
  is_macro = 1 if master_cell.isBlock() else 0
  cell_dict["is_macro"] = is_macro
  cell_dict["is_buf"] = 1 if design.isBuffer(master_cell) else 0
  cell_dict["is_inv"] = 1 if design.isInverter(master_cell) else 0
  cell_is_in_clk = 0#1 if design.CellIsInClock(inst) else 0
  #cell_dict["is_in_clk"] = is_in_clk
  cell_static_power = timing.staticPower(inst, corner)
  cell_dict["cell_static_power"] = cell_static_power
  cell_dynamic_power = timing.dynamicPower(inst, corner)
  cell_dict["cell_dynamic_power"] = cell_dynamic_power

  #cell-pin
  inst_ITerms = inst.getITerms()
  input_pins = []
  output_pins = []
  ######################
  #iterate through pins#
  ######################
  for ITerm in inst_ITerms:
    #skip VDD/VSS pins
    if ITerm.getNet().getSigType() != 'POWER' and ITerm.getNet().getSigType() != 'GROUND':
      #pin_property
      pin_name = design.getITermName(ITerm)
      #pin = design.getStaPin(pin_name)
      pin_net_name = ITerm.getNet().getName()
      pin_is_in_clk = 1 if design.isInClock(ITerm.getInst()) else 0
      if pin_is_in_clk:
        cell_is_in_clk = 1
      
      pin_dict = defaultdict()
      pin_dict["net_name"] = pin_net_name
      pin_dict["pin_name"] = pin_name
      pin_dict["cell_name"] = ITerm.getInst().getName()
      pin_dict["dir"] = 1 if ITerm.isOutputSignal() else 0
      pin_dict["is_in_clk"] = pin_is_in_clk
      pin_dict["x"] = Pin_X(ITerm)
      pin_dict["y"] = Pin_Y(ITerm)
      #pin_dict["is_startpoint"] = -1#timing.isStartpoint(ITerm)
      pin_dict["is_endpoint"] = timing.isEndpoint(ITerm)
      #pin_dict["maxtran"] = -1#timing.MaxSlewCheckLimit()    
      pin_dict["num_reachable_endpoint"] = Pin_Num_Reachable_Endpoint(ITerm, timing)
      pin_dict["pin_tran"] = timing.getPinSlew(ITerm)
      pin_dict["pin_slack"] = min(timing.getPinSlack(ITerm, timing.Fall, timing.Max), timing.getPinSlack(ITerm, timing.Rise, timing.Max))
      pin_dict["pin_rise_arr"] = timing.getPinArrival(ITerm, timing.Rise)
      pin_dict["pin_fall_arr"] = timing.getPinArrival(ITerm, timing.Fall)
      
      if ITerm.isInputSignal():
        pin_dict["input_pin_cap"] = timing.LibertyPortCapacitance(ITerm, timing.Max)
        #pin_dict["maxcap"] = "None"
      else:
        pin_dict["input_pin_cap"] = "None"
        #pin_dict["maxcap"] = -1#timing.getMaxCap(pin, corner)
      if args.w:
        print_pin_property_entry(_CircuitOps_File_DIR.pin_file, pin_dict)
      _CircuitOps_Tables.append_pin_property_entry(pin_dict)

      #################################################
      #build cell-pin edge table & cell-net edge table#
      #################################################
      if ITerm.isInputSignal():
        if args.w:
          with open(_CircuitOps_File_DIR.cell_pin_file, "a") as file:
            file.write("{},{},{},{}\n".format(pin_name, cell_name, "pin", "cell"))
          with open(_CircuitOps_File_DIR.cell_net_file, "a") as file:
            file.write("{},{},{},{}\n".format(pin_net_name, cell_name, "net", "cell"))
        _CircuitOps_Tables.append_cell_pin_edge(pin_name, cell_name, True)
        _CircuitOps_Tables.append_cell_net_edge(pin_net_name, cell_name, True)
        input_pins.append(pin_name)
      elif ITerm.isOutputSignal():
        if args.w:
          with open(_CircuitOps_File_DIR.cell_pin_file, "a") as file:
            file.write("{},{},{},{}\n".format(cell_name, pin_name, "cell", "pin"))
          with open(_CircuitOps_File_DIR.cell_net_file, "a") as file:
            file.write("{},{},{},{}\n".format(cell_name, pin_net_name, "cell", "net"))
        _CircuitOps_Tables.append_cell_pin_edge(cell_name, pin_name, False)
        _CircuitOps_Tables.append_cell_net_edge(cell_name, pin_net_name, False)
        output_pins.append(pin_name)
  ##########################
  #build pin-pin edge table#
  ##########################
  if (is_macro == 0 and is_seq == 0):
    if args.w:
      print_ip_op_pairs(_CircuitOps_File_DIR.pin_pin_file, input_pins, output_pins, 0)
    _CircuitOps_Tables.append_ip_op_pairs(input_pins, output_pins, 0)
  
  #check if cell is in clk
  cell_dict["is_in_clk"] = cell_is_in_clk 
  if args.w:
    print_cell_property_entry(_CircuitOps_File_DIR.cell_file, cell_dict)
  _CircuitOps_Tables.append_cell_property_entry(cell_dict)

if args.w:
  header = "net_name,net_route_length,net_steiner_length,fanout,total_cap,net_cap,net_coupling,net_res"
  with open(_CircuitOps_File_DIR.net_file, "w") as file:
    file.write(header + "\n")
  
  with open(_CircuitOps_File_DIR.net_pin_file, "w") as file:
    file.write("src,tar,src_type,tar_type\n")

######################
#iterate through nets#
######################
for net in nets:
  if net.getSigType() != 'POWER' and net.getSigType() != 'GROUND':
    net_name = net.getName()
    num_reachable_endpoint = 0
    net_ITerms = net.getITerms()
    
    net_dict = defaultdict()
    net_cap = net.getTotalCapacitance()
    net_res = net.getTotalResistance()
    net_coupling = net.getTotalCouplingCap()
    
    total_cap = timing.getNetCap(net, corner, timing.Max)

    input_pins = []
    output_pins = []
    input_cells = []
    output_cells = []
    ##########################
    #build net-pin edge table#
    ##########################
    net_ITerms = net.getITerms()
    for ITerm in net_ITerms:
      ITerm_name = design.getITermName(ITerm)
      cell_ITerm_name = ITerm.getInst().getName()
      if (ITerm.isInputSignal()):
        if args.w:
          with open(_CircuitOps_File_DIR.net_pin_file, "a") as file:
            file.write("{},{},{},{}\n".format(net_name, ITerm_name, "net", "pin"))
        _CircuitOps_Tables.append_net_pin_edge(net_name, ITerm_name, True)
        output_pins.append(ITerm_name)
        output_cells.append(cell_ITerm_name)
      elif (ITerm.isOutputSignal):
        if args.w:
          with open(_CircuitOps_File_DIR.net_pin_file, "a") as file:
            file.write("{},{},{},{}\n".format(ITerm_name, net_name, "pin", "net"))
        _CircuitOps_Tables.append_net_pin_edge(ITerm_name, net_name, False)
        input_pins.append(ITerm_name)
        input_cells.append(cell_ITerm_name)

    net_dict["net_name"] = net_name
    net_dict["net_cap"] = net_cap
    net_dict["net_res"] = net_res
    net_dict["net_coupling"] = net_coupling
    net_dict["fanout"] = len(output_pins)
    net_dict["net_route_length"] = get_net_route_length(net)
    net_dict["total_cap"] = total_cap

    if args.w:
      print_net_property_entry(_CircuitOps_File_DIR.net_file, net_dict)
    _CircuitOps_Tables.append_net_property_entry(net_dict)

    #################################################
    #build pin-pin edge table & cell-cell edge table#
    #################################################
    if args.w:
      print_ip_op_cell_pairs(_CircuitOps_File_DIR.cell_cell_file, input_cells, output_cells)
      print_ip_op_pairs(_CircuitOps_File_DIR.pin_pin_file, input_pins, output_pins, 1)
    _CircuitOps_Tables.append_ip_op_cell_pairs(input_cells, output_cells)
    _CircuitOps_Tables.append_ip_op_pairs(input_pins, output_pins, 1)
   
if args.w:
  header = "libcell_name,func_id,libcell_area,worst_input_cap,libcell_leakage,fo4_delay,libcell_delay_fixed_load"
  with open(_CircuitOps_File_DIR.libcell_file, "w") as file:
    file.write(header + "\n")

libs = db.getLibs()

libcell_hash_map = defaultdict()

for lib in libs:
  lib_name = lib.getName()
  lib_masters = lib.getMasters()
  for master in lib_masters:
    libcell_dict = defaultdict()
    libcell_name = master.getName()
    ###########################
    #filter duplicate libcells#
    ###########################
    if libcell_name in libcell_hash_map:
      continue
    else:
      libcell_hash_map[libcell_name] = libcell_name
    libcell_area = master.getHeight() * master.getWidth()

    libcell_dict["libcell_name"] = libcell_name
    libcell_dict["libcell_area"] = libcell_area

    if args.w:
      print_libcell_property_entry(_CircuitOps_File_DIR.libcell_file, libcell_dict)
    _CircuitOps_Tables.append_libcell_property_entry(libcell_dict)


