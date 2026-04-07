import ast
from loopinvar import LoopInvariantAnnotator
from unusedfn import remove_unused_functions

APPLIED = {
    "Constant Folding": False,
    "Copy Propagation": False,
    "Unreachable Code Removal": False,
    "Dead Assignment Elimination": False,
    "Unused Function Removal": False,
}

# ---------------------------
# Constant Folding
# ---------------------------
class ConstantFolder(ast.NodeTransformer):
    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            try:
                APPLIED["Constant Folding"] = True
                return ast.Constant(
                    value=eval(compile(ast.Expression(node), "", "eval"))
                )
            except Exception:
                pass
        return node

# ---------------------------
# Unreachable Code Removal
# ---------------------------
class UnreachableRemover(ast.NodeTransformer):
    def visit_If(self, node):
        self.generic_visit(node)
        if isinstance(node.test, ast.Constant):
            APPLIED["Unreachable Code Removal"] = True
            return node.body if node.test.value else node.orelse
        return node

    def visit_While(self, node):
        self.generic_visit(node)
        if isinstance(node.test, ast.Constant) and node.test.value is False:
            APPLIED["Unreachable Code Removal"] = True
            return []
        return node

# ---------------------------
# Copy Propagation
# ---------------------------
def copy_propagation(statements):
    aliases = {}
    new_body = []

    for stmt in statements:
        class Replacer(ast.NodeTransformer):
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Load) and node.id in aliases:
                    APPLIED["Copy Propagation"] = True
                    return ast.copy_location(
                        ast.Name(id=aliases[node.id], ctx=node.ctx), node
                    )
                return node

        stmt = Replacer().visit(stmt)

        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            t = stmt.targets[0]
            v = stmt.value
            if isinstance(t, ast.Name) and isinstance(v, ast.Name):
                aliases[t.id] = v.id
            elif isinstance(t, ast.Name):
                aliases.pop(t.id, None)

        new_body.append(stmt)

    return new_body
# ---------------------------
# Constant Propagation
# ---------------------------
def constant_propagation(statements):
    constants = {}
    new_body = []

    for stmt in statements:
        class Replacer(ast.NodeTransformer):
            def __init__(self):
                self.in_return = False

            def visit_Return(self, node):
                old = self.in_return
                self.in_return = True
                self.generic_visit(node)
                self.in_return = old
                return node

            def visit_Name(self, node):
                if (
                    isinstance(node.ctx, ast.Load)
                    and node.id in constants
                    and not self.in_return   # 🔥 do NOT replace inside return
                ):
                    return ast.copy_location(
                        ast.Constant(constants[node.id]), node
                    )
                return node

        replacer = Replacer()
        stmt = replacer.visit(stmt)

        # update constant table
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            t = stmt.targets[0]
            v = stmt.value
            if isinstance(t, ast.Name) and isinstance(v, ast.Constant):
                constants[t.id] = v.value
            elif isinstance(t, ast.Name):
                constants.pop(t.id, None)

        new_body.append(stmt)

    return new_body



# ---------------------------
# Dead Assignment Elimination
# ---------------------------
def remove_dead_assignments(statements):
    live = set()
    new_body = []

    for stmt in reversed(statements):
        remove = False

        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name) and target.id not in live:
                APPLIED["Dead Assignment Elimination"] = True
                remove = True

        if not remove:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Load):
                        live.add(node.id)
                    elif isinstance(node.ctx, ast.Store):
                        live.discard(node.id)
            new_body.append(stmt)

    return list(reversed(new_body))

# ---------------------------
# Optimize a block (KEY ADDITION)
# ---------------------------
def remove_unreachable_after_terminator(statements):
    new_body = []
    for stmt in statements:
        new_body.append(stmt)
        if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
            APPLIED["Unreachable Code Removal"] = True
            break
    return new_body

def optimize_block(statements):
    changed = True
    while changed:
        before = ast.dump(ast.Module(body=statements, type_ignores=[]))

        statements = constant_propagation(statements)
        statements = copy_propagation(statements)
        statements = remove_dead_assignments(statements)

        # 🔥 ADD THIS LINE (THE ACTUAL FIX)
        statements = remove_unreachable_after_terminator(statements)

        after = ast.dump(ast.Module(body=statements, type_ignores=[]))
        changed = before != after

    return statements



# ---------------------------
# Main Optimization Pipeline
# ---------------------------
def optimize(source_code: str) -> str:
    tree = ast.parse(source_code)

    changed = True
    while changed:
        before = ast.dump(tree)

        tree = ConstantFolder().visit(tree)
        tree = UnreachableRemover().visit(tree)

        # optimize module-level statements
        tree.body = optimize_block(tree.body)

        # 🔥 optimize INSIDE FUNCTIONS (THIS FIXES YOUR ISSUE)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                node.body = optimize_block(node.body)

        ast.fix_missing_locations(tree)
        after = ast.dump(tree)
        changed = before != after

    # 🔥 Only remove unused functions if there is more than one
    if len(tree.body) > 1:
        before = len(tree.body)
        tree = remove_unused_functions(tree)
        if len(tree.body) < before:
            APPLIED["Unused Function Removal"] = True


    tree = LoopInvariantAnnotator().visit(tree)

    ast.fix_missing_locations(tree)

    print("\nOptimizations applied:")
    for k, v in APPLIED.items():
        if v:
            print("✔", k)

    if not tree.body:
        print("WARNING: Optimizer collapsed entire module. Returning original.")
        return source_code

    return ast.unparse(tree)

