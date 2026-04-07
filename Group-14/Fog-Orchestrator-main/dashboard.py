import pandas as pd
import os
import json
import glob
import re
import streamlit as st
import subprocess
import sys
from pathlib import Path
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Fog Scheduler Digital Twin")

# --- Configuration ---
BASE_OUTPUT_DIR = "scheme/outputs"
DATASET_DIR = "datasets"
# Updated algorithm list
ALGORITHMS = ["HybridQIGA", "QIGA", "MOHEFT", "GA", "PSO", "DE", "RR", "RA", "OE", "OC","SQIGA","SHybridQIGA"]

try:
    from main import NUM_RUNS
except ImportError:
    NUM_RUNS = 5

PYTHON_EXECUTABLE = sys.executable 
ROOT_DIR = str(Path(__file__).parent.resolve())

# --- Helper: Get Available Scenarios ---
def get_available_scenarios():
    files = glob.glob(os.path.join(ROOT_DIR, DATASET_DIR, "*_ES-*.json"))
    scenarios = []
    for f in files:
        filename = os.path.basename(f)
        match = re.match(r"(.+)_ES-(\d+)_ED-(\d+)\.json", filename)
        if match:
            scenarios.append(match.group(1))
    return sorted(list(set(scenarios)))

# --- Helper: Find Dataset File ---
def get_dataset_path(scenario_name):
    search_pattern = os.path.join(ROOT_DIR, DATASET_DIR, f"{scenario_name}_ES-*.json")
    files = glob.glob(search_pattern)
    if files:
        return files[0]
    return None

# --- Layout Caching Engine ---
@st.cache_data
def get_fixed_layout(scenario_name):
    file_path = get_dataset_path(scenario_name)
    if not file_path: return None

    with open(file_path, 'r') as f:
        data = json.load(f)

    G = nx.Graph()
    
    if "BaseStation" in data:
        for bs in data["BaseStation"]: G.add_node(f"BS_{bs['attributes']['id']}")
    if "NetworkLink" in data:
        for link in data["NetworkLink"]:
            try:
                n1 = link["relationships"]["nodes"][0]["id"]
                n2 = link["relationships"]["nodes"][1]["id"]
                G.add_edge(f"BS_{n1}", f"BS_{n2}", weight=5) 
            except: pass
    if "EdgeServer" in data:
        for s in data["EdgeServer"]:
            sid = s['attributes']['id']
            bs_id = s['relationships']['base_station']['id']
            G.add_edge(f"S_{sid}", f"BS_{bs_id}", weight=2) 
    if "User" in data:
        for u in data["User"]:
            uid = u['attributes']['id']
            bs_id = u['relationships']['base_station']['id']
            G.add_edge(f"U_{uid}", f"BS_{bs_id}", weight=1)

    pos = nx.spring_layout(G, k=3.0, iterations=100, seed=42)
    
    scale = 3000
    scaled_pos = {node: {'x': coords[0] * scale, 'y': coords[1] * scale} for node, coords in pos.items()}
    return scaled_pos

