import pandas as pd
import os
import numpy as np

# --- Configuration ---
SCENARIOS_TO_ANALYZE = [
    "Base_Case",
    "High_Load",
    "Data_Heavy",
    "Compute_Heavy",
    "Resource_Scarce"
]
ALGORITHMS = ["QIGA", "MOHEFT", "RR", "RA", "OE", "OC"]
NUM_RUNS = 5  # The number of runs you did
BASE_OUTPUT_DIR = "scheme/outputs"
# ---------------------------

print("Analyzing Champion Schedules (Best-in-Class for each Metric)...")

# This will hold the "best possible" score for each algo in each scenario
final_champion_results = []

for scenario in SCENARIOS_TO_ANALYZE:
    
    # This will store the "best" results from all 5 runs
    run_champions = []

    for run_id in range(1, NUM_RUNS + 1):
        for algo in ALGORITHMS:
            file_path = f"{BASE_OUTPUT_DIR}/{scenario}/run_{run_id}/{algo}_best_population.csv"
            
            try:
                df = pd.read_csv(file_path)
                
                # --- THIS IS THE NEW LOGIC ---
                # Instead of .mean(), we find the .min() for each objective.
                # This finds the "champion" schedule for that metric
                # from the algorithm's final population.
                best_cost = df['cost'].min()
                best_energy = df['energy'].min()
                best_latency = df['latency'].min()
                
                run_champions.append({
                    "Scenario": scenario,
                    "Algorithm": algo,
                    "Best Cost": best_cost,
                    "Best Energy": best_energy,
                    "Best Latency": best_latency
                })
            except Exception:
                pass # Skip missing files

    if not run_champions:
        continue
    
    # Now we average the "best scores" from all 5 runs
    scenario_df = pd.DataFrame(run_champions)
    final_avg_champions_df = scenario_df.groupby('Algorithm').agg(
        avg_best_cost=('Best Cost', 'mean'),
        avg_best_energy=('Best Energy', 'mean'),
        avg_best_latency=('Best Latency', 'mean')
    ).reset_index()
    
    final_champion_results.append((scenario, final_avg_champions_df))

# --- Print the Final Report ---
print("\n\n--- FINAL EXPERIMENT SUMMARY (CHAMPION ANALYSIS) ---")

for scenario_name, results_df in final_champion_results:
    print(f"\n=======================================================")
    print(f"   CHAMPION Results for Scenario: {scenario_name}")
    print(f"   (This is the *best possible schedule* each algorithm found, averaged over 5 runs)")
    print(f"=======================================================\n")
    
    # Print one table for each metric
    print("--- LATENCY CHAMPIONS (Lowest is best) ---")
    print(results_df.sort_values(by='avg_best_latency').to_markdown(index=False, floatfmt=".2f"))
    
    print("\n--- COST CHAMPIONS (Lowest is best) ---")
    print(results_df.sort_values(by='avg_best_cost').to_markdown(index=False, floatfmt=".2f"))
    
    print("\n--- ENERGY CHAMPIONS (Lowest is best) ---")
    print(results_df.sort_values(by='avg_best_energy').to_markdown(index=False, floatfmt=".2f"))