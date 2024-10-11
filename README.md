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
The IR generation module transforms standard EDA files into LPGs
that store netlist information and are reused across tasks. The taskspecific dataset is constructed with the dataset generation module
using its AI-friendly data structures and interfaces. CircuitOps also
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

Modify [set_design.tcl](./src/tcl/set_design.tcl) to name the design and platform. If you need to add more designs, add them to the designs directory and modify the set_design.tcl file appropriately.

##### Run OpenROAD and TCL scripts to generate relational tables

The following command to generate the relations tables in the ./IRs/ directory.

```./path/to/binary/openroad ./src/tcl/generate_tables.tcl```

#### Generate IRs from OpenROAD using Python
Run the following command to generate the relations tables in the ./IRs/ directory.

```./path/to/binary/openroad -python ./src/python/generate_tables.py -w 1 -d <design_name>  -t <tech_node>
Arguments of python script:
-w --> [0 | 1] Store IR tables into csv files. Default: 0
-d --> To provide the design name for which IR table should be generated. Default: "gcd"
-t --> To provide the technology node. Default: "nangate45"
```

#### Sample IR tables
There are IR tables available for a number of designs in Nangate45, asap7 and sky130hd tech nodes in this git repo. This can be used by engineers for ML applications.

The list of designs available are given in the table below along with post filler instance count and runtime to generate IR tables using python script for these designs.

|Technode |Design              |# of instances|IR generation runtime (hrs)|Core utilisation|
|---------|--------------------|--------------|---------------------------|----------------|
|asap7    |gcd                 |1387          |0.0025                     |Default ORFS    |
|asap7    |uart                |1679          |0.0033                     |Default ORFS    |
|asap7    |mock-array_Element  |7994          |0.01                       |Default ORFS    |
|asap7    |ibex                |48237         |0.7024                     |Default ORFS    |
|asap7    |NV_NVDLA_partition_m|65353         |0.4797                     |30              |
|asap7    |NV_NVDLA_partition_a|111207        |1.734                      |30              |
|asap7    |jpeg                |169095        |3.2999                     |Default ORFS    |
|asap7    |NV_NVDLA_partition_p|215140        |5.0925                     |30              |
|asap7    |NV_NVDLA_partition_c|499581        |29.2552                    |30              |
|nangate45|gcd                 |752           |0.0019                     |Default ORFS    |
|nangate45|aes                 |30202         |0.3463                     |Default ORFS    |
|nangate45|ibex                |32111         |0.3906                     |Default ORFS    |
|nangate45|bp_fe               |96150         |0.9967                     |Default ORFS    |
|nangate45|bp_be               |141468        |2.1523                     |Default ORFS    |
|nangate45|jpeg                |141651        |4.1475                     |Default ORFS    |
|nangate45|swerv               |193054        |10.1427                    |Default ORFS    |
|sky130hd |gcd                 |1181          |0.0035                     |Default ORFS    |
|sky130hd |riscv32i            |20104         |0.1235                     |Default ORFS    |
|sky130hd |ibex                |42487         |0.5446                     |Default ORFS    |
|sky130hd |aes                 |64389         |0.2879                     |Default ORFS    |
|sky130hd |jpeg                |140975        |2.9748                     |Default ORFS    |

#### Generate Datasets
```cd src/python```

```python BT_sampling_OpenROAD.py ../../IRs/nangate45/gcd/ ../../datasets/```

#### gRPC-based Data Transfer



## Cite this work

* R. Liang, A. Agnesina, G. Pradipta, V. A. Chhabria and H. Ren, "**CircuitOps: An ML Infrastructure Enabling Generative AI for VLSI Circuit Optimization**", 2023 IEEE/ACM International Conference on Computer Aided Design (ICCAD). ([preprint](https://ieeexplore.ieee.org/abstract/document/10323611))

