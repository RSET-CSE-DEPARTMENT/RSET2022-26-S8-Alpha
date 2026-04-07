import javalang
from cfg_builder import build_cfg


# ----------------------------------------
# Recursive Expression Evaluation
# ----------------------------------------
def evaluate_expression(expr, constants, aliases):

    if expr is None:
        return None

    if isinstance(expr, javalang.tree.MemberReference):
        name = expr.member
        while name in aliases:
            name = aliases[name]
        return constants.get(name)

    if isinstance(expr, javalang.tree.Literal):
        return expr.value

    if isinstance(expr, javalang.tree.BinaryOperation):

        left = evaluate_expression(expr.operandl, constants, aliases)
        right = evaluate_expression(expr.operandr, constants, aliases)

        if left is not None and right is not None:

            try:
                if expr.operator == "+":
                    return str(int(left) + int(right))
                elif expr.operator == "-":
                    return str(int(left) - int(right))
                elif expr.operator == "*":
                    return str(int(left) * int(right))
                elif expr.operator == "/":
                    return str(int(left) // int(right))
            except:
                return None

    return None


# ----------------------------------------
# Block Optimizer (CFG Based)
# ----------------------------------------
def optimize_block(cfg_nodes, constants, aliases):

    lines = []

    for cfg_node in cfg_nodes:

        stmt = cfg_node.statement

        # -------------------------
        # IF Statement
        # -------------------------
        if isinstance(stmt, javalang.tree.IfStatement):

            if isinstance(stmt.condition, javalang.tree.Literal):

                if stmt.condition.value == "false":
                    continue

                if stmt.condition.value == "true":

                    if hasattr(stmt.then_statement, "statements"):

                        inner_cfg = build_cfg(stmt.then_statement.statements)

                        lines.extend(
                            optimize_block(
                                inner_cfg,
                                constants.copy(),
                                aliases.copy()
                            )
                        )

                    continue

        # -------------------------
        # Variable Declaration
        # -------------------------
        if isinstance(stmt, javalang.tree.LocalVariableDeclaration):

            var_type = stmt.type.name

            for decl in stmt.declarators:

                name = decl.name
                init = decl.initializer

                value = evaluate_expression(init, constants, aliases)

                if value is not None:

                    constants[name] = value
                    lines.append(f"{var_type} {name} = {value};")

                else:

                    if isinstance(init, javalang.tree.MemberReference):

                        src = init.member

                        while src in aliases:
                            src = aliases[src]

                        if src in constants:

                            constants[name] = constants[src]
                            lines.append(f"{var_type} {name} = {constants[src]};")

                        else:

                            aliases[name] = src
                            lines.append(f"{var_type} {name} = {src};")

                    else:
                        lines.append(f"{var_type} {name};")

            continue

        # -------------------------
        # Assignment / Print
        # -------------------------
        if isinstance(stmt, javalang.tree.StatementExpression):

            expr = stmt.expression

            # Assignment
            if isinstance(expr, javalang.tree.Assignment):

                lhs = expr.expressionl.member
                rhs = expr.value

                value = evaluate_expression(rhs, constants, aliases)

                if value is not None:

                    constants[lhs] = value
                    lines.append(f"{lhs} = {value};")

                else:
                    lines.append(f"{lhs} = {rhs};")

                continue

            # Print
            if isinstance(expr, javalang.tree.MethodInvocation):

                if expr.member == "println":

                    arg = expr.arguments[0]

                    if isinstance(arg, javalang.tree.MemberReference):
                        lines.append(f"System.out.println({arg.member});")

                    elif isinstance(arg, javalang.tree.Literal):
                        lines.append(f"System.out.println({arg.value});")

                    else:
                        lines.append("System.out.println(...);")

                continue

    return lines


# ----------------------------------------
# Dead Assignment Elimination
# ----------------------------------------
def remove_dead_assignments(lines):

    live = set()
    new_lines = []

    for line in lines:

        if "println(" in line:

            var = line.split("(")[1].split(")")[0]

            if var.isidentifier():
                live.add(var)

    for line in reversed(lines):

        if "=" in line and "int" in line:

            var = line.split("=")[0].replace("int", "").strip()

            if var not in live:
                continue

            live.discard(var)

        new_lines.append(line)

    return list(reversed(new_lines))


# ----------------------------------------
# Main Entry
# ----------------------------------------
def optimize_java(code: str):

    try:
        tree = javalang.parse.parse(code)

    except:

        wrapped = f"""
public class Temp {{
    public static void main(String[] args) {{
{code}
    }}
}}
"""

        try:
            tree = javalang.parse.parse(wrapped)
        except Exception as e:
            return f"// JAVA PARSE ERROR: {str(e)}"

    class_name = "OptimizedProgram"

    for _, node in tree:

        if isinstance(node, javalang.tree.ClassDeclaration):
            class_name = node.name

        if isinstance(node, javalang.tree.MethodDeclaration) and node.name == "main":

            constants = {}
            aliases = {}

            cfg_nodes = build_cfg(node.body)

            lines = optimize_block(cfg_nodes, constants, aliases)

            lines = remove_dead_assignments(lines)

            optimized_code = "\n".join(lines)

            return f"""
public class {class_name} {{
    public static void main(String[] args) {{

{optimized_code}

    }}
}}
"""

    return ""
