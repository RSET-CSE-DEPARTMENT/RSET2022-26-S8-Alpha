import math
from .sumo_interface import SUMOInterface

# ⭐ IMPORTANT — convert toy dataset grid → real world meters
INFRASTRUCTURE_SCALE = 500   # 1 grid unit = 500 meters

class MobilityManager:
    def __init__(self, data, use_gui=False):

        self.data = data
        self.base_stations = list(data['BaseStation'].all())

        # =====================================================
        # ⭐ CRITICAL FIX: SCALE INFRASTRUCTURE TO METERS
        # =====================================================
        print("🗺️ Scaling BaseStation coordinates to real-world meters...")
        max_bs_x = 0
        max_bs_y = 0
        
        for bs in self.base_stations:
            x, y = bs.coordinates
            bs.coordinates = (x * INFRASTRUCTURE_SCALE, y * INFRASTRUCTURE_SCALE)
            
            # Find the edges of our infrastructure grid
            max_bs_x = max(max_bs_x, bs.coordinates[0])
            max_bs_y = max(max_bs_y, bs.coordinates[1])

        # 🚗 Start SUMO and pass the infrastructure boundaries
        self.sumo = SUMOInterface(use_gui=use_gui, bs_bounds=(max_bs_x, max_bs_y))
        self.sumo.start()

        # spawn first vehicles
        self.sumo.step()
        self.sumo.update_vehicle_mapping()
        self.sumo.update_user_positions()
    # ----------------------------------------------------
    # Distance helper (meters now)
    # ----------------------------------------------------
    def _distance(self, p1, p2):
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    # ----------------------------------------------------
    # Find nearest base station
    # ----------------------------------------------------
    def _find_nearest_bs(self, user):
        min_dist = float('inf')
        nearest_bs = None

        for bs in self.base_stations:
            d = self._distance(user.coordinates, bs.coordinates)
            if d < min_dist:
                min_dist = d
                nearest_bs = bs

        return nearest_bs

    # ----------------------------------------------------
    # Perform base station handover
    # ----------------------------------------------------
    def _handover(self, user, new_bs):
        old_bs = getattr(user, "base_station", None)

        if old_bs and user in old_bs.users:
            old_bs.users.remove(user)

        user.base_station = new_bs
        new_bs.users.append(user)

        if old_bs:
            print(f"📡 User {user.id} handover: BS{old_bs.id} → BS{new_bs.id}")
        else:
            print(f"📡 User {user.id} connected to BS{new_bs.id}")

    # ----------------------------------------------------
    # 🚗 MAIN MOBILITY STEP
    # ----------------------------------------------------
    def step(self):
        # 1️⃣ Advance SUMO simulation
        self.sumo.step()

        # 2️⃣ Handle vehicle enter/leave events
        self.sumo.update_vehicle_mapping()

        # 3️⃣ Update vehicle positions (already in meters!)
        self.sumo.update_user_positions()

        # 4️⃣ Perform base-station handovers
        for user in self.sumo.get_active_users():
            nearest_bs = self._find_nearest_bs(user)

            if nearest_bs and getattr(user, "base_station", None) != nearest_bs:
                current_bs = getattr(user, "base_station", None)

                if current_bs:
                    current_dist = self._distance(user.coordinates, current_bs.coordinates)
                    new_dist = self._distance(user.coordinates, nearest_bs.coordinates)

                    # hysteresis to avoid ping-pong handover
                    if new_dist < current_dist * 0.8:
                        self._handover(user, nearest_bs)
                else:
                    self._handover(user, nearest_bs)

    # ----------------------------------------------------
    # expose dynamic users to scheduler
    # ----------------------------------------------------
    def get_active_users(self):
        return self.sumo.get_active_users()
