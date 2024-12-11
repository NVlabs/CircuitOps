import pandas as pd
import numpy as np
from graph_tool.all import *
from numpy.random import *
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn import preprocessing
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from sklearn.metrics import mean_squared_error, max_error, mean_absolute_error
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../src/")

from circuitops_api import *

def generate_dataset(IR_path):
    # Generate LPG and properties dataframes
    circuit_data = CircuitData(IR_path)
    
    # Extract required dataframes from master class
    pin_props = circuit_data.pin_props
    pin_pin_edge = circuit_data.pin_pin_edge
    cell_props = circuit_data.cell_props

    # Calculate load capacitance
    output_pins = pin_props.get_output_pins()
    pin_pin_edge = pin_pin_edge.calculate_load_cap(output_pins, circuit_data)

    # Get only pin arcs inside cells
    cell_pin_arcs_df = pin_pin_edge.get_arcs("cell")
    
    # Merge input tran and cell type to pins
    cell_pin_arcs_df = cell_pin_arcs_df.merge_tran_cell(circuit_data)
 
    return cell_pin_arcs_df.df

def generate_ML_data(cell_pin_arcs_df):
    # ML data extraction
    # Features: input tran, load cap, cell type
    # Label: arc delay

    data = cell_pin_arcs_df.loc[:,['pin_tran','output_cap','cell_type_coded','arc_delay']]
    X = data.iloc[:, :-1]
    y = data.iloc[:, -1]
    
    # Splitting into train and test datasets
    X_train, X_test, y_train, Y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Normalizing the feature columns
    scaler = StandardScaler()
    X_train_normalized = scaler.fit_transform(X_train)
    X_test_normalized = scaler.transform(X_test)
    
    return X_train_normalized, X_test_normalized, y_train, Y_test

def train_rf_model(X_train, Y_train):
    # Training the RF model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, Y_train)
    return model

def evaluate_model(model, X_test, Y_test):
    # Making predictions
    Y_predict = model.predict(X_test)
    
    mse = mean_squared_error(Y_test, Y_predict)
    mae = mean_absolute_error(Y_test,Y_predict)
    rmse = np.sqrt(mse)
    max_err = max_error(Y_test, Y_predict)
    
    print("Mean Absolute Error (MAE):", mae)
    print("Mean Squared Error (MSE):", mse)
    print("Root Mean Squared Error (RMSE):", rmse)
    
    Y_predict = Y_predict.reshape(-1)
    errors = Y_predict - Y_test
    abs_errors = abs(errors)
    error_percentages = (abs_errors / Y_test) * 100
    mean_percent = sum(error_percentages) / len(error_percentages)
    print("Max Error : ", max(abs_errors))
    print("Maximum Error %:", max(error_percentages))
    print("Mean Error %:", mean_percent)

if __name__ == "__main__":

     # Set the Circuitops path
    cops_path = "/home/vgopal18/Circuitops/CircuitOps/IRs/"
    design_name = "gcd"
    platform = "nangate45"

    IR_path = f"{cops_path}/{platform}/{design_name}/"
    
    cell_pin_arcs_df = generate_dataset(IR_path)

    X_train, X_test, Y_train, Y_test = generate_ML_data(cell_pin_arcs_df)

    model = train_rf_model(X_train, Y_train)

    evaluate_model(model, X_test, Y_test)
