# Arc delay predictor
It is a simple random forest regressor based model that predicts the worst-case arc delay with input slew, load capacitance and cell type as it's input features. 
This script is developed mainly to provide an example on how to use CircuitOps APIs for dataset generation. However it can also be used to replace the lookup table based arc delay extraction with an estimator that is differentiable.

## Usage
```
python3 arc_delay_prediction.py -d "gcd" -t "nangate45"

Arguments:
-d --> Optional argument to provide design name. Default: gcd
-t --> Optional argyment to provide tech node. Default: nangate45

Make sure you already have the IR tables generated for the design needed.
IR tables location: ./IRs/<technode>/<design>/
```
