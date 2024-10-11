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

set t1 [clock seconds]

set fp_log [open "${OUTPUT_DIR}/log" w]

load_design $DEF_FILE $NETLIST_FILE $LIB_FILES $TECH_LEF_FILE $LEF_FILES $SDC_FILE $DESIGN_NAME $SPEF_FILE $RCX_FILE $fp_log
source "${PLATFORM_DIR}/setRC.tcl"

set db [ord::get_db]
set chip [$db getChip]
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set insts [$block getInsts]
set nets [$block getNets]

set post_load [clock seconds]

#loop
set cell_outfile [open $cell_file w]
set header {cell_name is_seq is_macro is_in_clk x0 y0 x1 y1 is_buf is_inv libcell_name cell_static_power cell_dynamic_power}
puts $cell_outfile [join $header ","]

set pin_outfile [open $pin_file w]
set header {pin_name x y is_in_clk is_port is_startpoint is_endpoint dir maxcap maxtran num_reachable_endpoint cell_name net_name pin_tran pin_slack pin_rise_arr pin_fall_arr input_pin_cap}
puts $pin_outfile [join $header ","]

set cell_pin_outfile [open $cell_pin_file w]
set cell_net_outfile [open $cell_net_file w]
set pin_pin_outfile [open $pin_pin_file w]
set cell_cell_outfile [open $cell_cell_file w]
puts $cell_pin_outfile "src,tar,src_type,tar_type"
puts $cell_net_outfile "src,tar,src_type,tar_type"
puts $pin_pin_outfile "src,tar,src_type,tar_type,is_net,arc_delay"
puts $cell_cell_outfile "src,tar,src_type,tar_type"

puts " NUMBER OF INSTANCES [llength $insts]"
puts $fp_log " NUMBER OF INSTANCES [llength $insts]"

set clk_nets [::sta::find_all_clk_nets]

##########################################
#get startpoints & endpoints from OpenSTA#
##########################################
set startpoints [::sta::startpoints]
foreach startpoint $startpoints {
  set start_point_pin [::sta::sta_to_db_pin $startpoint]
  if { $start_point_pin == "NULL" } {
    continue
  }
  set start_point_inst_name [[$start_point_pin getInst] getName]
  set start_point_mterm_name [[$start_point_pin getMTerm] getName]
  dict set start_points "${start_point_inst_name}/${start_point_mterm_name}" 1
}

set endpoints [::sta::endpoints]
foreach endpoint $endpoints {
  set end_point_pin [::sta::sta_to_db_pin $endpoint]
  if { $end_point_pin == "NULL" } {
    continue
  }
  set end_point_inst_name [[$end_point_pin getInst] getName]
  set end_point_mterm_name [[$end_point_pin getMTerm] getName]
  dict set end_points "${end_point_inst_name}/${end_point_mterm_name}" 1
}

set post_ep_sp [clock seconds]

###########################
#get default design corner#
###########################
set corner [::sta::cmd_corner]


set seq_cells [::sta::all_register]
foreach seq_cell $seq_cells {
  dict set seq_cell_dict $seq_cell 1
}

set post_seq_cells [clock seconds]

############################################
#iterate through each instance and its pins#
#for the properties                        #
############################################
#
set maxtran [::sta::max_slew_check_limit]
set maxcap [::sta::max_capacitance_check_limit]

