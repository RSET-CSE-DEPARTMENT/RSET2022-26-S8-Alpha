from config import *
import random
import numpy as np
import copy

class DE:
    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.population_size = population_size
        self.generation_count = generation_count
        self.data = data
        
        # Robust Task Counting
        self.all_tasks = get_all_tasks(data)
        self.num_tasks = len(self.all_tasks)
        
        # FIX 1: Freeze Server List
        self.servers = list(self.data['EdgeServer'].all())
        self.num_resources = len(self.servers)
        
        self.gene_len = self.num_tasks * self.num_resources
        
        # DE Parameters
        self.F = 0.5  # Mutation factor
        self.CR = 0.7 # Crossover probability

    # --- Helper: Weighted Score ---
    def get_score(self, individual):
        if not individual.fitness or individual.fitness[0] == float('inf'): return float('inf')
        return sum(individual.fitness)

    # --- Continuous to Discrete Mapping ---
    def continuous_to_discrete(self, vector):
        """Converts continuous DE vector to One-Hot binary gene."""
        c_ind = []
        for i in range(self.num_tasks):
            start = i * self.num_resources
            end = start + self.num_resources
            segment = vector[start:end]
            
            # Argmax gives the index of the highest value in the segment
            chosen = np.argmax(segment)
            gene = [0] * self.num_resources
            gene[chosen] = 1
            c_ind.extend(gene)
        return c_ind

    # --- Main Loop ---
    def run(self):
        vectors = []
        population = []
        
        # 1. Random Initialization (No Seeding for Fair Comparison)
        for _ in range(self.population_size):
            # Create random vector [0, 1)
            vec = np.random.rand(self.gene_len)
            vectors.append(vec)
            
            # Map to Discrete Individual
            ind = Individual()
            ind.CInd = self.continuous_to_discrete(vec)
            population.append(ind)
            
        # Initial Evaluation
        population = self.fitness(population, self.data)

        # 2. Evolution Loop
        for _ in range(self.generation_count):
            new_population = []
            new_vectors = []
            
            for i in range(self.population_size):
                # Mutation: Target + F * (Difference)
                idxs = [idx for idx in range(self.population_size) if idx != i]
                a, b, c = np.random.choice(idxs, 3, replace=False)
                
                target_vec = vectors[i]
                donor_vec = vectors[a] + self.F * (vectors[b] - vectors[c])
                
                # Crossover (Binomial)
                trial_vec = np.zeros_like(target_vec)
                for j in range(self.gene_len):
                    if random.random() <= self.CR or j == random.randint(0, self.gene_len - 1):
                        trial_vec[j] = donor_vec[j]
                    else:
                        trial_vec[j] = target_vec[j]
                
                # Create Trial Individual
                trial_ind = Individual()
                trial_ind.CInd = self.continuous_to_discrete(trial_vec)
                
                new_population.append(trial_ind)
                new_vectors.append(trial_vec)

            # Evaluate Offspring
            new_population = self.fitness(new_population, self.data)
            
            # Selection (One-to-One Survival)
            final_population = []
            final_vectors = []
            
            for i in range(self.population_size):
                score_old = self.get_score(population[i])
                score_new = self.get_score(new_population[i])
                
                if score_new < score_old:
                    final_population.append(new_population[i])
                    final_vectors.append(new_vectors[i])
                else:
                    final_population.append(population[i])
                    final_vectors.append(vectors[i])
            
            population = final_population
            vectors = final_vectors

        # Return Best Solution
        best_overall = min(population, key=self.get_score) if population else None
        
        # Return as list for compatibility
        return best_overall, [best_overall]