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

proc check_inst_is_in_clk {inst clk_nets} {
  set is_in_clk 0
  set cell_pins [$inst getITerms]
  foreach cell_pin $cell_pins {
    set pin_nets [$cell_pin getNet]
    foreach pin_net $pin_nets {
      foreach clk_net $clk_nets {
        if {$pin_net == $clk_net} {
          set is_in_clk 1
          break
        }
      }
      if {$is_in_clk eq 1} {
        break
      }
    }
    if {$is_in_clk eq 1} {
      break
    }
  }
  return $is_in_clk
}

proc check_pin_is_in_clk {pin clk_nets} {
  set is_in_clk 0
  set pin_nets [$pin getNet]
  foreach pin_net $pin_nets {
    foreach clk_net $clk_nets {
      if {$pin_net == $clk_net} {
        set is_in_clk 1
        break
      }
    }
    if {$is_in_clk eq 1} {
      break
    }
  }
  return $is_in_clk
}

proc get_net_route_length {net} {
  set net_route_length 0
  set net_name [$net getName]

  if {[::sta::Net_is_power [get_net $net_name]] || [::sta::Net_is_ground [get_net $net_name]]} {
    set swire [$net getSWires]
    set wires [$swire getWires]
  } else {
    set wires [$net getWire]
  }
  foreach wire $wires {
    if {$wire eq "NULL"} {
      continue
    } else {
      set wire_length [$wire getLength]
      set net_route_length [expr {$net_route_length + $wire_length}]
    }
  }
  return $net_route_length
}

proc get_pin_arr {pin_arg rf} {
  set pin [::sta::get_port_pin_error "pin" $pin_arg]
  set pin_arr {}
  foreach vertex [$pin vertices] {
    if { $vertex != "NULL" } {
      if {$rf == "rise"} {
        set tmp_pin_arr [get_pin_arr_time $vertex "arrivals_clk" "NULL" "rise" "arrive"]
      } else {
        set tmp_pin_arr [get_pin_arr_time $vertex "arrivals_clk" "NULL" "rise" "hold"]
      }
      if {$tmp_pin_arr != ""} {
        lappend pin_arr $tmp_pin_arr
      }

      if {$rf == "rise"} {
        set tmp_pin_arr [get_pin_arr_time $vertex "arrivals_clk" [::sta::default_arrival_clock] "rise" "arrive"]
      } else {
        set tmp_pin_arr [get_pin_arr_time $vertex "arrivals_clk" [::sta::default_arrival_clock] "rise" "hold"]
      }
      if {$tmp_pin_arr != ""} {
        lappend pin_arr $tmp_pin_arr
      }
      
      foreach clk [all_clocks] {
        if {$rf == "rise"} {
          set tmp_pin_arr [get_pin_arr_time $vertex "arrivals_clk" $clk "rise" "arrive"]
        } else {
          set tmp_pin_arr [get_pin_arr_time $vertex "arrivals_clk" $clk "rise" "hold"]
        }
        if {$tmp_pin_arr != ""} {
          lappend pin_arr $tmp_pin_arr
        }

        if {$rf == "rise"} {
          set tmp_pin_arr [get_pin_arr_time $vertex "arrivals_clk" $clk "fall" "arrive"]
        } else {
          set tmp_pin_arr [get_pin_arr_time $vertex "arrivals_clk" $clk "fall" "hold"]
        }
        if {$tmp_pin_arr != ""} {
          lappend pin_arr $tmp_pin_arr
        }
      }
    }
  }
  set delay -1
  foreach delay_ $pin_arr {
    if {$delay_ > $delay} {
      set delay $delay_
    }
  }
  return $delay
}

