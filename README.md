# CircuitOps

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



``` git clone --recursive https://github.com/NVlabs/CircuitOps.git```


### Install CircuitOps


#### Dependencies

The following dependencies are needed by CircuitOps. OpenROAD is required for EDA tools file parsing and generating properties. 

- python3.7
- pip3
- OpenROAD


#### Install OpenROAD

Refer to the dependencies of the OpenROAD Project and instrcutions here incase of issues for OpenROAD installation.

TLDR instructions to build OpenROAD is listed below:


```
cd CircuitOps/src/OpenROAD
mkdir build
cd build
cmake ..
make -j
```

#### Install CircuitOps in Bash


```
python3 -m venv circuitops
source openpdn/bin/activate
pip3 install -r requirements.txt
```

### Use CircuitOps


#### Generate IRs from OpenROAD


#### Generate LPGs


#### Generate Datasets


## Cite this work


