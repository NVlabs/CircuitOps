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

import os
import pdn, odb, utl
from openroad import Tech, Design, Timing
import openroad as ord
import pandas as pd
from collections import defaultdict
import time

class CircuitOps_Tables:
  def __init__(self):
    self.cell_properties = {"cell_name": [],
                            "is_seq": [],
                            "is_macro": [],
                            "is_in_clk": [],
                            "x0": [],
                            "y0": [],
                            "x1": [],
                            "y1": [],
                            "is_buf": [],
                            "is_inv": [],
                            "libcell_name": [],
                            "cell_static_power": [],
                            "cell_dynamic_power": []
                            }
    self.cell_properties = pd.DataFrame(self.cell_properties)

    self.libcell_properties = {"libcell_name": [],
                              "func_id": [],
                              "libcell_area": [],
                              "worst_input_cap": [],
                              "libcell_leakage": [],
                              "fo4_delay": [],
                              "fix_load_delay": []
                              }
    self.libcell_properties = pd.DataFrame(self.libcell_properties)

    self.pin_properties = {"pin_name": [],
                          "x": [],
                          "y": [],
                          "is_in_clk": [],
                          "is_port": [],
                          "is_startpoint": [],
                          "is_endpoint": [],
                          "dir": [],
                          "maxcap": [],
                          "maxtran": [],
                          "num_reachable_endpoint": [],
                          "cell_name": [],
                          "net_name": [],
                          "pin_tran": [],
                          "pin_slack": [],
                          "pin_rise_arr": [],
                          "pin_fall_arr": [],
                          "input_pin_cap": []
                          }
    self.pin_properties = pd.DataFrame(self.pin_properties)

    self.net_properties = {"net_name": [],
                          "net_route_length": [],
                          #"net_steiner_length": [],
                          "fanout": [],
                          "total_cap": [],
                          "net_cap": [],
                          "net_coupling": [],
                          "net_res": []
                          }
    self.net_properties = pd.DataFrame(self.net_properties)

    self.cell_pin_edge = {"src": [],
                          "tar": [],
                          "src_type": [],
                          "tar_type": []
                          }
    self.cell_pin_edge = pd.DataFrame(self.cell_pin_edge)

    self.net_pin_edge = {"src": [],
                        "tar": [],
                        "src_type": [],
                        "tar_type": []
                        }
    self.net_pin_edge = pd.DataFrame(self.net_pin_edge)

    self.pin_pin_edge = {"src": [],
                        "tar": [],
                        "src_type": [],
                        "tar_type": [],
                        "is_net": [],
                        "arc_delay": []
                        }
    self.pin_pin_edge = pd.DataFrame(self.pin_pin_edge)

    self.cell_net_edge = {"src": [],
                         "tar": [],
                         "src_type": [],
                         "tar_type": []
                         }
    self.cell_net_edge = pd.DataFrame(self.cell_net_edge)

    self.cell_cell_edge = {"src": [],
                          "tar": [],
                          "src_type": [],
                          "tar_type": []
                          }
    self.cell_cell_edge = pd.DataFrame(self.cell_cell_edge)
    
  def append_cell_property_entry(self, cell_props):
    cell_entry = {"cell_name": [cell_props["cell_name"]],
                  "is_seq": [cell_props["is_seq"]],
                  "is_macro": [cell_props["is_macro"]],
                  "is_in_clk": [cell_props["is_in_clk"]],
                  "x0": [cell_props["x0"]],
                  "y0": [cell_props["y0"]],
                  "x1": [cell_props["x1"]],
                  "y1": [cell_props["y1"]],
                  "is_buf": [cell_props["is_buf"]],
                  "is_inv": [cell_props["is_inv"]],
                  "libcell_name": [cell_props["libcell_name"]],
                  "cell_static_power": [cell_props["cell_static_power"]],
                  "cell_dynamic_power": [cell_props["cell_dynamic_power"]]
                  }
    cell_entry = pd.DataFrame(cell_entry)
    self.cell_properties = pd.concat([self.cell_properties, cell_entry], ignore_index = True)
 
  def append_pin_property_entry(self, pin_props):
    pin_entry = {"pin_name": [pin_props["pin_name"]],
                "x": [pin_props["x"]],
                "y": [pin_props["y"]],
                "is_in_clk": [pin_props["is_in_clk"]],
                "is_port": [-1],
                "is_startpoint": [-1],
                "is_endpoint": [pin_props["is_endpoint"]],
                "dir": [pin_props["dir"]],
                "maxcap": [-1],
                "maxtran": [-1],
                "num_reachable_endpoint": [pin_props["num_reachable_endpoint"]],
                "cell_name": [pin_props["cell_name"]],
                "net_name": [pin_props["net_name"]],
                "pin_tran": [pin_props["pin_tran"]],
                "pin_slack": [pin_props["pin_slack"]],
                "pin_rise_arr": [pin_props["pin_rise_arr"]],
                "pin_fall_arr": [pin_props["pin_fall_arr"]],
                "input_pin_cap": [pin_props["input_pin_cap"]]
                }
    pin_entry = pd.DataFrame(pin_entry)
    self.pin_properties = pd.concat([self.pin_properties, pin_entry], ignore_index = True)

  def append_net_property_entry(self, net_props):
    net_entry = {"net_name": [net_props["net_name"]],
                "net_route_length": [net_props["net_route_length"]],
                "net_steiner_length": [-1],
                "fanout": [net_props["fanout"]],
                "total_cap": [net_props["total_cap"]],
                "net_cap": [net_props["net_cap"]],
                "net_coupling": [net_props["net_coupling"]],
                "net_res": [net_props["net_res"]]
                }
    net_entry = pd.DataFrame(net_entry)
    self.net_properties = pd.concat([self.net_properties, net_entry], ignore_index = True)

  def append_libcell_property_entry(self, libcell_props):
    libcell_entry = {"libcell_name": [libcell_props["libcell_name"]],
                    "func_id": [-1],
                    "libcell_area": [libcell_props["libcell_area"]],
                    "worst_input_cap": [-1],
                    "libcell_leakage": [-1],
                    "fo4_delay": [-1],
                    "fix_load_delay": [-1]
                    }
    libcell_entry = pd.DataFrame(libcell_entry)
    self.libcell_properties = pd.concat([self.libcell_properties, libcell_entry], ignore_index = True)

  def append_ip_op_cell_pairs(self, inputs, outputs):
    for input in inputs:
      for output in outputs:
        ip_op_cell_pairs = {"src": [input],
                            "tar": [output],
                            "src_type": ["cell"],
                            "tar_type": ["cell"]
                            }
        ip_op_cell_pairs = pd.DataFrame(ip_op_cell_pairs)
        self.cell_cell_edge = pd.concat([self.cell_cell_edge, ip_op_cell_pairs], ignore_index = True)

  def append_ip_op_pairs(self, input_pins, output_pins, is_net):
    count = 0
    for i_p_ in input_pins:
      for o_p_ in output_pins:
        ip_op_pairs = {"src": [i_p_],
                      "tar": [o_p_],
                      "src_type": ["pin"],
                      "tar_type": ["pin"],
                      "is_net": [is_net],
                      "arc_delay": [-1]
                      }
        ip_op_pairs = pd.DataFrame(ip_op_pairs)
        self.pin_pin_edge = pd.concat([self.pin_pin_edge, ip_op_pairs], ignore_index = True)
        count += 1

  def append_cell_net_edge(self, first_name, second_name, cell_net):
    if cell_net:
      new_edge = {"src": [first_name],
                  "tar": [second_name],
                  "src_type": ["net"],
                  "tar_type": ["cell"]
                  }
    else:
      new_edge = {"src": [first_name],
                  "tar": [second_name],
                  "src_type": ["cell"],
                  "tar_type": ["net"]
                  }
    new_edge = pd.DataFrame(new_edge)
    self.cell_net_edge = pd.concat([self.cell_net_edge, new_edge], ignore_index = True)

  def append_cell_pin_edge(self, first_name, second_name, cell_pin):
    if cell_pin:
      new_edge = {"src": [first_name],
                  "tar": [second_name],
                  "src_type": ["pin"],
                  "tar_type": ["cell"]
                  }
    else:
      new_edge = {"src": [first_name],
                  "tar": [second_name],
                  "src_type": ["cell"],
                  "tar_type": ["pin"]
                  }
    new_edge = pd.DataFrame(new_edge)
    self.cell_pin_edge = pd.concat([self.cell_pin_edge, new_edge], ignore_index = True)

  def append_net_pin_edge(self, first_name, second_name, net_pin):
    if net_pin:
      new_edge = {"src": [first_name],
                  "tar": [second_name],
                  "src_type": ["net"],
                  "tar_type": ["pin"]
                  }
    else:
      new_edge = {"src": [first_name],
                  "tar": [second_name],
                  "src_type": ["pin"],
                  "tar_type": ["net"]
                  }
    new_edge = pd.DataFrame(new_edge)
    self.net_pin_edge = pd.concat([self.net_pin_edge, new_edge], ignore_index = True)

  def get_IR_tables(self):
    IR_tables = defaultdict()
    IR_tables["cell_properties"] = self.cell_properties
    IR_tables["libcell_properties"] = self.libcell_properties
    IR_tables["pin_properties"] = self.pin_properties
    IR_tables["net_properties"] = self.net_properties
    IR_tables["cell_pin_edge"] = self.cell_pin_edge
    IR_tables["net_pin_edge"] = self.net_pin_edge
    IR_tables["pin_pin_edge"] = self.pin_pin_edge
    IR_tables["cell_net_edge"] = self.cell_net_edge
    IR_tables["cell_cell_edge"] =  self.cell_cell_edge
    return IR_tables
    

