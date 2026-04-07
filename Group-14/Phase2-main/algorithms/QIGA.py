from config import *
import random
import numpy as np
import copy

class QIGA:
    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.population_size = population_size
        self.generation_count = generation_count
        self.data = data
        
        # Robust Task Counting
        self.all_tasks = get_all_tasks(data)
        self.num_tasks = len(self.all_tasks)
        
        # FIX: Freeze and Sort servers to match config.py logic exactly
        self.servers = list(self.data['EdgeServer'].all())
        self.servers.sort(key=lambda s: s.id)
        self.num_resources = len(self.servers)
        
        # Quantum Parameters (Adaptive - Matching HybridQIGA for Fairness)
        self.initial_theta = 0.05 * np.pi
        self.min_theta = 0.01 * np.pi
        self.theta = self.initial_theta 
        self.mutation_rate = 0.01 
        
        # Cache for potential future logic, though seeding is removed
        self.server_costs = [s.power_model_parameters.get('monetary_cost', 0) for s in self.servers]

    # --- Helper: Weighted Score (Unifying the Evaluation) ---
    def get_score(self, ind):
        if not ind.fitness or ind.fitness[0] == float('inf'): return float('inf')
        return sum(ind.fitness)

    # --- Quantum Operations ---
    def _initialize_population(self):
        num_qubits = self.num_tasks * self.num_resources
        q_ind = []
        for _ in range(num_qubits):
            # True Standard QIGA: Start in pure superposition (equal probability for all states)
            q_ind.append(np.array([[1/np.sqrt(2)], [1/np.sqrt(2)]]))
        return q_ind

    def _measure(self, q_ind):
        classical_pop = []
        for _ in range(self.population_size):
            ind = Individual()
            ind.CInd = []
            
            for i in range(0, len(q_ind), self.num_resources):
                task_qubits = q_ind[i : i + self.num_resources]
                
                # Extract Probabilities (|beta|^2)
                probs = np.array([np.abs(q[1][0])**2 for q in task_qubits]).flatten()
                
                # Normalize
                if probs.sum() == 0: 
                    probs = np.ones(len(probs)) / len(probs)
                else: 
                    probs = probs / probs.sum()
                
                # Selection
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
            # 1. Quantum Mutation
            if random.random() < self.mutation_rate:
                random_angle = random.uniform(-0.1 * np.pi, 0.1 * np.pi)
                rot_mut = np.array([[np.cos(random_angle), -np.sin(random_angle)],
                                    [np.sin(random_angle), np.cos(random_angle)]])
                q_ind[i] = np.dot(rot_mut, q_ind[i])
                norm = np.linalg.norm(q_ind[i])
                q_ind[i] = q_ind[i] / norm
                continue

            # 2. Steering
            target_bit = best_solution.CInd[i]
            alpha = q_ind[i][0][0]
            beta = q_ind[i][1][0]
            
            # Stability Check
            if target_bit == 1 and abs(beta)**2 > 0.99: continue
            if target_bit == 0 and abs(alpha)**2 > 0.99: continue

            direction = 0
            if target_bit == 1:
                if abs(alpha * beta) < 1e-9: direction = 1 
                else: direction = 1 if alpha * beta > 0 else -1 
            else:
                if abs(alpha * beta) < 1e-9: direction = -1
                else: direction = -1 if alpha * beta > 0 else 1
            
            rotation_angle = direction * self.theta
            
            rot = np.array([[np.cos(rotation_angle), -np.sin(rotation_angle)],
                            [np.sin(rotation_angle), np.cos(rotation_angle)]])
            q_ind[i] = np.dot(rot, q_ind[i])
            
            # Normalization Fix
            norm = np.linalg.norm(q_ind[i])
            q_ind[i] = q_ind[i] / norm
            
        return q_ind

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

        q_ind = self._initialize_population()
        
        # --- PURE QIGA: No Seeding ---
        best_overall = None
        classical_pop = []
        
        for gen in range(self.generation_count):
            # 1. Measure the quantum states
            classical_pop = self._measure(q_ind)
            
            # 2. Evaluate fitness
            classical_pop = self.fitness(classical_pop, self.data)
            
            # 3. FAIR SCORING: Sort by simple weighted score
            classical_pop.sort(key=self.get_score)
            best_current = classical_pop[0]
            
            # 4. Update Global Best (Handling None state for the first generation)
            if best_overall is None:
                best_overall = copy.deepcopy(best_current)
            else:
                current_score = self.get_score(best_current)
                overall_score = self.get_score(best_overall)

                if current_score < overall_score:
                    best_overall = copy.deepcopy(best_current)
                elif current_score == overall_score:
                    if random.random() < 0.3:
                        best_overall = copy.deepcopy(best_current)

            # 5. Update Quantum Gates based on the FAIR best_overall
            q_ind = self._update_quantum_gates(q_ind, best_overall, gen)

        if best_overall:
            if best_overall not in classical_pop:
                classical_pop.insert(0, best_overall)
        
        return best_overall, classical_pop