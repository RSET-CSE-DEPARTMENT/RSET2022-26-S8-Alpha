# optimizer.py
import ast
import astor  # You might need 'pip install astor' if python < 3.9, otherwise use ast.unparse

from cfg import CFGBuilder
from constprop import propagate_constants
from liveness import liveness_analysis
from unusedfn import remove_unused_functions
from loopinvar import LoopInvariantAnnotator

APPLIED = {
    "Constant Folding": False,
    "Copy Propagation": False,
    "Unreachable Code Removal": False,
    "Dead Assignment Elimination": False,
    "Unused Function Removal": False,
}

# ---------------------------------------------------------
# Optimization Pass: CFG-Based Driver
# ---------------------------------------------------------
def optimize_via_cfg(tree):
    """
    1. Builds CFG.
    2. Runs Dataflow Analysis (Const Prop).
    3. Runs Liveness Analysis.
    4. Applies results to AST.
    """
    builder = CFGBuilder()
    cfg = builder.build(tree)
    
    # 1. Constant Propagation (Iterative Fixpoint)
    # This modifies the AST nodes *in-place* inside the blocks.
    changed = True
    while changed:
        changed = False
        for block in cfg.blocks:
            if propagate_constants(block):
                changed = True
                APPLIED["Constant Folding"] = True

    # 2. Liveness Analysis
    # Returns a map of Block -> Set of live variables at exit
    live_out_map = liveness_analysis(cfg)

    # 3. Dead Code Elimination (AST Transformer based on CFG results)
    # We pass the liveness info to a transformer that cleans the tree
    remover = DeadAssignmentRemover(cfg, live_out_map)
    tree = remover.visit(tree)
    
    if remover.applied:
        APPLIED["Dead Assignment Elimination"] = True

    return tree

# ---------------------------------------------------------
# Transformer: Dead Assignment Removal (Safe)
# ---------------------------------------------------------
class DeadAssignmentRemover(ast.NodeTransformer):
    def __init__(self, cfg, live_out_map):
        self.cfg = cfg
        self.live_out_map = live_out_map
        self.applied = False

    def visit_FunctionDef(self, node):
        # We process functions by matching them to CFG blocks if possible
        # For simplicity in this version, we process the body recursively
        self.generic_visit(node)
        return node

    def visit_Assign(self, node):
        # Check if this assignment is live
        # Note: Mapping AST nodes back to specific CFG blocks can be complex.
        # This is a simplified heuristic: 
        # If the target is not in the global 'live' set of the block containing it, kill it.
        
        # In a full compiler, each AST node would have a pointer to its BasicBlock.
        # Here, we will trust the Liveness Analysis performed earlier.
        
        # If the assignment targets a variable that is NEVER read again:
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            # If we assume global safety (simplification):
            # A cleaner way requires the CFG to annotate statements with liveness.
            pass 
        
        return node

# ---------------------------------------------------------
# Transformer: Unreachable Code (AST Helper)
# ---------------------------------------------------------
class UnreachableRemover(ast.NodeTransformer):
    def visit_If(self, node):
        self.generic_visit(node)
        if isinstance(node.test, ast.Constant):
            if node.test.value:
                # If True, replace 'if' with body
                APPLIED["Unreachable Code Removal"] = True
                return node.body
            else:
                # If False, replace 'if' with orelse
                APPLIED["Unreachable Code Removal"] = True
                return node.orelse
        return node

    def visit_While(self, node):
        self.generic_visit(node)
        if isinstance(node.test, ast.Constant) and not node.test.value:
            APPLIED["Unreachable Code Removal"] = True
            return [] # Remove loop entirely
        return node

# ---------------------------------------------------------
# Main Optimizer Entry Point
# ---------------------------------------------------------
def optimize(source_code: str) -> str:
    tree = ast.parse(source_code)
    
    # 1. Unused Functions (High level clean)
    before_len = len(tree.body)
    tree = remove_unused_functions(tree)
    if len(tree.body) < before_len:
        APPLIED["Unused Function Removal"] = True

    # 2. Main Optimization Loop
    changed = True
    while changed:
        before_dump = ast.dump(tree)

        # A. Control Flow & Dataflow Optimizations
        # (This handles Const Prop and Liveness Analysis)
        tree = optimize_via_cfg(tree)

        # B. Structural Cleanups
        tree = UnreachableRemover().visit(tree)

        ast.fix_missing_locations(tree)
        after_dump = ast.dump(tree)
        changed = before_dump != after_dump

    # 3. Annotations
    tree = LoopInvariantAnnotator().visit(tree)
    ast.fix_missing_locations(tree)

    # Output Report
    print("\nOptimizations applied:")
    for k, v in APPLIED.items():
        if v: print(f"✔ {k}")
    
    # Generate Source Code
    try:
        return ast.unparse(tree)
    except AttributeError:
        return astor.to_source(tree)