from config import *
import random
import copy
import numpy as np

class GA:
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
        
        self.gene_size = self.num_tasks * self.num_resources

    # --- Helper: Weighted Sum Score (Fairness Metric) ---
    def get_score(self, ind):
        """Returns the single weighted fitness score (Lower is better)."""
        if not ind.fitness: return float('inf')
        return sum(ind.fitness)

    # --- Core GA Methods ---

    def initialize_population(self):
        """
        Pure Random Initialization.
        FIX 2: Removed Heuristic Seeding for fair comparison against Quantum.
        """
        population = []
        for _ in range(self.population_size):
            individual = Individual()
            individual.CInd = []
            for _ in range(self.num_tasks):
                task_gene = [0] * self.num_resources
                # Pick random server
                chosen_server = random.randint(0, self.num_resources - 1)
                task_gene[chosen_server] = 1
                individual.CInd.extend(task_gene)
            population.append(individual)
        return population

    def selection(self, population):
        """Tournament Selection based on Weighted Score."""
        competitors = random.sample(population, 2)
        # Compare scores directly (Minimization)
        if self.get_score(competitors[0]) < self.get_score(competitors[1]):
            return competitors[0]
        return competitors[1]

    def crossover(self, p1, p2):
        # Task-Aware Uniform Crossover
        c1, c2 = Individual(), Individual()
        c1.CInd = []
        c2.CInd = []
        
        for i in range(self.num_tasks):
            start = i * self.num_resources
            end = start + self.num_resources
            
            # 50% chance to swap this task assignment between parents
            if random.random() < 0.5:
                c1.CInd.extend(p1.CInd[start:end])
                c2.CInd.extend(p2.CInd[start:end])
            else:
                c1.CInd.extend(p2.CInd[start:end])
                c2.CInd.extend(p1.CInd[start:end])
        return c1, c2

    def mutation(self, individual):
        """Random Resetting Mutation"""
        if self.num_tasks == 0: return individual
        new_genes = individual.CInd[:] 
        
        # Standard Mutation Rate
        if random.random() < 0.1: 
            task_idx = random.randint(0, self.num_tasks - 1)
            new_server = random.randint(0, self.num_resources - 1)
            
            start = task_idx * self.num_resources
            end = start + self.num_resources
            
            # Reset this task's bits to 0
            new_genes[start:end] = [0] * self.num_resources
            # Set new server bit to 1
            new_genes[start + new_server] = 1
            
        individual.CInd = new_genes
        return individual

    def run(self):
        # 🔴 DYNAMIC SYNCHRONIZATION
        self.all_tasks = get_all_tasks(self.data)
        self.num_tasks = len(self.all_tasks)
        self.gene_size = self.num_tasks * self.num_resources

        # 🛑 ZERO-TASK TRAP
        if self.num_tasks == 0:
            dummy = Individual()
            dummy.CInd = []
            pop = self.fitness([dummy], self.data)
            return pop[0], pop

        # 1. Initialize Randomly
        population = self.initialize_population()
        population = self.fitness(population, self.data)
        
        # 2. Sort by Weighted Score
        population.sort(key=self.get_score)
        best_overall = copy.deepcopy(population[0])
        
        for _ in range(self.generation_count):
            offspring = []
            
            # Elitism: Always keep the absolute best from previous gen
            offspring.append(copy.deepcopy(best_overall))
            
            # Fill the rest
            while len(offspring) < self.population_size:
                p1 = self.selection(population)
                p2 = self.selection(population)
                c1, c2 = self.crossover(p1, p2)
                offspring.extend([self.mutation(c1), self.mutation(c2)])
            
            # Trim to exact population size (handling potential overflow from extend)
            offspring = offspring[:self.population_size]
            
            # Evaluate new generation
            population = self.fitness(offspring, self.data)
            
            # Sort and Update Global Best
            population.sort(key=self.get_score)
            
            if self.get_score(population[0]) < self.get_score(best_overall):
                best_overall = copy.deepcopy(population[0])
            
        return best_overall, population