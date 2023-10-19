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

class CircuitOps_File_DIR:
  def __init__(self):
    ### SET DESIGN ###
    self.DESIGN_NAME = "gcd"
    #DESIGN_NAME = "aes"
    #DESIGN_NAME = "bp_fe"
    #DESIGN_NAME = "bp_be"
    
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
  return design

def get_ITerm_name(ITerm):
  MTerm_name = ITerm.getMTerm().getName()
  inst_name = ITerm.getInst().getName()
  ITerm_name = "{}/{}".format(inst_name, MTerm_name)
  return ITerm_name

def print_cell_property_entry(outfile, cell_props):
  cell_entry = []
  cell_entry.append(cell_props["cell_name"])#cell_name
  cell_entry.append(str(cell_props["is_seq"]))#is_seq
  cell_entry.append(str(cell_props["is_macro"]))#is_macro
  cell_entry.append("-1")#is_in_clk
  cell_entry.append(str(cell_props["x0"]))#x0
  cell_entry.append(str(cell_props["y0"]))#y0
  cell_entry.append(str(cell_props["x1"]))#x1
  cell_entry.append(str(cell_props["y1"]))#y1
  cell_entry.append("-1")#is_buf
  cell_entry.append("-1")#is_inv
  cell_entry.append(cell_props["libcell_name"])#libcell_name
  cell_entry.append("-1")#cell_static_power
  cell_entry.append("-1")#cell_dynamic_power
  final = ",".join(cell_entry)
  with open(outfile, "a") as file:
    file.write(final + "\n")

def print_pin_property_entry(outfile, pin_props):
  pin_entry = []
  pin_entry.append(pin_props["pin_name"])#pin_name
  pin_entry.append(str(pin_props["x"]))#x
  pin_entry.append(str(pin_props["y"]))#y
  pin_entry.append("-1")#is_port
  pin_entry.append("-1")#is_startpoint
  pin_entry.append("-1")#is_endpoint
  pin_entry.append(str(pin_props["dir"]))#dir
  pin_entry.append("-1")#maxcap
  pin_entry.append("-1")#maxtran
  pin_entry.append("-1")#num_reachable_endpoint
  pin_entry.append(pin_props["cell_name"])#cell_name
  pin_entry.append(pin_props["net_name"])#net_name
  pin_entry.append("-1")#pin_tran
  pin_entry.append("-1")#pin_slack
  pin_entry.append("-1")#pin_rise_arr
  pin_entry.append("-1")#pin_fall_arr
  pin_entry.append("-1")#input_pin_cap
  final = ",".join(pin_entry)
  with open(outfile, "a") as file:
    file.write(final + "\n")

def print_ip_op_cell_pairs(outfile, inputs, outputs):
  with open(outfile, "a") as file:
    for input in inputs:
      for output in outputs:
        file.write("{},{}\n".format(input, output))

def print_ip_op_pairs(outfile, input_pins, output_pins, is_net):
  with open(outfile, "a") as file:
    for i_p_ in input_pins:
      for o_p_ in output_pins:
        file.write("{},{},{},{}\n".format(i_p_, o_p_, is_net, str(-1)))

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
  net_entry.append("-1")#total_cap
  net_entry.append(str(net_props["net_cap"]))#net_cap
  net_entry.append(str(net_props["net_coupling"]))#net_coupling
  net_entry.append(str(net_props["net_res"]))#net_res
  final = ",".join(net_entry)
  with open(outfile, "a") as file:
    file.write(final + "\n")

def print_libcell_property_entry(outfile, libcell_props):
  libcell_entry = []
  libcell_entry.append(libcell_props["libcell_name"])#libcell_name
  libcell_entry.append("-1")#func. id (*8)
  libcell_entry.append(str(libcell_props["libcell_area"]))#libcell_area
  libcell_entry.append("-1")#worst_input_cap(*5)
  libcell_entry.append("-1")#libcell_leakage
  libcell_entry.append("-1")#fo4_delay
  libcell_entry.append("-1")#libcell_delay_fixed_load
  final = ",".join(libcell_entry)
  with open(outfile, "a") as file:
    file.write(final + "\n")










