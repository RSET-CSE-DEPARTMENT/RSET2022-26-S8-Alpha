import javalang
def dead_code_elimination(cfg_nodes):

    used = set()

    for node in cfg_nodes:

        stmt = node.statement

        if isinstance(stmt, javalang.tree.StatementExpression):

            expr = stmt.expression

            if isinstance(expr, javalang.tree.MethodInvocation):

                if expr.member == "println":

                    arg = expr.arguments[0]

                    if isinstance(arg, javalang.tree.MemberReference):
                        used.add(arg.member)

    new_nodes = []

    for node in cfg_nodes:

        stmt = node.statement

        if isinstance(stmt, javalang.tree.LocalVariableDeclaration):

            decl = stmt.declarators[0]

            if decl.name not in used:
                continue

        new_nodes.append(node)

    return new_nodes