foreach inst $insts {
  set cell_name [$inst getName]
  dict set cell_dict cell_name $cell_name

  set master_cell [$inst getMaster]
  set master_name [$master_cell getName]

  #cell properties
  set BBox [$inst getBBox]
  dict set cell_dict x0 [$BBox xMin]
  dict set cell_dict y0 [$BBox yMin]
  dict set cell_dict x1 [$BBox xMax]
  dict set cell_dict y1 [$BBox yMax]
  dict set cell_dict libcell_name $master_name
  set master_libcell [get_lib_cells $master_name]
  if {$master_libcell == ""} {
      puts "WARN: libcell definition not found for cell : $master_name"
      dict set cell_dict is_inv 0
      dict set cell_dict is_buf 0
  } else { 
  dict set cell_dict is_inv [get_property [get_lib_cells $master_name] is_inverter]
  dict set cell_dict is_buf [get_property [get_lib_cells $master_name] is_buffer]
  }
  set is_seq [dict exists $seq_cell_dict [get_cells $cell_name]]
  set is_macro [$master_cell isBlock];
  
  dict set cell_dict is_seq $is_seq
  dict set cell_dict is_macro $is_macro
  
  set cell_is_in_clk 0
  set inst_ITerms [$inst getITerms]
  set input_pins {}
  set output_pins {}
  ######################
  #iterate through pins#
  ######################
  foreach ITerm $inst_ITerms {
    set pin_name [get_ITerm_name $ITerm]
    set pin [get_pin $pin_name]
    set pin_net [$ITerm getNet]
    if {$pin_net == "NULL"} {
	puts "WARN: Pin $pin_name is not connected\n"
	set pin_net_name "NA"
	set is_connected 0
    } else {
    set pin_net_name [$pin_net getName]
    set is_connected 1
    }

    #skip VDD/VSS pins
    if {$is_connected == 1} {
    if {!([::sta::Net_is_power [get_net $pin_net_name]] || [::sta::Net_is_ground [get_net $pin_net_name]])} {
      set is_in_clk [check_pin_is_in_clk $ITerm $clk_nets]
      if {$is_in_clk == 1} {
        set cell_is_in_clk 1
      }
      if {[info exists dict_num_reachable_endpoint]} {
        if {[dict exists $dict_num_reachable_endpoint $pin_net_name]} {
          set num_reachable_endpoint [dict get $dict_num_reachable_endpoint $pin_net_name]
        } else {
          dict set dict_num_reachable_endpoint $pin_net_name 0
          set num_reachable_endpoint [get_pin_num_reachable_endpoint $ITerm $end_points]
        }
      } else {
        dict set dict_num_reachable_endpoint $pin_net_name 0
        set num_reachable_endpoint [get_pin_num_reachable_endpoint $ITerm $end_points]
      }
      dict set pin_dict net_name $pin_net_name
      dict set pin_dict pin_name $pin_name
      dict set pin_dict cell_name $cell_name
      dict set pin_dict is_in_clk $is_in_clk
      dict set pin_dict dir [$ITerm isOutputSignal]
      dict set pin_dict pin_slack [get_property [get_pins $pin_name] "slack_max"]
      dict set pin_dict is_startpoint [dict exists $start_points $pin_name]
      dict set pin_dict is_endpoint [dict exists $end_points $pin_name]
      dict set pin_dict maxtran $maxtran
      dict set pin_dict num_reachable_endpoint $num_reachable_endpoint
      dict set pin_dict x [get_pin_x $ITerm]
      dict set pin_dict y [get_pin_y $ITerm]
      dict set pin_dict pin_rise_arr [get_pin_arr [get_pin $pin_name] "rise"]
      dict set pin_dict pin_fall_arr [get_pin_arr [get_pin $pin_name] "fall"]
      dict set pin_dict pin_tran [get_pin_slew [get_pin $pin_name] $corner]
      dict set pin_dict input_pin_cap [get_pin_input_cap $pin_name $corner]
    } else {
      continue
    } 
    } else {
      dict set pin_dict net_name $pin_net_name
      dict set pin_dict pin_name $pin_name
      dict set pin_dict cell_name $cell_name
      dict set pin_dict is_in_clk "NA"
      dict set pin_dict dir [$ITerm isOutputSignal]
      dict set pin_dict pin_slack [get_property [get_pins $pin_name] "slack_max"]
      dict set pin_dict is_startpoint [dict exists $start_points $pin_name]
      dict set pin_dict is_endpoint [dict exists $end_points $pin_name]
      dict set pin_dict maxtran $maxtran
      dict set pin_dict num_reachable_endpoint 0
      dict set pin_dict x [get_pin_x $ITerm]
      dict set pin_dict y [get_pin_y $ITerm]
      dict set pin_dict pin_rise_arr [get_pin_arr [get_pin $pin_name] "rise"]
      dict set pin_dict pin_fall_arr [get_pin_arr [get_pin $pin_name] "fall"]
      dict set pin_dict pin_tran [get_pin_slew [get_pin $pin_name] $corner]
      dict set pin_dict input_pin_cap [get_pin_input_cap $pin_name $corner]
    }

    #################################################
    #build cell-pin edge table & cell-net edge table#
    #################################################
    if {[$ITerm isInputSignal]} {
      puts $cell_pin_outfile "${pin_name},${cell_name},pin,cell"
      puts $cell_net_outfile "${pin_net_name},${cell_name},net,cell"
      lappend input_pins $pin_name
      dict set pin_dict maxcap 0
    } elseif {[$ITerm isOutputSignal]} {
      puts $cell_pin_outfile "${cell_name},${pin_name},cell,pin"
      puts $cell_net_outfile "${cell_name},${pin_net_name},cell,net"
      lappend output_pins $pin_name
      dict set pin_dict maxcap $maxcap
    }
      print_pin_property_entry $pin_outfile $pin_dict
  }
  ##########################
  #build pin-pin edge table#
  ##########################
  if {$is_macro == 0 && $is_seq == 0 } {
    print_ip_op_pairs $pin_pin_outfile $input_pins $output_pins 0 $corner
  }
  #power
  dict set cell_dict cell_static_power [get_cell_leakage_power $cell_name $corner]

  set internal_power [get_cell_internal_power $cell_name $corner]
  set switch_power [get_cell_switch_power $cell_name $corner]
  dict set cell_dict cell_dynamic_power [expr {$switch_power + $internal_power}]
  
  #check if cell is in clk
  dict set cell_dict is_in_clk $cell_is_in_clk
  print_cell_property_entry $cell_outfile $cell_dict
}
set post_insts_loop [clock seconds]

