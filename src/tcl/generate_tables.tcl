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

source "./src/tcl/set_design.tcl"

load_design $DEF_FILE $NETLIST_FILE $LIB_FILES $TECH_LEF_FILE $LEF_FILES $SDC_FILE $DESIGN_NAME $SPEF_FILE 

set db [ord::get_db]
set chip [$db getChip]
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set insts [$block getInsts]
set nets [$block getNets]

#loop
#set inst  [lindex $insts 0]
set cell_outfile [open $cell_file w]
set header {cell_name is_seq is_macro is_in_clk x0 y0 x1 y1 is_buf is_inv libcell_name cell_static_power cell_dynamic_power}
puts $cell_outfile [join $header ","]

set pin_outfile [open $pin_file w]
set header {pin_name x y is_port is_startpoint is_endpoint dir maxcap maxtran num_reachable_endpoint cell_name net_name pin_tran pin_slack pin_arr input_pin_cap}
puts $pin_outfile [join $header ","]

set cell_pin_outfile [open $cell_pin_file w]
set cell_net_outfile [open $cell_net_file w]
set pin_pin_outfile [open $pin_pin_file w]
puts $cell_pin_outfile "src,tar"
puts $cell_net_outfile "src,tar"
puts $pin_pin_outfile "src,tar,is_net"

puts " NUMBER OF INSTANCES [llength $insts]"
foreach inst $insts {
  set cell_name [$inst getName]
  dict set cell_dict cell_name $cell_name
  
  # cell properties
  #location
  set BBox [$inst getBBox]
  dict set cell_dict x0 [$BBox xMin]
  dict set cell_dict y0 [$BBox yMin]
  dict set cell_dict x1 [$BBox xMax]
  dict set cell_dict y1 [$BBox yMax]

  set master_cell [$inst getMaster]
  set master_name [$master_cell getName]
  dict set cell_dict libcell_name $master_name 
  dict set cell_dict is_inv [get_property [get_lib_cells $master_name] is_inverter]
  dict set cell_dict is_buf [get_property [get_lib_cells $master_name] is_buffer]
  #set is_seq [$master_cell isSequential]; # NOT POPULATED
  set is_seq [expr [string first "DFF" $master_name] != -1]
  dict set cell_dict is_seq $is_seq
  set is_macro [$master_cell isBlock]; #POPULATED?
  dict set cell_dict is_macro $is_macro

  #cell-pins
  set inst_ITerms [$inst getITerms]
  set input_pins {}
  set output_pins {}


  foreach ITerm $inst_ITerms {
    #pin properties
    set pin_name [get_ITerm_name $ITerm] 
    set pin_net_name [[$ITerm getNet] getName]
    dict set pin_dict pin_name $pin_name
    dict set pin_dict cell_name $cell_name
    dict set pin_dict net_name $pin_net_name
    dict set pin_dict dir [$ITerm isOutputSignal]
    dict set pin_dict pin_slack [get_property [get_pins $pin_name] "slack_max"]

    print_pin_property_entry $pin_outfile $pin_dict

    #cell-pin
    #cell-net
    if {[$ITerm isInputSignal]} {
      puts $cell_pin_outfile "${pin_name},${cell_name}"
      puts $cell_net_outfile "${pin_net_name},${cell_name}"
      lappend input_pins $pin_name
    } elseif {[$ITerm isOutputSignal]} {
      puts $cell_pin_outfile "${cell_name},${pin_name}"
      puts $cell_net_outfile "${cell_name},${pin_net_name}"
      lappend output_pins $pin_name
    }
  }
  #pin-pin
  if {$is_macro == 0 && $is_seq == 0 } {print_ip_op_pairs $pin_pin_outfile $input_pins $output_pins 0}
  #power
  set corner [::sta::cmd_corner]
  set sta_cell [get_cell $cell_name]
  set inst_power [::sta::instance_power $sta_cell $corner]
  lassign $inst_power inst_pwr_intern inst_pwr_switch inst_pwr_leak inst_pwr_total
  dict set cell_dict cell_static_power $inst_pwr_leak
  dict set cell_dict cell_dynamic_power [expr {$inst_pwr_switch + $inst_pwr_intern}]

  print_cell_property_entry $cell_outfile $cell_dict
}
close $cell_outfile
close $pin_outfile
close $cell_pin_outfile
close $cell_net_outfile


