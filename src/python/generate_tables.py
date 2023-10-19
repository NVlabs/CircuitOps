from helpers import CircuitOps_File_DIR
from helpers import load_design, get_ITerm_name, print_cell_property_entry, print_pin_property_entry, print_ip_op_cell_pairs
from helpers import print_ip_op_pairs, get_net_route_length, print_net_property_entry, print_libcell_property_entry
import openroad as ord
import pdn, odb, utl
from openroad import Tech, Design
from collections import defaultdict


_CircuitOps_File_DIR = CircuitOps_File_DIR()
design = load_design(_CircuitOps_File_DIR)

db = ord.get_db()
chip = db.getChip()
block = ord.get_db_block()
tech = ord.get_db_tech()
insts = block.getInsts()
nets = block.getNets()

header = "cell_name,is_seq,is_macro,is_in_clk,x0,y0,x1,y1,is_buf,is_inv,libcell_name,cell_static_power,cell_dynamic_power"
with open(_CircuitOps_File_DIR.cell_file, "w") as file:
  file.write(header + "\n")

header = "pin_name,x,y,is_port,is_startpoint,is_endpoint,dir,maxcap,maxtran,num_reachable_endpoint,cell_name,net_name,pin_tran,pin_slack,pin_rise_arr,pin_fall_arr,input_pin_cap"
with open(_CircuitOps_File_DIR.pin_file, "w") as file:
  file.write(header + "\n")

with open(_CircuitOps_File_DIR.cell_pin_file, "w") as file:
  file.write("src,tar\n")
with open(_CircuitOps_File_DIR.cell_net_file, "w") as file:
  file.write("src,tar\n")
with open(_CircuitOps_File_DIR.pin_pin_file, "w") as file:
  file.write("src,tar,is_net,arc_delay\n")
with open(_CircuitOps_File_DIR.cell_cell_file, "w") as file:
  file.write("src,tar\n")  

print(" NUMBER OF INSTANCES [" + str(len(insts)) + "]")

for inst in insts:
  cell_dict = defaultdict()
  cell_name = inst.getName()
  cell_dict["cell_name"] = cell_name
  
  # cell properties
  #location
  BBox = inst.getBBox()
  inst_x0 = BBox.xMin()
  inst_y0 = BBox.yMin()
  inst_x1 = BBox.xMax()
  inst_y1 = BBox.yMax()
  cell_dict["x0"] = inst_x0
  cell_dict["y0"] = inst_y0
  cell_dict["x1"] = inst_x1
  cell_dict["y1"] = inst_y1

  master_cell = inst.getMaster()
  master_name = master_cell.getName()
  cell_dict["libcell_name"] = master_name
  is_seq = 1 if ("DEF" in master_name) else 0
  cell_dict["is_seq"] = is_seq
  is_macro = 1 if master_cell.isBlock() else 0
  cell_dict["is_macro"] = is_macro

  #cell-pin
  inst_ITerms = inst.getITerms()
  input_pins = []
  output_pins = []
  
  for ITerm in inst_ITerms:
    pin_name = get_ITerm_name(ITerm)
    pin_net_name = ITerm.getNet().getName()
    #cell-pin
    #cell-net
    if ITerm.isInputSignal():
      with open(_CircuitOps_File_DIR.cell_pin_file, "a") as file:
        file.write("{},{}\n".format(pin_name, cell_name))
      with open(_CircuitOps_File_DIR.cell_net_file, "a") as file:
        file.write("{},{}\n".format(pin_net_name, cell_name))
      input_pins.append(pin_name)
    elif ITerm.isOutputSignal():    
      with open(_CircuitOps_File_DIR.cell_pin_file, "a") as file:
        file.write("{},{}\n".format(cell_name, pin_name))
      with open(_CircuitOps_File_DIR.cell_net_file, "a") as file:
        file.write("{},{}\n".format(cell_name, pin_net_name))
      output_pins.append(pin_name)
  #pin-pin
  if (is_macro == 0 and is_seq == 0):
    print_ip_op_pairs(_CircuitOps_File_DIR.pin_pin_file, input_pins, output_pins, 0)
    pass
  print_cell_property_entry(_CircuitOps_File_DIR.cell_file, cell_dict)

