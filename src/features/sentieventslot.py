
import sys
import math
import os
import cdb
import csv
import collections

def _tsvToDict(fn, conv):
    return dict([conv(row) for row in csv.reader(open(fn), delimiter="\t") if None != conv(row)])


class sentieventslot_t:
    def __init__(self, fn):
        self.db = collections.defaultdict(list)
        genre   = None

        for row in csv.reader(open(fn), delimiter="\t"):
            if 0 == len(row) or row[0].startswith("#"):
                continue

            if row[0].startswith(":"):
                genre = row[0][1:]
                continue

            if 2 == len(row):
                self.db[(row[0] + "-v", row[1])] += [genre]
                self.db[row[0] + "-v"] += [(row[1], genre)]


    def getArgPol(self, v, r):
        return self.db.get((v, r), [])


    def getPol(self, v):
        return self.db.get(v, [])


    def getRefRel(self, r):
        if "nsubj" != r:
            return "nsubj"

        return "dobj"

    def shouldBeRemoved(self, v, r):
        return "yes" if self.db.has_key(("hit", v, r)) else "unknown"

    def calcHurting(self, v, r):
        if "nsubjpass" == r:
            r = "dobj"

        if None != self.dbHurtingHealing.get((v, r, -1)):
            return "negative"

        if None != self.dbHurtingHealing.get((v, r, 1)):
            return "positive"

        return "neutral"


    def calc(self, v, r):
        sp, sn = self.db.get((v, r, 1), 0), self.db.get((v, r, -1), 0)

        if sp > sn: return "positive"
        if sp < sn: return "negative"

        return "neutral"