class CircuitOps_File_DIR:
  def __init__(self, CircuitOps_dir, design, tech):
    ### SET DESIGN ###
    self.DESIGN_NAME = design
    
    ### SET PLATFORM ###
    self.PLATFORM = tech

    ### INTERNAL DEFINTIONS: DO NOT MODIFY BELOW ####
    self.CIRCUIT_OPS_DIR = CircuitOps_dir
    self.DESIGN_DIR = self.CIRCUIT_OPS_DIR + "/designs/" + self.PLATFORM + "/" + self.DESIGN_NAME
    self.PLATFORM_DIR = self.CIRCUIT_OPS_DIR + "/platforms/" + self.PLATFORM
    self.RCX_RULE = self.CIRCUIT_OPS_DIR + "/platforms/" + self.PLATFORM + "/rcx_patterns.rules"
    
    self.DEF_FILE = self.DESIGN_DIR + "/6_final.def.gz"
    self.TECH_LEF_FILE = [os.path.join(root, file) for root, _, files in os.walk(self.PLATFORM_DIR + "/lef/") for file in files if file.endswith("tech.lef")]
    self.LEF_FILES = [os.path.join(root, file) for root, _, files in os.walk(self.PLATFORM_DIR + "/lef/") for file in files if file.endswith(".lef")]
    self.LIB_FILES = [os.path.join(root, file) for root, _, files in os.walk(self.PLATFORM_DIR + "/lib/") for file in files if file.endswith(".lib")]
    self.SDC_FILE = self.DESIGN_DIR + "/6_final.sdc.gz"
    self.NETLIST_FILE = self.DESIGN_DIR + "/6_final.v.gz"
    self.SPEF_FILE = self.DESIGN_DIR + "/6_final.spef.gz"

    ### SET OUTPUT DIRECTORY ###
    self.OUTPUT_DIR = self.CIRCUIT_OPS_DIR + "/IRs/" + self.PLATFORM + "/" + self.DESIGN_NAME + "_trial"
    self.create_path()

    self.cell_file = self.OUTPUT_DIR + "/cell_properties.csv"
    self.design_file = self.OUTPUT_DIR + "/design_properties.csv"
    self.libcell_file = self.OUTPUT_DIR + "/libcell_properties.csv"
    self.pin_file = self.OUTPUT_DIR + "/pin_properties.csv"
    self.net_file = self.OUTPUT_DIR + "/net_properties.csv"
    self.cell_pin_file = self.OUTPUT_DIR + "/cell_pin_edge.csv"
    self.net_pin_file = self.OUTPUT_DIR + "/net_pin_edge.csv"
    self.pin_pin_file = self.OUTPUT_DIR + "/pin_pin_edge.csv"
    self.cell_net_file = self.OUTPUT_DIR + "/cell_net_edge.csv"
    self.cell_cell_file = self.OUTPUT_DIR + "/cell_cell_edge.csv"
    
  def create_path(self):
    if not(os.path.exists(self.OUTPUT_DIR)):
      os.mkdir(self.OUTPUT_DIR)

