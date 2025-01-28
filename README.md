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
The IR generation module transforms standard EDA files into IR tables and LPGs
that store netlist information and are reused across tasks. The taskspecific dataset is constructed with the dataset generation module
using its AI-friendly data structures and APIs. CircuitOps also
provides a gRPC-based data transfer method facilitating inference
of GAI models in production deployment.

<img src="etc/CircuitOps-overview.png"
     alt="Markdown Monster icon"
     style="float: left; margin-right: 10px;" />

Fig. 1: CircuitOps overview. (a) shows the structure of CircuitOps; (b) illustrates the netlist labeled property graph backed by relational tables.


## Initial Setup

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

This repository provides scripts to generate IR tables, sample IR tables of open source designs, APIs for processing and analyzing these tables, and example applications demonstrating how to use CircuitOps.

---

## Repository Structure

The repository is organized as follows:

1. **[Scripts for IR Generation](./scripts)**  
   Scripts to generate IR tables using TCL or Python from OpenROAD.

2. **[Sample designs](./designs)**  
   Design files for various open source designs across a few technology nodes.

3. **[Sample platforms](./platforms)**  
   Technology specific files for asap7, nangate45 and sky130hd technology nodes.
   
4. **[Sample IR Tables](./IRs)**  
   Pre-existing IR tables for various designs across a few technology nodes.

5. **[CircuitOps APIs](./src)**  
   Python APIs for preprocessing the IR tables and LPGs to generate application specific datasets.

6. **[Example Applications](./examples)**  
   Use case examples showcasing how to apply CircuitOps APIs.

---

## Quick Start Guide

### 1. Generate IR Tables
- First step to use CircuitOps is to generate the IR tables for the desired designs.
- Use **TCL scripts** or **Python scripts** in OpenROAD to generate IR tables.  
- Detailed instructions are provided in the [scripts folder README](./scripts/README.md).

### 2. Sample IR Tables
- Pre-existing IR tables for popular designs (e.g., gcd, aes, jpeg) across different technology nodes (asap7, nangate45, sky130hd) are available for direct use.  
- Details on available designs and their specifications are in the [sample_IRs folder README](./IRs/README.md).

### 3. Use CircuitOps APIs
- Once the IR tables are present for the desired designs CircuitOps APIs can be used to preprocess the data and geenrate custom application specific datasets.
- The `circuitops_api.py` provides a central API for accessing and analyzing IR tables.  
- See the [src folder README](./src/README.md) for usage details.

### 4. Example Applications
- Some ML use cases are provided in the [examples folder](./examples). See the [examples folder README](./examples/README.md) for detailed information.
- This can be helpful to understand how to use CircuitOps to generate custom datasets.

---


## Cite this work

* R. Liang, A. Agnesina, G. Pradipta, V. A. Chhabria and H. Ren, "**CircuitOps: An ML Infrastructure Enabling Generative AI for VLSI Circuit Optimization**", 2023 IEEE/ACM International Conference on Computer Aided Design (ICCAD). ([preprint](https://ieeexplore.ieee.org/abstract/document/10323611))

