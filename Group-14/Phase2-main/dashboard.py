import pandas as pd
import os
import glob
import re
import streamlit as st
import subprocess
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Vehicular Fog Simulator", page_icon="🚗")

# --- Configuration ---
DATASET_DIR = "datasets"
OUTPUT_DIR = "vehicular_outputs"

PYTHON_EXECUTABLE = sys.executable 
ROOT_DIR = str(Path(__file__).parent.resolve())

# Safely create directories if starting fresh
os.makedirs(os.path.join(ROOT_DIR, DATASET_DIR), exist_ok=True)
os.makedirs(os.path.join(ROOT_DIR, OUTPUT_DIR), exist_ok=True)

# --- Helper Functions ---
def get_available_scenarios():
    files = glob.glob(os.path.join(ROOT_DIR, DATASET_DIR, "*_ES-*.json"))
    scenarios = []
    for f in files:
        filename = os.path.basename(f)
        match = re.match(r"(.+)_ES-(\d+)_ED-(\d+)\.json", filename)
        if match:
            scenarios.append(f"{match.group(1)}_ES-{match.group(2)}")
        else:
            scenarios.append(filename.replace(".json", ""))
    return sorted(list(set(scenarios)))

# Custom Min-Max Scaler
def minmax_scale(series):
    if series.max() == series.min(): return [0.5] * len(series)
    return (series - series.min()) / (series.max() - series.min())

@st.cache_data
def load_vehicular_data():
    all_results = {}
    if not os.path.exists(OUTPUT_DIR): return {}
    
    scenario_folders = [d for d in os.listdir(OUTPUT_DIR) if os.path.isdir(os.path.join(OUTPUT_DIR, d))]
    
    for scenario in scenario_folders:
        scenario_path = os.path.join(OUTPUT_DIR, scenario)
        algo_folders = [d for d in os.listdir(scenario_path) if os.path.isdir(os.path.join(scenario_path, d))]
        
        scenario_dataframes = []
        for algo in algo_folders:
            algo_path = os.path.join(scenario_path, algo)
            run_folders = [d for d in os.listdir(algo_path) if d.startswith("run_")]
            
            algo_runs = []
            for run in run_folders:
                csv_path = os.path.join(algo_path, run, "runtime_metrics.csv")
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    df['Algorithm'] = algo
                    df['Run_ID'] = run
                    algo_runs.append(df)
            
            if algo_runs:
                combined_algo_df = pd.concat(algo_runs, ignore_index=True)
                averaged_algo_df = combined_algo_df.groupby(['Algorithm', 'time']).agg({
                    'active_vehicles': 'mean', 
                    'tasks_generated': 'mean',
                    'latency': 'mean',
                    'energy': 'mean',
                    'cost': 'mean',
                    'missed_deadlines': 'mean'
                }).reset_index()
                
                averaged_algo_df['sla_violation_rate'] = (averaged_algo_df['missed_deadlines'] / averaged_algo_df['tasks_generated']) * 100
                averaged_algo_df['sla_violation_rate'] = averaged_algo_df['sla_violation_rate'].fillna(0)
                
                scenario_dataframes.append(averaged_algo_df)
                
        if scenario_dataframes:
            all_results[scenario] = pd.concat(scenario_dataframes, ignore_index=True)
            
    return all_results

# ==============================================================================
# MAIN UI
# ==============================================================================
st.title("🚗 Vehicular Fog Orchestration Dashboard")
st.markdown("Interactive Digital Twin for Dynamic Mobile Edge Computing (Phase 2)")

