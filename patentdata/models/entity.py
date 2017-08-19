# -*- coding: utf-8 -*-


class Entity:
    """ Abstract object for instantiating entities.

    Attributes:
        ref_num - int representing associated reference number (maybe a list?)
        parent (? - or get from navigating children)
        children
        limitations
        essential - T or F (optional = F)
        number - (default = 1, >1 = plurality)
        order - if in a set of children where it comes in the claim

    """
    def __init__(self, string_name, occurrences=[]):
        """ Initialise object. """
        self.name = string_name
        self.occurrences = occurrences
        self.children = list()
        self.limitations = list()
        self.ref_num = list()

    def __repr__(self):
        return (
            "<Entity - name: {n}; "
            "occurrences: {o}; "
            "children: {c}; "
            "limitations: {l}"
        ).format(
            n=self.name,
            o=self.occurrences,
            c=self.children,
            l=self.limitations
        )

    def add_occurrence(self, spacy_span):
        """ Add an occurrence in the form of a spaCy span"""
        self.occurrences.append(spacy_span)
        return self.occurrences

    @property
    def first_occurrence(self):
        """ Return starting index of first occurrence."""
        return min([o[0].i for o in self.occurrences])

    def add_child(self, child):
        """ Add a child entity.

        child: an object of the same class
        """
        # if string convert to Entity
        if isinstance(child, str):
            child = type(self)(child)
        assert isinstance(child, type(self))
        self.children.append(child)
        return self.children

    def remove_child(self, child):
        """ Remove a child entity.

        child: a child object to remove
        """
        self.children.remove(child)
        return self.children

    def add_limitation(self, limitation):
        """ Add a limitation.

        limitation: a Limitation object
        """
        # if isinstance(limitation, str):
        # limitation = Limitation(limitation)
        # assert isinstance(limitation, Limitation)
        self.limitations.append(limitation)
        return self.limitations

    def remove_limitation(self, limitation):
        """ Remove a limitation.

       limitation: a Limitation object
        """
        self.limitations.remove(limitation)
        return self.limitations

    def prettyprint(self, object_str_single, object_str_plural, tabs=0):
        """ Pretty print a representation of feature with
        children and limitations.

        object_str_single: string to call feature instantiation
        object_str_plural: string to call feature instantiation (plural)
        """
        tabtext = "\t"*tabs
        print(
            "{0}{1}: {2}\n".format(
                tabtext,
                object_str_single,
                self.__repr__()
            )
        )

        if self.limitations:
            tabs = tabs + 1
            tabtext = "\t"*tabs
            print("{0}Limitations:\n".format(tabtext))
            for i, limitation in enumerate(self.limitations):
                print("\t{0}{1} - {2}\n".format(
                    tabtext,
                    i,
                    limitation.__repr__()
                    )
                )

        if self.children:
            tabs = tabs + 1
            print("{0}Child {1}:\n".format(tabtext, object_str_plural))
            for i, child in enumerate(self.children):
                child.prettyprint(tabs=tabs)
