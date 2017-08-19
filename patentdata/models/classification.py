# -*- coding: utf-8 -*-

import re

from patentdata.models.lib.utils import check_list


class Classification():
    """ Object to model IPC classification. """
    def __init__(
        self, section, first_class=None,
        subclass=None, maingroup=None, subgroup=None
    ):
        """ Initialise object and save classification portions. """
        self.section = section
        self.first_class = first_class
        self.subclass = subclass
        self.maingroup = maingroup
        self.subgroup = subgroup

    def __repr__(self):
        """ Print string representation of object. """
        return "<Classification {0}{1}{2} {3}/{4}>".format(
            self.section,
            self.first_class,
            self.subclass,
            self.maingroup,
            self.subgroup)

    def match(self, list_of_classes):
        """ Determines if current classification matches passed list of
        classifications. None = ignore for match. """
        # Convert to list if single classification is passed
        list_of_classes = check_list(list_of_classes)
        match = False
        for classification in list_of_classes:
            if self.section == classification.section:
                if (
                    self.first_class == classification.first_class
                    or not classification.first_class
                    or not self.first_class
                ):
                    if (
                        self.subclass == classification.subclass
                        or not classification.subclass
                        or not self.subclass
                    ):
                        if (
                            self.maingroup == classification.maingroup
                            or not classification.maingroup
                            or not self.maingroup
                        ):
                            if (
                                self.subgroup == classification.subgroup
                                or not classification.subgroup
                                or not self.subgroup
                            ):
                                match = True
        return match

    def as_string(self):
        """ Return a string representation. """
        return "C_{0}{1}{2}_{3}_{4}".format(
            self.section,
            self.first_class,
            self.subclass,
            self.maingroup,
            self.subgroup)

    def as_dict(self):
        """ Return a dictionary representation. """
        c_dict = dict()
        c_dict['section'] = self.section
        c_dict['first_class'] = self.first_class
        c_dict['subclass'] = self.subclass
        c_dict['maingroup'] = self.maingroup
        c_dict['subgroup'] = self.subgroup
        return c_dict

    @classmethod
    def process_classification(cls, class_string):
        """ Extract IPC classfication elements from a class_string."""
        ipc = r'[A-H][0-9][0-9][A-Z][0-9]{1,4}\/?[0-9]{1,6}'
        # Last bit can occur 1-3 times then we have \d+\\?\d+ -
        p = re.compile(ipc)
        classifications = [
            cls(
                match.group(0)[0],
                match.group(0)[1:3],
                match.group(0)[3],
                match.group(0)[4:].split('/')[0],
                match.group(0)[4:].split('/')[1]
            )
            for match in p.finditer(class_string)]
        return classifications
