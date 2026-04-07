class CFGNode:

    def __init__(self, statement):

        self.statement = statement
        self.next = []
        self.prev = []

    def add_edge(self, node):

        self.next.append(node)
        node.prev.append(self)