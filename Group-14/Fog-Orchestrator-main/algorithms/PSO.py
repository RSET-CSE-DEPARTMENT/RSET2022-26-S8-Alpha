from config import *
import random
import numpy as np
import copy

class PSO:
    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.population_size = population_size
        self.generation_count = generation_count
        self.data = data
        
        # Robust Task Counting
        self.all_tasks = get_all_tasks(data)
        self.num_tasks = len(self.all_tasks)
        
        # FIX 1: Freeze Server List (Crucial for Stability)
        self.servers = list(self.data['EdgeServer'].all())
        self.num_resources = len(self.servers)
        
        # PSO Hyperparameters
        self.w = 0.5  # Inertia
        self.c1 = 1.5 # Cognitive (Personal Best)
        self.c2 = 1.5 # Social (Global Best)
        
        # Cache server costs (still useful for future logic, though not used for seeding anymore)
        self.server_costs = [s.power_model_parameters.get('monetary_cost', 0) for s in self.servers]

    # --- Helper: Weighted Score ---
    def get_score(self, individual):
        """Returns the single weighted fitness score (Lower is better)."""
        if not individual.fitness or individual.fitness[0] == float('inf'): return float('inf')
        return sum(individual.fitness) 

    # --- Mapping Functions (Continuous <-> Discrete) ---
    def discrete_to_continuous(self, individual):
        """Converts binary gene to continuous vector for velocity math."""
        return np.array(individual.CInd, dtype=float)

    def continuous_to_discrete(self, vector):
        """Converts continuous position vector back to valid One-Hot binary gene."""
        c_ind = []
        for i in range(self.num_tasks):
            start = i * self.num_resources
            end = start + self.num_resources
            segment = vector[start:end]
            
            # One-Hot Encoding: The highest value in the segment gets the '1'
            chosen = np.argmax(segment)
            gene = [0] * self.num_resources
            gene[chosen] = 1
            c_ind.extend(gene)
        return c_ind

    # --- Main Loop ---
    def run(self):
        particles = []
        velocities = []
        
        # 1. Initialization (Pure Random - No Seeding)
        for _ in range(self.population_size):
            ind = Individual()
            ind.CInd = []
            for _ in range(self.num_tasks):
                gene = [0] * self.num_resources
                # Pick random server
                gene[random.randint(0, self.num_resources - 1)] = 1
                ind.CInd.extend(gene)
            particles.append(ind)
            
            # Initialize random velocity
            velocities.append(np.random.uniform(-1, 1, len(ind.CInd)))
        
        # Initial Evaluation
        particles = self.fitness(particles, self.data)
        
        # Initialize Personal Bests (p_best) to current positions
        p_best = copy.deepcopy(particles)
        p_best_scores = [self.get_score(p) for p in particles]
        
        # Initialize Global Best (g_best)
        g_best = min(p_best, key=self.get_score)
        g_best_score = self.get_score(g_best)
        g_best_pos = self.discrete_to_continuous(g_best)

        # 2. Optimization Loop
        for _ in range(self.generation_count):
            new_particles = []
            
            for i in range(self.population_size):
                current_pos = self.discrete_to_continuous(particles[i])
                p_best_pos = self.discrete_to_continuous(p_best[i])
                
                # Update Velocity
                # v = w*v + c1*r1*(pbest - current) + c2*r2*(gbest - current)
                r1, r2 = random.random(), random.random()
                velocities[i] = (self.w * velocities[i] + 
                                 self.c1 * r1 * (p_best_pos - current_pos) + 
                                 self.c2 * r2 * (g_best_pos - current_pos))
                
                # Update Position
                new_pos_continuous = current_pos + velocities[i]
                
                # Discretize back to Binary Individual
                new_ind = Individual()
                new_ind.CInd = self.continuous_to_discrete(new_pos_continuous)
                new_particles.append(new_ind)

            # Evaluate New Generation
            new_particles = self.fitness(new_particles, self.data)
            
            # Update Bests
            for i in range(self.population_size):
                score = self.get_score(new_particles[i])
                
                # Update Personal Best
                if score < p_best_scores[i]:
                    p_best[i] = copy.deepcopy(new_particles[i])
                    p_best_scores[i] = score
                    
                    # Update Global Best
                    if score < g_best_score:
                        g_best = copy.deepcopy(new_particles[i])
                        g_best_score = score
                        g_best_pos = self.discrete_to_continuous(g_best)
            
            particles = new_particles

        # Return best found solution
        # (Return as list for compatibility with runner script)
        return g_best, [g_best]