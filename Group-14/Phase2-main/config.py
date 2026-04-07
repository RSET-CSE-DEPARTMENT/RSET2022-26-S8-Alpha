import random
import numpy as np
import heapq
import math

# Simulation Parameters
K_POP_SIZE = 32
K_GEN_SIZE = 60

# --- OPTIMIZATION WEIGHTS ---
W_ENERGY = 0.2
W_LATENCY = 0.7
W_COST = 0.1

class Individual:
    def __init__(self):
        self.QInd = []
        self.CInd = []
        self.fitness = []
        self.cost = float('inf')
        self.energy = float('inf')
        self.latency = float('inf')
        self.crowding_distance = float('inf')
        self.rank = float('inf')
        self.qos = 0
        self.resource_utilization = 0
        self.missed_deadlines = 0
        self.max_resource_latency = 0
        self.mem_overload = False

def get_freq(model_name, resource=None):
    if resource and hasattr(resource, 'frequency') and resource.frequency > 0:
        return resource.frequency
    if "E5430" in model_name: return 2.66 * 1e9
    elif "Raspberry" in model_name: return 1.8 * 1e9
    elif "Cloud" in model_name: return 3.2 * 1e9
    return 2.0 * 1e9

def get_all_tasks(data):
    all_tasks = []
    users = list(data['User'].all())
    for user in users:
        for app in user.applications:
            for service in app.services:
                all_tasks.append({'user': user, 'service': service})
    return all_tasks

def decode(data, individual):
    # 1. Freeze AND Sort the server list (100% Deterministic)
    edge_servers = list(data['EdgeServer'].all())
    # Sort by ID ensures Server[0] is always the same server, every single time.
    edge_servers.sort(key=lambda s: s.id) 
    
    num_resources = len(edge_servers)
    all_tasks = get_all_tasks(data)
    num_tasks = len(all_tasks)

    resources_map = {r: [] for r in edge_servers}

    if len(individual.CInd) < num_tasks * num_resources:
        return resources_map

    for i in range(num_tasks):
        start_index = i * num_resources
        end_index = start_index + num_resources

        if start_index < len(individual.CInd):
            slice_data = individual.CInd[start_index:end_index]
            if sum(slice_data) > 0:
                assigned_resource_index = np.argmax(slice_data)
                
                # Modulo protection
                if num_resources > 0:
                    target_server = edge_servers[assigned_resource_index % num_resources]
                    resources_map[target_server].append(all_tasks[i])

    return resources_map

def memory_is_overloaded(task_dicts, av_memory):
    total_mem = sum(t['service'].memory_demand for t in task_dicts)
    return total_mem > av_memory

def get_exe_delay(av_frequency, task_weight):
    if av_frequency <= 0: return float('inf')
    return task_weight / av_frequency

def get_path_delay(resource_bs_id, user_bs_id, task_data_size, data, graph):
    # Wireless (User -> BS)
    user_bs = data['BaseStation'].find_by_id(user_bs_id)
    if not user_bs or user_bs.wireless_delay <= 0: return float('inf')
    
    upload_delay = task_data_size / user_bs.wireless_delay
    if user_bs_id == resource_bs_id: return upload_delay

    # Dijkstra (Fresh calculation per user request)
    pq = [(0, user_bs_id)]
    min_delay = {user_bs_id: 0}
    network_delay = float('inf')

    while pq:
        current_delay, current_node = heapq.heappop(pq)

        if current_node == resource_bs_id:
            network_delay = current_delay
            break

        if current_delay > min_delay.get(current_node, math.inf):
            continue

        for neighbor, bandwidth in graph.get(current_node, []):
            if bandwidth <= 0: continue
            
            # Link Delay = Size / Bandwidth
            link_delay = task_data_size / bandwidth
            new_delay = current_delay + link_delay

            if new_delay < min_delay.get(neighbor, math.inf):
                min_delay[neighbor] = new_delay
                heapq.heappush(pq, (new_delay, neighbor))

    if network_delay == float('inf'): return float('inf')
    return upload_delay + network_delay