proc get_pin_arr_time {vertex what clk clk_rf arrive_hold} {
  set rise [$vertex $what rise $clk $clk_rf]
  set fall [$vertex $what fall $clk $clk_rf]
  # Filter INF/-INF arrivals.
  set delay -1
  if { !([::sta::times_are_inf $rise] && [::sta::times_are_inf $fall]) } {
    if {$arrive_hold == "arrive"} {
      foreach delay_ $rise {
        if {!([::sta::times_are_inf $delay_])} {
          if {$delay_ > $delay} {
            set delay $delay_
          }
        }
      }
    } else {
      foreach delay_ $fall {
        if {!([::sta::times_are_inf $delay_])} {
          if {$delay_ > $delay} {
            set delay $delay_
          }
        }
      }
    }
  }
  return $delay
}


proc get_pin_slew {pin_arg corner} {
  global sta_report_default_digits
  set pin [::sta::get_port_pin_error "pin" $pin_arg]
  set digits $sta_report_default_digits
  set pin_slew -1
  foreach vertex [$pin vertices] {
    set pin_slew_ [$vertex slew_corner rise $corner max]
    if {$pin_slew_ > $pin_slew} {
      set pin_slew $pin_slew_
    }
  }
  return $pin_slew
}

#report_edge
proc print_ip_op_pairs {outfile input_pins output_pins is_net corner} {
  foreach i_p_ $input_pins {
    foreach o_p_ $output_pins {
      set input_pin [get_pin $i_p_]
      set output_pin [get_pin $o_p_]
      set arc_delays {}
      foreach from_vertex [$input_pin vertices] {
        foreach to_vertex [$output_pin vertices] {
          set iter [$from_vertex out_edge_iterator]
          while {[$iter has_next]} {
            set edge [$iter next]
            if { [$edge to] == $to_vertex } {
              set arc_delays_ [get_arc_delay $edge $corner]
              lappend arc_delays $arc_delays_
            }  
          }
        }
      }
      if {[llength $arc_delays] > 0} {
        set arc_delay -1
        foreach arc_delays_ $arc_delays {
          if {$arc_delays_ > $arc_delay} {
            set arc_delay $arc_delays_
          }
        }
      } else {
        set arc_delay " "
      }
      puts $outfile "${i_p_},${o_p_},pin,pin,$is_net,$arc_delay"
    }
  }
}

proc get_arc_delay {edge corner} {
  set delays_ -1
  foreach arc [$edge timing_arcs] {
    set delays [$edge arc_delay $arc $corner max]
    if {$delays > $delays_} {
      set delays_ $delays
    }
  }
  return $delays_
}

proc get_fix_load_delay {inst corner fix_load_insts tmp_net} {
  set inst_ITerms [$inst getITerms]
  foreach inst_ITerm $inst_ITerms {
    set pin_name [get_ITerm_name $inst_ITerm]
    if {[$inst_ITerm isInputSignal]} {
      if {[info exists input_pin]} {
        unset input_pin
      }
      set input_pin [get_pin $pin_name]
    }
    if {[$inst_ITerm isOutputSignal]} {
      if {[info exists output_pin]} {
         unset output_pin
      }
      set output_pin [get_pin $pin_name]
    }
  }

  set fix_load_inst_pins {}
  foreach fix_load_sta_inst $fix_load_insts {
    set fix_load_inst [::sta::sta_to_db_inst $fix_load_sta_inst]
    set fix_load_inst_ITerms [$fix_load_inst getITerms]
    foreach fix_load_inst_ITerm $fix_load_inst_ITerms {
      if {[$fix_load_inst_ITerm isInputSignal]} {
        set fix_load_inst_pin_name [get_ITerm_name $fix_load_inst_ITerm]
        set fix_load_inst_pin [get_pin $fix_load_inst_pin_name]
        lappend fix_load_inst_pins $fix_load_inst_pin
      }
    }
  }
  
  foreach fix_load_inst_pin $fix_load_inst_pins {
    ::sta::connect_pin $tmp_net $fix_load_inst_pin
  }

  set fix_load_delays {}
  if {[info exist input_pin] && [info exist output_pin]} {
    foreach from_vertex [$input_pin vertices] {
      foreach to_vertex [$output_pin vertices] {
        set iter [$from_vertex out_edge_iterator]
        while {[$iter has_next]} {
          set edge [$iter next]
          if { [$edge to] == $to_vertex } {
            set arc_delays_ [get_arc_delay $edge $corner]
            lappend fix_load_delays $arc_delays_
          }
        }
        $iter finish
      }
    }
    unset input_pin
    unset output_pin
  }
  set fix_load_delay -1
  if {[llength $fix_load_delays] > 0} {
    foreach fix_load_delays_ $fix_load_delays {
      if {$fix_load_delays_ > $fix_load_delay} {
        set fix_load_delay $fix_load_delays_
      }
    }
  }
  if {$fix_load_delay == -1} {
    set fix_load_delay None
  }
  return $fix_load_delay      
}