with st.sidebar:
    st.header("Experiment Controls")
    
    with st.form(key="vehicular_gen_form"):
        st.subheader("1. Generate Infrastructure Grid")
        st.caption("SUMO will dynamically inject vehicles and tasks into this infrastructure.")
        scenario_name = st.text_input("Scenario Name", "Highway_Base")
        num_tier1 = st.number_input("Tier 1 Nodes (Raspberry Pi/TX2)", min_value=1, value=20)
        num_tier2 = st.number_input("Tier 2 Servers (E5430 Fog Nodes)", min_value=1, value=5)
        st.caption("*Note: A single centralized Cloud Server is automatically provisioned.*")
        submit_vehicular_gen = st.form_submit_button("Generate Infrastructure")

    if submit_vehicular_gen:
        st.info("Generating Grid...")
        cmd = [PYTHON_EXECUTABLE, "generate_scenario.py", 
               "--scenario_name", scenario_name, 
               "--users", "0", 
               "--tier1", str(num_tier1), 
               "--tier2", str(num_tier2)]
        process = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        if process.returncode == 0:
            st.success(f"Infrastructure '{scenario_name}' Created!")
            st.cache_data.clear(); st.rerun()
        else:
            st.error("Error generating scenario.")
            st.code(process.stderr)

    st.divider()

    st.subheader("2. Run Dynamic Simulation")
    use_gui = st.checkbox("Show SUMO GUI during run", value=False)
    available_scenarios = get_available_scenarios()
    
    selected_scenarios = st.multiselect("Select Infrastructure Scenarios:", available_scenarios)
    
    if st.button("Run Vehicular Simulation 🚦"):
        if not selected_scenarios: 
            st.error("Please select at least one scenario.")
        else:
            with st.spinner("Running Dynamic SUMO Environment... Check terminal for live logs!"):
                base_names = [s.split('_ES-')[0] for s in selected_scenarios]
                cmd = [PYTHON_EXECUTABLE, "main_vehicular.py", "--scenarios"] + base_names
                if use_gui: cmd.append("--gui")
                subprocess.run(cmd, cwd=ROOT_DIR)
            st.success("Vehicular Experiment Complete!")
            st.cache_data.clear(); st.rerun()

# ==============================================================================
# RESULTS VISUALIZATION
# ==============================================================================
vehicular_results = load_vehicular_data()

if not vehicular_results:
    st.info("👋 Welcome to Phase 2! No results found yet. Generate an infrastructure grid in the sidebar and run a simulation to start analyzing data.")
