import ast

class UnusedFunctionRemover(ast.NodeTransformer):
    def __init__(self):
        self.defined = set()
        self.called = set()

    def visit_FunctionDef(self, node):
        self.defined.add(node.name)
        self.generic_visit(node)
        return node

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.called.add(node.func.id)
        self.generic_visit(node)
        return node

def remove_unused_functions(tree):
    remover = UnusedFunctionRemover()
    remover.visit(tree)

    keep = {"main"}
    unused = remover.defined - remover.called - keep

    new_body = []
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name in unused:
            continue
        new_body.append(stmt)

    tree.body = new_body
    return tree
