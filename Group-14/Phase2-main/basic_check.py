import sys
import os
import random

# Ensure the script can see the parent directory for imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from algorithms import QIGA, HybridQIGA, GA, MOHEFT, DE, PSO, OC, OE, RA, RR
from config import Individual

# --- Robust Mock Infrastructure ---
class MockObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def create_mock_data():
    """
    Creates a data dictionary that mimics EdgeSimPy structure 
    sufficiently for all algorithms to initialize and run one step.
    """
    # 1. Create Base Stations
    bs1 = MockObject(id=1, wireless_delay=1.0)
    bs2 = MockObject(id=2, wireless_delay=2.0)
    
    # 2. Create Edge Servers (Tier 1 and Tier 2)
    servers = [
        MockObject(
            id=101, 
            model_name="Cloud Server", 
            frequency=50e9,
            memory=100000,
            base_station=bs1,
            power_model_parameters={'monetary_cost': 10, 'static_power_percentage': 0.1}
        ),
        MockObject(
            id=102, 
            model_name="Raspberry Pi", 
            frequency=1.8e9, 
            memory=4000,
            base_station=bs2,
            power_model_parameters={'monetary_cost': 1, 'static_power_percentage': 0.05}
        ),
        MockObject(
            id=103, 
            model_name="E5430", 
            frequency=2.66e9, 
            memory=8000,
            base_station=bs2,
            power_model_parameters={'monetary_cost': 5, 'static_power_percentage': 0.08}
        )
    ]

    # 3. Create Users with Applications and Services (Tasks)
    users = []
    for i in range(5): # 5 Users
        # Each user has 1 App with 1 Service
        service = MockObject(
            weight=100, 
            memory_demand=50, 
            deadline=200, 
            data_size=100
        )
        app = MockObject(services=[service])
        user = MockObject(
            id=i, 
            applications=[app], 
            base_station=bs1
        )
        users.append(user)

    # 4. Create Graph (Network Links)
    # Simple empty graph for get_path_delay to default to wireless only
    graph = {} 

    # 5. Assemble Data Dictionary
    data = {
        'EdgeServer': MockObject(all=lambda: servers, count=lambda: len(servers)),
        'User': MockObject(all=lambda: users, count=lambda: len(users)),
        'BaseStation': MockObject(find_by_id=lambda x: bs1 if x==1 else bs2),
        'NetworkLink': MockObject(all=lambda: []),
        'graph': graph
    }
    
    return data

# --- Mock Fitness Function ---
def mock_fitness(pop, data):
    for ind in pop:
        # Assign random fitness values to avoid math errors in sorting/ranking
        ind.fitness = [random.random(), random.random(), random.random()]
        ind.energy = random.random() * 100
        ind.cost = random.random() * 50
        ind.latency = random.random() * 20
    return pop

# --- Test Runner ---
def test_algo(AlgoClass, name):
    try:
        data = create_mock_data()
        
        # Instantiate Algorithm
        if name == "OC":
            algo = AlgoClass(mock_fitness, data)
        else:
            # pop_size=10, gen_count=2
            algo = AlgoClass(mock_fitness, 10, 2, data)
        
        # Run Algorithm
        res = algo.run()
        
        # Validation
        if not isinstance(res, tuple) or len(res) != 2:
            print(f"FAIL: {name} did not return tuple (best, pop)")
            return False
        
        best, pop = res
        
        if not isinstance(pop, list):
            print(f"FAIL: {name} population is not a list")
            return False
            
        if best is None:
            print(f"FAIL: {name} returned None for best solution")
            return False
            
        if len(best.CInd) == 0:
             print(f"FAIL: {name} produced empty individual")
             return False

        print(f"PASS: {name}")
        return True
        
    except Exception as e:
        print(f"FAIL: {name} crashed with {e}")
        # traceback.print_exc() # Uncomment for debugging
        return False

# --- Execution ---
if __name__ == "__main__":
    print("--- Starting Interface Check ---")
    algos = [
        (QIGA.QIGA, "QIGA"),
        (HybridQIGA.HybridQIGA, "HybridQIGA"),
        (GA.GA, "GA"),
        (MOHEFT.MOHEFT, "MOHEFT"),
        (DE.DE, "DE"),
        (PSO.PSO, "PSO"),
        (OC.OC, "OC"),
        (OE.OE, "OE"),
        (RA.RA, "RA"),
        (RR.RR, "RR")
    ]

    passed = 0
    for Cls, Name in algos:
        if test_algo(Cls, Name): passed += 1

    print(f"\nSummary: {passed}/{len(algos)} Algorithms passed basic interface check.")