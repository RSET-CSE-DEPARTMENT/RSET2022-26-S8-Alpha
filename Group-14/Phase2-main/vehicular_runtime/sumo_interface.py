from edge_sim_py import User
import traci
import os
import time

class SUMOInterface:
    def __init__(self, sumo_config="sumo_sim/simulation.sumocfg", use_gui=False, bs_bounds=(1000, 1000)):
        self.sumo_config = sumo_config
        self.started = False
        self.use_gui = use_gui
        self.bs_max_x, self.bs_max_y = bs_bounds  # Store the infrastructure bounds

        # 🚗 Vehicle → EdgeSimPy User mapping
        self.vehicle_to_user = {}

    # ----------------------------------------------------
    # START / STOP SUMO
    # ----------------------------------------------------
    def start(self):
        if self.started:
            return  # prevent double start

        if "SUMO_HOME" not in os.environ:
            raise EnvironmentError("Please set SUMO_HOME environment variable")

        sumoBinary = "sumo-gui" if self.use_gui else "sumo"
        traci.start([sumoBinary, "-c", self.sumo_config])

        self.started = True
        print("🚦 SUMO started")

    def step(self):
        if not self.started:
            return

        traci.simulationStep()

        # ⭐ GUI animation delay (fix frozen GUI)
        if self.use_gui:
            time.sleep(0.03)

    def close(self):
        if self.started:
            traci.close()
            self.started = False
            print("🛑 SUMO closed")

    # ----------------------------------------------------
    # 🔵 CREATE USERS FROM VEHICLES
    # ----------------------------------------------------
    def spawn_users_from_vehicles(self):
        vehicles = traci.vehicle.getIDList()

        for veh_id in vehicles:
            if veh_id in self.vehicle_to_user:
                continue

            user = User()
            user.id = int(veh_id) if veh_id.isdigit() else abs(hash(veh_id)) % 1000000
            user.coordinates = (0, 0)
            user.applications = []

            self.vehicle_to_user[veh_id] = user
            print(f"👤 New Edge user created for vehicle {veh_id}")

    # ----------------------------------------------------
    # 🚗 SYNC VEHICLES ↔ USERS
    # ----------------------------------------------------
    def update_vehicle_mapping(self):
        active_vehicles = set(traci.vehicle.getIDList())

        # spawn new users
        self.spawn_users_from_vehicles()

        # remove vehicles that left
        to_remove = []
        for veh_id in list(self.vehicle_to_user.keys()):
            if veh_id not in active_vehicles:
                to_remove.append(veh_id)

        for veh_id in to_remove:
            del self.vehicle_to_user[veh_id]
            print(f"🚘 Vehicle left simulation: {veh_id}")

    # ----------------------------------------------------
    # 📍 UPDATE USER POSITIONS
    # ----------------------------------------------------
    def update_user_positions(self):
        for veh_id, user in list(self.vehicle_to_user.items()):
            try:
                # Get SUMO map boundary once
                if not hasattr(self, "sumo_boundary"):
                    (xmin, ymin), (xmax, ymax) = traci.simulation.getNetBoundary()
                    self.sumo_boundary = (xmin, ymin, xmax, ymax)

                xmin, ymin, xmax, ymax = self.sumo_boundary

                # Get vehicle position in SUMO world
                x, y = traci.vehicle.getPosition(veh_id)

                # Normalize to 0–1 range (percentage across the map)
                norm_x = (x - xmin) / (xmax - xmin)
                norm_y = (y - ymin) / (ymax - ymin)

                # ⭐ THE FIX: Map perfectly over the Base Station grid
                scaled_x = norm_x * self.bs_max_x
                scaled_y = norm_y * self.bs_max_y

                user.coordinates = (scaled_x, scaled_y)

            except Exception:
                # vehicle vanished mid-step
                if veh_id in self.vehicle_to_user:
                    del self.vehicle_to_user[veh_id]
                    print(f"🚘 Vehicle removed during step: {veh_id}")

    # ----------------------------------------------------
    # 👥 GET ACTIVE USERS (VERY IMPORTANT)
    # ----------------------------------------------------
    def get_active_users(self):
        return list(self.vehicle_to_user.values())

    # ----------------------------------------------------
    # ⚠️ LEGACY STATIC MAPPING (unused)
    # ----------------------------------------------------
    def map_vehicles_to_users(self, users):
        vehicles = traci.vehicle.getIDList()
        users = list(users)

        count = min(len(users), len(vehicles))
        for i in range(count):
            self.vehicle_to_user[vehicles[i]] = users[i]

        print(f"🔗 Mapped {count} SUMO vehicles to EdgeSimPy users (legacy)")
