# liveness.py
# Liveness analysis on CFG (minimal)

import ast


def compute_use_def(block):
    use = set()
    defs = set()

    for stmt in block.statements:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load) and node.id not in defs:
                    use.add(node.id)
                elif isinstance(node.ctx, ast.Store):
                    defs.add(node.id)

    return use, defs


def liveness_analysis(cfg):
    use = {}
    defs = {}
    live_out = {}

    # initialize
    for block in cfg.blocks:
        use[block], defs[block] = compute_use_def(block)
        live_out[block] = set()

    changed = True
    while changed:
        changed = False

        for block in cfg.blocks:
            new_live_out = set()

            for succ in block.next_blocks:
                new_live_out |= (use[succ] | (live_out[succ] - defs[succ]))

            if new_live_out != live_out[block]:
                live_out[block] = new_live_out
                changed = True

    return live_out
def statement_liveness(block, live_out):
    live = set(live_out)
    result = []

    for stmt in reversed(block.statements):
        result.append((stmt, set(live)))

        for node in ast.walk(stmt):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    live.add(node.id)
                elif isinstance(node.ctx, ast.Store):
                    live.discard(node.id)

    result.reverse()
    return result