close $cell_outfile
close $cell_pin_outfile
close $cell_net_outfile
close $pin_outfile

set net_outfile [open $net_file w]
set header {net_name net_route_length net_steiner_length fanout total_cap net_cap net_coupling net_res}
puts $net_outfile [join $header ","]

set net_pin_outfile [open $net_pin_file w]
puts $net_pin_outfile "src,tar,src_type,tar_type"

######################
#iterate through nets#
######################
foreach net $nets {
  set net_name [$net getName]
  if {!([::sta::Net_is_power [get_net $net_name]] || [::sta::Net_is_ground [get_net $net_name]])} {
    set total_cap [::sta::Net_capacitance [get_net $net_name] $corner max]
    set net_ITerms [$net getITerms]

    dict set net_dict net_name $net_name
    dict set net_dict net_cap [[get_net $net_name] wire_capacitance $corner max]
    dict set net_dict net_res [$net getTotalResistance]
    dict set net_dict net_coupling [$net getTotalCouplingCap]
    
    set input_pins {}
    set output_pins {}
    set input_cells {}
    set output_cells {}
    ##########################
    #build net-pin edge table#
    ##########################
    set net_ITerms [$net getITerms]
    foreach ITerm $net_ITerms {
      set ITerm_name [get_ITerm_name $ITerm]
      set cell_ITerm_name [[$ITerm getInst] getName]
      if {[$ITerm isInputSignal]} {
        puts $net_pin_outfile "${net_name},${ITerm_name},net,pin"
        lappend output_pins $ITerm_name;
        lappend output_cells $cell_ITerm_name;
      } elseif {[$ITerm isOutputSignal]} {
        puts $net_pin_outfile "${ITerm_name},${net_name},pin,net"
        lappend input_pins $ITerm_name;
        lappend input_cells $cell_ITerm_name;
      }
    }

    dict set net_dict fanout [llength $output_pins] 
    dict set net_dict total_cap $total_cap
    dict set net_dict net_route_length [get_net_route_length $net]
    print_net_property_entry $net_outfile $net_dict
    #################################################
    #build pin-pin edge table & cell-cell edge table#
    #################################################
    print_ip_op_pairs $pin_pin_outfile $input_pins $output_pins 1 $corner
    print_ip_op_cell_pairs $cell_cell_outfile $input_cells $output_cells

  }
}

