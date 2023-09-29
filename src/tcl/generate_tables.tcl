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
source "./src/tcl/helpers.tcl"

load_design $DEF_FILE $NETLIST_FILE $LIB_FILES $TECH_LEF_FILE $LEF_FILES $SDC_FILE $DESIGN_NAME $SPEF_FILE 

set db [ord::get_db]
set chip [$db getChip]
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set insts [$block getInsts]
set nets [$block getNets]

#loop
set cell_outfile [open $cell_file w]
set header {cell_name is_seq is_macro is_in_clk x0 y0 x1 y1 is_buf is_inv libcell_name cell_static_power cell_dynamic_power}
puts $cell_outfile [join $header ","]

set pin_outfile [open $pin_file w]
set header {pin_name x y is_port is_startpoint is_endpoint dir maxcap maxtran num_reachable_endpoint cell_name net_name pin_tran pin_slack pin_rise_arr pin_fall_arr input_pin_cap}
puts $pin_outfile [join $header ","]

set cell_pin_outfile [open $cell_pin_file w]
set cell_net_outfile [open $cell_net_file w]
set pin_pin_outfile [open $pin_pin_file w]
set cell_cell_outfile [open $cell_cell_file w]
puts $cell_pin_outfile "src,tar"
puts $cell_net_outfile "src,tar"
puts $pin_pin_outfile "src,tar,is_net,arc_delay"
puts $cell_cell_outfile "src,tar"

puts " NUMBER OF INSTANCES [llength $insts]"

set clk_nets [::sta::find_all_clk_nets]


