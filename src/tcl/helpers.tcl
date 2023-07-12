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

proc load_design {def netlist libs tech_lef lefs sdc design spef} {
  foreach libFile $libs {
    read_liberty $libFile
  }
  read_lef $tech_lef
  foreach lef $lefs {
    read_lef $lef
  }
  #read_verilog $netlist
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

proc get_ITerm_name {ITerm} {
  set MTerm_name [[$ITerm getMTerm] getName]
  set inst_name [[$ITerm getInst] getName]
  set ITerm_name "${inst_name}/${MTerm_name}"
  return $ITerm_name
}

proc print_ip_op_pairs {outfile inputs outputs is_net} {
  foreach input $inputs {
    foreach output $outputs {
      puts $outfile "${input},${output},$is_net"
    }
  }
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
