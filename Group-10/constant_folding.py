import javalang
def constant_folding(cfg_nodes):

    for node in cfg_nodes:

        stmt = node.statement

        if isinstance(stmt, javalang.tree.LocalVariableDeclaration):

            decl = stmt.declarators[0]
            init = decl.initializer

            if isinstance(init, javalang.tree.BinaryOperation):

                if (
                    isinstance(init.operandl, javalang.tree.Literal)
                    and isinstance(init.operandr, javalang.tree.Literal)
                ):

                    left = int(init.operandl.value)
                    right = int(init.operandr.value)

                    if init.operator == "+":
                        result = left + right
                    elif init.operator == "-":
                        result = left - right
                    elif init.operator == "*":
                        result = left * right
                    elif init.operator == "/":
                        result = left // right
                    else:
                        continue

                    # replace expression with literal
                    decl.initializer = javalang.tree.Literal(str(result))

    return cfg_nodes
