from config import *
import random

class RA:
    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.population_size = population_size
        self.generation_count = generation_count # Not used
        self.data = data
        
        self.all_tasks = get_all_tasks(data)
        self.num_tasks = len(self.all_tasks)

        # FIX: Freeze and Sort servers to match config.py logic exactly
        self.servers = list(self.data['EdgeServer'].all())
        self.servers.sort(key=lambda s: s.id)
        self.num_resources = len(self.servers)

    def schedule(self):
        individual = Individual()
        # Initialize gene with zeros
        individual.CInd = [0] * (self.num_tasks * self.num_resources)

        for task_idx in range(self.num_tasks):
            start_idx = task_idx * self.num_resources
            
            # Pure Random Assignment
            assigned_resource = random.randint(0, self.num_resources - 1)
            
            # Set the bit
            individual.CInd[start_idx + assigned_resource] = 1

        return individual

    def run(self):
        # Generate 'population_size' random solutions and pick the best one
        # This gives RA a fair chance to find something decent
        population = [self.schedule() for _ in range(self.population_size)]
        
        evaluated_population = self.fitness(population, self.data)
        
        # Simple weighted score helper
        def get_score(ind):
            if not ind.fitness or ind.fitness[0] == float('inf'): return float('inf')
            return sum(ind.fitness)

        # Return best found random assignment
        best_overall = min(evaluated_population, key=get_score)
        return best_overall, evaluated_population