import ast

class LoopInvariantAnnotator(ast.NodeTransformer):
    def visit_While(self, node):
        self.generic_visit(node)
        return node

    def visit_For(self, node):
        self.generic_visit(node)
        return node
