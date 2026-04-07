from config import *
import random
import numpy as np
import copy

class SQIGA:
    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.population_size = population_size
        self.generation_count = generation_count
        self.data = data
        
        # 1. Freeze Data (MUST match config.py logic exactly)
        self.all_tasks = get_all_tasks(data) 
        self.num_tasks = len(self.all_tasks)
        
        # FIX 1: Freeze AND Sort Server List (Determinism match with config.py)
        self.servers = list(self.data['EdgeServer'].all()) 
        self.servers.sort(key=lambda s: s.id)
        self.num_resources = len(self.servers)
        
        # Quantum Parameters
        self.initial_theta = 0.05 * np.pi
        self.min_theta = 0.01 * np.pi
        self.theta = self.initial_theta 
        self.mutation_rate = 0.01 
        
        # Cache for seeding
        self.server_costs = [s.power_model_parameters.get('monetary_cost', 0) for s in self.servers]
        self.server_freqs = [get_freq(s.model_name, s) for s in self.servers]

    # --- Seeding (Safe Round-Robin) ---
    def _generate_heuristic_seed(self):
        """Cost-optimized seed, distributed to prevent overload."""
        ind = Individual()
        ind.CInd = []
        
        # Sort indices by cost
        sorted_indices = np.argsort(self.server_costs)
        
        # FIX 2: Poison Seed Fix (Use 50% of servers, not just 3)
        # This prevents immediate congestion in the seed
        top_k = max(3, self.num_resources // 2)
        best_servers = sorted_indices[:top_k]
        
        for i in range(self.num_tasks):
            target_idx = best_servers[i % top_k]
            gene = [0] * self.num_resources
            gene[target_idx] = 1
            ind.CInd.extend(gene)
        return ind
    
    def _generate_latency_seed(self):
        """Speed-optimized seed, distributed to prevent overload."""
        ind = Individual()
        ind.CInd = []
        
        # Sort indices by speed (Descending)
        sorted_indices = np.argsort(self.server_freqs)[::-1]
        
        # FIX 2: Poison Seed Fix
        top_k = max(3, self.num_resources // 2)
        best_servers = sorted_indices[:top_k]
        
        for i in range(self.num_tasks):
            target_idx = best_servers[i % top_k]
            gene = [0] * self.num_resources
            gene[target_idx] = 1
            ind.CInd.extend(gene)
        return ind

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
            # Mutation
            if random.random() < self.mutation_rate:
                random_angle = random.uniform(-0.1 * np.pi, 0.1 * np.pi)
                rot_mut = np.array([[np.cos(random_angle), -np.sin(random_angle)],
                                    [np.sin(random_angle), np.cos(random_angle)]])
                q_ind[i] = np.dot(rot_mut, q_ind[i])
                # Normalize
                norm = np.linalg.norm(q_ind[i])
                q_ind[i] = q_ind[i] / norm
                continue

            # Steering
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
            
            # Normalize
            norm = np.linalg.norm(q_ind[i])
            q_ind[i] = q_ind[i] / norm
            
        return q_ind

    def get_score(self, ind):
        if not ind.fitness: return float('inf')
        return sum(ind.fitness)

    def run(self):
        q_ind = self._initialize_population()
        
        # --- SEEDING ---
        seed_cost = self._generate_heuristic_seed()
        seed_latency = self._generate_latency_seed()
        seeded_pop = self.fitness([seed_cost, seed_latency], self.data)
        seeded_pop.sort(key=self.get_score)
        best_overall = copy.deepcopy(seeded_pop[0])
        # ---------------

        classical_pop = []
        
        for gen in range(self.generation_count):
            classical_pop = self._measure(q_ind)
            classical_pop = self.fitness(classical_pop, self.data)
            
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