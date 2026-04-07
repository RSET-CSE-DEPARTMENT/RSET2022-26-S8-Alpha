from config import *

class OC:
    def __init__(self, fitness, data):
        self.fitness = fitness
        self.data = data
        
        # Robust task counting
        self.all_tasks = get_all_tasks(data)
        self.num_tasks = len(self.all_tasks)

        # FIX: Freeze and Sort servers to match config.py logic exactly
        self.servers = list(self.data['EdgeServer'].all())
        self.servers.sort(key=lambda s: s.id)
        self.num_resources = len(self.servers)

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

        individual = Individual()
        individual.CInd = []
        
        # Find the Cloud Index in the SORTED list
        cloud_index = -1
        for i, server in enumerate(self.servers):
            if "Cloud" in server.model_name:
                cloud_index = i
                break
        
        # Fallback: If no cloud found (rare), use the last server (likely powerful)
        if cloud_index == -1:
            cloud_index = self.num_resources - 1

        # Assign ALL tasks to Cloud
        for _ in range(self.num_tasks):
            gene = [0] * self.num_resources
            gene[cloud_index] = 1
            individual.CInd.extend(gene)
        
        # Evaluate
        population = [individual]
        population = self.fitness(population, self.data)
        
        return population[0], population