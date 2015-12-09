
import sys
import math
import os
import cdb
import csv
import collections

def _tsvToDict(fn, conv):
    return dict([conv(row) for row in csv.reader(open(fn), delimiter="\t") if None != conv(row)])


class sentieventslot_t:
    def __init__(self, fn, fnHurting, fnHealing, fnRespect, fnRemove):
        self.dbHurtingHealing = collections.defaultdict(int)
        self.dbRespect        = _tsvToDict(fnRespect, lambda row: [((row[1] + "-v", row[0]), None), None][1 if row[0] == "0" else 0] )
        self.dbRemove        = _tsvToDict(fnRemove, lambda row: [((row[1] + "-v", row[0]), None), None][1 if row[0] == "0" else 0] )

        for ln in open(fnHurting):
            ln = ln.strip().split(":")

            if "1" != ln[0]:
                continue

            self.dbHurtingHealing[("%s-v" % ln[1], "dobj", -1)] = 1

        for ln in open(fnHealing):
            ln = ln.strip().split(":")

            if "1" != ln[0]:
                continue

            self.dbHurtingHealing[("%s-v" % ln[1], "dobj", 1)] = 1

        self.db = collections.defaultdict(int)

        for row in csv.reader(open(fn), delimiter="\t"):
            if row[6] != "1": continue

            self.db[(row[1], row[2], 1)] += int(row[0])
            self.db[(row[1], row[4], -1)] += int(row[0])


    def isRespected(self, v, r):
        return "yes" if self.dbRespect.has_key((v, r)) else "unknown"

    def shouldBeRemoved(self, v, r):
        return "yes" if self.dbRemove.has_key((v, r)) else "unknown"
        
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
