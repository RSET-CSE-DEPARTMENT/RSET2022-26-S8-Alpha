import os
import pandas as pd

BASE_DIR = "vehicular_outputs/vehicular_scenario"
ALGORITHMS = ["SHybridQIGA", "MOHEFT"]

print("\n====================================================")
print("🚀 VEHICULAR FOG ORCHESTRATION — RESULT ANALYSIS")
print("====================================================\n")

# ------------------------------------------------------------
# Load all runs of one algorithm
# ------------------------------------------------------------
def load_all_runs(algo):
    algo_dir = os.path.join(BASE_DIR, algo)

    if not os.path.exists(algo_dir):
        print(f"❌ No results found for {algo}")
        return None

    runs = [d for d in os.listdir(algo_dir) if d.startswith("run_")]

    dfs = []
    for run in runs:
        file = os.path.join(algo_dir, run, "runtime_metrics.csv")
        if os.path.exists(file):
            df = pd.read_csv(file)
            dfs.append(df)

    if not dfs:
        return None

    return pd.concat(dfs)


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------
data = {}
for algo in ALGORITHMS:
    df = load_all_runs(algo)
    if df is not None:
        data[algo] = df

if not data:
    print("❌ No runtime CSV files found!")
    exit()

# ------------------------------------------------------------
# Compute averages
# ------------------------------------------------------------
summary = []

for algo, df in data.items():
    summary.append({
        "Algorithm": algo,
        "Avg Latency (s)": df["latency"].mean(),
        "Avg Energy (J)": df["energy"].mean(),
        "Avg Cost ($)": df["cost"].mean(),
        "Avg Missed Deadlines": df["missed_deadlines"].mean()
    })

summary_df = pd.DataFrame(summary)

# Weighted score (same as paper)
summary_df["Weighted Score"] = (
    summary_df["Avg Energy (J)"] * 0.2 +
    summary_df["Avg Latency (s)"] * 0.7 +
    summary_df["Avg Cost ($)"] * 0.1
)

summary_df = summary_df.sort_values("Weighted Score")

# ------------------------------------------------------------
# Print comparison table
# ------------------------------------------------------------
print("📊 FINAL COMPARISON TABLE\n")
print(summary_df.to_string(index=False))

# ------------------------------------------------------------
# Winner announcement
# ------------------------------------------------------------
winner = summary_df.iloc[0]["Algorithm"]

print("\n🏆 BEST ALGORITHM:", winner)

print("\n====================================================")
print("Analysis Complete")
print("====================================================")
