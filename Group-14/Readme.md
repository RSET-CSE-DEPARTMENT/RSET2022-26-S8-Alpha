# 🚗 Fog & Vehicular Edge Orchestrator: Digital Twin & Benchmarking Suite

A comprehensive, multi-objective **Simulation Framework and Digital Twin** for evaluating **Task Scheduling algorithms** in both static IoT and dynamic Vehicular Fog Computing environments.

This repository introduces the **Smart Hybrid Quantum-Inspired Genetic Algorithm (SHybridQIGA)**, designed to solve NP-hard task offloading problems across a **3-Tier Edge-Fog-Cloud infrastructure**.

---

## 🌟 Project Overview

As IoT and Smart City applications demand increasingly stringent real-time processing, relying solely on centralized Cloud data centers leads to unacceptable latency and bandwidth bottlenecks.

This project provides a **full-stack simulation environment** to evaluate how effectively computational tasks can be offloaded to Edge and Fog nodes.

### 🔄 Operational Phases

#### Phase 1: Static Fog Orchestrator
- Simulates stationary IoT sensors and cameras  
- Uses a hierarchical mesh topology  
- Powered by a physics-based simulation engine  

#### Phase 2: Vehicular Fog Orchestration (SUMO + EdgeSimPy)
- Integrates Eclipse SUMO traffic simulator  
- Vehicles act as dynamic data sources  
- Supports real-time base station handovers  

---

## 🧠 Proposed Algorithm: SHybridQIGA

Traditional evolutionary algorithms struggle with real-time constraints, while greedy heuristics consume excessive energy.

### 🚀 Key Innovations

#### 1. Intelligent Safe Seeding (Phase 1)
- Avoids random initialization  
- Uses load-balanced round-robin scheduling  
- Prevents infeasible mappings and speeds convergence  

#### 2. Energy-Aware Smart Repair Mechanism (Phase 3)
- Fixes only violating task-server mappings  
- Handles:
  - RAM constraint violations  
  - Deadline misses  
- Uses:
  - Multi-core aware diagnostics  
  - Energy-efficient reassignment strategy  
- Cloud (Tier-3) is used only as a last resort  

### 📊 Performance Impact

- ~93% reduction in energy consumption compared to MOHEFT  
- Maintains strict QoS  
- Reduces SLA violations significantly  

---

## 📚 Supported Baseline Algorithms

### Quantum / Evolutionary
- QIGA  
- HybridQIGA  
- SQIGA  

### Metaheuristic Benchmarks
- GA (Genetic Algorithm)  
- PSO (Particle Swarm Optimization)  
- DE (Differential Evolution)  

### Constructive Heuristics
- MOHEFT (NSGA-II based)  
- RR (Round Robin)  
- RA (Random Assignment)  
- OC (Only Cloud)  
- OE (Only Edge)  

---

## 🏗️ System Architecture & Digital Twin

### 3-Tier Infrastructure (EdgeSimPy)

#### Tier 1 – Edge
- Raspberry Pi 4 Base Stations  
- Ultra-low latency  
- Highly energy-efficient  
- Max Power: 7.5W  
- Compute constrained  

#### Tier 2 – Fog
- Intel Xeon E5430 Servers  
- Balanced performance and power  
- Max Power: 200W  

#### Tier 3 – Cloud
- 64-Core Data Centers  
- Near-infinite capacity  
- High propagation delay (~50 ms)  
- High energy and monetary cost  
- Max Power: 600W  

---

### ⚙️ Physics Engine & Analytics

- Energy modeled as: **P × t (Power × Time)**  
- Latency includes:
  - BFS-based network delay  
  - Multi-core execution time  

### 📊 Streamlit Dashboard Features
- Interactive topology visualization (PyVis)  
- Node congestion visualization  
- Trade-off analysis (Pareto efficiency)  

---

## 🚀 Installation & Usage

### 1. Prerequisites

To run vehicular simulations, install **Eclipse SUMO**:

#### Ubuntu
```bash
sudo apt-get install sumo sumo-tools sumo-doc
```

#### Windows
- Download from official SUMO website  
- Add `SUMO_HOME` to environment variables  

---

### 2. Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate environment
source venv/bin/activate        # Linux / Mac
.\venv\Scripts\activate         # Windows

# Install dependencies
pip install "mesa==1.2.1" EdgeSimPy traci networkx pandas streamlit matplotlib pyvis numpy
```

---

### 3. Running the Simulations

#### Phase 1: Static Digital Twin & Dashboard

```bash
streamlit run dashboard.py
```

- Generate scenarios (compute-heavy, real-time, etc.)  
- Configure algorithms  
- Visualize simulation in real-time  

---

#### Phase 2: Dynamic Vehicular Orchestration

```bash
python main_vehicular.py
```

- Simulates:
  - Moving vehicles  
  - Dynamic task generation  
  - Real-time scheduling and handovers  

---

## 📊 Key Research Findings

### Energy-Latency Trade-off
- MOHEFT achieves faster execution but consumes high energy  
- SHybridQIGA provides an optimal balance  

### Constraint-Aware Dominance
- Smart repair reduces SLA violations  
- Avoids evaluating invalid schedules  

### Network Saturation
- Fog nodes may overload under heavy traffic conditions  
- Dynamic Edge-Cloud switching is necessary  

---

## 👨‍💻 Authors

- Ajay Mukund A  
- Adithyan Ajayan  
- Anna George  
- Alex Babu  
- Bennette A Sabu  

Department of Computer Science and Engineering  
Rajagiri School of Engineering & Technology, Kochi, India  

---

## 🙏 Acknowledgments

This project integrates:

- EdgeSimPy for Edge Computing modeling  
- Eclipse SUMO for mobility simulation  
- QIGA foundations inspired by Galavani et al. (2025)  

---