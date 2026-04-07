"""
run_local.py
============
Pass your 6 joint arrays directly and get the rep list of lists as output.

Usage
-----
1. Place base_model.pt in the same folder as this file.
2. Edit the INPUT SECTION below with your actual arrays.
3. Run:  python run_local.py

Output
------
A list of lists, each entry:
  [start_index, end_index, [array1, array2, array3, array4, array5, array6]]

where start/end are frame indices within the 480-frame window and
each array is the slice of that joint's data covering that rep.
"""

import numpy as np
import os
import inference   # inference.py must be in the same folder

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_model.pt")

# ═══════════════════════════════════════════════════════════════════════════════
#  INPUT SECTION — replace these with your actual joint arrays
#  Rules:
#    - Provide 1 array (other 5 filled with zeros) or all 6
#    - Each array can be any length; code pads/trims to 480 internally
# ═══════════════════════════════════════════════════════════════════════════════

arrays = [
    np.random.randn(480),   # Joint 1  ← replace with your data
    np.random.randn(480),   # Joint 2
    np.random.randn(480),   # Joint 3
    np.random.randn(480),   # Joint 4
    np.random.randn(480),   # Joint 5
    np.random.randn(480),   # Joint 6
]

# ═══════════════════════════════════════════════════════════════════════════════

result = inference.predict(arrays=arrays, model_path=MODEL_PATH, device=None)
reps   = result["reps"]

print(f"Total reps found: {len(reps)}\n")
print(reps)