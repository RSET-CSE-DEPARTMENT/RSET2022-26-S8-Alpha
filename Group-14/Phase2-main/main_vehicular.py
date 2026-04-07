import glob
import os
import argparse
import re
import traci

from edge_sim_py import *
from vehicular_runtime.scheduler_loop import DynamicSchedulerLoop
from config import *

# ----------------------------------------------------
# Build data dictionary used by scheduler
# ----------------------------------------------------
def build_data_dict():
    data = {
        'BaseStation': BaseStation,
        'EdgeServer': EdgeServer,
        'User': User,  
        'NetworkSwitch': NetworkSwitch,
        'NetworkLink': NetworkLink
    }
    return data

# ----------------------------------------------------
# Prepare output folders
# ----------------------------------------------------
def prepare_output_dirs():
    os.makedirs("vehicular_outputs", exist_ok=True)

# ----------------------------------------------------
# MAIN ENTRY
# ----------------------------------------------------
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Run SUMO with GUI")
    parser.add_argument('--scenarios', nargs='+', help='List of specific scenario names to run')
    args = parser.parse_args()

    print("\n=======================================================")
    print("🚗 VEHICULAR FOG ORCHESTRATION - BATCH SCENARIO RUNNER")
    print("=======================================================")

    prepare_output_dirs()

    # 1️⃣ Fetch all datasets
    dataset_files = glob.glob("datasets/*.json")

    if not dataset_files:
        print("❌ No datasets found in /datasets folder.")
        print("Run your dashboard/scenario generator first.")
        exit()

    print(f"📂 Found {len(dataset_files)} datasets to process.\n")

    # Regex to extract scenario names like "HighwayBase_ES-20_ED-0.json"
    filename_regex = re.compile(r"datasets[/\\](.+)_ES-(\d+)_ED-(\d+)\.json")

    for dataset_path in dataset_files:
        # 2️⃣ Extract Scenario Name for organized output folders
        match = filename_regex.search(dataset_path)
        if not match:
            filename = os.path.basename(dataset_path)
            match = re.match(r"(.+)_ES-(\d+)_ED-(\d+)\.json", filename)
            
        if match:
            base_scenario_name = match.group(1)
            es_count = match.group(2)
            scenario_folder_name = f"{base_scenario_name}_ES-{es_count}"
        else:
            scenario_folder_name = os.path.basename(dataset_path).replace('.json', '')
            base_scenario_name = scenario_folder_name

        # Dashboard Filtering Logic
        if args.scenarios and base_scenario_name not in args.scenarios:
            continue

        print("\n" + "=".ljust(70, "="))
        print(f"🚀 STARTING SCENARIO: {scenario_folder_name}")
        print(f"📂 Dataset file: {dataset_path}")
        print("=".ljust(70, "="))

        # 3️⃣ Ensure clean state for EdgeSimPy
        simulator = Simulator()
        simulator.initialize(input_file=dataset_path)

        # 4️⃣ Prepare data dictionary for algorithms
        data = build_data_dict()

        # 5️⃣ Start dynamic vehicular orchestration loop
        runtime = DynamicSchedulerLoop(
            simulator=simulator, 
            data=data, 
            use_gui=args.gui, 
            scenario_name=scenario_folder_name
        )
        runtime.run()

        # 6️⃣ Failsafe: Ensure SUMO TraCI is closed before the next iteration
        try:
            traci.close()
        except traci.exceptions.FatalTraCIError:
            pass 

    print("\n✅ All batch scenarios completed successfully!")
    print("📈 Check the 'vehicular_outputs' folder for organized results.")