else:
    st.markdown("---")
    st.markdown("## 🔬 Experimental Results & Algorithmic Analysis")
    
    scenario_tabs = st.tabs(list(vehicular_results.keys()))
    
    for i, (scenario_name, df) in enumerate(vehicular_results.items()):
        with scenario_tabs[i]:
            
            all_algos = df['Algorithm'].unique().tolist()
            default_algos = [a for a in ["SHybridQIGA", "GA", "QIGA", "MOHEFT", "OC"] if a in all_algos]
            if not default_algos: default_algos = all_algos
            
            selected_algos = st.multiselect(
                "🧪 Select Algorithms to Compare:",
                options=all_algos, default=default_algos, key=f"algo_select_{scenario_name}"
            )
            
            if not selected_algos: 
                st.warning("Please select at least one algorithm.")
                continue
                
            filtered_df = df[df['Algorithm'].isin(selected_algos)]
            
            # Aggregate Cumulative Data
            summary_df = filtered_df.groupby('Algorithm').agg(
                Total_Tasks=('tasks_generated', 'sum'),
                Total_Missed_Deadlines=('missed_deadlines', 'sum'),
                Total_Energy_Consumed=('energy', 'sum'),
                Total_Financial_Cost=('cost', 'sum'),
                Average_Latency=('latency', 'mean')
            ).reset_index()
            
            summary_df['SLA_Violation_Rate (%)'] = (summary_df['Total_Missed_Deadlines'] / summary_df['Total_Tasks']) * 100
            
            # Average Energy Per Task
            summary_df['Avg_Energy_Per_Task (J)'] = summary_df['Total_Energy_Consumed'] / summary_df['Total_Tasks']

            sub_tabs = st.tabs(["📊 Standard Metrics & Time Series", "🕸️ Advanced Trade-off Analysis (Evaluator View)"])
            
            # ==========================================
            # SUB-TAB 1: STANDARD METRICS
            # ==========================================
            with sub_tabs[0]:
                st.markdown("### 🏆 Cumulative Performance Leaderboard")
                
                # Arrange columns logically
                cols = ['Algorithm', 'Total_Tasks', 'Total_Missed_Deadlines', 'SLA_Violation_Rate (%)', 'Average_Latency', 'Avg_Energy_Per_Task (J)', 'Total_Energy_Consumed', 'Total_Financial_Cost']
                display_df = summary_df[cols].copy()
                
                # ⭐ CRITICAL FIX: Use Pandas .style.format() so the underlying data remains Floats for perfect numerical sorting!
                styled_df = display_df.style.format({
                    'Total_Tasks': "{:,.0f}",
                    'Total_Missed_Deadlines': "{:,.0f}",
                    'SLA_Violation_Rate (%)': "{:.2f}%",
                    'Average_Latency': "{:.3f} s",
                    'Avg_Energy_Per_Task (J)': "{:.3f} J",
                    'Total_Energy_Consumed': "{:,.1f} J",  # Adding commas for big numbers!
                    'Total_Financial_Cost': "${:,.2f}"
                })
                
                st.dataframe(styled_df)
                
                # CSV Download Button
                csv_export = summary_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Aggregated Results as CSV",
                    data=csv_export,
                    file_name=f"{scenario_name}_aggregated_results.csv",
                    mime="text/csv",
                )

                st.divider()

                st.markdown("### 📈 Real-Time Network Dynamics")
                
                # Plotly Chart: Traffic (Fixed Pan mode - UNSTACKED)
                load_df = filtered_df[filtered_df['Algorithm'] == filtered_df['Algorithm'].iloc[0]]
                fig_load = px.line(load_df, x='time', y=['tasks_generated', 'active_vehicles'], 
                                   title="🚦 Vehicular Traffic Injection (SUMO)", 
                                   color_discrete_sequence=["#FFA500", "#FF4B4B"])
                
                # Fill the area to the x-axis, but turn off stacking!
                fig_load.update_traces(fill='tozeroy') 
                fig_load.update_layout(
                    dragmode='pan',
                    yaxis_title="Count (Tasks & Vehicles)",
                    legend_title_text="Metric"
                )
                st.plotly_chart(fig_load)
                
                c1, c2 = st.columns(2)
                with c1:
                    fig_energy = px.line(filtered_df, x='time', y='energy', color='Algorithm', 
                                         title="⚡ Total Energy Drain vs Time (Joules)", markers=True)
                    fig_energy.update_layout(dragmode='pan')
                    st.plotly_chart(fig_energy)
                    
                    fig_cost = px.line(filtered_df, x='time', y='cost', color='Algorithm', 
                                       title="💰 Financial Cost vs Time ($)", line_dash='Algorithm')
                    fig_cost.update_layout(dragmode='pan')
                    st.plotly_chart(fig_cost)

                with c2:
                    fig_sla = px.line(filtered_df, x='time', y='sla_violation_rate', color='Algorithm', 
                                      title="❌ SLA Violation Rate vs Time (%)", markers=True)
                    fig_sla.update_layout(dragmode='pan')
                    st.plotly_chart(fig_sla)
                    
                    fig_lat = px.line(filtered_df, x='time', y='latency', color='Algorithm', 
                                      title="⏱️ Average Network Latency vs Time (s)", line_dash='Algorithm')
                    fig_lat.update_layout(dragmode='pan')
                    st.plotly_chart(fig_lat)

            # ==========================================
            # SUB-TAB 2: ADVANCED TRADE-OFF ANALYSIS
            # ==========================================
            with sub_tabs[1]:
                st.markdown("### 🎯 Algorithmic Impact & Trade-off Analysis")
                st.caption("Use this section during your defense to prove Pareto-efficiency and quantify algorithmic improvements.")
                
                # --- DYNAMIC INTELLIGENT CALCULATOR ---
                with st.container(border=True):
                    st.markdown("#### 🧮 Dynamic Analytical Engine")
                    col_b1, col_b2 = st.columns(2)
                    with col_b1: target_algo = st.selectbox("Target Algorithm:", selected_algos, index=selected_algos.index("SHybridQIGA") if "SHybridQIGA" in selected_algos else 0, key=f"t_{scenario_name}")
                    with col_b2: baseline_algo = st.selectbox("Baseline Algorithm:", selected_algos, index=selected_algos.index("GA") if "GA" in selected_algos else 0, key=f"b_{scenario_name}")
                    
                    if target_algo != baseline_algo:
                        t_stats = summary_df[summary_df['Algorithm'] == target_algo].iloc[0]
                        b_stats = summary_df[summary_df['Algorithm'] == baseline_algo].iloc[0]
                        
                        # Calculate improvements logically
                        sla_imp = ((b_stats['SLA_Violation_Rate (%)'] - t_stats['SLA_Violation_Rate (%)']) / max(b_stats['SLA_Violation_Rate (%)'], 0.0001)) * 100
                        lat_imp = ((b_stats['Average_Latency'] - t_stats['Average_Latency']) / max(b_stats['Average_Latency'], 0.0001)) * 100
                        e_imp = ((b_stats['Total_Energy_Consumed'] - t_stats['Total_Energy_Consumed']) / max(b_stats['Total_Energy_Consumed'], 0.0001)) * 100
                        
                        # 1. QoS Dynamics (Deadlines and Latency)
                        sla_text = f"**reduced** SLA Violations by **{abs(sla_imp):.1f}%**" if sla_imp >= 0 else f"**increased** SLA Violations by **{abs(sla_imp):.1f}%**"
                        lat_text = f"**improved** average latency by **{abs(lat_imp):.1f}%**" if lat_imp >= 0 else f"**worsened** average latency by **{abs(lat_imp):.1f}%**"
                        
                        st.markdown(f"**Conclusion for Evaluator:** Comparing the metrics, **{target_algo}** {sla_text} and {lat_text} compared to the **{baseline_algo}** baseline.")
                        
                        # 2. Energy Trade-off Dynamics
                        if e_imp >= 0:
                            st.success(f"🌱 **Energy Efficiency:** **{target_algo}** was highly efficient, saving **{abs(e_imp):.1f}%** more energy overall than the baseline.")
                        else:
                            if sla_imp > 0:
                                st.warning(f"⚡ **Strategic Trade-off:** To achieve its superior Quality of Service (QoS), **{target_algo}** strategically expended **{abs(e_imp):.1f}%** more energy than **{baseline_algo}** by actively clearing network bottlenecks.")
                            else:
                                st.error(f"📉 **Underperformance:** **{target_algo}** failed to optimize the network efficiently, expending **{abs(e_imp):.1f}%** more energy than **{baseline_algo}** while simultaneously delivering worse latency.")

                st.divider()

                c_radar, c_pareto = st.columns(2)
                
                # --- RADAR CHART (FIXED ZOOM) ---
                with c_radar:
                    st.markdown("#### 🕸️ Algorithm Footprint (Radar)")
                    st.caption("Lower surface area = Better overall optimization across all constraints.")
                    
                    norm_df = summary_df.copy()
                    for col in ['Average_Latency', 'Total_Energy_Consumed', 'Total_Financial_Cost', 'SLA_Violation_Rate (%)']:
                        norm_df[col] = minmax_scale(norm_df[col])
                        
                    fig_radar = go.Figure()
                    for idx, row in norm_df.iterrows():
                        fig_radar.add_trace(go.Scatterpolar(
                            r=[row['Average_Latency'], row['Total_Energy_Consumed'], row['Total_Financial_Cost'], row['SLA_Violation_Rate (%)']],
                            theta=['Latency', 'Energy', 'Cost', 'SLA Violation'],
                            fill='toself',
                            name=row['Algorithm']
                        ))
                    
                    # Lock dragmode to prevent accidental zooming/panning on the radar chart
                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=False)), 
                        margin=dict(l=40, r=40, t=20, b=20),
                        dragmode=False
                    )
                    
                    # Hide the Plotly toolbar to keep it clean
                    st.plotly_chart(fig_radar, config={'displayModeBar': False})

                # --- PARETO SCATTER PLOT ---
                with c_pareto:
                    st.markdown("#### 🎯 Pareto Frontier (Energy vs. QoS)")
                    st.caption("Algorithms closer to the **Bottom-Left** form the Pareto-optimal front.")
                    
                    fig_scatter = px.scatter(
                        summary_df, 
                        x="SLA_Violation_Rate (%)", 
                        y="Total_Energy_Consumed", 
                        color="Algorithm", 
                        size=[1.5]*len(summary_df),
                        hover_data=['Average_Latency', 'Total_Missed_Deadlines'], 
                        text="Algorithm",
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    fig_scatter.update_traces(textposition='top center', marker=dict(size=14, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
                    fig_scatter.update_layout(
                        xaxis_title="SLA Violation Rate (%) ➡️", 
                        yaxis_title="Total Energy Drain (Joules) ⬆️", 
                        margin=dict(l=0, r=0, t=20, b=0),
                        showlegend=False,
                        dragmode='pan' # Panning fixed here too
                    )
                    st.plotly_chart(fig_scatter)