def fitness(population, data):
    if not isinstance(population, list): population = [population]
    graph = data.get('graph', {})
    energy_values, latency_values, cost_values = [], [], []

    for individual in population:
        resources_map = decode(data, individual)
        individual.missed_deadlines = 0
        individual.mem_overload = False
        
        total_energy = 0; total_latency = 0; total_cost = 0; total_tasks = 0

        for resource, task_dicts in resources_map.items():
            if not task_dicts: continue

            # Parameters
            cpu_cores = getattr(resource, 'cpu', 1) 
            base_frequency = get_freq(resource.model_name, resource)
            cost_per_second = resource.power_model_parameters.get('monetary_cost', 0)
            max_power = resource.power_model_parameters.get('max_power_consumption', 0)
            static_pct = resource.power_model_parameters.get('static_power_percentage', 0) / 100.0
            dynamic_power = max_power * (1.0 - static_pct)

            if memory_is_overloaded(task_dicts, resource.memory):
                individual.mem_overload = True

            # Parallelism Logic (CRITICAL PHYSICS)
            sorted_tasks = sorted(task_dicts, key=lambda t: t['service'].deadline)
            num_parallel_tasks = len(sorted_tasks)

            # If 10 tasks run on 1 core, freq is divided by 10.
            if num_parallel_tasks <= cpu_cores:
                effective_frequency = base_frequency
            else:
                effective_frequency = (cpu_cores * base_frequency) / num_parallel_tasks

            for t_dict in sorted_tasks:
                user = t_dict['user']; task = t_dict['service']
                
                exe_delay = get_exe_delay(effective_frequency, task.weight)
                path_delay = get_path_delay(resource.base_station.id, user.base_station.id, task.data_size, data, graph)
                
                delay = path_delay + exe_delay
                energy_consumption = dynamic_power * exe_delay
                task_cost = cost_per_second * exe_delay

                # Accumulate
                total_energy += energy_consumption
                total_cost += task_cost
                total_latency += delay
                total_tasks += 1

                if delay > task.deadline: individual.missed_deadlines += 1

        # =========================================================
        # ⭐ CRITICAL PHYSICS FIX: Totals vs Averages
        # =========================================================
        # Latency is a User QoS metric (Average is correct)
        individual.latency = total_latency / total_tasks if total_tasks > 0 else float('inf')
        
        # Energy and Cost are System Overhead metrics (Absolute Totals are required)
        individual.energy = total_energy if total_tasks > 0 else float('inf')
        individual.cost = total_cost if total_tasks > 0 else float('inf')
        # =========================================================

        energy_values.append(individual.energy)
        latency_values.append(individual.latency)
        cost_values.append(individual.cost)

    if not energy_values: return population

    # Normalization (CRITICAL MATH)
    # Protection against Division by Zero
    min_e, max_e = min(energy_values), max(energy_values)
    min_l, max_l = min(latency_values), max(latency_values)
    min_c, max_c = min(cost_values), max(cost_values)

    range_e = max_e - min_e if max_e > min_e else 1.0
    range_l = max_l - min_l if max_l > min_l else 1.0
    range_c = max_c - min_c if max_c > min_c else 1.0

    for individual in population:
        norm_e = (individual.energy - min_e) / range_e
        norm_l = (individual.latency - min_l) / range_l
        norm_c = (individual.cost - min_c) / range_c
        
        # Penalties: Linear for Deadline, Huge Step for Memory
        penalty = (individual.missed_deadlines * 1.0) + (100.0 if individual.mem_overload else 0.0)
        
        # Weighted Sum (Single Objective)
        individual.fitness = [
            (norm_e * W_ENERGY) + penalty, 
            (norm_l * W_LATENCY) + penalty, 
            (norm_c * W_COST) + penalty
        ]

    return population