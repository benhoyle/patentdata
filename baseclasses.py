# -*- coding: utf-8 -*-
# Import abstract class functions
from abc import ABCMeta, abstractmethod


class BasePatentDataSource(metaclass=ABCMeta):
    """ Abstract class for patent data sources. """

    @abstractmethod
    def get_patentdoc(self, publication_number):
        """ Return a Patent Doc object corresponding
        to a publication number. """
        pass

    @abstractmethod
    def patentdoc_generator(self, publication_numbers=None, sample_size=None):
        """ Return a generator that provides Patent Doc objects.
        publication_numbers is a list or iterator that provides a
        limiting group of publication numbers.
        sample_size limits results to a random sample of size sample_size"""
        pass
