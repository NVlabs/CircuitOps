# Sample IR tables
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
