import random
from config import *

class OE:
    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.population_size = population_size
        self.generation_count = generation_count
        self.data = data
        
        self.all_tasks = get_all_tasks(data)
        self.num_tasks = len(self.all_tasks)

        # FIX: Freeze and Sort servers to match config.py logic exactly
        self.servers = list(self.data['EdgeServer'].all())
        self.servers.sort(key=lambda s: s.id)
        self.num_resources = len(self.servers)

        # Pre-calculate valid indices (Edge Nodes Only)
        # We assume "Cloud" is in the model name for the cloud server
        self.edge_indices = []
        for i, s in enumerate(self.servers):
            if "Cloud" not in s.model_name:
                self.edge_indices.append(i)
        
        # Fallback: If no edge servers found (weird scenario), allow all
        if not self.edge_indices:
            self.edge_indices = list(range(self.num_resources))

    def schedule(self):
        individual = Individual()
        individual.CInd = [0] * (self.num_tasks * self.num_resources)

        for task_idx in range(self.num_tasks):
            start_idx = task_idx * self.num_resources
            
            # Pick a random VALID Edge Server
            assigned_resource = random.choice(self.edge_indices)
            
            # Set the bit
            individual.CInd[start_idx + assigned_resource] = 1
            
        return individual

    def run(self):
        population = [self.schedule() for _ in range(self.population_size)]
        evaluated_population = self.fitness(population, self.data)
        
        def get_score(ind):
            if not ind.fitness or ind.fitness[0] == float('inf'): return float('inf')
            return sum(ind.fitness)

        best_overall = min(evaluated_population, key=get_score)
        return best_overall, evaluated_population