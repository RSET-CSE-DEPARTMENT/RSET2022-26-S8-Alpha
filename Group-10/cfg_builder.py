import javalang
from cfgj import CFGNode


def build_cfg(statements):

    nodes = []
    prev_node = None

    for stmt in statements:

        node = CFGNode(stmt)
        nodes.append(node)

        if prev_node:
            prev_node.add_edge(node)

        prev_node = node

    return nodes