# -*- coding: utf-8 -*-
from collections import OrderedDict
from graphviz import Digraph
import mumpy as np

class Node(object):
    """ Node in a graph. """

    def __init__(self, label, root_token=None):
        """ Initialise a node."""
        self.label = label
        self.root_token = root_token
        self.tokens = [root_token]

    def __repr__(self):
        return self.label


class Graph(object):
    """ Based on object here -
    https://www.python-course.eu/graphs_python.php"""

    def __init__(self, spacy_token=None):
        """ initializes a graph object
            If no dictionary or None is given,
            an empty dictionary will be used
        """
        self.__graph_dict = OrderedDict()
        if spacy_token:
            self.build_graph(spacy_token)

    @property
    def nodes(self):
        """ returns the nodes of a graph """
        return list(self.__graph_dict.keys())

    @property
    def edges(self):
        """ returns the edges of a graph """
        return self.__generate_edges()

    @property
    def edge_indices(self):
        """ returns edges in terms of indices in nodes"""
        return [
            (self.nodes.index(node1), self.nodes.index(node2))
            for node1, node2 in self.edges
        ]

    @property
    def node_labels(self):
        """ Return all node labels."""
        return [n.label for n in self.nodes]

    @property
    def adj_mat(self):
        """ Return adjacency matrix as a numpy array.
        parent>child connections are indicated with +1,
        child>parent with -1
        """
        n = len(self.nodes)
        A = np.zeros((n,n))
        new_edges = edges_to_indices(self.edges, self.nodes)
        for i, j in new_edges:
            A[i, j] = 1
            A[j, i] = -1
        return A

    def add_node(self, node_label, token=None):
        """ If the node "node" is not in
            self.__graph_dict, a key "node" with an empty
            list as a value is added to the dictionary.
            Otherwise nothing has to be done.
        """
        if node_label not in self.node_labels:
            # Create a new node from the label
            node = Node(node_label, token)
            self.__graph_dict[node] = []
            return node
        else:
            for node in self.nodes:
                if node_label == node.label:
                    return node

    def add_edge(self, edge):
        """ assumes that edge is of type set, tuple or list;
            between two nodes can be multiple edges!
        """
        (node1, node2) = tuple(edge)
        if not isinstance(node1, Node):
            # Check for prexisting
            node1 = self.add_node(node1)
        if not isinstance(node2, Node):
            # Check for prexisting
            node2 = self.add_node(node2)
        if node1 in self.__graph_dict:
            self.__graph_dict[node1].append(node2)
        else:
            self.__graph_dict[node1] = [node2]

    def __generate_edges(self):
        """ A static method generating the edges of the
            graph "graph". Edges are represented as sets
            with one (a loop back to the node) or two
            node
        """
        edges = []
        for node in self.__graph_dict:
            for neighbour in self.__graph_dict[node]:
                if (neighbour, node) not in edges:
                    edges.append((node, neighbour))
        return edges

    def __str__(self):
        res = "nodes: "
        for k in self.__graph_dict:
            res += str(k) + " "
        res += "\nedges: "
        for edge in self.__generate_edges():
            res += str(edge) + " "
        return res

    def merge_nodes(self, parent_node, child_node):
        """Merge child node into parent node"""
        # Merge labels and tokens of child into parent
        parent_node.tokens = parent_node.tokens + child_node.tokens
        # Sort parent_node tokens
        parent_node.tokens.sort(key=lambda token: token.i)
        parent_node.label = " ".join([
            "{0}_{1}_{2}_{3}".format(
                token.text, token.tag_, token.dep_, token.i
                )
            for token in parent_node.tokens
            ])
        # Reconnect any dangling grandchildren
        grandchildren = self._Graph__graph_dict[child_node]
        if grandchildren:
            for grandchild in grandchildren:
                self.add_edge((parent_node, grandchild))
        return parent_node

    def remove_node(self, node):
        """ Delete a node. """
        self.__graph_dict.pop(node, None)
        # Also remove from all entries of graph_dict
        for existing_node, entries in self.__graph_dict.items():
            if node in entries:
                self.__graph_dict[existing_node].remove(node)

    def remove_edge(self, edge):
        pass

    def get_graphviz(self):
        """ Visualise via Graphviz."""
        gv = Digraph()
        for node in self.nodes:
            gv.node(node.label)
        for node1, node2 in self.edges:
            gv.edge(node1.label, node2.label)
        return gv

    def get_rootgraph(self):
        """ Return a graph with just root tokens."""
        gv = Digraph()
        for node in self.nodes:
            gv.node(
                "{0}_{1}".format(node.root_token.text, node.root_token.i)
            )
        for node1, node2 in self.edges:
            gv.edge(
                "{0}_{1}".format(node1.root_token.text, node1.root_token.i),
                "{0}_{1}".format(node2.root_token.text, node2.root_token.i)
            )
        return gv

    def build_graph(self, token):
        """ Print a graph ."""
        # Add node to graph
        node_name = "{0}_{1}_{2}_{3}".format(
            token.text, token.tag_, token.dep_, token.i
            )
        self.add_node(node_name, token)
        for child in token.children:
            child_name = self.build_graph(child)
            self.add_edge((node_name, child_name))
        return node_name

    def flatten_graph(self):
        """ Merge nodes with no children into parent node."""
        # Does this need to run recursively?
        nodes_to_pop = []
        for node in self.nodes:
            # Get nodes connected to current node
            children = self.__graph_dict[node]
            for child in children:
                # If connected node has no children
                if not self.__graph_dict[child]:
                    self.merge_nodes(node, child)
                    nodes_to_pop.append(child)
        for ntp in nodes_to_pop:
            self.remove_node(ntp)

    def merge_single_children(self):
        """ Merge nodes with single children."""

        nodes_to_pop = []
        nodes_to_merge = []
        # Does this need to run recursively?
        for node in self.nodes:
            # Get nodes connected to current node
            children = self._Graph__graph_dict[node]
            if len(children) == 1:
                child = children[0]
                nodes_to_merge.append((node, child))
                nodes_to_pop.append(child)

        # Merge nodes
        nodes_to_merge = list(reversed(nodes_to_merge))
        while nodes_to_merge:
            parent_node, child_node = nodes_to_merge.pop()
            updated_parent_node = self.merge_nodes(parent_node, child_node)
            nodes_to_merge = [
                (updated_parent_node, c) if p == child_node
                else (p, c)
                for p, c in nodes_to_merge
            ]

        # Remove merged nodes
        for ntp in nodes_to_pop:
            self.remove_node(ntp)

        return self
