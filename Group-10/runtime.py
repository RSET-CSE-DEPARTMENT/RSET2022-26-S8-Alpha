import ast

class SmartComplexityAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.current_score = 0
        self.max_score = 0
        self.func_name = None
        self.recursive_calls = 0
        self.has_recursion = False

    def visit_FunctionDef(self, node):
        self.func_name = node.name
        self.recursive_calls = 0
        self.has_recursion = False

        old_score = self.current_score
        self.current_score = 0

        self.generic_visit(node)

        if self.has_recursion:
            if self.recursive_calls > 1:
                self.max_score = max(self.max_score, 10)
            else:
                self.max_score = max(self.max_score, 1)

        self.current_score = old_score

    def visit_For(self, node):
        is_constant = False

        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
            if node.iter.func.id == 'range':
                if node.iter.args and isinstance(node.iter.args[0], ast.Constant):
                    is_constant = True

        if isinstance(node.iter, (ast.List, ast.Tuple)):
            is_constant = True

        if not is_constant:
            self.current_score += 1

        self.max_score = max(self.max_score, self.current_score)
        self.generic_visit(node)

        if not is_constant:
            self.current_score -= 1

    def visit_While(self, node):
        self.current_score += 1
        self.max_score = max(self.max_score, self.current_score)
        self.generic_visit(node)
        self.current_score -= 1

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == self.func_name:
            self.has_recursion = True
            self.recursive_calls += 1

        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'sort':
                self.max_score = max(self.max_score, self.current_score + 1)

        self.generic_visit(node)

def get_complexity_label(score):
    if score == 0: return "O(1) - Constant Time"
    if score == 1: return "O(N) - Linear Time"
    if score == 2: return "O(N²) - Quadratic Time"
    if score == 3: return "O(N³) - Cubic Time"
    if score >= 10: return "O(2^N) - Exponential Time"
    return f"O(N^{score}) - Polynomial Time"

def estimate_time_complexity(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return "Syntax Error"

    analyzer = SmartComplexityAnalyzer()
    analyzer.visit(tree)
    return get_complexity_label(analyzer.max_score)

# 🔥 NEW CLEAN FUNCTION
def analyze_code(code: str):
    return estimate_time_complexity(code)
