import os
import random
import argparse
from edge_sim_py import *
from edge_sim_py.dataset_generator import *
from edge_sim_py.components.mobility_models import random_mobility
from edge_sim_py.dataset_generator.edge_servers import raspberry_pi4, e5430

# --- Step 1: Parse Command-Line Arguments ---
parser = argparse.ArgumentParser(description="Generate a custom Fog scenario.")
parser.add_argument("--scenario_name", type=str, default="Base_Case")
parser.add_argument("--users", type=int, default=50)
parser.add_argument("--tier1", type=int, default=15)
parser.add_argument("--tier2", type=int, default=4)
parser.add_argument("--avg_weight", type=int, default=3)
parser.add_argument("--avg_data_size", type=int, default=500)
parser.add_argument("--deadline", type=float, default=30.0)
args = parser.parse_args()

# --- Step 2: Define Scenario Size ---
NUM_USERS = args.users
NUM_TIER1_NODES = args.tier1
NUM_TIER2_SERVERS = args.tier2
NUM_TIER3_CLOUD = 1 
TOTAL_SERVERS = NUM_TIER1_NODES + NUM_TIER2_SERVERS + NUM_TIER3_CLOUD
SCENARIO_FILENAME = f"{args.scenario_name}_ES-{TOTAL_SERVERS}_ED-{NUM_USERS}"

# Calculate Grid Size
TOTAL_BS_NEEDED = NUM_TIER1_NODES + NUM_TIER2_SERVERS + NUM_TIER3_CLOUD
MAP_SIZE = int(TOTAL_BS_NEEDED**0.5) + 2
TOTAL_BS = MAP_SIZE * MAP_SIZE

print(f"Generating: {SCENARIO_FILENAME} | Grid: {MAP_SIZE}x{MAP_SIZE}")
print(f"Topology: Hierarchical Mesh (Tier 1 Ring + Tier 2 Uplinks)")

# --- Step 3: Output Dir ---
output_dir = "datasets"
os.makedirs(output_dir, exist_ok=True)

# --- Step 4: Map ---
map_coordinates = quadratic_grid(x_size=MAP_SIZE, y_size=MAP_SIZE)

# --- Step 5: Base Stations ---
base_stations = []
network_switches = []
for i, coords in enumerate(map_coordinates):
    bs = BaseStation()
    bs.id = i + 1
    bs.coordinates = coords
    bs.wireless_delay = 100 # 100 Mbps wireless link assumed
    base_stations.append(bs)
    
    switch = NetworkSwitch()
    switch.id = i + 1
    network_switches.append(switch)
    bs._connect_to_network_switch(switch)

# --- Step 6: Edge Servers ---
edge_servers = []
server_id_counter = 1

# Tier 1 (Pi - Fog Nodes)
for i in range(NUM_TIER1_NODES):
    fog_node = raspberry_pi4()
    fog_node.id = server_id_counter
    fog_node.power_model_parameters["monetary_cost"] = 1
    edge_servers.append(fog_node)
    
    # Distribute them across the map
    if i < len(base_stations):
        base_stations[i]._connect_to_edge_server(fog_node)
    server_id_counter += 1

# Tier 2 (Xeon - Edge Servers)
for i in range(NUM_TIER2_SERVERS):
    fog_server = e5430()
    fog_server.id = server_id_counter
    fog_server.power_model_parameters["monetary_cost"] = 3
    edge_servers.append(fog_server)
    
    # Place them after Tier 1 nodes
    idx = NUM_TIER1_NODES + i
    if idx < len(base_stations):
        base_stations[idx]._connect_to_edge_server(fog_server)
    server_id_counter += 1

# Tier 3 (Cloud)
cloud_server = EdgeServer()
cloud_server.id = server_id_counter
cloud_server.model_name = "Cloud-Server"
cloud_server.cpu = 64
cloud_server.memory = 262144
cloud_server.disk = 1048576
cloud_server.frequency = 3.2 * 1e9 # 3.2 GHz
cloud_server.power_model_parameters = {
    "max_power_consumption": 600,
    "static_power_percentage": 65,
    "monetary_cost": 10
}
edge_servers.append(cloud_server)

# Place Cloud at the "End" of the grid or middle
c_idx = NUM_TIER1_NODES + NUM_TIER2_SERVERS
if c_idx < len(base_stations):
    base_stations[c_idx]._connect_to_edge_server(cloud_server)

# --- Step 7: Network Topology (FIX 2: HIERARCHICAL MESH) ---
topology = Topology()
topology.id = 1
topology.add_nodes_from(network_switches)

# Define Layers based on your server placement logic
tier_1_indices = range(0, NUM_TIER1_NODES)
tier_2_indices = range(NUM_TIER1_NODES, NUM_TIER1_NODES + NUM_TIER2_SERVERS)

cloud_switch_idx = c_idx
if cloud_switch_idx >= len(network_switches):
    cloud_switch = network_switches[-1]