def add_global_connection(design, *,
                          net_name=None,
                          inst_pattern=None,
                          pin_pattern=None,
                          power=False,
                          ground=False,
                          region=None):
  if net_name is None:
    utl.error(utl.PDN, 1501, "The net option for the " +
                  "add_global_connection command is required.")

  if inst_pattern is None:
    inst_pattern = ".*"

  if pin_pattern is None:
    utl.error(utl.PDN, 1502, "The pin_pattern option for the " +
                  "add_global_connection command is required.")

  net = design.getBlock().findNet(net_name)
  if net is None:
    net = odb.dbNet_create(design.getBlock(), net_name)

  if power and ground:
    utl.error(utl.PDN, 1551, "Only power or ground can be specified")
  elif power:
    net.setSpecial()
    net.setSigType("POWER")
  elif ground:
    net.setSpecial()
    net.setSigType("GROUND")

  if region is not None:
    region = design.getBlock().findRegion(region)
    if region is None:
      utl.error(utl.PDN, 1504, f"Region {region} not defined")

  design.getBlock().addGlobalConnect(region, inst_pattern, pin_pattern, net, True)


def load_design(_CircuitOps_File_DIR):
  tech = Tech()
  for libFile in _CircuitOps_File_DIR.LIB_FILES:  
    tech.readLiberty(libFile)
  for techFile in _CircuitOps_File_DIR.TECH_LEF_FILE:
    tech.readLef(techFile)
  for lefFile in _CircuitOps_File_DIR.LEF_FILES:
    tech.readLef(lefFile)
  
  design = Design(tech)
  design.readDef(_CircuitOps_File_DIR.DEF_FILE)
  design.evalTclString("read_sdc " + _CircuitOps_File_DIR.SDC_FILE)  
  #design.evalTclString("read_spef " + _CircuitOps_File_DIR.SPEF_FILE)
  design.evalTclString("set_propagated_clock [all_clocks]")
  add_global_connection(design, net_name="VDD", pin_pattern="VDD", power=True)
  add_global_connection(design, net_name="VSS", pin_pattern="VSS", ground=True)
  odb.dbBlock.globalConnect(ord.get_db_block())
  design.evalTclString("extract_parasitics -ext_model_file "+_CircuitOps_File_DIR.RCX_RULE)
  return tech, design

