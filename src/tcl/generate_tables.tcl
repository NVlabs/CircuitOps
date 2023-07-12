<<<<<<< HEAD
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

=======
>>>>>>> fb9b32e1618c028526e35d2da945a9d167fae5e8
set DESIGN_NAME gcd
#set DESIGN_NAME aes
#set DESIGN_NAME bp_fe
#set DESIGN_NAME bp_be

set PLATFORM nangate45

set DEF_FILE ./designs/$PLATFORM/$DESIGN_NAME/6_final.def
set TECH_LEF_FILE [glob ./platforms/$PLATFORM/lef/*tech.lef]
#set LEF_FILES [glob ./platforms/$PLATFORM/lef/*macro.lef]
set LEF_FILES [glob ./platforms/$PLATFORM/lef/*.lef]
set LIB_FILES [glob ./platforms/$PLATFORM/lib/*.lib]
set SDC_FILE ./designs/$PLATFORM/$DESIGN_NAME/6_final.sdc
set NETLIST_FILE  ./designs/$PLATFORM/$DESIGN_NAME/6_final.v
set SPEF_FILE ./designs/$PLATFORM/$DESIGN_NAME/6_final.spef

set cell_file "IRs/${DESIGN_NAME}_cell_properties.csv"
set libcell_file "IRs/${DESIGN_NAME}_libcell_properties.csv"
set pin_file "IRs/${DESIGN_NAME}_pin_properties.csv"
set net_file "IRs/${DESIGN_NAME}_net_properties.csv"
set cell_pin_file "IRs/${DESIGN_NAME}_cell_pin_edge.csv"
set net_pin_file "IRs/${DESIGN_NAME}_net_pin_edge.csv"
set pin_pin_file "IRs/${DESIGN_NAME}_pin_pin_edge.csv"
set cell_net_file "IRs/${DESIGN_NAME}_cell_net_edge.csv"


proc load_design {def netlist libs tech_lef lefs sdc design spef} {
  foreach libFile $libs {
    read_liberty $libFile
  }
  read_lef $tech_lef
  foreach lef $lefs {
    read_lef $lef
  }
  read_verilog $netlist
  read_def $def
  read_spef $spef
  #read_db $db
  #link_design $design
  read_sdc $sdc
  set_propagated_clock [all_clocks]
  # Ensure all OR created (rsz/cts) instances are connected
  add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
  add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
  global_connect
}

load_design $DEF_FILE $NETLIST_FILE $LIB_FILES $TECH_LEF_FILE $LEF_FILES $SDC_FILE $DESIGN_NAME $SPEF_FILE 


set db [ord::get_db]
set chip [$db getChip]
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set insts [$block getInsts]
set nets [$block getNets]

#source "scripts/load_design.tcl"

proc get_ITerm_name {ITerm} {
  set MTerm_name [[$ITerm getMTerm] getName]
  set inst_name [[$ITerm getInst] getName]
  set ITerm_name "${inst_name}/${MTerm_name}"
  return $ITerm_name
}

proc print_ip_op_pairs {outfile inputs outputs is_net} {
  #set ip_op_pairs {}
  foreach input $inputs {
    foreach output $outputs {
      #lappend ip_op_pairs "${input},${output}"
      puts $outfile "${input},${output},$is_net"
    }
  }
  #return $ip_op_pairs
}

proc print_pin_property_entry {outfile pin_props} {
  set pin_entry {}
  lappend pin_entry [dict get $pin_props "pin_name"];#pin_name 
  lappend pin_entry "-1";#x
  lappend pin_entry "-1";#y
  lappend pin_entry "-1";#is_port
  lappend pin_entry "-1";#is_startpoint
  lappend pin_entry "-1";#is_endpoint
  lappend pin_entry [dict get $pin_props "dir"];#dir 
  lappend pin_entry "-1";#maxcap
  lappend pin_entry "-1";#maxtran
  lappend pin_entry "-1";#num_reachable_endpoint
  lappend pin_entry [dict get $pin_props "cell_name"];#cell_name 
  lappend pin_entry [dict get $pin_props "net_name"];#net_name 
  lappend pin_entry "-1";#pin_tran
  lappend pin_entry [dict get $pin_props "pin_slack"];#pin_slack
  lappend pin_entry "-1";#pin_arr
  lappend pin_entry "-1";#input_pin_cap
  puts $outfile [join $pin_entry ","]
}

proc print_cell_property_entry {outfile cell_props} {
  set cell_entry {}
  lappend cell_entry [dict get $cell_props "cell_name"];#cell_name 
  lappend cell_entry [dict get $cell_props "is_seq"];#is_seq
  lappend cell_entry [dict get $cell_props "is_macro"];#is_macro
  lappend cell_entry "-1";#is_in_clk
  lappend cell_entry [dict get $cell_props "x0"];#x0
  lappend cell_entry [dict get $cell_props "y0"];#y0
  lappend cell_entry [dict get $cell_props "x1"];#x1
  lappend cell_entry [dict get $cell_props "y1"];#y1
  lappend cell_entry [dict get $cell_props "is_buf"];#is_buf
  lappend cell_entry [dict get $cell_props "is_inv"];#is_inv
  lappend cell_entry [dict get $cell_props "libcell_name"];#libcell_name 
  lappend cell_entry [dict get $cell_props "cell_static_power"];#cell_static_power
  lappend cell_entry [dict get $cell_props "cell_dynamic_power"];#cell_dynamic_power
  puts $outfile [join $cell_entry ","]
}

proc print_net_property_entry {outfile net_props} {
  set net_entry {}
  lappend net_entry [dict get $net_props "net_name"];#net_name
  #lappend net_entry [dict get $net_props "net_route_length"];#net_route_length
  lappend net_entry "-1";#net_route_length
  lappend net_entry "-1";#net_steiner_length
  lappend net_entry [dict get $net_props "fanout"];#fanout
  lappend net_entry "-1";#total_cap
  lappend net_entry [dict get $net_props "net_cap"];#net_cap
  lappend net_entry [dict get $net_props "net_coupling"];#net_coupling
  lappend net_entry [dict get $net_props "net_res"];#net_res
  puts $outfile [join $net_entry ","]
}

proc print_libcell_property_entry {outfile libcell_props} {
  set libcell_entry {}
  lappend libcell_entry [dict get $libcell_props "libcell_name"];#libcell_name
  lappend libcell_entry [dict get $libcell_props "func_id"];##func. id (*8)
  lappend libcell_entry [dict get $libcell_props "libcell_area"];#libcell_area
  lappend libcell_entry "-1";#worst_input_cap(*5)
  lappend libcell_entry "-1";#libcell_leakage
  lappend libcell_entry "-1";#fo4_delay
  lappend libcell_entry "-1";#libcell_delay_fixed_load
  puts $outfile [join $libcell_entry ","]
}

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
<<<<<<< HEAD
      set max_func_id $func_id
=======
      set max_func_id $func_id 
>>>>>>> fb9b32e1618c028526e35d2da945a9d167fae5e8
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
<<<<<<< HEAD
  ::sta::make_equiv_cells $sta_lib
=======
  ::sta::make_equiv_cells $sta_lib 
>>>>>>> fb9b32e1618c028526e35d2da945a9d167fae5e8
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