else:
    cloud_switch = network_switches[cloud_switch_idx]

# 1. LAYER 1: ACCESS RING (Horizontal Traffic)
# Connect all neighbors (i -> i+1) to form a ring
for i in range(len(network_switches)):
    node_a = network_switches[i]
    target_idx = (i + 1) % len(network_switches)
    node_b = network_switches[target_idx]

    link = NetworkLink()
    link.id = len(topology.edges) + 1
    link.nodes = [node_a, node_b]
    link.bandwidth = 1000  # 1 Gbps
    link.delay = 0.002     # 2ms
    link.topology = topology
    topology.add_edge(node_a, node_b)
    if node_a in topology._adj: topology._adj[node_a][node_b] = link
    if node_b in topology._adj: topology._adj[node_b][node_a] = link

# 2. LAYER 2: AGGREGATION UPLINKS (Vertical Traffic)
# Connect Tier 1 Nodes to Tier 2 Parents
tier_2_nodes = [network_switches[i] for i in tier_2_indices if i < len(network_switches)]

if tier_2_nodes:
    for t1_idx in tier_1_indices:
        if t1_idx >= len(network_switches): continue
        t1_node = network_switches[t1_idx]
        
        # Load Balancing: Distribute Tier 1 nodes evenly among Tier 2 parents
        parent_node = tier_2_nodes[t1_idx % len(tier_2_nodes)]
        
        # Avoid duplicate links if they are already neighbors
        if parent_node not in topology.neighbors(t1_node):
            link = NetworkLink()
            link.id = len(topology.edges) + 1
            link.nodes = [t1_node, parent_node]
            link.bandwidth = 2000 # 2 Gbps
            link.delay = 0.005    # 5ms
            link.topology = topology
            topology.add_edge(link.nodes[0], link.nodes[1])
            if link.nodes[0] in topology._adj: topology._adj[link.nodes[0]][link.nodes[1]] = link
            if link.nodes[1] in topology._adj: topology._adj[link.nodes[1]][link.nodes[0]] = link

# 3. LAYER 3: CORE BACKHAUL (Tier 2 -> Cloud)
for t2_node in tier_2_nodes:
    if t2_node != cloud_switch:
        link = NetworkLink()
        link.id = len(topology.edges) + 1
        link.nodes = [t2_node, cloud_switch]
        link.bandwidth = 200   # 200 Mbps Bottleneck
        link.delay = 0.050     # 50ms Delay
        link.topology = topology
        topology.add_edge(link.nodes[0], link.nodes[1])
        if link.nodes[0] in topology._adj: topology._adj[link.nodes[0]][link.nodes[1]] = link
        if link.nodes[1] in topology._adj: topology._adj[link.nodes[1]][link.nodes[0]] = link

# Fallback: Connect Cloud to start if no Tier 2 exists
if not tier_2_nodes and cloud_switch != network_switches[0]:
    link = NetworkLink()
    link.id = len(topology.edges) + 1
    link.nodes = [network_switches[0], cloud_switch]
    link.bandwidth = 200
    link.delay = 0.050
    link.topology = topology
    topology.add_edge(network_switches[0], cloud_switch)
    if network_switches[0] in topology._adj: topology._adj[network_switches[0]][cloud_switch] = link
    if cloud_switch in topology._adj: topology._adj[cloud_switch][network_switches[0]] = link


# --- Step 8: Users ---
for i in range(NUM_USERS):
    user = User()
    user.id = i + 1
    
    # --- FIX 1: HIERARCHY ENFORCEMENT ---
    # Users only spawn at Tier 1 (Indices 0 to 14) to ensure proper Fog behavior
    valid_bs = base_stations[:NUM_TIER1_NODES] 
    if not valid_bs: valid_bs = base_stations
    user_bs = random.choice(valid_bs)
    
    user.coordinates = user_bs.coordinates
    user.coordinates_trace = [user_bs.coordinates]
    user.base_station = user_bs
    user_bs.users.append(user)
    user.mobility_model = random_mobility # Fine for static snapshot
    
    app = Application()
    app.id = i + 1
    
    service = Service()
    service.id = i + 1
    service.cpu_demand = random.randint(50, 200)
    service.memory_demand = random.randint(32, 128)
    
    # Task Weight (Cycles)
    w_base = max(1, args.avg_weight)
    service.weight = random.randint(w_base, w_base + 3) * 1e9
    
    # Data Size (MB)
    d_base = max(50, args.avg_data_size)
    service.data_size = random.randint(d_base, d_base + 200)
    
    service.deadline = args.deadline
    
    app.connect_to_service(service)
    user._connect_to_application(app, delay_sla=service.deadline)

# --- Step 9: Export ---
print(f"Exporting scenario to {output_dir}/{SCENARIO_FILENAME}.json ...")
ComponentManager.export_scenario(save_to_file=True, file_name=SCENARIO_FILENAME)
print("Done!")