def print_cell_property_entry(outfile, cell_props):
  cell_entry = []
  cell_entry.append(cell_props["cell_name"])#cell_name
  cell_entry.append(str(cell_props["is_seq"]))#is_seq
  cell_entry.append(str(cell_props["is_macro"]))#is_macro
  cell_entry.append(str(cell_props["is_in_clk"]))#is_in_clk
  cell_entry.append(str(cell_props["x0"]))#x0
  cell_entry.append(str(cell_props["y0"]))#y0
  cell_entry.append(str(cell_props["x1"]))#x1
  cell_entry.append(str(cell_props["y1"]))#y1
  cell_entry.append(str(cell_props["is_fill"]))#is_buf
  cell_entry.append(str(cell_props["is_buf"]))#is_buf
  cell_entry.append(str(cell_props["is_inv"]))#is_inv
  cell_entry.append(cell_props["libcell_name"])#libcell_name
  cell_entry.append(str(cell_props["cell_static_power"]))#cell_static_power
  cell_entry.append(str(cell_props["cell_dynamic_power"]))#cell_dynamic_power
  final = ",".join(cell_entry)
  with open(outfile, "a") as file:
    file.write(final + "\n")


def print_pin_property_entry(outfile, pin_props):
  pin_entry = []
  pin_entry.append(pin_props["pin_name"])#pin_name
  pin_entry.append(str(pin_props["x"]))#x
  pin_entry.append(str(pin_props["y"]))#y
  pin_entry.append(str(pin_props["is_in_clk"]))#is_in_clk
  pin_entry.append("-1")#is_port
  pin_entry.append(str(pin_props["is_startpoint"]))#is_startpoint
  pin_entry.append(str(pin_props["is_endpoint"]))#is_endpoint
  pin_entry.append(str(pin_props["dir"]))#dir
  pin_entry.append(str(pin_props["maxcap"]))#maxcap
  pin_entry.append(str(pin_props["maxtran"]))#maxtran
  pin_entry.append(str(pin_props["num_reachable_endpoint"]))#num_reachable_endpoint
  pin_entry.append(pin_props["cell_name"])#cell_name
  pin_entry.append(pin_props["net_name"])#net_name
  pin_entry.append(str(pin_props["pin_tran"]))#pin_tran
  pin_entry.append(str(pin_props["pin_slack"]))#pin_slack
  pin_entry.append(str(pin_props["pin_rise_arr"]))#pin_rise_arr
  pin_entry.append(str(pin_props["pin_fall_arr"]))#pin_fall_arr
  pin_entry.append(str(pin_props["input_pin_cap"]))#input_pin_cap
  final = ",".join(pin_entry)
  with open(outfile, "a") as file:
    file.write(final + "\n")

