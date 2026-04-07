import os
import pandas as pd
import numpy as np
from scipy import stats

# Configuration
SCENARIO = "Scarce_PenaltyTrap" # The scenario where HybridQIGA shines
ALGO_A = "HybridQIGA"
ALGO_B = "GA"             # The baseline to beat
NUM_RUNS = 5
METRIC = "latency"        # We want to prove HybridQIGA is faster (Reliability)

def load_run_metric(scenario, run_id, algorithm, metric):
    # Path matches your main.py output structure: scheme/outputs/{scenario}/run_{id}/{algo}_best_population.csv
    path = f"scheme/outputs/{scenario}/run_{run_id}/{algorithm}_best_population.csv"
    
    try:
        df = pd.read_csv(path)
        # We assume the CSV contains the final population. 
        # For 'latency', lower is better. We take the mean of the top solution or the whole population.
        # Let's take the BEST (min) latency found in that run to be fair.
        val = df[metric].min()
        return val
    except FileNotFoundError:
        print(f"Warning: File not found {path}")
        return None

def run_statistical_test():
    print(f"--- RESEARCH VALIDATION: {ALGO_A} vs {ALGO_B} ---")
    print(f"Scenario: {SCENARIO}")
    print(f"Metric: {METRIC} (Lower is Better)\n")

    data_a = []
    data_b = []

    # 1. Collect Data
    for i in range(1, NUM_RUNS + 1):
        val_a = load_run_metric(SCENARIO, i, ALGO_A, METRIC)
        val_b = load_run_metric(SCENARIO, i, ALGO_B, METRIC)
        
        if val_a is not None and val_b is not None:
            data_a.append(val_a)
            data_b.append(val_b)

    if len(data_a) < 2:
        print("Not enough data to run t-test. Run simulations first.")
        return

    # 2. Calculate Statistics
    mean_a = np.mean(data_a)
    std_a = np.std(data_a)
    mean_b = np.mean(data_b)
    std_b = np.std(data_b)

    print(f"{ALGO_A} Results: {data_a}")
    print(f"{ALGO_B} Results: {data_b}")
    print(f"\nMean {ALGO_A}: {mean_a:.4f} (Std: {std_a:.4f})")
    print(f"Mean {ALGO_B}: {mean_b:.4f} (Std: {std_b:.4f})")

    # 3. Perform T-Test (Independent samples)
    t_stat, p_value = stats.ttest_ind(data_a, data_b, equal_var=False)

    print(f"\n--- T-TEST RESULTS ---")
    print(f"T-Statistic: {t_stat:.4f}")
    print(f"P-Value: {p_value:.4f}")

    # 4. Scientific Conclusion
    alpha = 0.05
    print("\n>>> CONCLUSION:")
    if p_value < alpha:
        if mean_a < mean_b:
            print(f"SUCCESS! {ALGO_A} is STATISTICALLY SIGNIFICANTLY better (lower {METRIC}) than {ALGO_B}.")
            print(f"You can claim this in your paper with 95% confidence.")
        else:
            print(f"Result is significant, but {ALGO_A} is WORSE (higher {METRIC}). Check your logic.")
    else:
        print(f"The difference is NOT statistically significant (p >= {alpha}).")
        print("In the paper, you must state: 'While HybridQIGA showed improved average performance, statistical significance was not established with the current number of runs.'")

if __name__ == "__main__":
    run_statistical_test()