
import sys
import math
import os
import cdb
import csv
import collections

def _tsvToDict(fn, conv):
    return dict([conv(row) for row in csv.reader(open(fn), delimiter="\t") if None != conv(row)])


def _mtsvToDict(fn):
    d = {}

    for row in csv.reader(open(fn), delimiter="\t"):
        for ent in row[2].split(","):
            if "+Effect" == row[1]: d[ent] = "p"
            if "-Effect" == row[1]: d[ent] = "n"

    return d


def _read(fn, val):
    return dict([(ln.strip(), val) for ln in open(fn)])


class sentieventslot_t:
    def __init__(self, fn, di_ppv = "/home/naoya-i/dict/goyal13_PPV", fn_ewn = "/home/naoya-i/dict/effectwordnet/merged.tff"):

        #
        # Read Goyal 13 et al.'s PPV lexicon.
        self.ppv = _read(os.path.join(di_ppv, "KindAgentRatio1"), "p")
        self.ppv.update(_read(os.path.join(di_ppv, "EvilAgentRatio1"), "n"))
        self.ppv.update(_read(os.path.join(di_ppv, "PosBasilisk"), "p"))
        self.ppv.update(_read(os.path.join(di_ppv, "NegBasilisk"), "n"))

        self.ewn = _mtsvToDict(fn_ewn)

        self.db = collections.defaultdict(list)
        genre   = None

        for row in csv.reader(open(fn), delimiter="\t"):
            if 0 == len(row) or row[0].startswith("#"):
                continue

            if row[0].startswith(":"):
                genre = row[0][1:]
                continue

            if 2 == len(row):
                self.db[(row[0], row[1])] += [genre]
                self.db[row[0]] += [(genre, row[1])]


    def getFineGrainedAS(self, v):
        return self.db.get(v, [])


    def getArgPol(self, v, r):
        return self.db.get((v, r), [])


    def getPol(self, v):
        return self.db.get(v, [])


    def getG13Pol(self, v):
        return self.ppv.get(v, [])


    def getC14Pol(self, v):
        return self.ewn.get(v, [])


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
