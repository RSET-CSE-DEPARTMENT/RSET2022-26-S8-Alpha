import os
import csv
import copy
from config import *

# 1️⃣ IMPORT ALL ALGORITHMS
from algorithms import (
    SHybridQIGA, MOHEFT, GA, PSO, DE, 
    QIGA, OE, OC, RA, RR
)
from .mobility_manager import MobilityManager
from .task_generator import VehicularTaskGenerator

SCHEDULING_INTERVAL = 15
SIMULATION_DURATION = 120

# 2️⃣ EXPAND ALGORITHM DICTIONARY
ALGORITHMS = {
    "SHybridQIGA": SHybridQIGA.SHybridQIGA,
    "MOHEFT": MOHEFT.MOHEFT,
    "GA": GA.GA,
    "PSO": PSO.PSO,
    "DE": DE.DE,
    "QIGA": QIGA.QIGA,
    "RR": RR.RR,
    "RA": RA.RA,
    "OE": OE.OE,
    "OC": OC.OC,
    # If you also fixed these two, uncomment them:
    # "SQIGA": SQIGA.SQIGA,
    # "HybridQIGA": HybridQIGA.HybridQIGA
}

class DynamicSchedulerLoop:
    def __init__(self, simulator, data, use_gui=False, scenario_name="vehicular_scenario"):
        self.simulator = simulator
        self.data = data
        self.use_gui = use_gui
        self.scenario_name = scenario_name

        self.csv_paths = {}

    # ==========================================================
    # CSV LOGGER PER ALGORITHM
    # ==========================================================
    def _get_next_run_id(self, base_dir):
        if not os.path.exists(base_dir):
            return 1
        existing=[d for d in os.listdir(base_dir) if d.startswith("run_")]
        if not existing:
            return 1
        nums=[int(d.split("_")[1]) for d in existing]
        return max(nums)+1

    def _prepare_all_loggers(self):
        for algo_name in ALGORITHMS.keys():

            base_dir=f"vehicular_outputs/{self.scenario_name}/{algo_name}"
            os.makedirs(base_dir,exist_ok=True)

            run_id=self._get_next_run_id(base_dir)
            run_dir=f"{base_dir}/run_{run_id}"
            os.makedirs(run_dir,exist_ok=True)

            csv_path=f"{run_dir}/runtime_metrics.csv"

            with open(csv_path,"w",newline="") as f:
                writer=csv.writer(f)
                writer.writerow([
                    "time","active_vehicles","tasks_generated",
                    "latency","energy","cost","missed_deadlines"
                ])

            self.csv_paths[algo_name]=csv_path
            print(f"📁 {algo_name} results → {run_dir}")

    def _log_row(self, algo_name, t, vehicles, tasks, sol):
        with open(self.csv_paths[algo_name],"a",newline="") as f:
            writer=csv.writer(f)
            writer.writerow([
                t,vehicles,tasks,
                round(sol.latency,4),
                round(sol.energy,4),
                round(sol.cost,4),
                sol.missed_deadlines
            ])

    # ==========================================================
    # BUILD NETWORK GRAPH
    # ==========================================================
    def _build_graph(self):
        graph={}
        for link in self.data['NetworkLink'].all():
            n1=link.nodes[0].base_station.id
            n2=link.nodes[1].base_station.id
            graph.setdefault(n1,[]).append((n2,link.bandwidth))
            graph.setdefault(n2,[]).append((n1,link.bandwidth))
        self.data['graph']=graph

    # ==========================================================
    # Inject dynamic users into EdgeSimPy
    # ==========================================================
    def _inject_users(self, mobility):
        active_users=mobility.get_active_users()
        from edge_sim_py import User
        User.all=classmethod(lambda cls: active_users)
        return active_users

    # ==========================================================
    # Snapshot current tasks (CRITICAL FOR FAIR COMPARISON)
    # ==========================================================
    def _snapshot_tasks(self, users):
        snapshot={}
        for u in users:
            snapshot[u.id]=copy.deepcopy(u.applications)
        return snapshot

    def _restore_tasks(self, users, snapshot):
        for u in users:
            u.applications=copy.deepcopy(snapshot[u.id])

    # ==========================================================
    # 🚀 MAIN LOOP (PARALLEL ALGORITHM MODE)
    # ==========================================================
    def run(self):

        print("\n🚗 Starting FAIR Multi-Algorithm Vehicular Experiment")

        self._build_graph()
        self._prepare_all_loggers()

        mobility=MobilityManager(self.data,use_gui=self.use_gui)
        task_gen=VehicularTaskGenerator(mobility)

        current_time=0
        tasks_window=0

        while current_time < SIMULATION_DURATION:

            if not mobility.sumo.started:
                break

            # 1️⃣ Move vehicles
            mobility.step()

            # 2️⃣ Generate tasks
            tasks_created=task_gen.step(current_time)
            tasks_window+=tasks_created

            # ==================================================
            # ⚙️ SCHEDULER TRIGGER
            # ==================================================
            if current_time % SCHEDULING_INTERVAL == 0 and current_time != 0:

                print("\n"+"="*70)
                print(f"⚙️  SCHEDULER TRIGGER @ t={current_time}s")
                print("="*70)

                users=self._inject_users(mobility)
                vehicles=len(users)

                print(f"🚗 Active Vehicles : {vehicles}")
                print(f"🧠 Tasks Generated : {tasks_window}")

                # ⭐ SNAPSHOT TASKS ONCE
                task_snapshot=self._snapshot_tasks(users)

                # 🔁 RUN ALL ALGORITHMS ON SAME TASKS
                for algo_name, AlgoClass in ALGORITHMS.items():

                    print(f"\n🔬 Running {algo_name}...")

                    # Restore identical tasks
                    self._restore_tasks(users,task_snapshot)

                    # 3️⃣ FIX: Handle specific argument requirements
                    if algo_name == "OC":
                        # Only Cloud takes no population/gen arguments
                        alg = AlgoClass(fitness, self.data)
                    else:
                        alg = AlgoClass(fitness, K_POP_SIZE, K_GEN_SIZE, self.data)
                    
                    best_solution, _ = alg.run()

                    print(f"{algo_name} → Lat={best_solution.latency:.3f} "
                          f"Energy={best_solution.energy:.3f} "
                          f"Cost={best_solution.cost:.3f} "
                          f"MissDL={best_solution.missed_deadlines}")

                    # Save CSV row per algorithm
                    self._log_row(algo_name,current_time,vehicles,tasks_window,best_solution)

                # 🔄 CLEAR TASKS AFTER ALL ALGOS HAVE RUN
                for u in users:
                    u.applications.clear()

                tasks_window=0

            current_time+=1

        if mobility.sumo.started:
            mobility.sumo.close()

        print("\n🏁 Experiment Finished")