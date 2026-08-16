class KnowledgeGraph:


    def __init__(self):

        self.nodes = {}

        self.relationships = []



    def add_node(
        self,
        name,
        node_type="concept",
        data=None,
    ):

        self.nodes[name] = {
            "name": name,
            "type": node_type,
            "data": data or {},
        }

        return self.nodes[name]



    def connect(
        self,
        source,
        relation,
        target,
    ):

        edge = {
            "source": source,
            "relation": relation,
            "target": target,
        }


        self.relationships.append(
            edge
        )

        return edge



    def get_connections(
        self,
        node,
    ):

        results = []


        for edge in self.relationships:

            if edge["source"] == node:
                results.append(edge)

            if edge["target"] == node:
                results.append(edge)


        return results



    def search(
        self,
        query,
    ):

        query = str(query).lower()

        results = []


        for name, node in self.nodes.items():

            if query in name.lower():

                results.append(node)


        return results



    def graph_state(self):

        return {
            "nodes": self.nodes,
            "relationships": self.relationships,
        }