header = "net_name,net_route_length,net_steiner_length,fanout,total_cap,net_cap,net_coupling,net_res"
with open(_CircuitOps_File_DIR.net_file, "w") as file:
  file.write(header + "\n")

with open(_CircuitOps_File_DIR.net_pin_file, "w") as file:
  file.write("src,tar\n")

#net loop
for net in nets:
  net_name = net.getName()
  num_reachable_endpoint = 0
  net_ITerms = net.getITerms()
  
  for net_ITerm in net_ITerms:
    #pin_property
    pin_name = get_ITerm_name(net_ITerm)
    pin_x, pin_y = 0, 0
    count = 0
    pin_geometries = net_ITerm.getGeometries()
    for pin_geometry in pin_geometries:
      tmp_pin_x = pin_geometry.xMin() + pin_geometry.xMax()
      tmp_pin_x = tmp_pin_x / 2
      tmp_pin_y = pin_geometry.xMin() + pin_geometry.xMax()
      tmp_pin_y = tmp_pin_y / 2
      count = count + 1
      pin_x = pin_x + tmp_pin_x
      pin_y = pin_y + tmp_pin_y
    pin_x = pin_x / count
    pin_y = pin_y / count  
    
    pin_dict = defaultdict()
    pin_dict["net_name"] = net_name
    pin_dict["pin_name"] = pin_name
    pin_dict["cell_name"] = net_ITerm.getInst().getName()
    pin_dict["dir"] = "1" if net_ITerm.isOutputSignal() else "0"
    pin_dict["x"] = pin_x
    pin_dict["y"] = pin_y
    print_pin_property_entry(_CircuitOps_File_DIR.pin_file, pin_dict)

  #net properties
  net_dict = defaultdict()
  net_cap = net.getTotalCapacitance()
  net_res = net.getTotalResistance()
  net_coupling = net.getTotalCouplingCap()
  
  input_pins = []
  output_pins = []
  input_cells = []
  output_cells = []
  #net-pin
  net_ITerms = net.getITerms()
  for ITerm in net_ITerms:
    ITerm_name = get_ITerm_name(ITerm)
    cell_ITerm_name = ITerm.getInst().getName()
    if (ITerm.isInputSignal()):
      with open(_CircuitOps_File_DIR.net_pin_file, "a") as file:
        file.write("{},{}\n".format(net_name, ITerm_name))
      output_pins.append(ITerm_name)
      output_cells.append(cell_ITerm_name)
    elif (ITerm.isOutputSignal):
      with open(_CircuitOps_File_DIR.net_pin_file, "a") as file:
        file.write("{},{}\n".format(ITerm_name, net_name))
      input_pins.append(ITerm_name)
      input_cells.append(cell_ITerm_name)
  
  print_ip_op_cell_pairs(_CircuitOps_File_DIR.cell_cell_file, input_cells, output_cells)
  print_ip_op_pairs(_CircuitOps_File_DIR.pin_pin_file, input_pins, output_pins, 1)
  
  net_dict["net_name"] = net_name
  net_dict["net_cap"] = net_cap
  net_dict["net_res"] = net_res
  net_dict["net_coupling"] = net_coupling
  net_dict["fanout"] = len(output_pins)
  net_dict["net_route_length"] = get_net_route_length(net)
  
  print_net_property_entry(_CircuitOps_File_DIR.net_file, net_dict)

#libcell table
header = "libcell_name,func_id,libcell_area,worst_input_cap,libcell_leakage,fo4_delay,libcell_delay_fixed_load"
with open(_CircuitOps_File_DIR.libcell_file, "w") as file:
  file.write(header + "\n")

libs = db.getLibs()
func_id = -1
func_dict = defaultdict()
func_dict["start"] = -1
for lib in libs:
  lib_name = lib.getName()
  lib_masters = lib.getMasters()
  for master in lib_masters:
    libcell_dict = defaultdict()
    libcell_name = master.getName()
    libcell_area = master.getHeight() * master.getWidth()

    libcell_dict["libcell_name"] = libcell_name
    libcell_dict["libcell_area"] = libcell_area
    
    print_libcell_property_entry(_CircuitOps_File_DIR.libcell_file, libcell_dict)














