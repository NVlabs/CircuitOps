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
from openroad import Tech, Design
import openroad as ord
import pandas as pd
from collections import defaultdict

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
                          "net_steiner_length": [],
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
  def __init__(self):
    ### SET DESIGN ###
    self.DESIGN_NAME = "gcd"
    #self.DESIGN_NAME = "aes"
    #self.DESIGN_NAME = "bp_fe"
    #self.DESIGN_NAME = "bp_be"
    
    ### SET PLATFORM ###
    self.PLATFORM = "nangate45"

    ### SET OUTPUT DIRECTORY ###
    self.OUTPUT_DIR = "./IRs/" + self.PLATFORM + "/" + self.DESIGN_NAME
    self.create_path()

    ### INTERNAL DEFINTIONS: DO NOT MODIFY BELOW ####
    self.CIRCUIT_OPS_DIR = "./"
    self.DESIGN_DIR = self.CIRCUIT_OPS_DIR + "/designs/" + self.PLATFORM + "/" + self.DESIGN_NAME
    self.PLATFORM_DIR = self.CIRCUIT_OPS_DIR + "/platforms/" + self.PLATFORM
    
    self.DEF_FILE = self.DESIGN_DIR + "/6_final.def.gz"
    self.TECH_LEF_FILE = [os.path.join(root, file) for root, _, files in os.walk(self.PLATFORM_DIR + "/lef/") for file in files if file.endswith("tech.lef")]
    self.LEF_FILES = [os.path.join(root, file) for root, _, files in os.walk(self.PLATFORM_DIR + "/lef/") for file in files if file.endswith(".lef")]
    self.LIB_FILES = [os.path.join(root, file) for root, _, files in os.walk(self.PLATFORM_DIR + "/lib/") for file in files if file.endswith(".lib")]
    self.SDC_FILE = self.DESIGN_DIR + "/6_final.sdc.gz"
    self.NETLIST_FILE = self.DESIGN_DIR + "/6_final.v"
    self.SPEF_FILE = self.DESIGN_DIR + "/6_final.spef.gz"

    self.cell_file = self.OUTPUT_DIR + "/cell_properties.csv"
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

  # region = None
  if region is not None:
    region = design.getBlock().findRegion(region)
    if region is None:
      utl.error(utl.PDN, 1504, f"Region {region} not defined")

  design.getBlock().addGlobalConnect(region, inst_pattern, pin_pattern, net, True)


def load_design(_CircuitOps_File_DIR):
  tech = Tech()
  tech_design = ord.Tech()
  for libFile in _CircuitOps_File_DIR.LIB_FILES:  
    tech.readLiberty(libFile)
  for techFile in _CircuitOps_File_DIR.TECH_LEF_FILE:
    tech.readLef(techFile)
  for lefFile in _CircuitOps_File_DIR.LEF_FILES:
    tech.readLef(lefFile)
  
  design = Design(tech)
  design.readDef(_CircuitOps_File_DIR.DEF_FILE)
  design.evalTclString("read_sdc " + _CircuitOps_File_DIR.SDC_FILE)  
  design.evalTclString("read_spef " + _CircuitOps_File_DIR.SPEF_FILE)
  design.evalTclString("set_propagated_clock [all_clocks]")
  add_global_connection(design, net_name="VDD", pin_pattern="VDD", power=True)
  add_global_connection(design, net_name="VSS", pin_pattern="VSS", ground=True)
  odb.dbBlock.globalConnect(ord.get_db_block())
  return tech_design, design

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
  pin_entry.append("-1")#is_startpoint
  pin_entry.append(str(pin_props["is_endpoint"]))#is_endpoint
  pin_entry.append(str(pin_props["dir"]))#dir
  pin_entry.append("-1")#maxcap
  pin_entry.append("-1")#maxtran
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

def print_ip_op_pairs(outfile, input_pins, output_pins, is_net):
  count = 0
  with open(outfile, "a") as file:
    for i_p_ in input_pins:
      for o_p_ in output_pins:
        file.write("{},{},{},{},{},{}\n".format(i_p_, o_p_, "pin", "pin", is_net, -1))#arc_delays[count]))
        count += 1

def get_net_route_length(net):
  net_route_length = 0
  net_name = net.getName()
  wires = [net.getWire()]
  
  swire = net.getSWires()
  if (len(swire) != 0):
    wires = swire[0].getWires()

  for wire in wires:
    if wire == None:
      continue
    else:
      wire_length = wire.getLength()
      net_route_length = net_route_length + wire_length

  return net_route_length

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

def Pin_X(ITerm):
  pin_x, count = 0, 0
  pin_geometries = ITerm.getGeometries()
  for pin_geometry in pin_geometries:
    tmp_pin_x = pin_geometry.xMin() + pin_geometry.xMax()
    tmp_pin_x = tmp_pin_x /2
    count = count + 1
    pin_x = pin_x + tmp_pin_x
  pin_x = pin_x / count
  return pin_x

def Pin_Y(ITerm):
  pin_y, count = 0, 0
  pin_geometries = ITerm.getGeometries()
  for pin_geometry in pin_geometries:
    tmp_pin_y = pin_geometry.yMin() + pin_geometry.yMax()
    tmp_pin_y = tmp_pin_y /2
    count = count + 1
    pin_y = pin_y + tmp_pin_y
  pin_y = pin_y / count
  return pin_y

def Pin_Num_Reachable_Endpoint(ITerm, timing):
  tmp_net = ITerm.getNet()
  tmp_ITerms = tmp_net.getITerms()
  num = 0
  for tmp_ITerm in tmp_ITerms:
    if timing.isEndpoint(tmp_ITerm):
      num += 1
  return num





