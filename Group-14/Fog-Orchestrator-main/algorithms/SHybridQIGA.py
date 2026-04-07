from config import *
import random
import numpy as np
import copy

class SHybridQIGA:
    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.population_size = population_size
        self.generation_count = generation_count
        self.data = data
        
        # 1. Freeze Data (MUST match config.py logic exactly)
        self.all_tasks = get_all_tasks(data)
        self.num_tasks = len(self.all_tasks)
        
        # FIX 1: Freeze AND Sort Server List (Determinism)
        self.servers = list(self.data['EdgeServer'].all()) 
        self.servers.sort(key=lambda s: s.id)
        self.num_resources = len(self.servers)
        
        # Quantum Parameters
        self.initial_theta = 0.05 * np.pi
        self.min_theta = 0.01 * np.pi
        self.theta = self.initial_theta 
        
        # Dynamic Mutation
        self.base_mutation_rate = 0.01
        self.mutation_rate = self.base_mutation_rate
        
        # Cache Static Data
        self.server_freqs = [get_freq(s.model_name, s) for s in self.servers]
        self.server_costs = [s.power_model_parameters.get('monetary_cost', 0) for s in self.servers]
            
        self.task_weights = [t['service'].weight for t in self.all_tasks]
        self.avg_task_weight = sum(self.task_weights) / len(self.task_weights) if self.task_weights else 0

    # --- Quantum Operations ---
    def _initialize_population(self):
        num_qubits = self.num_tasks * self.num_resources
        q_ind = []
        for _ in range(num_qubits):
            q_ind.append(np.array([[1/np.sqrt(2)], [1/np.sqrt(2)]]))
        return q_ind

    def _measure(self, q_ind):
        classical_pop = []
        for _ in range(self.population_size):
            ind = Individual()
            ind.CInd = []
            for i in range(0, len(q_ind), self.num_resources):
                task_qubits = q_ind[i : i + self.num_resources]
                probs = np.array([np.abs(q[1][0])**2 for q in task_qubits]).flatten()
                
                if probs.sum() == 0: probs = np.ones(len(probs)) / len(probs)
                else: probs = probs / probs.sum()
                
                chosen_server = np.random.choice(len(probs), p=probs)
                gene = [0] * self.num_resources
                gene[chosen_server] = 1
                ind.CInd.extend(gene)
            classical_pop.append(ind)
        return classical_pop

    def _update_quantum_gates(self, q_ind, best_solution, current_gen):
        if best_solution is None: return q_ind
        
        decay_factor = 1 - (current_gen / self.generation_count)
        self.theta = self.min_theta + (self.initial_theta - self.min_theta) * decay_factor

        for i in range(len(q_ind)):
            if random.random() < self.mutation_rate:
                random_angle = random.uniform(-0.1 * np.pi, 0.1 * np.pi)
                rot_mut = np.array([[np.cos(random_angle), -np.sin(random_angle)],
                                    [np.sin(random_angle), np.cos(random_angle)]])
                q_ind[i] = np.dot(rot_mut, q_ind[i])
                norm = np.linalg.norm(q_ind[i])
                q_ind[i] = q_ind[i] / norm
                continue

            target_bit = best_solution.CInd[i]
            alpha = q_ind[i][0][0]
            beta = q_ind[i][1][0]
            
            if target_bit == 1 and abs(beta)**2 > 0.99: continue
            if target_bit == 0 and abs(alpha)**2 > 0.99: continue

            direction = 0
            if target_bit == 1:
                direction = 1 if alpha * beta > 0 else -1 
            else:
                direction = -1 if alpha * beta > 0 else 1
            
            rotation_angle = direction * self.theta
            rot = np.array([[np.cos(rotation_angle), -np.sin(rotation_angle)],
                            [np.sin(rotation_angle), np.cos(rotation_angle)]])
            q_ind[i] = np.dot(rot, q_ind[i])
            
            norm = np.linalg.norm(q_ind[i])
            q_ind[i] = q_ind[i] / norm
        return q_ind

    def _generate_heuristic_seed(self):
        """Cost-optimized seed, safe distribution."""
        ind = Individual()
        ind.CInd = []
        
        sorted_indices = np.argsort(self.server_costs)
        
        # FIX 2: Poison Seed Fix (Use 50% of servers)
        top_k = max(3, self.num_resources // 2)
        best_servers = sorted_indices[:top_k]
        
        for i in range(self.num_tasks):
            target_idx = best_servers[i % top_k]
            gene = [0] * self.num_resources
            gene[target_idx] = 1 
            ind.CInd.extend(gene)
        return ind

    # --- SMART REPAIR MECHANISM ---
    def repair_population(self, population):
        graph = self.data.get('graph', {})
        
        for ind in population:
            resources_map = decode(self.data, ind)
            
            for resource, task_dicts in resources_map.items():
                if not task_dicts: continue
                
                # Safe ID Lookup
                r_idx = -1
                for idx, s in enumerate(self.servers):
                    if s.id == resource.id: 
                        r_idx = idx
                        break
                if r_idx == -1: continue
                
                av_freq = self.server_freqs[r_idx]
                r_bs_id = resource.base_station.id
                
                for t_dict in task_dicts:
                    t_service = t_dict['service']
                    t_user = t_dict['user']
                    u_bs_id = t_user.base_station.id
                    
                    # Safe Task Lookup
                    task_index = -1
                    for i, item in enumerate(self.all_tasks):
                        if item['service'] == t_service:
                            task_index = i
                            break
                    if task_index == -1: continue

                    # Check Violations
                    exe_delay = get_exe_delay(av_freq, t_service.weight)
                    path_delay = get_path_delay(r_bs_id, u_bs_id, t_service.data_size, self.data, graph)
                    total_delay = exe_delay + path_delay
                    
                    best_target = -1
                    
                    # A. Deadline Miss?
                    if total_delay > t_service.deadline:
                        if path_delay > exe_delay:
                            # Bottleneck is Network: Move to Local BS
                            candidates = [s for s in range(self.num_resources) 
                                          if self.servers[s].base_station.id == u_bs_id]
                            if candidates:
                                best_target = random.choice(candidates)
                            else:
                                # Fallback: Best Freq
                                best_target = max(range(self.num_resources), key=lambda s: self.server_freqs[s])
                        else:
                            # Bottleneck is CPU: FIX 3 (Energy-Aware Repair)
                            # Instead of blindly picking MAX freq (Cloud), find "Good Enough" freq
                            candidates = []
                            for s in range(self.num_resources):
                                # Estimate if this server is fast enough
                                est_exe = get_exe_delay(self.server_freqs[s], t_service.weight)
                                if est_exe < t_service.deadline * 0.8: # 20% safety margin
                                    candidates.append(s)
                            
                            if candidates:
                                # Pick the CHEAPEST/LOWEST POWER among valid candidates
                                best_target = min(candidates, key=lambda s: self.server_costs[s])
                            else:
                                # Panic: No server is fast enough? Pick the absolute fastest.
                                best_target = max(range(self.num_resources), key=lambda s: self.server_freqs[s])

                    # B. Cost Optimization (If Deadline OK)
                    else:
                        current_cost = self.server_costs[r_idx]
                        min_cost = min(self.server_costs)
                        if current_cost > min_cost * 2.0 and t_service.weight < self.avg_task_weight:
                             best_target = min(range(self.num_resources), key=lambda s: self.server_costs[s])

                    # Apply Repair
                    if best_target != -1 and best_target != r_idx:
                        start = task_index * self.num_resources
                        ind.CInd[start + r_idx] = 0
                        ind.CInd[start + best_target] = 1
        return population

    def get_score(self, ind):
        if not ind.fitness: return float('inf')
        return sum(ind.fitness)

    def run(self):
        q_ind = self._initialize_population()
        
        # Seeding
        seed_ind = self._generate_heuristic_seed()
        seeded_pop = self.fitness([seed_ind], self.data)
        best_overall = copy.deepcopy(seeded_pop[0])
        
        classical_pop = []
        
        for gen in range(self.generation_count):
            classical_pop = self._measure(q_ind)
            
            # --- HYBRID REPAIR ---
            classical_pop = self.repair_population(classical_pop) 
            
            classical_pop = self.fitness(classical_pop, self.data)
            
            # Dynamic Mutation
            unique_costs = len(set(ind.cost for ind in classical_pop))
            if unique_costs < 5: self.mutation_rate = 0.05 
            else: self.mutation_rate = self.base_mutation_rate
            
            classical_pop.sort(key=self.get_score)
            best_current = classical_pop[0]
            
            current_score = self.get_score(best_current)
            overall_score = self.get_score(best_overall)

            if current_score < overall_score:
                best_overall = copy.deepcopy(best_current)
            elif current_score == overall_score:
                if random.random() < 0.3: best_overall = copy.deepcopy(best_current)

            q_ind = self._update_quantum_gates(q_ind, best_overall, gen)

        if best_overall and best_overall not in classical_pop:
            classical_pop.insert(0, best_overall)
        
        return best_overall, classical_pop