import javalang
def constant_propagation(cfg_nodes):

    constants = {}

    for node in cfg_nodes:

        stmt = node.statement

        if isinstance(stmt, javalang.tree.LocalVariableDeclaration):

            decl = stmt.declarators[0]
            name = decl.name
            init = decl.initializer

            if isinstance(init, javalang.tree.Literal):
                constants[name] = init.value

            if isinstance(init, javalang.tree.MemberReference):

                var = init.member

                if var in constants:
                    decl.initializer = javalang.tree.Literal(constants[var])

    return cfg_nodes
