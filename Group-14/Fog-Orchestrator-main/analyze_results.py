import pandas as pd
import os

# --- Configuration ---

# List the scenarios you ran (must match folder names)
SCENARIOS_TO_ANALYZE = [
    "Base_Case",
    "High_Load"
]

# The algorithms we're comparing
ALGORITHMS = ["QIGA", "MOHEFT", "RR", "RA", "OE", "OC"]

# The number of runs you did for each scenario
NUM_RUNS = 5 

# The root output directory
BASE_OUTPUT_DIR = "scheme/outputs"

# --- End Configuration ---

all_scenario_results = {}

print("Starting analysis of all experiment runs...")

for scenario in SCENARIOS_TO_ANALYZE:
    print(f"\nAnalyzing Scenario: {scenario}")
    
    # This will store the results for all 5 runs
    scenario_runs_data = []

    for run_id in range(1, NUM_RUNS + 1):
        for algo in ALGORITHMS:
            file_path = f"{BASE_OUTPUT_DIR}/{scenario}/run_{run_id}/{algo}_best_population.csv"
            
            try:
                df = pd.read_csv(file_path)
                
                # Get the average of the final population for this run
                avg_cost = df['cost'].mean()
                avg_energy = df['energy'].mean()
                avg_latency = df['latency'].mean()
                
                scenario_runs_data.append({
                    "Scenario": scenario,
                    "Run": run_id,
                    "Algorithm": algo,
                    "Cost": avg_cost,
                    "Energy": avg_energy,
                    "Latency": avg_latency
                })

            except FileNotFoundError:
                print(f"  [Warning] File not found, skipping: {file_path}")
            except Exception as e:
                print(f"  [Error] Could not read {file_path}: {e}")

    # Convert all results for this scenario into a DataFrame
    if not scenario_runs_data:
        print(f"  [Error] No data found for scenario: {scenario}")
        continue
        
    scenario_df = pd.DataFrame(scenario_runs_data)
    
    # Calculate the final average across all 5 runs
    final_avg_df = scenario_df.groupby('Algorithm').agg(
        avg_cost=('Cost', 'mean'),
        avg_energy=('Energy', 'mean'),
        avg_latency=('Latency', 'mean')
    ).reset_index()
    
    # Store it for the final report
    all_scenario_results[scenario] = final_avg_df

# --- Print the Final Report ---
print("\n\n--- FINAL EXPERIMENT SUMMARY ---")

for scenario_name, results_df in all_scenario_results.items():
    print(f"\n======================================")
    print(f"   Results for Scenario: {scenario_name}")
    print(f"   (Averaged over {NUM_RUNS} runs)")
    print(f"======================================")
    
    # Sort by Cost, then Energy, then Latency
    results_df = results_df.sort_values(by=['avg_cost', 'avg_energy', 'avg_latency'])
    
    print(results_df.to_markdown(index=False, floatfmt=".2f"))