# --- Visualizer Engine ---
def generate_network_html(scenario_name, algorithm_to_trace=None, run_id=1, use_physics=False):
    file_path = get_dataset_path(scenario_name)
    if not file_path: return None

    fixed_positions = get_fixed_layout(scenario_name)
    
    with open(file_path, 'r') as f:
        data = json.load(f)

    # CALCULATE LOAD
    server_load = {}
    if algorithm_to_trace and algorithm_to_trace != "None":
        assign_path = os.path.join(ROOT_DIR, BASE_OUTPUT_DIR, scenario_name, f"run_{run_id}", f"{algorithm_to_trace}_assignments.json")
        if os.path.exists(assign_path):
            with open(assign_path, 'r') as f:
                assignments = json.load(f)
                for uid, sid in assignments.items(): server_load[sid] = server_load.get(sid, 0) + 1

    net = Network(height="750px", width="100%", bgcolor="#1E1E1E", font_color="white")
    
    if use_physics:
        net.barnes_hut(gravity=-2000, central_gravity=0.1, spring_length=200, spring_strength=0.05, damping=0.09, overlap=0)
    else:
        net.toggle_physics(False)

    # Base Stations
    if "BaseStation" in data:
        for bs in data["BaseStation"]:
            bid = bs["attributes"]["id"]
            node_id = f"BS_{bid}"
            x, y = fixed_positions.get(node_id, {'x': 0, 'y': 0}).values()
            
            if not use_physics:
                net.add_node(node_id, label=f"BS {bid}", title="Intersection", color="#333333", size=10, shape="square", x=x, y=y)
            else:
                net.add_node(node_id, label=f"BS {bid}", title="Intersection", color="#333333", size=10, shape="square")

    # Servers (Traffic Lights)
    if "EdgeServer" in data:
        for s in data["EdgeServer"]:
            sid = s["attributes"]["id"]
            model = s["attributes"]["model_name"]
            node_id = f"S_{sid}"
            bs_id = s["relationships"]["base_station"]["id"]
            
            load = server_load.get(sid, 0)
            
            # Tier Styling
            if "Cloud" in model: 
                color = "#FF4B4B"; size = 45; shape = "star"; label = f"☁️ Cloud ({load})"
                width = 4
            elif "E5430" in model: 
                color = "#FFA500"; size = 25; shape = "triangle"; label = f"Fog Srv ({load})"
                width = 3
            else: 
                # Traffic Light Logic
                is_congested = load > 5 
                color = "#FF0000" if is_congested else "#00FF00"
                shape = "diamond" if is_congested else "dot"
                label = f"🚦 JAM ({load})" if is_congested else f"🟢 OK ({load})"
                size = 20
                width = 2
            
            x, y = fixed_positions.get(node_id, {'x': 0, 'y': 0}).values()
            
            if not use_physics:
                net.add_node(node_id, label=label, title=f"{model}\nLoad: {load}", color=color, shape=shape, size=size, x=x, y=y)
            else:
                net.add_node(node_id, label=label, title=f"{model}\nLoad: {load}", color=color, shape=shape, size=size)
            
            net.add_edge(node_id, f"BS_{bs_id}", color=color, width=width)

    # Users
    if "User" in data:
        for u in data["User"]:
            uid = u["attributes"]["id"]
            node_id = f"U_{uid}"
            bs_id = u["relationships"]["base_station"]["id"]
            
            x, y = fixed_positions.get(node_id, {'x': 0, 'y': 0}).values()
            
            if not use_physics:
                net.add_node(node_id, label=f"🚗 {uid}", title=f"Vehicle {uid}", color="#00C0F2", size=10, shape="text", x=x, y=y)
            else:
                net.add_node(node_id, label=f"🚗 {uid}", title=f"Vehicle {uid}", color="#00C0F2", size=10, shape="text")
                
            net.add_edge(node_id, f"BS_{bs_id}", color="#444444", width=1, dashes=True)

    # Traceroute
    if algorithm_to_trace and algorithm_to_trace != "None":
        assign_path = os.path.join(ROOT_DIR, BASE_OUTPUT_DIR, scenario_name, f"run_{run_id}", f"{algorithm_to_trace}_assignments.json")
        if os.path.exists(assign_path):
            with open(assign_path, 'r') as f: assignments = json.load(f)
            for uid_str, sid_str in assignments.items():
                u_node = f"U_{uid_str}"
                s_node = f"S_{sid_str}"
                try:
                    # Bright Yellow Route
                    net.add_edge(u_node, s_node, color="#FFFF00", width=3, title=f"Route")
                except: pass

    # Network Links
    if "NetworkLink" in data:
        for link in data["NetworkLink"]:
            try:
                n1 = link["relationships"]["nodes"][0]["id"]
                n2 = link["relationships"]["nodes"][1]["id"]
                node1, node2 = f"BS_{n1}", f"BS_{n2}"
                if node1 in fixed_positions and node2 in fixed_positions:
                    net.add_edge(node1, node2, color="#252525", width=1)
            except: pass

    return net.generate_html()

# --- Data Loading ---
@st.cache_data
def load_and_process_data():
    all_scenario_results = {}
    try:
        scenario_folders = [d for d in os.listdir(BASE_OUTPUT_DIR) if os.path.isdir(os.path.join(BASE_OUTPUT_DIR, d))]
    except FileNotFoundError: return {} 

    for scenario in scenario_folders:
        scenario_runs_data = []
        for run_id in range(1, NUM_RUNS + 1):
            for algo in ALGORITHMS:
                file_path = os.path.join(ROOT_DIR, BASE_OUTPUT_DIR, scenario, f"run_{run_id}", f"{algo}_best_population.csv")
                try:
                    df = pd.read_csv(file_path)
                    scenario_runs_data.append({
                        "Scenario": scenario, "Run": run_id, "Algorithm": algo,
                        "Cost": df['cost'].mean(), "Energy": df['energy'].mean(), "Latency": df['latency'].mean()
                    })
                except: pass 
        if scenario_runs_data:
            df = pd.DataFrame(scenario_runs_data)
            final_avg_df = df.groupby('Algorithm').agg(
                avg_cost=('Cost', 'mean'),
                avg_energy=('Energy', 'mean'),
                avg_latency=('Latency', 'mean')
            ).reset_index()
            
            # --- NEW: Calculate Weighted Score ---
            # Formula: (0.1 * Energy) + (0.8 * Latency) + (0.1 * Cost)
            final_avg_df['weighted_score'] = (final_avg_df['avg_energy'] * 0.2) + \
                                             (final_avg_df['avg_latency'] * 0.7) + \
                                             (final_avg_df['avg_cost'] * 0.1)
        
            all_scenario_results[scenario] = final_avg_df
            
    return all_scenario_results

