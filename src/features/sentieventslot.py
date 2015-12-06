
import sys
import math
import os
import cdb
import csv
import collections

class sentieventslot_t:
    def __init__(self, fn):
        self.db = collections.defaultdict(int)

        for row in csv.reader(open(fn), delimiter="\t"):
            if row[6] != "1": continue

            self.db[(row[1], row[2], 1)] += int(row[0])
            self.db[(row[1], row[4], -1)] += int(row[0])


    def calc(self, v, r):
        sp, sn = self.db.get((v, r, 1), 0), self.db.get((v, r, -1), 0)

        if sp > sn: return "positive"
        if sp < sn: return "negative"

        return "neutral"
