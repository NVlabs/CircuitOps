# Liberty units are fF,kOhm
set_layer_rc -layer M1 -resistance 1.3889e-01 -capacitance 1.1368e-01
set_layer_rc -layer M2 -resistance 2.4222e-02 -capacitance 1.3426e-01
set_layer_rc -layer M3 -resistance 2.4222e-02 -capacitance 1.2918e-01
set_layer_rc -layer M4 -resistance 1.6778e-02 -capacitance 1.1396e-01
set_layer_rc -layer M5 -resistance 1.4677e-02 -capacitance 1.3323e-01
set_layer_rc -layer M6 -resistance 1.0371e-02 -capacitance 1.1575e-01
set_layer_rc -layer M7 -resistance 9.6720e-03 -capacitance 1.3293e-01
set_layer_rc -layer M8 -resistance 7.4310e-03 -capacitance 1.1822e-01
set_layer_rc -layer M9 -resistance 6.8740e-03 -capacitance 1.3497e-01

set_wire_rc -signal -layer M3
set_wire_rc -clock  -layer M5