foreach inst $insts {
  set cell_name [$inst getName]
  dict set cell_dict cell_name $cell_name
 
  # cell properties
  #location
  set BBox [$inst getBBox]
  set inst_x0 [$BBox xMin]
  set inst_y0 [$BBox yMin]
  set inst_x1 [$BBox xMax]
  set inst_y1 [$BBox yMax]
  dict set cell_dict x0 [$BBox xMin]
  dict set cell_dict y0 [$BBox yMin]
  dict set cell_dict x1 [$BBox xMax]
  dict set cell_dict y1 [$BBox yMax]

  set master_cell [$inst getMaster]
  set master_name [$master_cell getName]
  dict set cell_dict libcell_name $master_name 
  dict set cell_dict is_inv [get_property [get_lib_cells $master_name] is_inverter]
  dict set cell_dict is_buf [get_property [get_lib_cells $master_name] is_buffer]
  set is_seq [expr [string first "DFF" $master_name] != -1]
  dict set cell_dict is_seq $is_seq
  set is_macro [$master_cell isBlock]; #POPULATED?
  dict set cell_dict is_macro $is_macro
  
  dict set cell_dict is_in_clk [check_is_in_clk $inst $clk_nets]

  #cell-pins
  set inst_ITerms [$inst getITerms]
  set input_pins {}
  set output_pins {}

  foreach ITerm $inst_ITerms {
    #pin properties
    set pin_name [get_ITerm_name $ITerm] 
    set pin_net_name [[$ITerm getNet] getName]
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
close $cell_pin_outfile
close $cell_net_outfile

set net_outfile [open $net_file w]
set header {net_name net_route_length net_steiner_length fanout total_cap net_cap net_coupling net_res}
puts $net_outfile [join $header ","]

set net_pin_outfile [open $net_pin_file w]
puts $net_pin_outfile "src,tar"

set startpoints [::sta::startpoints]
set start_points {}
foreach startpoint $startpoints {
  set start_point_pin [::sta::sta_to_db_pin $startpoint]
  if { $start_point_pin == "NULL" } {
    continue
  }
  set start_point_inst_name [[$start_point_pin getInst] getName]
  set start_point_mterm_name [[$start_point_pin getMTerm] getName]
  lappend start_points "${start_point_inst_name}/${start_point_mterm_name}"
}

set endpoints [::sta::endpoints]
set end_points {}
foreach endpoint $endpoints {
  set end_point_pin [::sta::sta_to_db_pin $endpoint]
  if { $end_point_pin == "NULL" } {
    continue
  }
  set end_point_inst_name [[$end_point_pin getInst] getName]
  set end_point_mterm_name [[$end_point_pin getMTerm] getName]
  lappend end_points "${end_point_inst_name}/${end_point_mterm_name}"
}

#net loop
foreach net $nets {
  set net_name [$net getName]
  set num_reachable_endpoint 0 
  set corner [::sta::cmd_corner]
  set total_cap [::sta::Net_capacitance [get_net $net_name] $corner max]
  set net_ITerms [$net getITerms]

  if {[::sta::Net_is_power [get_net $net_name]] || [::sta::Net_is_ground [get_net $net_name]]} {
    foreach net_ITerm $net_ITerms {
      set pin_name [get_ITerm_name $net_ITerm]
      set maxtran [::sta::max_slew_check_limit]
      set pin_tran None
      set pin_rise_arr None
      set pin_fall_arr None
      set libport_cap None
      set is_startpoint 0
      set is_endpoint 0
      set pin_x 0
      set pin_y 0
      set count 0
      set pin_geometries [$net_ITerm getGeometries]
      foreach pin_geometry $pin_geometries {
        set tmp_pin_x [expr {[$pin_geometry xMin] + [$pin_geometry xMax]}]
        set tmp_pin_x [expr {$tmp_pin_x / 2}]
        set tmp_pin_y [expr {[$pin_geometry yMin] + [$pin_geometry yMax]}]
        set tmp_pin_y [expr {$tmp_pin_y / 2}]
        set count [expr {$count + 1}]
        set pin_x [expr {$pin_x + $tmp_pin_x}]
        set pin_y [expr {$pin_y + $tmp_pin_y}]
      }
      set pin_x [expr {$pin_x / $count}]
      set pin_y [expr {$pin_y / $count}]
      
      dict set pin_dict net_name $net_name
      dict set pin_dict pin_name $pin_name
      dict set pin_dict cell_name [[$net_ITerm getInst] getName]
      dict set pin_dict dir [$net_ITerm isOutputSignal]
      dict set pin_dict pin_slack [get_property [get_pins $pin_name] "slack_max"]
      dict set pin_dict is_startpoint $is_startpoint
      dict set pin_dict is_endpoint $is_endpoint
      dict set pin_dict maxtran $maxtran
      dict set pin_dict num_reachable_endpoint $num_reachable_endpoint
      dict set pin_dict x $pin_x
      dict set pin_dict y $pin_y
      dict set pin_dict pin_rise_arr $pin_rise_arr
      dict set pin_dict pin_fall_arr $pin_fall_arr
      dict set pin_dict pin_tran $pin_tran
      dict set pin_dict input_pin_cap $libport_cap
      print_pin_property_entry $pin_outfile $pin_dict
    }
  } else {
    foreach net_ITerm $net_ITerms {
      set pin_name [get_ITerm_name $net_ITerm]
      foreach edpt $end_points {
        if {$edpt == $pin_name} {
          set num_reachable_endpoint [expr {$num_reachable_endpoint + 1}]
        } 
      }
    }
    foreach net_ITerm $net_ITerms {
      #pin_property
      set pin_name [get_ITerm_name $net_ITerm]

      set maxtran [::sta::max_slew_check_limit]
      set pin_rise_arrs [get_pin_arr [get_pin $pin_name] "rise"]
      set pin_fall_arrs [get_pin_arr [get_pin $pin_name] "fall"]
      if {[llength $pin_rise_arrs] == 0} {
        set pin_rise_arr "None"
      } else {
        set pin_rise_arr ""
        foreach pin_rise_arrs_ $pin_rise_arrs {
          if {$pin_rise_arr == ""} {
            set pin_rise_arr $pin_rise_arrs_
          } else {
            set pin_rise_arr "$pin_rise_arr $pin_rise_arrs_"
          }
        }
      }
      if {[llength $pin_fall_arrs] == 0} {
        set pin_fall_arr "None"
      } else {
        set pin_fall_arr ""
        foreach pin_fall_arrs_ $pin_fall_arrs {
          if {$pin_fall_arr == ""} {
            set pin_fall_arr $pin_fall_arrs_
          } else {
            set pin_fall_arr "$pin_fall_arr $pin_fall_arrs_"
          }
        }
      }
      set pin_trans [get_pin_slew [get_pin $pin_name]]
      set pin_tran ""
      foreach pin_trans_ $pin_trans {
        if {$pin_tran == ""} {
          set pin_tran $pin_trans_
        } else {
          set pin_tran "$pin_tran $pin_trans_"
        }
      }

      set libport [::sta::Pin_liberty_port [get_pin $pin_name]]
      if {$libport != "NULL"} {
        set libport_cap [::sta::LibertyPort_capacitance $libport $corner max]
        if {$libport_cap == 0.0} {
          set libport_cap None
        }
      } else {
        set libport_cap None
      }
  
      set is_startpoint 0
      set is_endpoint 0
      foreach stpt $start_points {
        if {$stpt == $pin_name} {
          set is_startpoint 1
        }
      }
      foreach edpt $end_points {
        if {$edpt == $pin_name} {
          set is_endpoint 1
        }
      }
      set pin_x 0
      set pin_y 0
      set count 0
      set pin_geometries [$net_ITerm getGeometries]
      foreach pin_geometry $pin_geometries {
        set tmp_pin_x [expr {[$pin_geometry xMin] + [$pin_geometry xMax]}]
        set tmp_pin_x [expr {$tmp_pin_x / 2}]
        set tmp_pin_y [expr {[$pin_geometry yMin] + [$pin_geometry yMax]}]
        set tmp_pin_y [expr {$tmp_pin_y / 2}]
        set count [expr {$count + 1}]
        set pin_x [expr {$pin_x + $tmp_pin_x}]
        set pin_y [expr {$pin_y + $tmp_pin_y}]
      }
      set pin_x [expr {$pin_x / $count}]
      set pin_y [expr {$pin_y / $count}]

      dict set pin_dict net_name $net_name
      dict set pin_dict pin_name $pin_name
      dict set pin_dict cell_name [[$net_ITerm getInst] getName]
      dict set pin_dict dir [$net_ITerm isOutputSignal]
      dict set pin_dict pin_slack [get_property [get_pins $pin_name] "slack_max"]
      dict set pin_dict is_startpoint $is_startpoint
      dict set pin_dict is_endpoint $is_endpoint
      dict set pin_dict maxtran $maxtran
      dict set pin_dict num_reachable_endpoint $num_reachable_endpoint
      dict set pin_dict x $pin_x
      dict set pin_dict y $pin_y
      dict set pin_dict pin_rise_arr $pin_rise_arr
      dict set pin_dict pin_fall_arr $pin_fall_arr
      dict set pin_dict pin_tran $pin_tran
      dict set pin_dict input_pin_cap $libport_cap
      print_pin_property_entry $pin_outfile $pin_dict   
    }
  }
  #net properties$
  set net_name [$net getName]
  dict set net_dict net_name $net_name
  dict set net_dict net_cap [$net getTotalCapacitance]
  dict set net_dict net_res [$net getTotalResistance]
  dict set net_dict net_coupling [$net getTotalCouplingCap]
  
  set net_cap [$net getTotalCapacitance]
  set net_res [$net getTotalResistance]
  set net_coupling [$net getTotalCouplingCap]
  
  set input_pins {}
  set output_pins {}
  set input_cells {}
  set output_cells {}
  #net-pin
  set net_ITerms [$net getITerms]
  foreach ITerm $net_ITerms {
    set ITerm_name [get_ITerm_name $ITerm]
    set cell_ITerm_name [[$ITerm getInst] getName]
    if {[$ITerm isInputSignal]} {
      puts $net_pin_outfile "${net_name},${ITerm_name}"
      lappend output_pins $ITerm_name;
      lappend output_cells $cell_ITerm_name;
    } elseif {[$ITerm isOutputSignal]} {
      puts $net_pin_outfile "${ITerm_name},${net_name}"
      lappend input_pins $ITerm_name;
      lappend input_cells $cell_ITerm_name;
    }
  }

  print_ip_op_cell_pairs $cell_cell_outfile $input_cells $output_cells
  print_ip_op_pairs $pin_pin_outfile $input_pins $output_pins 1
  dict set net_dict fanout [llength $output_pins] 
  dict set net_dict total_cap $total_cap
  dict set net_dict net_route_length [get_net_route_length $net]

  print_net_property_entry $net_outfile $net_dict

}

close $net_outfile
close $net_pin_outfile
close $pin_pin_outfile
close $cell_cell_outfile
close $pin_outfile

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


