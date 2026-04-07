# 🏭 Fog Scheduler Digital Twin & Benchmarking Suite

This repository houses a comprehensive **Digital Twin and Simulation Framework** for Task Scheduling in Fog Computing environments. It compares **Quantum-Inspired algorithms** against classical **Evolutionary** and **Swarm Intelligence** methods under realistic constraints.

The system simulates a 3-Tier Network Architecture (Edge Nodes, Fog Servers, Cloud) and optimizes for three conflicting objectives: **Latency**, **Energy Consumption**, and **Monetary Cost**.

---

## 🧠 Implemented Algorithms

We have implemented **9 distinctive scheduling algorithms** for rigorous comparison:

### Proposed Methods
* **QIGA (Quantum-Inspired Genetic Algorithm):** Uses adaptive quantum rotation gates ($\theta$) to explore the search space.
* **MOHEFT (NSGA-II):** A multi-objective genetic algorithm using non-dominated sorting (Currently the efficiency champion).

### Metaheuristic Benchmarks
* **GA (Genetic Algorithm):** Standard single-objective genetic algorithm (Scalarized fitness).
* **PSO (Particle Swarm Optimization):** Modified for discrete server selection.
* **DE (Differential Evolution):** Adapted for integer-based task assignment.

### Baselines
* **OC (Only Cloud):** Offloads all tasks to the high-speed, high-cost Cloud.
* **OE (Only Edge):** Forces local processing on limited Fog nodes.
* **RR (Round Robin):** Cyclic assignment.
* **RA (Random Assignment):** Stochastic assignment.

---

## 🏗️ System Architecture

### 1. The Physics Engine (`config.py`)
Unlike simple simulations, this project uses realistic physics models:
* **Energy:** Calculated as $Power (Watts) \times Time (Seconds)$.
* **Latency:** Includes **Network Pathfinding (BFS)** delays + **Compute Execution** time.
* **Prediction Noise:** Simulates real-world uncertainty by injecting $\pm 10\%$ noise into task weight estimates.

### 2. The Digital Twin Dashboard (`dashboard.py`)
A comprehensive Streamlit interface featuring:
* **Traffic Light Logic:** Visualizes congestion (Red/Green) on nodes in real-time.
* **Interactive Topology:** Uses `PyVis` for a physics-enabled network map.
* **Scenario Generator:** Dynamically creates datasets (e.g., "Scarce Resources", "High Load").

### 3. The Scenarios
We test on specific stress-test datasets:
* **Scarce_PenaltyTrap:** High user load on weak Tier-1 hardware (Raspberry Pis).
* **DataHeavy:** Bottlenecks the network bandwidth.
* **ComputeHeavy:** Bottlenecks the CPU processing power.

---

## 🚀 Installation & Usage

### 1. Environment Setup
```bash
# Create Virtual Environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# Install Dependencies (Requires specific Mesa version)
pip install "mesa==1.2.1" networkx msgpack pandas streamlit matplotlib pyvis numpy
```

### 2. Running the Simulation

You can run the full pipeline via the Dashboard:

```bash
streamlit run dashboard.py
```

**Workflow:**

1. Go to **Admin Controls**.
2. Select a Scenario (e.g., `Base_Case`) and click **Generate Dataset**.
3. Select scenarios to simulate and click **Run Simulation**.
4. Analyze the results in the interactive tabs.

---

## 📊 Key Findings (Current Research Status)

* **Scalarization Dominance:** The Standard **GA** (Single-Objective) currently outperforms Pareto-based methods (QIGA, NSGA-II) in pure efficiency for this specific discrete problem topology.
* **Discrete vs. Continuous:** Algorithms relying on discrete crossover (GA, MOHEFT) outperform those relying on continuous probability mapping (QIGA, PSO).
* **Fog vs. Cloud:** In high-concurrency scenarios ($N > 150$ users), the distributed Fog layer achieves lower latency than the centralized Cloud due to parallel processing capability.

---

## 👏 Acknowledgments & Credits

This project builds upon the work of multiple open-source contributions:

1. **Original QIGA Framework:**
   * Base architecture and QIGA algorithm logic derived from *Galavani et al.* [Dynamic Scheduling in Mobile Edge Computing](https://www.google.com/search?q=https://doi.org/10.1109/CSICC65765.2025.10967435).
   * Original Repo: [Anonymous0-0paper/QIGA](https://github.com/Anonymous0-0paper/QIGA).

2. **Metaheuristic Benchmarks (GA, PSO, DE):**
   * The implementations of Genetic Algorithm, Particle Swarm Optimization, and Differential Evolution were adapted from the **Vehicular Fog Computing** repository.
   * Source: [ahujatarang/vehicular-fog-computing](https://www.google.com/search?q=https://github.com/ahujatarang/vehicular-fog-computing).

3. **Modifications:**
   * We have significantly modified the original codebase to include a physics-based energy model ($P \times t$), a prediction noise module for robustness testing, and a Streamlit-based Digital Twin dashboard.
   * The MOHEFT algorithm was upgraded from a heuristic to a full NSGA-II evolutionary algorithm.

---

## 📜 Citation

If you use the QIGA implementation from this repo, please cite the original paper:

```bibtex
@INPROCEEDINGS{10967435,
  author={Galavani, Sadra et al.},
  title={QIGA: Quantum-Inspired Genetic Algorithm for Dynamic Scheduling in Mobile Edge Computing}, 
  year={2025},
  doi={10.1109/CSICC65765.2025.10967435}
}
```