def print_ip_op_cell_pairs(outfile, inputs, outputs):
  with open(outfile, "a") as file:
    for input in inputs:
      for output in outputs:
        file.write("{},{},{},{}\n".format(input, output, "cell", "cell"))

def print_ip_op_pairs(outfile, input_pins, output_pins, is_net, corner, design):
  count = 0
  with open(outfile, "a") as file:
    delay = -1
    skip_arc_calc = 0
    for i_p_ in input_pins:
      for o_p_ in output_pins:
        if (not skip_arc_calc):
          try:
            delay = get_ip_op_delay(i_p_, o_p_, corner, design)
          except:
            delay = -1
        file.write("{},{},{},{},{},{}\n".format(i_p_, o_p_, "pin", "pin", is_net, delay))#arc_delays[count]))
        count += 1

def get_ip_op_delay(i_p, o_p, corner, design):
  input_pin = design.evalTclString("get_pin "+i_p)
  output_pin = design.evalTclString("get_pin "+o_p)
  arc_delays = []
  for from_vertex in design.evalTclString(input_pin+" vertices").split():
    for to_vertex in design.evalTclString(output_pin+" vertices").split():
      iterv = design.evalTclString(from_vertex+" out_edge_iterator")
      while (int(design.evalTclString(iterv+" has_next"))):
        edge = design.evalTclString(iterv+" next")
        if (design.evalTclString(edge+" to") == to_vertex):
          arc_delay = get_arc_delay(edge, corner, design)
          arc_delays.append(arc_delay)
  if (len(arc_delays) > 0):
    arc_delay = max(arc_delays)
  else:
    arc_delay = -1
  return arc_delay

def get_arc_delay (edge, corner, design):
  delay_ = -1
  for arc in design.evalTclString(edge+" timing_arcs").split():
    delay = float(design.evalTclString(edge+" arc_delay "+arc+" "+corner+" max"))
    #print(delay)
    if (delay > delay_):
      delay_ = delay
  return delay_

def get_total_power(design, corner):
  block = ord.get_db_block()
  insts = block.getInsts()
  timing = Timing(design)
  s_power = 0
  d_power = 0
  for i in insts:
    s_power += timing.staticPower(i, corner)
    d_power += timing.dynamicPower(i, corner)
  return s_power, d_power

def print_net_property_entry(outfile, net_props):
  net_entry = []
  net_entry.append(net_props["net_name"])#net_name
  net_entry.append(str(net_props["net_route_length"]))#net_route_length
  net_entry.append("-1")#net_steiner_length
  net_entry.append(str(net_props["fanout"]))#fanout
  net_entry.append(str(net_props["total_cap"]))#total_cap
  net_entry.append(str(net_props["net_cap"]))#net_cap
  net_entry.append(str(net_props["net_coupling"]))#net_coupling
  net_entry.append(str(net_props["net_res"]))#net_res
  final = ",".join(net_entry)
  with open(outfile, "a") as file:
    file.write(final + "\n")

def print_libcell_property_entry(outfile, libcell_props):
  libcell_entry = []
  libcell_entry.append(str(libcell_props["libcell_name"]))#libcell_name
  libcell_entry.append('-1')#func. id (*8)
  libcell_entry.append(str(libcell_props["libcell_area"]))#libcell_area
  libcell_entry.append('-1')#worst_input_cap(*5)
  libcell_entry.append('-1')#libcell_leakage
  libcell_entry.append('-1')#fo4_delay
  libcell_entry.append('-1')#libcell_delay_fixed_load
  final = ",".join(libcell_entry)
  with open(outfile, "a") as file:
    file.write(final + "\n")

