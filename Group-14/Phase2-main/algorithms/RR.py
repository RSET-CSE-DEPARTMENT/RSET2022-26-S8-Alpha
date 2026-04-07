from config import *

class RR:
    def __init__(self, fitness, population_size, generation_count, data):
        self.fitness = fitness
        self.population_size = population_size # Not used, but needed for interface
        self.generation_count = generation_count # Not used
        self.data = data
        
        self.all_tasks = get_all_tasks(data)
        self.num_tasks = len(self.all_tasks)

        # FIX: Freeze and Sort servers to match config.py logic
        self.servers = list(self.data['EdgeServer'].all())
        self.servers.sort(key=lambda s: s.id)
        self.num_resources = len(self.servers)
        
        self.current_resource_idx = 0

    def schedule(self):
        individual = Individual()
        # Initialize gene with zeros
        individual.CInd = [0] * (self.num_tasks * self.num_resources)

        for task_idx in range(self.num_tasks):
            start_idx = task_idx * self.num_resources
            
            # Simple Round Robin logic
            assigned_resource = self.current_resource_idx % self.num_resources
            
            # Set the bit
            individual.CInd[start_idx + assigned_resource] = 1
            
            # Move to next server
            self.current_resource_idx += 1

        return individual

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

        # Create single deterministic solution
        population = [self.schedule()]
        # Evaluate
        evaluated_population = self.fitness(population, self.data)
        # Return format: (Best, Population_List)
        return evaluated_population[0], evaluated_population