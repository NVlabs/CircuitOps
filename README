# CircuitOps

## Introduction

CircuitOps is a data infrastructure to facilitate dataset generation and model deployment in Generative AI (GAI)-based circuit optimization tasks. It mainly has the following contributes:
1) Shared Intermediate Representation: labeled property graphs (LPGs) backed by relational tables, a flexible way to represent detailed netlist information and suitable for parallel processing;
2) Tools-agnostic IR generation: parsing standard EDA files and attributes tables to generate LPGs for given netlists, which can be reused for many
downstream GAI applications;
3) Customizable dataset generation: generating a customized dataset for each GAI application by performing on the AI-friendly LPGs;
4) Inference with gRPC-based data transfer: facilitating the
deployment of GAI models into production.

The following figure depicts the overview of CircuitOps. Based on the Intermediate Representation of labeled property graphs, CircuitOps consists of two main modules: IR generation and dataset generation.
The IR generation module transforms standard EDA files into LPGs
that store netlist information and are reused across tasks. The taskspecific dataset is constructed with the dataset generation module
using its AI-friendly data structures and interfaces. CircuitOps also
provides a gRPC-based data transfer method facilitating inference
of GAI models in production deployment.



## Dependency
pandas
graph-tool
numpy
dgl
openroad
