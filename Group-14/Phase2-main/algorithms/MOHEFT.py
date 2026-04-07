from config import *
import numpy as np

class MOHEFT:
    """
    True MOHEFT (Multi-Objective HEFT)
    FULLY COMPATIBLE WITH DYNAMIC VEHICULAR RUNTIME
    (Fixed with Multi-Core Load Awareness)
    """

    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.data = data

        # Freeze server list (decode order must match config)
        self.servers = list(self.data['EdgeServer'].all())
        self.servers.sort(key=lambda s: s.id)
        self.num_resources = len(self.servers)

        # Precompute frequencies and cores
        self.server_freqs = [get_freq(s.model_name, s) for s in self.servers]
        self.server_cores = [getattr(s, 'cpu', 1) for s in self.servers]

    # ==========================================================
    # MAIN ALGORITHM
    # ==========================================================
    def run(self):

        # 🔴 DYNAMIC SYNCHRONIZATION
        self.all_tasks = get_all_tasks(self.data)
        self.num_tasks = len(self.all_tasks)

        # 🛑 ZERO-TASK TRAP
        if self.num_tasks == 0:
            dummy = Individual()
            dummy.CInd = []
            pop = self.fitness([dummy], self.data)
            return pop[0], pop

        # ======================================================
        # 1️⃣ Sort tasks by earliest deadline
        # ======================================================
        indexed_tasks = []
        for i, t_dict in enumerate(self.all_tasks):
            indexed_tasks.append({
                "gene_index": i,
                "user": t_dict["user"],
                "service": t_dict["service"]
            })

        indexed_tasks.sort(key=lambda x: x["service"].deadline)

        # Create chromosome
        ind = Individual()
        ind.CInd = [0] * (self.num_tasks * self.num_resources)

        # Track memory usage and task load per server
        server_loads = {s.id: [] for s in self.servers}

        # ======================================================
        # 2️⃣ Greedy placement loop
        # ======================================================
        for item in indexed_tasks:

            task = item["service"]
            user = item["user"]
            gene_idx = item["gene_index"]
            candidates = []

            # Evaluate all servers
            for s_idx, server in enumerate(self.servers):

                current_load = server_loads[server.id]
                
                # Memory check
                if memory_is_overloaded(current_load + [item], server.memory):
                    continue

                # ⭐ CRITICAL FIX: Multi-Core Load-Aware CPU Estimation
                c_cores = self.server_cores[s_idx]
                future_task_count = len(current_load) + 1
                
                if future_task_count <= c_cores:
                    effective_freq = self.server_freqs[s_idx]
                else:
                    effective_freq = (c_cores * self.server_freqs[s_idx]) / future_task_count

                exe_delay = get_exe_delay(effective_freq, task.weight)

                path_delay = get_path_delay(
                    server.base_station.id,
                    user.base_station.id,
                    task.data_size,
                    self.data,
                    self.data.get("graph", {})
                )

                total_delay = exe_delay + path_delay

                # Energy model (using the accurate effective delay)
                max_p = server.power_model_parameters.get("max_power_consumption", 0)
                static_pct = server.power_model_parameters.get("static_power_percentage", 0) / 100.0
                dynamic_power = max_p * (1 - static_pct)
                total_energy = dynamic_power * exe_delay

                # Monetary cost
                cost_rate = server.power_model_parameters.get("monetary_cost", 0)
                total_cost = cost_rate * exe_delay

                candidates.append({
                    "server_idx": s_idx,
                    "server_obj": server,
                    "energy": total_energy,
                    "latency": total_delay,
                    "cost": total_cost
                })

            # ☁️ fallback → cloud if all full
            if not candidates:
                cloud_idx = self.num_resources - 1
                for i, s in enumerate(self.servers):
                    if "Cloud" in s.model_name:
                        cloud_idx = i
                        break

                candidates.append({
                    "server_idx": cloud_idx,
                    "server_obj": self.servers[cloud_idx],
                    "energy": 9999,
                    "latency": 9999,
                    "cost": 9999
                })

            # ==================================================
            # 3️⃣ Multi-objective normalization
            # ==================================================
            energies = [c["energy"] for c in candidates]
            latencies = [c["latency"] for c in candidates]
            costs = [c["cost"] for c in candidates]

            min_e, max_e = min(energies), max(energies)
            min_l, max_l = min(latencies), max(latencies)
            min_c, max_c = min(costs), max(costs)

            range_e = max(max_e - min_e, 1e-9)
            range_l = max(max_l - min_l, 1e-9)
            range_c = max(max_c - min_c, 1e-9)

            best_score = float("inf")
            best_server_idx = None
            best_server_obj = None

            for c in candidates:
                norm_e = (c["energy"] - min_e) / range_e
                norm_l = (c["latency"] - min_l) / range_l
                norm_c = (c["cost"] - min_c) / range_c

                score = (
                    norm_e * W_ENERGY +
                    norm_l * W_LATENCY +
                    norm_c * W_COST
                )

                # deadline penalty
                if c["latency"] > task.deadline:
                    score += 1000

                if score < best_score:
                    best_score = score
                    best_server_idx = c["server_idx"]
                    best_server_obj = c["server_obj"]

            # Assign gene
            start_bit = gene_idx * self.num_resources
            ind.CInd[start_bit + best_server_idx] = 1

            # ⭐ Update load so the next task knows the server is busy!
            server_loads[best_server_obj.id].append(item)

        # ======================================================
        # 4️⃣ Final evaluation
        # ======================================================
        population = self.fitness([ind], self.data)
        best_solution = population[0]

        return best_solution, [best_solution]