proc get_fo4_delay {inst corner tmp_net lib_cell} {
  set inst_ITerms [$inst getITerms]
  foreach inst_ITerm $inst_ITerms {
    set pin_name [get_ITerm_name $inst_ITerm]
    if {[$inst_ITerm isInputSignal]} {
      if {[info exists input_pin]} {
        unset input_pin
      }
      set input_pin [get_pin $pin_name]
    }
  }
  foreach inst_ITerm $inst_ITerms {
    set pin_name [get_ITerm_name $inst_ITerm]
    if {[$inst_ITerm isOutputSignal]} {
      if {[info exists output_pin]} {
        unset output_pin
      }
      set output_pin [get_pin $pin_name]
    }
  }
  
  set fo4_load_insts {}
  for {set i 0} {$i < 4} {incr i} {
    set fo4_load_ref_inv_inst [::sta::make_instance tmp_inst$i$i $lib_cell]
    set fo4_load_ref_inv_db_inst [::sta::sta_to_db_inst $fo4_load_ref_inv_inst]
    lappend fo4_load_insts $fo4_load_ref_inv_inst
  }

  set fo4_load_inst_pins {}  
  foreach fo4_load_sta_inst $fo4_load_insts {
    set fo4_load_inst [::sta::sta_to_db_inst $fo4_load_sta_inst]
    set fo4_load_inst_ITerms [$fo4_load_inst getITerms]
    foreach fo4_load_inst_ITerm $fo4_load_inst_ITerms {
      if {[$fo4_load_inst_ITerm isInputSignal]} {
        set fo4_load_inst_pin_name [get_ITerm_name $fo4_load_inst_ITerm]
        set fo4_load_inst_pin [get_pin $fo4_load_inst_pin_name]
        lappend fo4_load_inst_pins $fo4_load_inst_pin
      }
    }
  }
  foreach fo4_load_inst_pin $fo4_load_inst_pins {
    ::sta::connect_pin $tmp_net $fo4_load_inst_pin
  }

  set fo4_delays {}
  if {[info exist input_pin] && [info exist output_pin]} {
    foreach from_vertex [$input_pin vertices] {
      foreach to_vertex [$output_pin vertices] {
        set iter [$from_vertex out_edge_iterator]
        while {[$iter has_next]} {
          set edge [$iter next]
          if { [$edge to] == $to_vertex } {
            set arc_delays_ [get_arc_delay $edge $corner]
            lappend fo4_delays $arc_delays_
          }
        }
        $iter finish
      }
    }
    unset input_pin
    unset output_pin
  }
  set fo4_delay -1
  if {[llength $fo4_delays] > 0} {
    foreach fo4_delays_ $fo4_delays {
      if {$fo4_delays_ > $fo4_delay} {
        set fo4_delay $fo4_delays_
      }
    }
  }
  if {$fo4_delay == -1} {
    set fo4_delay None
  }
  
  foreach fo4_load_inst_pin $fo4_load_inst_pins {
    ::sta::disconnect_pin $tmp_net $fo4_load_inst_pin
  }
  foreach fo4_load_inst $fo4_load_insts {
    ::sta::delete_instance $fo4_load_inst
  }
  unset fo4_load_insts
  return $fo4_delay
}

