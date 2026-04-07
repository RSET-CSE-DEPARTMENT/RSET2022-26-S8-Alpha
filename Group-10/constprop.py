# constprop.py
# Intra-block constant propagation (loop-safe, conservative)

import ast


def propagate_constants(block):
    constants = {}
    new_statements = []
    changed = False

    class Replacer(ast.NodeTransformer):
        def visit_Call(self, node):
            # Do not replace inside function calls aggressively
            return self.generic_visit(node)

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load) and node.id in constants:
                return ast.copy_location(
                    ast.Constant(constants[node.id]), node
                )
            return node

    for stmt in block.statements:

        # 🚧 LOOP BARRIER
        # If we encounter a loop, treat it as a propagation barrier.
        # Do NOT propagate into its condition or body.
        if isinstance(stmt, (ast.While, ast.For)):
            constants.clear()
            new_statements.append(stmt)
            constants.clear()   # also clear after loop (state unknown)
            continue

        # Apply constant replacement only for non-loop statements
        replacer = Replacer()
        new_stmt = replacer.visit(stmt)

        if new_stmt is not stmt:
            changed = True

        # Update constant table
        if isinstance(new_stmt, ast.Assign) and len(new_stmt.targets) == 1:
            target = new_stmt.targets[0]
            value = new_stmt.value

            if isinstance(target, ast.Name):
                # If assigned constant → track
                if isinstance(value, ast.Constant):
                    constants[target.id] = value.value
                else:
                    # Any non-constant assignment kills constant info
                    constants.pop(target.id, None)

        new_statements.append(new_stmt)

    block.statements[:] = new_statements
    return changed
