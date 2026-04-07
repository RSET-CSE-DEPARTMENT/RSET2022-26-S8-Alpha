import random
from edge_sim_py import Application, Service

# Task generation intervals (seconds)
TASK_INTERVALS = {
    "telemetry": 1,   # 🟢 NEW: Constant background pinging
    "collision": 3,
    "vision": 5,
    "navigation": 10,
    "analytics": 30
}

# Real-world probability of a vehicle triggering this task at its interval
TASK_PROBABILITIES = {
    "telemetry": 0.90,  # 90% chance (almost always pinging)
    "collision": 0.40,  # 40% chance (event-driven)
    "vision": 0.30,     # 30% chance (periodic camera frames)
    "navigation": 0.20, # 20% chance (route recalculation)
    "analytics": 0.05   # 5% chance (heavy predictive maintenance)
}

class VehicularTaskGenerator:
    def __init__(self, mobility_manager):
        self.mobility = mobility_manager
        self.task_counter = 0

        # 📊 Per-window counters (for logs/dashboard)
        self.task_type_counts = {
            "telemetry": 0,
            "collision": 0,
            "vision": 0,
            "navigation": 0,
            "analytics": 0
        }

    # ----------------------------------------------------
    # 🚨 TASK TEMPLATES
    # ----------------------------------------------------
    def _create_telemetry_task(self, user):
        app = Application()
        app.id = f"telemetry_app_{self.task_counter}"

        service = Service()
        service.id = f"telemetry_service_{self.task_counter}"
        service.cpu_demand = random.randint(5, 15)       # Very light compute
        service.memory_demand = random.randint(8, 16)    # Tiny memory
        service.weight = random.randint(1, 2) * 1e8      # Very light weight (10^8)
        service.data_size = random.randint(1, 5)         # 1-5 MB
        service.deadline = random.uniform(0.5, 2.0)      # Strict deadline

        app.connect_to_service(service)
        user._connect_to_application(app, delay_sla=service.deadline)

    def _create_collision_task(self, user):
        app = Application()
        app.id = f"collision_app_{self.task_counter}"

        service = Service()
        service.id = f"collision_service_{self.task_counter}"
        service.cpu_demand = random.randint(10, 40)
        service.memory_demand = random.randint(16, 64)
        service.weight = random.randint(1, 3) * 1e9
        service.data_size = random.randint(5, 20)
        service.deadline = random.uniform(1, 3)

        app.connect_to_service(service)
        user._connect_to_application(app, delay_sla=service.deadline)

    def _create_vision_task(self, user):
        app = Application()
        app.id = f"vision_app_{self.task_counter}"

        service = Service()
        service.id = f"vision_service_{self.task_counter}"
        service.cpu_demand = random.randint(50, 150)
        service.memory_demand = random.randint(64, 256)
        service.weight = random.randint(3, 7) * 1e9
        service.data_size = random.randint(200, 600)
        service.deadline = random.uniform(3, 8)

        app.connect_to_service(service)
        user._connect_to_application(app, delay_sla=service.deadline)

    def _create_navigation_task(self, user):
        app = Application()
        app.id = f"nav_app_{self.task_counter}"

        service = Service()
        service.id = f"nav_service_{self.task_counter}"
        service.cpu_demand = random.randint(20, 80)
        service.memory_demand = random.randint(32, 128)
        service.weight = random.randint(2, 5) * 1e9
        service.data_size = random.randint(50, 150)
        service.deadline = random.uniform(5, 15)

        app.connect_to_service(service)
        user._connect_to_application(app, delay_sla=service.deadline)

    def _create_analytics_task(self, user):
        app = Application()
        app.id = f"analytics_app_{self.task_counter}"

        service = Service()
        service.id = f"analytics_service_{self.task_counter}"
        service.cpu_demand = random.randint(80, 200)
        service.memory_demand = random.randint(128, 512)
        service.weight = random.randint(5, 10) * 1e9
        service.data_size = random.randint(500, 1200)
        service.deadline = random.uniform(20, 60)

        app.connect_to_service(service)
        user._connect_to_application(app, delay_sla=service.deadline)

    # ----------------------------------------------------
    # 🚗 MAIN TASK GENERATION LOOP
    # ----------------------------------------------------
    def step(self, current_time):
        users = self.mobility.get_active_users()

        # ❌ Skip t=0 to avoid biased first window
        if current_time == 0:
            return 0

        if not users:
            return 0

        tasks_created = 0

        for task_type, interval in TASK_INTERVALS.items():

            if current_time % interval != 0:
                continue

            for user in users:
                
                # ⭐ Use specific probability for this task type
                prob = TASK_PROBABILITIES[task_type]
                if random.random() > prob:
                    continue

                self.task_counter += 1
                tasks_created += 1
                self.task_type_counts[task_type] += 1

                if task_type == "telemetry":
                    self._create_telemetry_task(user)
                elif task_type == "collision":
                    self._create_collision_task(user)
                elif task_type == "vision":
                    self._create_vision_task(user)
                elif task_type == "navigation":
                    self._create_navigation_task(user)
                elif task_type == "analytics":
                    self._create_analytics_task(user)

        # Optional: Print detailed breakdown for debugging
        # print(f"🧠 Tasks at t={current_time}s: Tel:{self.task_type_counts['telemetry']} Col:{self.task_type_counts['collision']} Vis:{self.task_type_counts['vision']} Nav:{self.task_type_counts['navigation']} Ana:{self.task_type_counts['analytics']}")

        return tasks_created

    # ----------------------------------------------------
    # 📊 Reset counters after scheduler window
    # ----------------------------------------------------
    def reset_window_counters(self):
        for k in self.task_type_counts:
            self.task_type_counts[k] = 0