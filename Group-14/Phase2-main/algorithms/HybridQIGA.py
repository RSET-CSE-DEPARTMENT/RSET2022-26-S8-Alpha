from config import *
import random
import numpy as np
import copy

class HybridQIGA:
    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.population_size = population_size
        self.generation_count = generation_count
        self.data = data
        
        # Robust Task Counting
        self.all_tasks = get_all_tasks(data)
        self.num_tasks = len(self.all_tasks)
        self.num_resources = self.data['EdgeServer'].count()
        
        # Quantum Parameters (Adaptive)
        self.initial_theta = 0.05 * np.pi
        self.min_theta = 0.01 * np.pi
        self.theta = self.initial_theta 
        
        # Mutation Rate (Dynamic)
        self.base_mutation_rate = 0.01
        self.mutation_rate = self.base_mutation_rate
        
        # Cache Server Data
        self.servers = self.data['EdgeServer'].all()
        self.server_freqs = []
        self.server_costs = []
        
        for s in self.servers:
            f = get_freq(s.model_name, s)
            self.server_freqs.append(f)
            c = s.power_model_parameters.get('monetary_cost', 0)
            self.server_costs.append(c)
            
        # Cache Task Weights and Calculate Average
        self.task_weights = []
        for t_dict in self.all_tasks:
            self.task_weights.append(t_dict['service'].weight)
            
        self.avg_task_weight = sum(self.task_weights) / len(self.task_weights) if self.task_weights else 0

    # --- NSGA-II Helpers ---
    def dominates(self, fitness1, fitness2):
        return all(f1 <= f2 for f1, f2 in zip(fitness1, fitness2)) and any(f1 < f2 for f1, f2 in zip(fitness1, fitness2))

    def non_dominated_sorting(self, population):
        fronts = [[]]
        for p in population:
            p.domination_count = 0
            p.dominated_set = []
            for q in population:
                if self.dominates(p.fitness, q.fitness):
                    p.dominated_set.append(q)
                elif self.dominates(q.fitness, p.fitness):
                    p.domination_count += 1
            if p.domination_count == 0:
                p.rank = 0
                fronts[0].append(p)
        
        i = 0
        while len(fronts[i]) > 0:
            next_front = []
            for p in fronts[i]:
                for q in p.dominated_set:
                    q.domination_count -= 1
                    if q.domination_count == 0:
                        q.rank = i + 1
                        next_front.append(q)
            i += 1
            fronts.append(next_front)
        
        if not fronts[-1]: fronts.pop()
        return fronts

    def calculate_crowding_distance(self, front):
        if not front: return
        num_objectives = len(front[0].fitness)
        for p in front: p.crowding_distance = 0
        for m in range(num_objectives):
            front.sort(key=lambda x: x.fitness[m])
            front[0].crowding_distance = float('inf')
            front[-1].crowding_distance = float('inf')
            min_v, max_v = front[0].fitness[m], front[-1].fitness[m]
            if max_v == min_v: continue
            norm = max_v - min_v
            for i in range(1, len(front) - 1):
                front[i].crowding_distance += (front[i+1].fitness[m] - front[i-1].fitness[m]) / norm

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
        
        # Adaptive Decay: Linearly decrease rotation angle
        decay_factor = 1 - (current_gen / self.generation_count)
        self.theta = self.min_theta + (self.initial_theta - self.min_theta) * decay_factor

        for i in range(len(q_ind)):
            # Quantum Mutation (Dynamic)
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
        """Creates a single solution optimized purely for COST to seed the algorithm."""
        ind = Individual()
        ind.CInd = []
        
        # Pre-calculate cheapest resource index
        cheapest_idx = self.server_costs.index(min(self.server_costs))
        
        for _ in range(self.num_tasks):
            gene = [0] * self.num_resources
            gene[cheapest_idx] = 1 # Force assignment to cheapest server
            ind.CInd.extend(gene)
        return ind

    # --- CONDITIONAL SMART REPAIR MECHANISM ---
    
    def repair_population(self, population):
        graph = self.data.get('graph', {})
        
        for ind in population:
            # Decode to get current assignment and objects
            resources_map = decode(self.data, ind)
            
            for resource, task_dicts in resources_map.items():
                if not task_dicts: continue
                
                # Get Resource Info
                r_idx = -1
                for idx, s in enumerate(self.servers):
                    if s.id == resource.id: 
                        r_idx = idx
                        break
                
                if r_idx == -1: continue # Should not happen
                
                av_freq = self.server_freqs[r_idx]
                r_bs_id = resource.base_station.id
                
                for t_dict in task_dicts:
                    t_service = t_dict['service']
                    t_user = t_dict['user']
                    u_bs_id = t_user.base_station.id
                    
                    # 1. Identify Task Index in Genome (to flip bits)
                    # We match by service object identity
                    task_index = -1
                    for i, item in enumerate(self.all_tasks):
                        if item['service'] == t_service:
                            task_index = i
                            break
                    
                    if task_index == -1: continue

                    # 2. Check Constraints (Deadline)
                    exe_delay = get_exe_delay(av_freq, t_service.weight)
                    path_delay = get_path_delay(r_bs_id, u_bs_id, t_service.data_size, self.data, graph)
                    total_delay = exe_delay + path_delay
                    
                    best_target = -1
                    
                    # --- DEADLINE VIOLATION REPAIR ---
                    if total_delay > t_service.deadline:
                        # Constraint Violated! Determine Bottleneck.
                        
                        if path_delay > exe_delay:
                            # Network Bottleneck: Move to CLOSEST server (Same BS)
                            candidates = [s for s in range(self.num_resources) 
                                          if self.servers[s].base_station.id == u_bs_id]
                            
                            if candidates:
                                # Pick random local server (e.g., Raspberry Pi at edge)
                                best_target = random.choice(candidates)
                            else:
                                # No local server? Try to find any server with minimal path delay?
                                # Fallback: Just maximize frequency to compensate
                                best_target = max(range(self.num_resources), key=lambda s: self.server_freqs[s])
                        
                        else:
                            # Compute Bottleneck: Move to FASTEST server (Cloud)
                            best_target = max(range(self.num_resources), key=lambda s: self.server_freqs[s])

                    # --- COST OPTIMIZATION (Only if Deadline Met) ---
                    else:
                        current_cost = self.server_costs[r_idx]
                        min_cost = min(self.server_costs)
                        
                        # If we are on an expensive node (Cloud) but task is light
                        if current_cost > min_cost * 2.0 and t_service.weight < self.avg_task_weight:
                             best_target = min(range(self.num_resources), key=lambda s: self.server_costs[s])

                    # 3. Apply Gene Flip if Target Found
                    if best_target != -1 and best_target != r_idx:
                        start = task_index * self.num_resources
                        ind.CInd[start + r_idx] = 0
                        ind.CInd[start + best_target] = 1
                        
        return population

    # --- Main Loop ---

    def run(self):
        q_ind = self._initialize_population()
        
        # --- SEEDING ---
        seed_ind = self._generate_heuristic_seed()
        seeded_pop = self.fitness([seed_ind], self.data)
        best_overall = copy.deepcopy(seeded_pop[0])
        # ---------------

        classical_pop = []
        
        for gen in range(self.generation_count):
            classical_pop = self._measure(q_ind)
            classical_pop = self.repair_population(classical_pop)
            classical_pop = self.fitness(classical_pop, self.data)
            
            # --- DIVERSITY CHECK (Dynamic Mutation) ---
            # If all individuals have similar costs, boost mutation
            unique_costs = len(set(ind.cost for ind in classical_pop))
            if unique_costs < 5:
                self.mutation_rate = 0.05 # Boost
            else:
                self.mutation_rate = self.base_mutation_rate
            # ------------------------------------------
            
            fronts = self.non_dominated_sorting(classical_pop)
            self.calculate_crowding_distance(fronts[0])
            fronts[0].sort(key=lambda x: x.crowding_distance, reverse=True)
            best_current = fronts[0][0]
            
            if best_overall is None:
                best_overall = copy.deepcopy(best_current)
            elif self.dominates(best_current.fitness, best_overall.fitness):
                best_overall = copy.deepcopy(best_current)
            elif not self.dominates(best_overall.fitness, best_current.fitness):
                if random.random() < 0.3:
                    best_overall = copy.deepcopy(best_current)

            # Pass 'gen' to the update function
            q_ind = self._update_quantum_gates(q_ind, best_overall, gen)

        if best_overall:
            if best_overall not in classical_pop:
                classical_pop.append(best_overall)

        return best_overall, classical_pop