def Pin_Num_Reachable_Endpoint(ITerm, timing):
  tmp_net = ITerm.getNet()
  tmp_ITerms = tmp_net.getITerms()
  num = 0
  for tmp_ITerm in tmp_ITerms:
    if timing.isEndpoint(tmp_ITerm):
      num += 1
  return num

def get_startpoints(design):
    start_points = []
    start_points_ptr = design.evalTclString("::sta::startpoints").split()
    for sp in start_points_ptr:
        start_point_pin = design.evalTclString("::sta::sta_to_db_pin "+sp)
        if start_point_pin != "NULL":
            start_point_inst_name = design.evalTclString("["+start_point_pin+" getInst] getName")
            start_point_mterm_name = design.evalTclString("["+start_point_pin+" getMTerm] getName")
            start_points.append(start_point_inst_name+"/"+start_point_mterm_name)
    return start_points

def get_registers(design):
    registers = []
    regs_ptr = design.evalTclString("::sta::all_register").split()
    for reg in regs_ptr:
        reg_db_ptr = design.evalTclString("::sta::sta_to_db_inst "+reg)
        if reg_db_ptr != "NULL":
            reg_inst_name = design.evalTclString(reg_db_ptr+" getName")
            registers.append(reg_inst_name)
    return registers

def get_clknets(design):
    clk_nets = []
    clk_nets_ptr = design.evalTclString("::sta::find_all_clk_nets").split()
    clk_nets = [design.evalTclString(x+" getName") for x in clk_nets_ptr]
    return clk_nets

