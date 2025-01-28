# Scripts for IR Table Generation

The `scripts` folder contains scipts to generate Intermediate Representation (IR) tables for any design. 

---
### Prerequisite: Add Design Data

Before running the IR generation scripts, make sure you have a folder for your design in the [designs](./designs) folder and it contains the design files (def, sdc, spef and netlist).

### Generate IRs from OpenROAD using TCL

#### Set design and platform

Modify [set_design.tcl](./scripts/tcl/set_design.tcl) to name the design and platform. If you need to add more designs, add them to the designs directory and modify the set_design.tcl file appropriately.

Also modify the **fixed_load_cell** in set_design.tcl, which provides the type of cell that should be used to calculate the fixed load delay for cells.

#### Run OpenROAD and TCL scripts to generate relational tables

The following command to generate the relations tables in the ./IRs/ directory.

```./path/to/binary/openroad ./scripts/tcl/generate_tables.tcl```

### Generate IRs from OpenROAD using Python
Run the following command to generate the relations tables in the ./IRs/ directory.

```
./path/to/binary/openroad -python ./scripts/python/generate_tables.py -w 1 -d <design_name>  -t <tech_node>

Arguments of python script:
-w --> [0 | 1] Store IR tables into csv files. Default: 0
-d --> To provide the design name for which IR table should be generated. Default: "gcd"
-t --> To provide the technology node. Default: "nangate45"
```