close $net_outfile
close $net_pin_outfile
close $pin_pin_outfile
close $cell_cell_outfile

set post_nets_loop [clock seconds]

set libcell_outfile [open $libcell_file w]
set header {libcell_name func_id libcell_area worst_input_cap libcell_leakage fo4_delay fix_load_delay}
puts $libcell_outfile [join $header ","]

set libs [$db getLibs]
#set libs [get_libs *]
set func_id -1
dict set func_dict start -1

############################
#set fix load reference cap#
############################
#set fix_load_insts [get_fix_load_load_cells "sky130_fd_sc_hd__inv_1"]
#set fix_load_insts [get_fix_load_load_cells "INV_X1"]
set fix_load_insts [get_fix_load_load_cells "INVx1_ASAP7_75t_R"]

###########################
#iterate through libraries#
###########################
foreach sta_lib [get_libs *] {
    ::sta::make_equiv_cells $sta_lib
}

foreach lib $libs {
  set lib_name [$lib getName]
  #if {[string first "NangateOpenCellLibrary"  $lib_name] != -1} {
  #  set sta_lib [get_libs "NangateOpenCellLibrary"]
  #} else {
  #  set sta_lib [get_libs $lib_name]
  #}
  #set sta_lib $lib
  #::sta::make_equiv_cells $sta_lib 
  set lib_masters [$lib getMasters]

  foreach master $lib_masters {
    set libcell_name [$master getName]
    
    ###########################
    #filter duplicate libcells#
    ###########################
    if {[info exists libcell_name_map]} {
      if {[dict exists $libcell_name_map $libcell_name]} {
        continue  
      } else {
        dict set libcell_name_map $libcell_name 0
      }
    } else {
      dict set libcell_name_map $libcell_name 0
    }   
    
    #leakage power
    dict set libcell_dict libcell_leakage [get_libcell_leakage_power $libcell_name $corner]

    set res [find_func_id $func_dict $libcell_name]
    set func_id [lindex $res 1]
    if {[lindex $res 0] == 0} {
      dict set func_dict $libcell_name $func_id
    }
    
    dict set libcell_dict libcell_name $libcell_name
    dict set libcell_dict libcell_area [expr [$master getHeight] * [$master getWidth]]
    dict set libcell_dict fo4_delay [get_fo4_delay $libcell_name $corner]
    dict set libcell_dict fix_load_delay [get_fix_load_delay $libcell_name $corner $fix_load_insts]
    dict set libcell_dict func_id $func_id
    dict set libcell_dict worst_input_cap [get_libcell_worst_input_pin_cap $libcell_name $corner]
    print_libcell_property_entry $libcell_outfile $libcell_dict
  }
}

close $libcell_outfile

set post_libs_loop [clock seconds]

foreach fix_load_inst $fix_load_insts {
  ::sta::delete_instance $fix_load_inst
}
set final [clock seconds]

puts $fp_log "Time after load design : $post_load ; Difference: [expr $post_load-$t1]"
puts $fp_log "Time after getting start and endpoints : $post_ep_sp  ; Difference: [expr $post_ep_sp-$post_load]"
puts $fp_log "Time after getting sequential cells : $post_seq_cells ; Difference: [expr $post_seq_cells-$post_ep_sp]"
puts $fp_log "Time after insts loop : $post_insts_loop ; Difference: [expr $post_insts_loop-$post_seq_cells]"
puts $fp_log "Time after nets loop : $post_nets_loop ; Difference: [expr $post_nets_loop-$post_insts_loop]"
puts $fp_log "Time after libs loop : $post_libs_loop ; Difference: [expr $post_libs_loop-$post_nets_loop]"
puts $fp_log "total time : [expr $final-$t1]"
close $fp_log
exit

