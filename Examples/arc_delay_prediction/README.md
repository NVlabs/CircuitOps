# Arc delay predictor
It is a simple random forest regressor based model that predicts the cell delay with input slew and load capacitance.
This script is generated mainly to provide an example on how to use CircuitOps APIs for dataset geenration.

## Usage
```
python3 arc_delay_prediction.py -d "gcd" -t "nangate45"

Arguments:
-d --> Optional argument to provide design name. Default: gcd
-t --> Optional argyment to provide tech node. Default: nangate45

Make sure you already have the IR tables generated for the design needed.
IR tables location: ./IRs/<technode>/<design>/
```
