# CircuitOps
(Notice: This Github repository is currently in the progress of being developed and some files are still missing. We will try to complete it ASAP. Thanks for your patience!)
## Introduction

CircuitOps is a data infrastructure to facilitate dataset generation and model deployment in Generative AI (GAI)-based circuit optimization tasks. It mainly has the following contributes:
1) Shared Intermediate Representation: labeled property graphs (LPGs) backed by relational tables, a flexible way to represent detailed netlist information and suitable for parallel processing;
2) Tools-agnostic IR generation: parsing standard EDA files and attributes tables to generate LPGs for given netlists, which can be reused for many
downstream GAI applications;
3) Customizable dataset generation: generating a customized dataset for each GAI application by performing on the AI-friendly LPGs;
4) Inference with gRPC-based data transfer: facilitating the
deployment of GAI models into production.

Figure.1 depicts the overview of CircuitOps. Based on the Intermediate Representation of labeled property graphs, CircuitOps consists of two main modules: IR generation and dataset generation.
The IR generation module transforms standard EDA files into IR tables and LPGs
that store netlist information and are reused across tasks. The taskspecific dataset is constructed with the dataset generation module
using its AI-friendly data structures and APIs. CircuitOps also
provides a gRPC-based data transfer method facilitating inference
of GAI models in production deployment.

<img src="etc/CircuitOps-overview.png"
     alt="Markdown Monster icon"
     style="float: left; margin-right: 10px;" />

Fig. 1: CircuitOps overview. (a) shows the structure of CircuitOps; (b) illustrates the netlist labeled property graph backed by relational tables.


## Getting Started

Download the CircuitOps repository as shown below:


```
git clone --recursive https://github.com/NVlabs/CircuitOps.git
cd CircuitOps
```


### Install CircuitOps


#### Dependencies

The following dependencies are needed by CircuitOps. OpenROAD is required for EDA tools file parsing and generating properties.

- python3.7
- pip3
- OpenROAD


#### Install OpenROAD

Refer to the dependencies of the OpenROAD Project and instrcutions [here](https://openroad.readthedocs.io/en/latest/main/README.html#build-openroad).

We use OpenROAD to read in standard EDA files and generate relational tables as IRs.


TLDR instructions to build OpenROAD is listed below:

```
cd CircuitOps/src/OpenROAD
mkdir build
cd build
cmake ..
make -j
```

#### Install CircuitOps in Bash

From the IRs, CircuitOps uses the relational tables generated from OpenROAD and creates LPGs and datasets.  Installation of Python scripts of Circuit ops in described below through a virtual environment and pip.  From the CircuitOps top level directory run the following commands:

```
python3 -m venv circuitops
source circuitops/bin/activate
pip3 install -r requirements.txt
```

### Use CircuitOps


#### Generate IRs from OpenROAD using TCL

##### Set design and platform

Modify [set_design.tcl](./scripts/tcl/set_design.tcl) to name the design and platform. If you need to add more designs, add them to the designs directory and modify the set_design.tcl file appropriately.

Also modify the **fixed_load_cell** in set_design.tcl, which provides the type of cell that should be used to calculate the fixed load delay for cells.

##### Run OpenROAD and TCL scripts to generate relational tables

The following command to generate the relations tables in the ./IRs/ directory.

```./path/to/binary/openroad ./scripts/tcl/generate_tables.tcl```

#### Generate IRs from OpenROAD using Python
Run the following command to generate the relations tables in the ./IRs/ directory.

```
./path/to/binary/openroad -python ./scripts/python/generate_tables.py -w 1 -d <design_name>  -t <tech_node>

Arguments of python script:
-w --> [0 | 1] Store IR tables into csv files. Default: 0
-d --> To provide the design name for which IR table should be generated. Default: "gcd"
-t --> To provide the technology node. Default: "nangate45"
```

#### Sample IR tables
There are IR tables available for a number of designs in Nangate45, asap7 and sky130hd tech nodes in this git repo. This can be used by engineers for ML applications.

The list of designs available are given in the table below along with post filler instance count and runtime to generate IR tables using python script for these designs.

|Technode |Design              |# of instances|IR generation runtime (mins)|Core utilisation|
|---------|--------------------|--------------|----------------------------|----------------|
|asap7    |gcd                 |1387          |0.15                        |Default ORFS    |
|asap7    |uart                |1679          |0.20                        |Default ORFS    |
|asap7    |mock-array_Element  |7994          |0.60                        |Default ORFS    |
|asap7    |ibex                |48237         |42.14                       |Default ORFS    |
|asap7    |NV_NVDLA_partition_m|65353         |28.78                       |30              |
|asap7    |NV_NVDLA_partition_a|111207        |104.04                      |30              |
|asap7    |jpeg                |169095        |197.99                      |Default ORFS    |
|asap7    |NV_NVDLA_partition_p|215140        |305.55                      |30              |
|asap7    |NV_NVDLA_partition_c|499581        |1755.31                     |30              |
|nangate45|gcd                 |752           |0.11                        |Default ORFS    |
|nangate45|aes                 |30202         |20.78                       |Default ORFS    |
|nangate45|ibex                |32111         |23.44                       |Default ORFS    |
|nangate45|bp_fe               |96150         |59.80                       |Default ORFS    |
|nangate45|bp_be               |141468        |129.14                      |Default ORFS    |
|nangate45|jpeg                |141651        |248.85                      |Default ORFS    |
|nangate45|swerv               |193054        |608.56                      |Default ORFS    |
|sky130hd |gcd                 |1181          |0.21                        |Default ORFS    |
|sky130hd |riscv32i            |20104         |7.41                        |Default ORFS    |
|sky130hd |ibex                |42487         |32.68                       |Default ORFS    |
|sky130hd |aes                 |64389         |17.27                       |Default ORFS    |
|sky130hd |jpeg                |140975        |178.49                      |Default ORFS    |

#### Generate Datasets
Once the IR tables are generated we can use CircuitOps APIs to generate application specific datasets. Import [circuitops_api.py](./src/circuitops_api.py)  file in your python code to use these APIs.

Use the following command to create a CircuitData class which will contain all the properties and edge IR tables as classes. It also has the LPG object implemented using graph-tool. There are few APIs associated with each class and its documentation is given at[to be added].
```
circuit_data = CircuitData(IR_path)

Arguments:
IR_path --> Path to the directory with IR table files of a design.
```
 
Three example applications are given at ./Examples folder, to help understand how to use the CircuitOps APIs.

```cd src/python```

```python BT_sampling_OpenROAD.py ../../IRs/nangate45/gcd/ ../../datasets/```

#### gRPC-based Data Transfer



## Cite this work

* R. Liang, A. Agnesina, G. Pradipta, V. A. Chhabria and H. Ren, "**CircuitOps: An ML Infrastructure Enabling Generative AI for VLSI Circuit Optimization**", 2023 IEEE/ACM International Conference on Computer Aided Design (ICCAD). ([preprint](https://ieeexplore.ieee.org/abstract/document/10323611))