def get_tables_OpenROAD_API(data_root, write_table, return_df, design, tech):
  s1 = time.time()  
  _CircuitOps_File_DIR = CircuitOps_File_DIR(data_root, design, tech)
  tech_design, design = load_design(_CircuitOps_File_DIR)
  design.evalTclString("read_spef " + _CircuitOps_File_DIR.SPEF_FILE)
  timing = Timing(design)
  log = open(_CircuitOps_File_DIR.OUTPUT_DIR+'/log','w')
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
  startpoints = get_startpoints(design)
  registers = get_registers(design)
  corner_sta = design.evalTclString("sta::cmd_corner")
  clk_nets = get_clknets(design)
  if write_table:
    header = "cell_name,is_seq,is_macro,is_in_clk,x0,y0,x1,y1,is_filler,is_buf,is_inv,libcell_name,cell_static_power,cell_dynamic_power"
    with open(_CircuitOps_File_DIR.cell_file, "w") as file:
      file.write(header + "\n")
    header = "design_name, die_width, die_height, die_area, core_width, core_height, core_area, insts_count, net_count, total_static_power, total_dynamic_power"
    with open(_CircuitOps_File_DIR.design_file, "w") as file:
        file.write(header+"\n")
        design_name = block.getName()
        dbunits = block.getDbUnitsPerMicron()
        die_width = block.getDieArea().dx() / dbunits
        die_height = block.getDieArea().dy() / dbunits
        core_width = block.getCoreArea().dx() / dbunits
        core_height = block.getCoreArea().dy() / dbunits
        die_area = die_width*die_height
        core_area = core_width*core_height
        num_insts = len(insts)
        num_nets = len(nets)
        static_power, dynamic_power = get_total_power(design,corner)
        file.write(design_name+','+str(die_width)+','+str(die_height)+','+str(die_area)+','+str(core_width)+','+str(core_height)+','+str(core_area)+','+str(num_insts)+','+str(num_nets)+','+str(static_power)+','+str(dynamic_power)+'\n')
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
  block = ord.get_db_block()
  insts = block.getInsts()
  t_b4_instsloop = time.time()
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
    #is_seq = 1 if ("DFF" in master_name) else 0
    is_seq = 1 if (cell_name in registers) else 0
    cell_dict["is_seq"] = is_seq
    is_macro = 1 if master_cell.isBlock() else 0
    cell_dict["is_macro"] = is_macro
    cell_dict["is_fill"] = 1 if master_cell.isFiller() else 0
    cell_dict["is_buf"] = 1 if design.isBuffer(master_cell) else 0
    cell_dict["is_inv"] = 1 if design.isInverter(master_cell) else 0
    cell_dict["is_in_clk"] = 1 if design.isInClock(inst) else 0
    cell_static_power = timing.staticPower(inst, corner)
    cell_dict["cell_static_power"] = cell_static_power
    cell_dynamic_power = timing.dynamicPower(inst, corner)
    cell_dict["cell_dynamic_power"] = cell_dynamic_power
  
    if write_table:
      print_cell_property_entry(_CircuitOps_File_DIR.cell_file, cell_dict)
    if return_df:
      _CircuitOps_Tables.append_cell_property_entry(cell_dict)

    #cell-pin
    inst_ITerms = inst.getITerms()
    input_pins = []
    output_pins = []
    ######################
    #iterate through pins#
    ######################
    for ITerm in inst_ITerms:
      #skip VDD/VSS pins
      net = ITerm.getNet()
      if net == None:
        print("WARN: Pin "+ITerm.getName()+" is not connected")
        pin_net_name = 'NA'
        pin_name = design.getITermName(ITerm)
        pin_is_in_clk = 0
        continue
      if ITerm.getNet().getSigType() != 'POWER' and ITerm.getNet().getSigType() != 'GROUND':
        #pin_property
        pin_name = design.getITermName(ITerm)
        pin_net_name = ITerm.getNet().getName()
        pin_is_in_clk = 1 if pin_net_name in clk_nets else 0
        library_cell_pin = [MTerm for MTerm in ITerm.getInst().getMaster().getMTerms() if (ITerm.getInst().getName() + "/" + MTerm.getName()) == pin_name][0]
        pin_dict = defaultdict()
        pin_dict["net_name"] = pin_net_name
        pin_dict["pin_name"] = pin_name
        pin_dict["cell_name"] = ITerm.getInst().getName()
        pin_dict["dir"] = 1 if ITerm.isOutputSignal() else 0
        pin_dict["is_in_clk"] = pin_is_in_clk
        PinXY_list = ITerm.getAvgXY()
        if PinXY_list[0]:
          pin_dict["x"] = PinXY_list[1]
          pin_dict["y"] = PinXY_list[2]
        else:
          pin_dict["x"] = -1
          pin_dict["y"] = -1
        pin_dict["is_endpoint"] = 1 if timing.isEndpoint(ITerm) else 0
        pin_dict["is_startpoint"] = 1 if pin_name in startpoints else 0
        pin_dict["num_reachable_endpoint"] = Pin_Num_Reachable_Endpoint(ITerm, timing)
        pin_dict["pin_tran"] = timing.getPinSlew(ITerm)
        pin_dict["pin_slack"] = min(timing.getPinSlack(ITerm, timing.Fall, timing.Max), timing.getPinSlack(ITerm, timing.Rise, timing.Max))
        pin_dict["pin_rise_arr"] = timing.getPinArrival(ITerm, timing.Rise)
        pin_dict["pin_fall_arr"] = timing.getPinArrival(ITerm, timing.Fall)
        pin_dict["maxcap"] = timing.getMaxCapLimit(library_cell_pin)
        pin_dict["maxtran"] = timing.getMaxSlewLimit(library_cell_pin)
        if ITerm.isInputSignal():
          pin_dict["input_pin_cap"] = timing.getPortCap(ITerm, corner, timing.Max)
        else:
          pin_dict["input_pin_cap"] = -1
        if write_table:
          print_pin_property_entry(_CircuitOps_File_DIR.pin_file, pin_dict)
        if return_df:
          _CircuitOps_Tables.append_pin_property_entry(pin_dict)

        #################################################
        #build cell-pin edge table & cell-net edge table#
        #################################################
        if ITerm.isInputSignal():
          if write_table:
            with open(_CircuitOps_File_DIR.cell_pin_file, "a") as file:
              file.write("{},{},{},{}\n".format(pin_name, cell_name, "pin", "cell"))
            with open(_CircuitOps_File_DIR.cell_net_file, "a") as file:
              file.write("{},{},{},{}\n".format(pin_net_name, cell_name, "net", "cell"))
          if return_df:
            _CircuitOps_Tables.append_cell_pin_edge(pin_name, cell_name, True)
            _CircuitOps_Tables.append_cell_net_edge(pin_net_name, cell_name, True)
          input_pins.append(pin_name)
        elif ITerm.isOutputSignal():
          if write_table:
            with open(_CircuitOps_File_DIR.cell_pin_file, "a") as file:
              file.write("{},{},{},{}\n".format(cell_name, pin_name, "cell", "pin"))
            with open(_CircuitOps_File_DIR.cell_net_file, "a") as file:
              file.write("{},{},{},{}\n".format(cell_name, pin_net_name, "cell", "net"))
          if return_df:
            _CircuitOps_Tables.append_cell_pin_edge(cell_name, pin_name, False)
            _CircuitOps_Tables.append_cell_net_edge(cell_name, pin_net_name, False)
          output_pins.append(pin_name)
    ##########################
    #build pin-pin edge table#
    ##########################
    if (is_macro == 0 and is_seq == 0):
      if write_table:
        print_ip_op_pairs(_CircuitOps_File_DIR.pin_pin_file, input_pins, output_pins, 0, corner_sta, design)
      if return_df:
        _CircuitOps_Tables.append_ip_op_pairs(input_pins, output_pins, 0)
  t_aft_insts_loop = time.time()
  if write_table:
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
      #net_res = design.getNetRoutedLength(net) * 34.11886
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
          if write_table:
            with open(_CircuitOps_File_DIR.net_pin_file, "a") as file:
              file.write("{},{},{},{}\n".format(net_name, ITerm_name, "net", "pin"))
          if return_df:
            _CircuitOps_Tables.append_net_pin_edge(net_name, ITerm_name, True)
          output_pins.append(ITerm_name)
          output_cells.append(cell_ITerm_name)
        elif (ITerm.isOutputSignal):
          if write_table:
            with open(_CircuitOps_File_DIR.net_pin_file, "a") as file:
              file.write("{},{},{},{}\n".format(ITerm_name, net_name, "pin", "net"))
          if return_df:
            _CircuitOps_Tables.append_net_pin_edge(ITerm_name, net_name, False)
          input_pins.append(ITerm_name)
          input_cells.append(cell_ITerm_name)

      net_dict["net_name"] = net_name
      net_dict["net_cap"] = net_cap
      net_dict["net_res"] = net_res
      net_dict["net_coupling"] = net_coupling
      net_dict["fanout"] = len(output_pins)
      net_dict["net_route_length"] = design.getNetRoutedLength(net)
      net_dict["total_cap"] = total_cap

      if write_table:
        print_net_property_entry(_CircuitOps_File_DIR.net_file, net_dict)
      if return_df:
        _CircuitOps_Tables.append_net_property_entry(net_dict)

      #################################################
      #build pin-pin edge table & cell-cell edge table#
      #################################################
      if write_table:
        print_ip_op_cell_pairs(_CircuitOps_File_DIR.cell_cell_file, input_cells, output_cells)
        print_ip_op_pairs(_CircuitOps_File_DIR.pin_pin_file, input_pins, output_pins, 1, corner_sta, design)
      if return_df:
        _CircuitOps_Tables.append_ip_op_cell_pairs(input_cells, output_cells)
        _CircuitOps_Tables.append_ip_op_pairs(input_pins, output_pins, 1)
  t_aft_nets_loop = time.time()
  if write_table:
    header = "libcell_name,func_id,libcell_area,worst_input_cap,libcell_leakage,fo4_delay,fix_load_delay"
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

      if write_table:
        print_libcell_property_entry(_CircuitOps_File_DIR.libcell_file, libcell_dict)
      if return_df:
        _CircuitOps_Tables.append_libcell_property_entry(libcell_dict)
  t_aft_libs_loop = time.time()
  log.write("Time before insts loop: "+str(t_b4_instsloop-s1)+"\n")
  log.write("Time taken by insts loop: "+str(t_aft_insts_loop-t_b4_instsloop)+"\n")
  log.write("Time taken by nets loop: "+str(t_aft_nets_loop-t_aft_insts_loop)+"\n")
  log.write("Time taken by libs loop: "+str(t_aft_libs_loop-t_aft_nets_loop)+"\n")
  log.write("Total run time: "+str(t_aft_libs_loop-s1)+"\n")
  log.close()
  return _CircuitOps_Tables.get_IR_tables() if return_df else None