proc load_design {def netlist libs tech_lef lefs sdc design spef} {
  foreach libFile $libs {
    read_liberty $libFile
  }
  read_lef $tech_lef
  foreach lef $lefs {
    read_lef $lef
  }
  read_def $def
  read_spef $spef
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

proc print_ip_op_cell_pairs {outfile inputs outputs} {
  foreach input $inputs {
    foreach output $outputs {
      puts $outfile "${input},${output},cell,cell"
    }
  }
}

proc get_ports {net} {
  set patterns [string map {\\ \\\\} [lindex $net 0]]
  set ports {}
  foreach pattern $patterns {
    set matches [::sta::find_ports_matching $pattern 0 0]
    if { $matches != {} } {
      set ports [concat $ports $matches]
    }
  }
  return $ports
}

proc report_flute_net { net } {
  set pins [lassign $net net_name drvr_index]
  set xs {}
  set ys {}
  foreach pin $pins {
    lassign $pin pin_name x y
    lappend xs $x
    lappend ys $y
  }
  stt::report_flute_tree $xs $ys 0
}

proc print_pin_property_entry {outfile pin_props} {
  set pin_entry {}
  lappend pin_entry [dict get $pin_props "pin_name"];#pin_name 
  lappend pin_entry [dict get $pin_props "x"];#x
  lappend pin_entry [dict get $pin_props "y"];#y
  lappend pin_entry [dict get $pin_props "is_in_clk"];#is_in_clk
  lappend pin_entry "-1";#is_port
  lappend pin_entry [dict get $pin_props "is_startpoint"];#is_startpoint
  lappend pin_entry [dict get $pin_props "is_endpoint"];#is_endpoint
  lappend pin_entry [dict get $pin_props "dir"];#dir 
  lappend pin_entry "-1";#maxcap
  lappend pin_entry [dict get $pin_props "maxtran"];#maxtran
  lappend pin_entry [dict get $pin_props "num_reachable_endpoint"];#num_reachable_endpoint
  lappend pin_entry [dict get $pin_props "cell_name"];#cell_name 
  lappend pin_entry [dict get $pin_props "net_name"];#net_name 
  lappend pin_entry [dict get $pin_props "pin_tran"];#pin_tran
  lappend pin_entry [dict get $pin_props "pin_slack"];#pin_slack
  lappend pin_entry [dict get $pin_props "pin_rise_arr"];#pin_rise_arr
  lappend pin_entry [dict get $pin_props "pin_fall_arr"];#pin_fall_arr
  lappend pin_entry [dict get $pin_props "input_pin_cap"];#input_pin_cap
  puts $outfile [join $pin_entry ","]
}

proc print_cell_property_entry {outfile cell_props} {
  set cell_entry {}
  lappend cell_entry [dict get $cell_props "cell_name"];#cell_name 
  lappend cell_entry [dict get $cell_props "is_seq"];#is_seq
  lappend cell_entry [dict get $cell_props "is_macro"];#is_macro
  lappend cell_entry [dict get $cell_props "is_in_clk"];#is_in_clk
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
  lappend net_entry [dict get $net_props "net_route_length"];#net_route_length
  lappend net_entry "-1";#net_steiner_length
  lappend net_entry [dict get $net_props "fanout"];#fanout
  lappend net_entry [dict get $net_props "total_cap"];#total_cap
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
  lappend libcell_entry [dict get $libcell_props "worst_input_cap"];#worst_input_cap(*5)
  lappend libcell_entry [dict get $libcell_props "libcell_leakage"];#libcell_leakage
  lappend libcell_entry [dict get $libcell_props "fo4_delay"];#fo4_delay
  lappend libcell_entry [dict get $libcell_props "fix_load_delay"];#libcell_delay_fixed_load
  puts $outfile [join $libcell_entry ","]
}


