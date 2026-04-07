from config import *
import numpy as np
import copy

class MOHEFT:
    """
    True MOHEFT (Multi-Objective Heterogeneous Earliest Finish Time).
    
    IMPROVED LOGIC:
    1. Sorts tasks by Deadline (Earliest Deadline First).
    2. Dynamic Memory Tracking: Checks capacity BEFORE assigning.
    3. Local Normalization: Calculates relative quality of servers.
    """
    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.data = data
        
        # Robust Task Counting
        self.all_tasks = get_all_tasks(data)
        self.num_tasks = len(self.all_tasks)
        
        # Freeze Server List (Must match config.py's decode order)
        self.servers = list(self.data['EdgeServer'].all())
        self.servers.sort(key=lambda s: s.id) # Deterministic Sort
        self.num_resources = len(self.servers)
        
        # Pre-fetch static parameters
        self.server_freqs = [get_freq(s.model_name, s) for s in self.servers]

    def run(self):
        # 1. Sort Tasks by Deadline (Earliest First)
        indexed_tasks = []
        for i, t_dict in enumerate(self.all_tasks):
            indexed_tasks.append({
                'gene_index': i,
                'user': t_dict['user'],
                'service': t_dict['service']
            })
            
        indexed_tasks.sort(key=lambda x: x['service'].deadline)
        
        # Initialize Empty Individual
        ind = Individual()
        ind.CInd = [0] * (self.num_tasks * self.num_resources)
        
        # TRACKING: Keep track of what we put on each server
        server_loads = {s.id: [] for s in self.servers}
        
        # 2. Greedy Construction Loop
        for item in indexed_tasks:
            task = item['service']
            user = item['user']
            gene_idx = item['gene_index']
            
            # Temporary storage for candidate metrics
            candidates = []
            
            # A. Evaluate specific Task on EVERY Server
            for s_idx, server in enumerate(self.servers):
                
                # --- MEMORY CHECK (The Fix) ---
                # Check if adding this task would explode the server
                current_load = server_loads[server.id]
                if memory_is_overloaded(current_load + [item], server.memory):
                    continue # Skip this server, it's full!

                # --- Match Logic from fitness() ---
                
                # 1. Frequency
                freq = self.server_freqs[s_idx]
                
                # 2. Delays (Optimistic mean)
                predicted_weight = task.weight * 1.0 
                exe_delay = get_exe_delay(freq, predicted_weight)
                path_delay = get_path_delay(
                    server.base_station.id, 
                    user.base_station.id, 
                    task.data_size, 
                    self.data, 
                    self.data.get('graph', {})
                )
                
                total_delay = exe_delay + path_delay
                
                # 3. Energy
                max_p = server.power_model_parameters.get('max_power_consumption', 0)
                static_pct = server.power_model_parameters.get('static_power_percentage', 0) / 100.0
                dynamic_power = max_p * (1.0 - static_pct)
                total_energy = dynamic_power * exe_delay
                
                # 4. Cost
                cost_rate = server.power_model_parameters.get('monetary_cost', 0)
                total_cost = cost_rate * exe_delay
                
                candidates.append({
                    'server_idx': s_idx,
                    'server_obj': server,
                    'energy': total_energy,
                    'latency': total_delay,
                    'cost': total_cost
                })

            # FALLBACK: If all servers are full (candidates empty), 
            # we MUST pick one. We pick the cloud (or last server).
            if not candidates:
                # Find cloud or just pick last one
                target_idx = self.num_resources - 1
                for i, s in enumerate(self.servers):
                    if "Cloud" in s.model_name:
                        target_idx = i
                        break
                # Create a dummy candidate just to allow assignment
                candidates.append({
                    'server_idx': target_idx,
                    'server_obj': self.servers[target_idx],
                    'energy': 9999, 'latency': 9999, 'cost': 9999
                })

            # B. Local Normalization
            energies = [c['energy'] for c in candidates]
            latencies = [c['latency'] for c in candidates]
            costs = [c['cost'] for c in candidates]
            
            min_e, max_e = min(energies), max(energies)
            min_l, max_l = min(latencies), max(latencies)
            min_c, max_c = min(costs), max(costs)
            
            range_e = max_e - min_e if max_e > min_e else 1.0
            range_l = max_l - min_l if max_l > min_l else 1.0
            range_c = max_c - min_c if max_c > min_c else 1.0
            
            # C. Pick Best Server
            best_server_idx = -1
            best_server_obj = None
            best_score = float('inf')
            
            for c in candidates:
                norm_e = (c['energy'] - min_e) / range_e
                norm_l = (c['latency'] - min_l) / range_l
                norm_c = (c['cost'] - min_c) / range_c
                
                score = (norm_e * W_ENERGY) + (norm_l * W_LATENCY) + (norm_c * W_COST)
                
                if c['latency'] > task.deadline:
                    score += 1000.0 
                
                if score < best_score:
                    best_score = score
                    best_server_idx = c['server_idx']
                    best_server_obj = c['server_obj']
            
            # D. Assign
            start_bit = gene_idx * self.num_resources
            ind.CInd[start_bit + best_server_idx] = 1
            
            # UPDATE TRACKING
            server_loads[best_server_obj.id].append(item)

        # 3. Final Evaluation
        population = self.fitness([ind], self.data)
        best_overall = population[0]
        
        return best_overall, [best_overall]