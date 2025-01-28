# CircuitOps APIs  

Once the IR tables are generated we can use CircuitOps APIs to generate application specific datasets. 
Import [circuitops_api.py](./src/circuitops_api.py)  file in your python code to use these APIs.

Use the following command to create a CircuitData class which will contain all the properties and edge IR tables as classes. 
It also has the LPG object implemented using graph-tool. 
There are few APIs associated with each class and its documentation is given at [CircuitOps_API_documentation.pdf](./docs/CircuitOps_API_documentation.pdf).

Here’s an example:  

```python
from circuitops_api import *  

# Initialize CircuitData with the path to the IR tables  
circuit_data = CircuitData(IR_path="path/to/IR_tables")  

# Access LPG and other components  
lpg = circuit_data.graph  
cell_props = circuit_data.cell_props  
net_props = circuit_data.net_props
```

### CircuitData Class  

The `CircuitData` class is designed to simplify access to CircuitOps data. 
It organizes the various components of the IR tables and LPG into structured attributes.  

#### Elements of `CircuitData`  

- **`CircuitData`**
  - **`graph`**  
    - A graph-tool object representing the Labeled Property Graph (LPG).  
  - **`pin_props`**  
    - DataFrame containing properties of pins in the design.  
  - **`cell_props`**  
    - DataFrame with information about cells.  
  - **`net_props`**  
    - DataFrame capturing properties of nets.  
  - **`design_props`**  
    - DataFrame with metadata about the overall design, such as design name, utilization, and technology node.  
  - **`libcell_props`**  
    - DataFrame with details of library cells.  
  - **`pin_pin_edge`**  
    - Edge table representing connections between pins in the LPG.  
  - **`cell_pin_edge`**  
    - Edge table representing connections between cells and pins in the LPG.  
  - **`net_pin_edge`**  
    - Edge table capturing the relationships between nets and pins in the LPG.  
  - **`cell_cell_edge`**  
    - Edge table representing logical connections between cells.  
  - **`cell_net_edge`**  
    - Edge table capturing the association between cells and nets.  
---

### Example usecases
Also look into the [examples folder](./examples) for scripts of some complete ML applications which uses CircuitOps for dataset generation.
This can help to get a better understanding on how to use CircuitOps.

