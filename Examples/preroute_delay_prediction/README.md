# Pre-route delay predictor
This is a cross-stage timing predictor.
It uses a random forest regressor to predict the post-route net delay between stages in a post-placement design.

This script is based on the paper:

E. C. Barboza, N. Shukla, Y. Chen and J. Hu, "Machine Learning-Based Pre-Routing Timing Prediction with Reduced Pessimism," 2019 56th ACM/IEEE Design Automation Conference (DAC), Las Vegas, NV, USA, 2019, pp. 1-6.


## Usage
```
python3 preroute_delay_prediction.py -d "gcd" -t "nangate45"

Arguments:
-d --> Optional argument to provide design name. Default: gcd
-t --> Optional argyment to provide tech node. Default: nangate45

Make sure you already have the IR tables generated for the design needed.
IR tables location: ./IRs/<technode>/<design>/
```