# --- Main UI ---
st.title("🏭 Fog Scheduler Digital Twin")

# Sidebar
with st.sidebar:
    st.header("Admin Controls")
    
    # --- GENERATOR ---
    with st.form(key="generator_form"):
        st.subheader("1. Generate New Scenario")
        scenario_name = st.text_input("Scenario Name", "Base_Case")
        num_users = st.number_input("Number of Users", 50)
        num_tier1 = st.number_input("Tier 1 Nodes", 15)
        num_tier2 = st.number_input("Tier 2 Servers", 4)
        st.write("Task Parameters:")
        avg_weight = st.slider("Compute Weight (x 10e9)", 1, 50, 3)
        avg_data_size = st.slider("Data Size (MB)", 100, 5000, 500)
        deadline = st.number_input("Deadline", 30.0)
        submit_generate = st.form_submit_button("Generate Dataset")

    if submit_generate:
        st.info("Generating...")
        cmd = [PYTHON_EXECUTABLE, "generate_scenario.py", "--scenario_name", scenario_name, "--users", str(num_users), "--tier1", str(num_tier1), "--tier2", str(num_tier2), "--avg_weight", str(avg_weight), "--avg_data_size", str(avg_data_size), "--deadline", str(deadline)]
        subprocess.run(cmd, cwd=ROOT_DIR)
        st.success("Done!")
        st.cache_data.clear(); st.rerun()

    # --- SIMULATOR (SELECTIVE) ---
    st.subheader("2. Run Simulation")
    
    # 1. Get available scenarios
    available_scenarios = get_available_scenarios()
    
    # 2. Multiselect Box
    selected_scenarios = st.multiselect(
        "Select Scenarios to Run:", 
        available_scenarios,
        default=None,
        help="Choose which datasets to run experiments on."
    )
    
    # 3. Run Selected Button
    if st.button("Run Selected Scenarios"):
        if not selected_scenarios:
            st.error("Please select at least one scenario.")
        else:
            st.info(f"Running simulation for: {', '.join(selected_scenarios)}...")
            with st.spinner("Simulating..."):
                # Pass the list of selected names to main.py
                cmd = [PYTHON_EXECUTABLE, "main.py", "--scenarios"] + selected_scenarios
                process = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
                
            if process.returncode == 0:
                st.success("Complete!")
                st.cache_data.clear(); st.rerun()
            else:
                st.error("Error:"); st.code(process.stderr)

    # 4. Run ALL Button (Fallback)
    if st.button("Run ALL Scenarios (Slow)"):
        st.warning("Running ALL available scenarios. This might take a while...")
        with st.spinner("Simulating Everything..."):
            cmd = [PYTHON_EXECUTABLE, "main.py"] # No args = run all
            subprocess.run(cmd, cwd=ROOT_DIR)
        st.success("All Complete!")
        st.cache_data.clear(); st.rerun()

# --- DASHBOARD TABS ---
all_results = load_and_process_data()

if not all_results:
    st.info("👋 No results found. Generate a dataset and run a simulation to start.")
else:
    tab_list = st.tabs(list(all_results.keys()))

    for i, (scenario_name, results_df) in enumerate(all_results.items()):
        with tab_list[i]:
            st.markdown(f"### 🗺️ Digital Twin Topology: {scenario_name}")
            
            c1, c2 = st.columns([3, 1])
            with c1: algo_trace = st.selectbox("Trace Traffic:", ["None"] + ALGORITHMS, key=f"tr_{scenario_name}")
            with c2: use_physics = st.checkbox("Enable Physics", False, key=f"ph_{scenario_name}")

            html = generate_network_html(scenario_name, algo_trace, use_physics=use_physics)
            if html: components.html(html, height=760)
            else: st.warning("Blueprint not found.")
            
            st.divider()
            st.markdown("### 📊 KPI Analysis")
            
            # --- UPDATED: 4 Columns to include Weighted Score ---
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.subheader("Cost"); st.bar_chart(results_df, x="Algorithm", y="avg_cost", color="#FF4B4B")
            with c2: st.subheader("Energy"); st.bar_chart(results_df, x="Algorithm", y="avg_energy", color="#00C0F2")
            with c3: st.subheader("Latency"); st.bar_chart(results_df, x="Algorithm", y="avg_latency", color="#00A968")
            with c4: st.subheader("Weighted Score"); st.bar_chart(results_df, x="Algorithm", y="weighted_score", color="#FFA500")
            
            # Show table sorted by Weighted Score
            st.dataframe(results_df.sort_values(by=['weighted_score']))