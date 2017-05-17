# -*- coding: utf-8 -*-


from patentdata.models.basemodels import BaseTextSet
from patentdata.models.lib.utils_claimset import (
    check_set_claims, clean_data
)


class Claimset(BaseTextSet):
    """ Object to model a claim set. """

    # Map claims onto units
    def __getattr__(self, name):
        if name == "claims":
            return self.units

    def __init__(self, initial_input):
        """ Process initial input to clean data and check claims. """
        if check_set_claims(initial_input):
            self.units = initial_input
        else:
            self.units = clean_data(initial_input)

        self.count = len(self.units)

    def get_claim(self, number):
        """ Return claim having the passed number. """
        return super(Claimset, self).get_unit(number)

    def claim_tf_idf(self, number):
        """ Calculate term frequency - inverse document frequency statistic
        for claim 'number' when compared to whole claimset. """
        claim = self.get_claim(number)

        # Need to remove punctuation, numbers and normal english stopwords?

        # Calculate term frequencies and normalise
        word_freqs = claim.get_word_freq(normalize=True)

        # Calculate IDF > log(total claims / no. of claims term appears in)
        tf_idf = [{
            'term': key,
            'tf': word_freqs[key],
            'tf_idf': word_freqs[key]*len(self.appears_in(key))
            }
            for key in word_freqs]
        # Sort list by tf_idf
        tf_idf = sorted(tf_idf, key=lambda k: k['tf_idf'], reverse=True)

        return tf_idf

    def independent_claims(self):
        """ Return independent claims. """
        return [c for c in self.claims if c.dependency == 0]

    def get_dependent_claims(self, claim):
        """ Return all claims that ultimately depend on 'claim'."""
        # claim_number = claim.number
        pass

    def get_root_claim_parent(self, claim_number):
        """ If claim is dependent, get independent claim it depends on. """
        claim = self.get_claim(claim_number)
        if claim.dependency == 0:
            return claim.number
        else:
            return self.get_root_claim_parent(claim.dependency)

    def print_dependencies(self):
        """ Output dependencies."""
        for c in self.claims:
            print(c.number, c.dependency)

    def get_dependency_groups(self):
        """ Return a list of sublists, where each sublist is a group
        of claims with common dependency, the independent claim
        being first in the set. """
        # Or a tree structure? - this will be recursive for chains of
        # dependencies
        # First level will be all claims with dependency = 0 then recursively
        # navigate dependencies
        root_list = [
            (claim.number, self.get_root_claim_parent(claim.number))
            for claim in self.claims
            ]
        claim_groups = {}
        for n, d in root_list:
            if d not in claim_groups.keys():
                claim_groups[d] = []
            else:
                claim_groups[d].append(n)
        return claim_groups

    # to print
    # for k in sorted(claim_groups.keys()):
    #   print(k, claim_groups[k])

    def get_entities(self):
        """ Determine a set of unique noun phrases over the claimset."""
        # Do we actually want to do this for sets of claims with common
        # dependencies?
        for claim in self.claims:
            # Build an initial dictionary
            pass