set net_outfile [open $net_file w]
set header {net_name net_route_length net_steiner_length fanout total_cap net_cap net_coupling net_res}
puts $net_outfile [join $header ","]

set net_pin_outfile [open $net_pin_file w]
puts $net_pin_outfile "src,tar"

#net loop
foreach net $nets {
  set net_name [$net getName]
  dict set net_dict net_name $net_name

  set wire [$net getWire]
  
  #net properties$
  dict set net_dict net_cap [$net getTotalCapacitance]
  dict set net_dict net_res [$net getTotalResistance]
  dict set net_dict net_coupling [$net getTotalCouplingCap]
  #dict set net_dict net_route_length [$wire getLength]
  
  set input_pins {}
  set output_pins {}
  #net-pin
  set net_ITerms [$net getITerms]
  foreach ITerm $net_ITerms {
    set ITerm_name [get_ITerm_name $ITerm] 
    #set is_macro [[[$ITerm getInst] getMaster] isBlock]
    #set is_seq [[[$ITerm getInst] getMaster] isSequential]
    if {[$ITerm isInputSignal]} {
      puts $net_pin_outfile "${net_name},${ITerm_name}"
      lappend output_pins $ITerm_name;
    } elseif {[$ITerm isOutputSignal]} {
      puts $net_pin_outfile "${ITerm_name},${net_name}"
      lappend input_pins $ITerm_name;
    }
  }
  print_ip_op_pairs $pin_pin_outfile $input_pins $output_pins 1
  #dict set net_dict fanout [expr [$net getITermCount] - 1]
  dict set net_dict fanout [llength $output_pins] 
  
  print_net_property_entry $net_outfile $net_dict
}
close $net_outfile
close $net_pin_outfile
close $pin_pin_outfile


proc find_func_id {lib_dict libcell_name} {
  set max_func_id -1
  dict for {lib_id func_id} $lib_dict {
    if {$func_id > $max_func_id} {
      set max_func_id $func_id 
    }
    set cell1 [::sta::find_liberty_cell $lib_id]
    set cell2 [::sta::find_liberty_cell $libcell_name]
    if {$cell1 == "" || $cell2 == "" || $cell1 == "NULL" || $cell2 == "NULL"} {continue}
    if {[::sta::equiv_cells $cell1 $cell2]} {
      return [list 1 $func_id]
    }
  }
  set func_id [expr $max_func_id + 1]
  return [list 0 $func_id]
}


#libcell table
set libcell_outfile [open $libcell_file w]
set header {libcell_name func_id libcell_area worst_input_cap libcell_leakage fo4_delay libcell_delay_fixed_load}
puts $libcell_outfile [join $header ","]

set libs [$db getLibs]
set func_id -1
dict set func_dict start -1
foreach lib $libs {
  set lib_name [$lib getName]
  if {[string first "NangateOpenCellLibrary"  $lib_name] != -1} {
    set sta_lib [get_libs "NangateOpenCellLibrary"]
  } else {
    set sta_lib [get_libs $lib_name]
  }
  ::sta::make_equiv_cells $sta_lib 
  set lib_masters [$lib getMasters]
  foreach master $lib_masters {
    set libcell_name [$master getName]
    dict set libcell_dict libcell_name $libcell_name
    set libcell_area [expr [$master getHeight] * [$master getWidth]]
    dict set libcell_dict libcell_area $libcell_area

    set res [find_func_id $func_dict $libcell_name]
    set func_id [lindex $res 1]
    if {[lindex $res 0] == 0} {
      dict set func_dict $libcell_name $func_id
    }
    dict set libcell_dict func_id $func_id

    print_libcell_property_entry $libcell_outfile $libcell_dict
    incr a
  }
}
close $libcell_outfile


